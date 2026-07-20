from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.payment_service import get_payment_intent
from services.refund_service import create_refund, get_refunds

user_refunds_bp = Blueprint("user_refunds", __name__, url_prefix="/api/user/refunds")


@user_refunds_bp.route("", methods=["GET"])
@jwt_required()
def api_user_refunds():
    customer_id = get_jwt_identity()
    payment_intent_id = request.args.get("payment_intent_id")
    if not payment_intent_id:
        return jsonify({"error": "payment_intent_id parametresi zorunludur."}), 400

    payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
    if not payment:
        return jsonify({"error": "Yetkisiz işlem veya ödeme bulunamadı."}), 403

    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_refunds(payment_intent_id=payment_intent_id, limit=limit, starting_after=starting_after)
    return jsonify(result)


@user_refunds_bp.route("", methods=["POST"])
@jwt_required()
def api_user_create_refund():
    customer_id = get_jwt_identity()
    data = request.get_json()
    payment_intent_id = data["payment_intent_id"]

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
