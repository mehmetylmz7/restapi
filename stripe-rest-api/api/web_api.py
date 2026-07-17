from flask import Flask, jsonify, request, render_template, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from core.config import JWT_SECRET_KEY
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
from core.database import init_pool, get_db
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

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
jwt = JWTManager(app)
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


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "E-posta ve şifre zorunludur."}), 400
        
    email = data["email"].strip().lower()
    password = data["password"]
    name = data.get("name", "").strip()
    
    # Kullanıcı zaten var mı kontrol et
    try:
        with get_db() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"error": "Bu e-posta adresiyle zaten kayıtlı bir kullanıcı var."}), 400
    except Exception as e:
        return jsonify({"error": f"Veritabanı hatası: {str(e)}"}), 500

    # Stripe üzerinde müşteri oluştur
    try:
        stripe_customer = create_customer(name=name or email, email=email)
        if not stripe_customer or not stripe_customer.get("id"):
            return jsonify({"error": "Stripe üzerinde müşteri oluşturulamadı."}), 500
        stripe_customer_id = stripe_customer["id"]
    except Exception as e:
        return jsonify({"error": f"Stripe entegrasyon hatası: {str(e)}"}), 500

    # Şifreyi hash'le ve DB'ye kaydet
    password_hash = generate_password_hash(password)
    try:
        with get_db() as cursor:
            cursor.execute(
                "INSERT INTO users (email, password_hash, stripe_customer_id) VALUES (%s, %s, %s)",
                (email, password_hash, stripe_customer_id)
            )
        return jsonify({"message": "Kullanıcı başarıyla kaydedildi.", "stripe_customer_id": stripe_customer_id}), 201
    except Exception as e:
        return jsonify({"error": f"Veritabanına kaydedilirken hata oluştu: {str(e)}"}), 500


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "E-posta ve şifre zorunludur."}), 400
        
    email = data["email"].strip().lower()
    password = data["password"]
    
    try:
        with get_db() as cursor:
            cursor.execute("SELECT password_hash, stripe_customer_id FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            
        if not row:
            return jsonify({"error": "Geçersiz e-posta veya şifre."}), 401
            
        password_hash, stripe_customer_id = row[0], row[1]
        
        if not check_password_hash(password_hash, password):
            return jsonify({"error": "Geçersiz e-posta veya şifre."}), 401
            
        # JWT access token oluştur (identity olarak stripe_customer_id kullanıyoruz)
        access_token = create_access_token(identity=stripe_customer_id)
        return jsonify({
            "access_token": access_token,
            "stripe_customer_id": stripe_customer_id,
            "email": email
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Giriş hatası: {str(e)}"}), 500


@app.route("/api/customers/me", methods=["GET"])
@jwt_required()
def api_customer_me():
    customer_id = get_jwt_identity()
    from services.customer_service import get_customer
    customer = get_customer(customer_id)
    if not customer:
        return jsonify({"error": "Müşteri profili bulunamadı."}), 404
    return jsonify(customer)


@app.route("/api/customers", methods=["GET"])
@jwt_required()
def api_customers():
    # Güvenlik amacıyla normal müşteriler diğer müşterileri listeleyemez, sadece admin yetkilendirmesi gibi düşünülebilir
    # Ancak basitlik için JWT zorunlu tutup listelemeyi de koruyoruz.
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
@jwt_required()
def api_payments():
    customer_id = get_jwt_identity()
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_payment_intents(limit=limit, starting_after=starting_after, customer_id=customer_id)
    return jsonify(result)


@app.route("/api/payments", methods=["POST"])
@jwt_required()
def api_create_payment():
    customer_id = get_jwt_identity()
    data = request.get_json()
    payment = create_payment_intent(
        customer_id=customer_id,
        amount=int(float(data["amount"]) * 100),
        currency=data.get("currency", "usd"),
        order_id=data.get("order_id"),
    )
    return jsonify(payment), 201


@app.route("/api/refunds", methods=["GET"])
@jwt_required()
def api_refunds():
    customer_id = get_jwt_identity()
    payment_intent_id = request.args.get("payment_intent_id")
    if not payment_intent_id:
        return jsonify({"error": "payment_intent_id parametresi zorunludur."}), 400
        
    from services.payment_service import get_payment_intent
    payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
    if not payment:
        return jsonify({"error": "Yetkisiz işlem veya ödeme bulunamadı."}), 403

    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_refunds(payment_intent_id=payment_intent_id, limit=limit, starting_after=starting_after)
    return jsonify(result)


@app.route("/api/refunds", methods=["POST"])
@jwt_required()
def api_create_refund():
    customer_id = get_jwt_identity()
    data = request.get_json()
    payment_intent_id = data["payment_intent_id"]
    
    from services.payment_service import get_payment_intent
    payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
    if not payment:
        return jsonify({"error": "Yetkisiz işlem veya ödeme bulunamadı."}), 403

    amount = data.get("amount")
    refund = create_refund(
        payment_intent_id=payment_intent_id,
        amount=int(float(amount) * 100) if amount else None,
        reason=data.get("reason"),
    )
    return jsonify(refund), 201


# 2. APP.RUN BLOĞU KESİNLİKLE EN ALTTA OLMALI


@app.route("/api/payments/<payment_id>/pdf", methods=["POST"])
@jwt_required()
def api_create_payment_pdf(payment_id):
    """PDF üretir ve LONGBLOB'a kaydeder.

    Query param:
        force=true  → Mevcut PDF varsa üzerine yazar.
        force=false (varsayılan) → Mevcut PDF varsa 409 döner.
    """
    customer_id = get_jwt_identity()
    force = request.args.get("force", "false").lower() == "true"

    # Mevcut PDF var mı kontrol et (force=false ise)
    if not force and pdf_exists(payment_id, customer_id=customer_id):
        return jsonify({"already_exists": True, "payment_id": payment_id}), 409

    pdf_bytes = create_payment_pdf(payment_id, force=force, customer_id=customer_id)
    if pdf_bytes is None:
        return jsonify({"error": "PDF oluşturulamadı veya yetkisiz işlem."}), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=odeme_{payment_id}.pdf"},
    )


@app.route("/api/payments/<payment_id>/pdf", methods=["GET"])
@jwt_required()
def api_get_payment_pdf(payment_id):
    """Daha önce oluşturulmuş PDF'i DB'den okuyup döner."""
    customer_id = get_jwt_identity()
    pdf_bytes = get_payment_pdf(payment_id, customer_id=customer_id)
    if pdf_bytes is None:
        return jsonify({"error": "PDF bulunamadı veya yetkisiz işlem."}), 404
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
@jwt_required()
def api_invoice_preview():
    customer_id = get_jwt_identity()
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "Ürün bilgileri zorunludur."}), 400

    preview = preview_invoice(
        customer_id=customer_id,
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
@jwt_required()
def api_create_invoice():
    customer_id = get_jwt_identity()
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "Ürün bilgileri zorunludur."}), 400

    try:
        invoice = create_and_finalize_invoice(
            customer_id=customer_id,
            currency=data.get("currency", "usd"),
            items=data["items"],
        )
        return jsonify(invoice), 201
    except Exception as e:
        return jsonify(
            {"error": f"Fatura oluşturma ve kesinleştirme başarısız: {str(e)}"}
        ), 500


@app.route("/api/invoices", methods=["GET"])
@jwt_required()
def api_get_invoices():
    customer_id = get_jwt_identity()
    limit = int(request.args.get("limit", 50))
    invoices = get_local_invoices(customer_id=customer_id, limit=limit)
    return jsonify({"data": invoices})


@app.route("/api/invoices/<invoice_id>/pdf", methods=["GET"])
@jwt_required()
def api_get_invoice_pdf(invoice_id):
    customer_id = get_jwt_identity()
    pdf_bytes = get_local_invoice_pdf(invoice_id, customer_id=customer_id)
    if pdf_bytes is None:
        return jsonify(
            {"error": "Fatura PDF'i bulunamadı veya yetkisiz işlem."}
        ), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=fatura_{invoice_id}.pdf"},
    )


