from flask import Blueprint, jsonify, request, Response
from services.payment_service import (
    create_payment_intent,
    get_payment_intents,
    create_payment_pdf,
    get_payment_pdf,
    pdf_exists,
)

admin_payments_bp = Blueprint("admin_payments", __name__, url_prefix="/api/payments")


@admin_payments_bp.route("", methods=["GET"])
def api_payments():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_payment_intents(limit=limit, starting_after=starting_after)
    return jsonify(result)


@admin_payments_bp.route("", methods=["POST"])
def api_create_payment():
    data = request.get_json()
    payment = create_payment_intent(
        customer_id=data["customer_id"],
        amount=int(float(data["amount"]) * 100),
        currency=data.get("currency", "usd"),
        order_id=data.get("order_id"),
    )
    return jsonify(payment), 201


@admin_payments_bp.route("/<payment_id>/pdf", methods=["POST"])
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


@admin_payments_bp.route("/<payment_id>/pdf", methods=["GET"])
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
