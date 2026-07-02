from flask import Flask, jsonify,request
from flask_cors import CORS
from services.customer_service import get_customers,create_customer
from services.product_service import get_products,create_product
from services.payment_service import create_payment_intent, get_payment_intents
from services.refund_service import create_refund, get_refunds

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return {
        "message": "Stripe REST API Backend is running!"
    }


@app.route("/api/customers", methods=["GET"])
def api_customers():

    customers = get_customers()

    return jsonify(customers)

@app.route("/api/customers", methods=["POST"])
def api_create_customer():

    data=request.get_json()

    customer = create_customer(
        data["name"],
        data["email"],
        )
    
    return jsonify(customer), 201

@app.route("/api/products", methods=["GET"])
def api_products():
    products = get_products()

    return jsonify(products)

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

    payments = get_payment_intents()

    return jsonify(payments)

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

    refunds=get_refunds()

    return jsonify(refunds)

if __name__ == "__main__":
    app.run(debug=True, port=5000)