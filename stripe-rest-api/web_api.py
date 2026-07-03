from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from services.customer_service import get_customers, create_customer
from services.product_service import get_products, create_product
from services.payment_service import create_payment_intent, get_payment_intents
from services.refund_service import create_refund, get_refunds
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
if __name__ == "__main__":
    app.run(debug=True, port=5000)