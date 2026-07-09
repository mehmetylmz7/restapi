from flask import Flask, jsonify, request, render_template, Response
from flask_cors import CORS
import json
import csv
import time
from services.customer_service import get_customers, create_customer
from services.product_service import get_products, create_product
from services.payment_service import create_payment_intent, get_payment_intents, create_payment_pdf, get_payment_pdf
from services.refund_service import create_refund, get_refunds
from services.file_service import upload_dispute_evidence, list_uploaded_files
from services.export_service import export_to_json, export_to_csv, _fetch_all
from database import init_pool, get_db

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
        created_lte=created_lte
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
        data["name"],
        data.get("description"),
        price=data.get("price")
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
        order_id=data.get("order_id")
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
        reason=data.get("reason")
    )
    return jsonify(refund), 201

# 2. APP.RUN BLOĞU KESİNLİKLE EN ALTTA OLMALI

# ── PDF Endpoint'leri ──────────────────────────────────────────────────────
@app.route("/api/payments/<payment_id>/pdf", methods=["POST"])
def api_create_payment_pdf(payment_id):
    """Ödeme için PDF üretir (bellekte), LONGBLOB'a kaydeder, tarayıcıya döner."""
    pdf_bytes = create_payment_pdf(payment_id)
    if pdf_bytes is None:
        return jsonify({"error": "PDF oluşturulamadı. Ödeme ID'yi kontrol edin."}), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=odeme_{payment_id}.pdf"}
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
        headers={"Content-Disposition": f"inline; filename=odeme_{payment_id}.pdf"}
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
        payment_intent_id=payment_intent_id,
        file_bytes=f.read(),
        filename=f.filename
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
    body: { "resource": "customers", "format": "json", "limit": "100" }
    limit: '100' = son 100 kayıt (hızlı), 'all' = tüm kayıtlar (yavaş)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body bekleniyor."}), 400

    resource  = data.get("resource", "")
    fmt       = data.get("format", "json")
    limit_val = data.get("limit", "100")  # '100' veya 'all'

    valid_resources = ("customers", "products", "payments", "refunds")
    if resource not in valid_resources:
        return jsonify({"error": f"Geçersiz kaynak. Geçerli: {valid_resources}"}), 400
    if fmt not in ("json", "csv"):
        return jsonify({"error": "Geçersiz format. 'json' veya 'csv' kullanın."}), 400

    fetch_all = (limit_val == "all")

    try:
        if fmt == "json":
            content  = export_to_json(resource, fetch_all=fetch_all)
            mimetype = "application/json"
            filename = f"{resource}.json"
        else:
            content  = export_to_csv(resource, fetch_all=fetch_all)
            mimetype = "text/csv; charset=utf-8"
            filename = f"{resource}.csv"
    except Exception as e:
        return jsonify({"error": f"Export hatası: {str(e)}"}), 500

    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/import", methods=["POST"])
def api_import():
    """Müşteri verilerini JSON veya CSV olarak alır ve toplu içe aktarır."""
    fmt = request.form.get("format", "json")
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]
    filename = file.filename.lower()

    # 1. Dosya Uzantısı Kontrolü
    if fmt == "json":
        if not filename.endswith(".json"):
            return jsonify({"error": "JSON formatı seçildi ancak yüklenen dosya .json uzantılı değil."}), 400
    elif fmt == "csv":
        if not filename.endswith(".csv"):
            return jsonify({"error": "CSV formatı seçildi ancak yüklenen dosya .csv uzantılı değil."}), 400
    else:
        return jsonify({"error": "Geçersiz format seçimi."}), 400

    file_bytes = file.read()
    records = []

    # 2. Veri Ayrıştırma ve Şema/Format Kontrolü
    if fmt == "json":
        try:
            content = file_bytes.decode("utf-8")
            data = json.loads(content)

            if not isinstance(data, list):
                return jsonify({"error": "JSON dosyası bir liste (array) olmalıdır."}), 400

            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    return jsonify({"error": f"JSON listesinin {idx+1}. elemanı bir obje olmalıdır."}), 400
                if "name" not in item or "email" not in item:
                    return jsonify({"error": f"JSON objesi 'name' ve 'email' alanlarını içermelidir. (Hata konumu: {idx+1}. eleman)"}), 400
                records.append({
                    "name": str(item["name"]).strip(),
                    "email": str(item["email"]).strip()
                })
        except json.JSONDecodeError:
            return jsonify({"error": "JSON dosyası geçerli bir JSON formatında değil."}), 400
        except Exception as e:
            return jsonify({"error": f"JSON okuma hatası: {str(e)}"}), 400

    elif fmt == "csv":
        try:
            import io
            content = file_bytes.decode("utf-8-sig")
            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                return jsonify({"error": "CSV dosyasının başlık satırı bulunamadı."}), 400

            headers = [h.strip() for h in reader.fieldnames]
            if "name" not in headers or "email" not in headers:
                return jsonify({"error": "CSV dosyasında 'name' ve 'email' başlıkları bulunmalıdır."}), 400

            for idx, row in enumerate(reader):
                row_clean = {k.strip(): v for k, v in row.items() if k is not None}
                name = row_clean.get("name")
                email = row_clean.get("email")

                if name is None or email is None:
                    return jsonify({"error": f"CSV dosyasının {idx+2}. satırında 'name' veya 'email' alanı eksik."}), 400

                records.append({
                    "name": str(name).strip(),
                    "email": str(email).strip()
                })
        except Exception as e:
            return jsonify({"error": f"CSV okuma hatası: {str(e)}"}), 400

    # 3. Stripe'a Aktarım İşlemi
    results = {"success": 0, "skipped": 0, "failed": 0, "failed_list": []}

    for record in records:
        name = record["name"]
        email = record["email"]

        if not name or not email:
            results["skipped"] += 1
            continue

        try:
            time.sleep(0.05)  # Rate limit koruması için kısa bekleme
            customer = create_customer(name=name, email=email)
            if customer and customer.get("id"):
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_list"].append({"name": name, "email": email, "reason": "Stripe did not return customer ID"})
        except Exception as e:
            results["failed"] += 1
            results["failed_list"].append({"name": name, "email": email, "reason": str(e)})

    return jsonify({
        "message": "İçe aktarım tamamlandı.",
        "stats": results
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)