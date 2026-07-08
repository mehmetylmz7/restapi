from flask import Flask, jsonify, request, render_template, Response
from flask_cors import CORS
from services.customer_service import get_customers, create_customer
from services.product_service import get_products, create_product
from services.payment_service import create_payment_intent, get_payment_intents, create_payment_pdf, get_payment_pdf
from services.refund_service import create_refund, get_refunds
from services.file_service import upload_dispute_evidence, list_uploaded_files
from database import init_pool

# Uygulama başlarken bağlantı havuzunu oluştur (bir kez çalışır)
init_pool(pool_size=5)

app = Flask(__name__)
CORS(app)

# 1. ESKİ JSON DÖNDÜREN ROTAYI SİLDİK VE YENİSİNİ BURAYA ALDIK
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/customers", methods=["GET"])
def api_customers():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_customers(limit=limit, starting_after=starting_after)
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
        data["description"]
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)