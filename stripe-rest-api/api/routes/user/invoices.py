from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.invoice_service import (
    get_local_invoices,
    get_local_invoice_pdf,
    save_invoices_to_db,
)

user_invoices_bp = Blueprint("user_invoices", __name__, url_prefix="/api/user/invoices")


@user_invoices_bp.route("", methods=["GET"])
@jwt_required()
def api_user_get_invoices():
    customer_id = get_jwt_identity()
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after")
    created_gte = request.args.get("created_gte")
    created_lte = request.args.get("created_lte")
    result = get_local_invoices(
        customer_id=customer_id,
        limit=limit,
        starting_after=starting_after,
        created_gte=created_gte,
        created_lte=created_lte,
    )
    return jsonify(result)


@user_invoices_bp.route("/<invoice_id>/pdf", methods=["GET"])
@jwt_required()
def api_user_get_invoice_pdf(invoice_id):
    customer_id = get_jwt_identity()
    pdf_bytes = get_local_invoice_pdf(invoice_id, customer_id=customer_id)
    if pdf_bytes is None:
        return jsonify({"error": "Fatura PDF'i bulunamadı veya yetkisiz işlem."}), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=fatura_{invoice_id}.pdf"},
    )


@user_invoices_bp.route("/save_to_db", methods=["POST"])
@jwt_required()
def api_user_save_invoices_to_db():
    customer_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    created_gte = data.get("created_gte") or request.args.get("created_gte")
    created_lte = data.get("created_lte") or request.args.get("created_lte")
    result = save_invoices_to_db(
        customer_id=customer_id,
        created_gte=created_gte,
        created_lte=created_lte,
    )
    return jsonify(result)
