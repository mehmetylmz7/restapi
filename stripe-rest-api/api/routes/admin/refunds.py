from flask import Blueprint, jsonify, request
from services.refund_service import create_refund, get_refunds

admin_refunds_bp = Blueprint("admin_refunds", __name__, url_prefix="/api/refunds")


@admin_refunds_bp.route("", methods=["GET"])
def api_refunds():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    payment_intent_id = request.args.get("payment_intent_id")
    result = get_refunds(payment_intent_id=payment_intent_id, limit=limit, starting_after=starting_after)
    return jsonify(result)


@admin_refunds_bp.route("", methods=["POST"])
def api_create_refund():
    data = request.get_json()
    amount = data.get("amount")
    refund = create_refund(
        payment_intent_id=data["payment_intent_id"],
        amount=int(float(amount) * 100) if amount else None,
        reason=data.get("reason"),
    )
    return jsonify(refund), 201
