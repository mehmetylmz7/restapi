from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.payment_service import (
    create_payment_intent,
    get_payment_intents,
    create_payment_pdf,
    get_payment_pdf,
    pdf_exists,
)

user_payments_bp = Blueprint("user_payments", __name__, url_prefix="/api/user/payments")


@user_payments_bp.route("", methods=["GET"])
@jwt_required()
def api_user_payments():
    customer_id = get_jwt_identity()
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_payment_intents(limit=limit, starting_after=starting_after, customer_id=customer_id)
    return jsonify(result)


@user_payments_bp.route("", methods=["POST"])
@jwt_required()
def api_user_create_payment():
    customer_id = get_jwt_identity()
    data = request.get_json()
    if not data or "amount" not in data:
        return jsonify({"error": "Tutar zorunludur."}), 400
    payment = create_payment_intent(
        customer_id=customer_id,
        amount=int(float(data["amount"]) * 100),
        currency=data.get("currency", "usd"),
        order_id=data.get("order_id"),
    )
    return jsonify(payment), 201


@user_payments_bp.route("/<payment_id>/pdf", methods=["POST"])
@jwt_required()
def api_user_create_payment_pdf(payment_id):
    customer_id = get_jwt_identity()
    force = request.args.get("force", "false").lower() == "true"
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


@user_payments_bp.route("/<payment_id>/pdf", methods=["GET"])
@jwt_required()
def api_user_get_payment_pdf(payment_id):
    customer_id = get_jwt_identity()
    pdf_bytes = get_payment_pdf(payment_id, customer_id=customer_id)
    if pdf_bytes is None:
        return jsonify({"error": "PDF bulunamadı veya yetkisiz işlem."}), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=odeme_{payment_id}.pdf"},
    )
