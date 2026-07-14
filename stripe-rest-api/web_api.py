from flask import Flask, jsonify, request, render_template, Response
from flask_cors import CORS
import json
import time
from services.customer_service import get_customers, create_customer
from services.product_service import get_products, create_product
from services.payment_service import (
    create_payment_intent,
    get_payment_intents,
    create_payment_pdf,
    get_payment_pdf,
    pdf_exists,
)
from services.refund_service import create_refund, get_refunds
from services.file_service import upload_dispute_evidence, list_uploaded_files
from services.export_service import export_data, _fetch_all
from database import init_pool
from services.import_service import (
    parse_file,
    infer_data_types,
    validate_and_map_records,
    execute_import_record,
)
from services.invoice_service import (
    preview_invoice,
    create_and_finalize_invoice,
    get_local_invoices,
    get_local_invoice_pdf,
)

# Uygulama başlarken bağlantı havuzunu oluştur (bir kez çalışır)
init_pool(pool_size=5)

app = Flask(__name__)
CORS(app)


@app.route("/api/stats", methods=["GET"])
def api_stats():
    stats = {"customers": 0, "payments": 0, "refunds": 0, "products": 0}
    try:
        # Fetch counts from Stripe API (sayfa sayfa dolaşılarak)
        stats["customers"] = len(_fetch_all("customers"))
        stats["payments"] = len(_fetch_all("payments"))
        stats["refunds"] = len(_fetch_all("refunds"))
        stats["products"] = len(_fetch_all("products"))
    except Exception as e:
        print(f"Stats fetch error: {e}")
    return jsonify(stats)


# deneme
# 1. ESKİ JSON DÖNDÜREN ROTAYI SİLDİK VE YENİSİNİ BURAYA ALDIK
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/customers", methods=["GET"])
def api_customers():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    created_gte = request.args.get("created_gte", None)
    created_lte = request.args.get("created_lte", None)
    result = get_customers(
        limit=limit,
        starting_after=starting_after,
        created_gte=created_gte,
        created_lte=created_lte,
    )
    return jsonify(result)


@app.route("/api/customers", methods=["POST"])
def api_create_customer():
    data = request.get_json()
    customer = create_customer(
        data["name"],
        data["email"],
    )
    return jsonify(customer), 201


@app.route("/api/products", methods=["GET"])
def api_products():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_products(limit=limit, starting_after=starting_after)
    return jsonify(result)


@app.route("/api/products", methods=["POST"])
def api_create_product():
    data = request.get_json()
    product = create_product(
        data["name"], data.get("description"), price=data.get("price")
    )
    return jsonify(product), 201


@app.route("/api/payments", methods=["GET"])
def api_payments():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_payment_intents(limit=limit, starting_after=starting_after)
    return jsonify(result)


@app.route("/api/payments", methods=["POST"])
def api_create_payment():
    data = request.get_json()
    payment = create_payment_intent(
        customer_id=data["customer_id"],
        amount=int(float(data["amount"]) * 100),
        currency=data.get("currency", "usd"),
        order_id=data.get("order_id"),
    )
    return jsonify(payment), 201


@app.route("/api/refunds", methods=["GET"])
def api_refunds():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_refunds(limit=limit, starting_after=starting_after)
    return jsonify(result)


@app.route("/api/refunds", methods=["POST"])
def api_create_refund():
    data = request.get_json()
    amount = data.get("amount")
    refund = create_refund(
        payment_intent_id=data["payment_intent_id"],
        amount=int(float(amount) * 100) if amount else None,
        reason=data.get("reason"),
    )
    return jsonify(refund), 201


# 2. APP.RUN BLOĞU KESİNLİKLE EN ALTTA OLMALI


@app.route("/api/payments/<payment_id>/pdf", methods=["POST"])
def api_create_payment_pdf(payment_id):
    """PDF üretir ve LONGBLOB'a kaydeder.

    Query param:
        force=true  → Mevcut PDF varsa üzerine yazar.
        force=false (varsayılan) → Mevcut PDF varsa 409 döner.
    """
    force = request.args.get("force", "false").lower() == "true"

    # Mevcut PDF var mı kontrol et (force=false ise)
    if not force and pdf_exists(payment_id):
        return jsonify({"already_exists": True, "payment_id": payment_id}), 409

    pdf_bytes = create_payment_pdf(payment_id, force=force)
    if pdf_bytes is None:
        return jsonify({"error": "PDF oluşturulamadı. Ödeme ID'yi kontrol edin."}), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=odeme_{payment_id}.pdf"},
    )


@app.route("/api/payments/<payment_id>/pdf", methods=["GET"])
def api_get_payment_pdf(payment_id):
    """Daha önce oluşturulmuş PDF'i DB'den okuyup döner."""
    pdf_bytes = get_payment_pdf(payment_id)
    if pdf_bytes is None:
        return jsonify({"error": "PDF bulunamadı. Önce PDF Oluştur'u kullanın."}), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=odeme_{payment_id}.pdf"},
    )


# ── Stripe Files Endpoint'leri ─────────────────────────────────────────────
@app.route("/api/files/upload", methods=["POST"])
def api_upload_file():
    """PDF'i multipart/form-data olarak alır, Stripe Files API'ye yükler."""
    payment_intent_id = request.form.get("payment_intent_id", "").strip()
    if "file" not in request.files:
        return jsonify({"error": "Dosya bulunamadı. 'file' alanı eksik."}), 400

    f = request.files["file"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Sadece PDF dosyaları kabul edilmektedir."}), 400

    file_obj = upload_dispute_evidence(
        payment_intent_id=payment_intent_id, file_bytes=f.read(), filename=f.filename
    )
    if file_obj is None:
        return jsonify({"error": "Stripe'a yükleme başarısız."}), 500

    return jsonify(file_obj), 201


@app.route("/api/files", methods=["GET"])
def api_list_files():
    """DB'deki yüklü dosyaları listeler."""
    payment_id = request.args.get("payment_intent_id")
    files = list_uploaded_files(payment_id)
    # datetime nesnelerini string'e çevir
    for f in files:
        if "olusturma_tarihi" in f and f["olusturma_tarihi"]:
            f["olusturma_tarihi"] = str(f["olusturma_tarihi"])
    return jsonify({"data": files})


# ── Export Endpoint'i ──────────────────────────────────────────────────────
@app.route("/api/export", methods=["POST"])
def api_export():
    """
    Stripe'tan veri çekip JSON veya CSV olarak tarayıcıya indirir.
    body: { "resource": "customers", "format": "json", "limit": "100", "created_gte": 1720000000, "created_lte": 1730000000, "fields": ["id", "name"] }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body bekleniyor."}), 400

    resource = data.get("resource", "")
    fmt = data.get("format", "json")
    limit_val = data.get("limit", "100")
    created_gte = data.get("created_gte")
    created_lte = data.get("created_lte")
    fields = data.get("fields")

    valid_resources = ("customers", "products", "payments", "refunds")
    if resource not in valid_resources:
        return jsonify({"error": f"Geçersiz kaynak. Geçerli: {valid_resources}"}), 400
    if fmt not in ("json", "csv"):
        return jsonify({"error": "Geçersiz format. 'json' veya 'csv' kullanın."}), 400

    try:
        content = export_data(
            resource=resource,
            fmt=fmt,
            limit_val=limit_val,
            created_gte=created_gte,
            created_lte=created_lte,
            fields=fields,
        )
        if fmt == "json":
            mimetype = "application/json"
            filename = f"{resource}.json"
        else:
            mimetype = "text/csv; charset=utf-8"
            filename = f"{resource}.csv"
    except Exception as e:
        return jsonify({"error": f"Export hatası: {str(e)}"}), 500

    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/import/analyze", methods=["POST"])
def api_import_analyze():
    """
    Yüklenen dosyayı okur, veri tiplerini analiz eder ve ilk 3 satırın önizlemesini döner.
    """
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]  # elimizde Flaskın FileStorage nesnesi var
    filename = file.filename  # name alinma sebebi json mi csv mi onu anlamak icin

    try:
        file_bytes = file.read()
        records = parse_file(file_bytes, filename)
        if not records:
            return jsonify({"error": "Dosya boş veya okunamadı."}), 400

        inferred_types = infer_data_types(records)
        preview = records[:3]

        return jsonify(
            {
                "filename": filename,
                "total_rows": len(records),
                "columns": list(inferred_types.keys()),
                "inferred_types": inferred_types,
                "preview": preview,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Dosya analiz hatası: {str(e)}"}), 400


@app.route("/api/import/preview", methods=["POST"])
def api_import_preview():
    """
    Dosyayı ve eşleştirme şemasını alır, geçerli/geçersiz kayıtları doğrular.
    """
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]
    target_model = request.form.get("model")
    mapping_str = request.form.get("mapping")

    if not target_model or not mapping_str:
        return jsonify({"error": "Model ve eşleştirme bilgisi zorunludur."}), 400

    try:
        mapping = json.loads(mapping_str)
        file_bytes = file.read()
        records = parse_file(file_bytes, file.filename)

        result = validate_and_map_records(records, target_model, mapping)
        return jsonify(
            {
                "total_records": len(records),
                "valid_count": len(result["valid"]),
                "invalid_count": len(result["invalid"]),
                "existing_count": len(result["existing"]),
                "valid": result["valid"][:10],  # Önizleme için ilk 10 adet geçerli
                "invalid": result["invalid"][:10],  # Önizleme için ilk 10 adet geçersiz
                "existing": result["existing"][:10],  # Önizleme için ilk 10 adet mevcut
            }
        )
    except Exception as e:
        return jsonify({"error": f"Önizleme oluşturma hatası: {str(e)}"}), 400


@app.route("/api/import/execute", methods=["POST"])
def api_import_execute():
    """
    Dosyayı ve eşleştirme şemasını alır, geçerli kayıtları Stripe ve veritabanına aktarır.
    """
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]
    target_model = request.form.get("model")
    mapping_str = request.form.get("mapping")

    if not target_model or not mapping_str:
        return jsonify({"error": "Model ve eşleştirme bilgisi zorunludur."}), 400

    try:
        mapping = json.loads(mapping_str)
        file_bytes = file.read()
        records = parse_file(file_bytes, file.filename)

        validation = validate_and_map_records(records, target_model, mapping)
        valid_records = validation["valid"]

        results = {"success": 0, "failed": 0, "failed_list": []}

        for item in valid_records:
            time.sleep(0.3)  # Rate limit koruması
            mapped_data = item["mapped"]
            res = execute_import_record(target_model, mapped_data)

            if res["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_list"].append(
                    {
                        "row_index": item["row_index"],
                        "mapped": mapped_data,
                        "reason": res["reason"],
                    }
                )

        # Geçersiz kayıtları da hata raporuna ekle
        for item in validation["invalid"]:
            results["failed"] += 1
            results["failed_list"].append(
                {
                    "row_index": item["row_index"],
                    "mapped": item["mapped"],
                    "reason": f"Doğrulama Hatası: {item['reason']}",
                }
            )

        return jsonify({"message": "Aktarım tamamlandı.", "stats": results})
    except Exception as e:
        return jsonify({"error": f"Aktarım hatası: {str(e)}"}), 400


# ── Fatura (Invoice) Endpoint'leri ─────────────────────────────────────────
@app.route("/api/invoices/preview", methods=["POST"])
def api_invoice_preview():
    data = request.get_json()
    if not data or "customer" not in data or "items" not in data:
        return jsonify({"error": "Müşteri ve ürün bilgileri zorunludur."}), 400

    preview = preview_invoice(
        customer_id=data["customer"],
        currency=data.get("currency", "usd"),
        items=data["items"],
    )
    if preview is None:
        return jsonify(
            {
                "error": "Fatura önizlemesi oluşturulamadı. Stripe API hatası veya uyumsuz para birimi."
            }
        ), 500
    return jsonify(preview)


@app.route("/api/invoices", methods=["POST"])
def api_create_invoice():
    data = request.get_json()
    if not data or "customer" not in data or "items" not in data:
        return jsonify({"error": "Müşteri ve ürün bilgileri zorunludur."}), 400

    try:
        invoice = create_and_finalize_invoice(
            customer_id=data["customer"],
            currency=data.get("currency", "usd"),
            items=data["items"],
        )
        return jsonify(invoice), 201
    except Exception as e:
        return jsonify(
            {"error": f"Fatura oluşturma ve kesinleştirme başarısız: {str(e)}"}
        ), 500


@app.route("/api/invoices", methods=["GET"])
def api_get_invoices():
    limit = int(request.args.get("limit", 50))
    invoices = get_local_invoices(limit=limit)
    return jsonify({"data": invoices})


@app.route("/api/invoices/<invoice_id>/pdf", methods=["GET"])
def api_get_invoice_pdf(invoice_id):
    pdf_bytes = get_local_invoice_pdf(invoice_id)
    if pdf_bytes is None:
        return jsonify(
            {"error": "Fatura PDF'i bulunamadı veya diskten okunamadı."}
        ), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=fatura_{invoice_id}.pdf"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
