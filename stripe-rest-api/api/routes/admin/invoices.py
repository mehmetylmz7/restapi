from flask import Blueprint, jsonify, request, Response
from services.invoice_service import (
    preview_invoice,
    create_and_finalize_invoice,
    get_local_invoices,
    get_local_invoice_pdf,
)

admin_invoices_bp = Blueprint("admin_invoices", __name__, url_prefix="/api/invoices")


@admin_invoices_bp.route("/preview", methods=["POST"])
def api_invoice_preview():
    data = request.get_json()
    if not data or "customer" not in data or "items" not in data:
        return jsonify({"error": "Müşteri ve ürün bilgileri zorunludur."}), 400

    preview = preview_invoice(
        customer_id=data["customer"],
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


@admin_invoices_bp.route("", methods=["POST"])
def api_create_invoice():
    data = request.get_json()
    if not data or "customer" not in data or "items" not in data:
        return jsonify({"error": "Müşteri ve ürün bilgileri zorunludur."}), 400

    try:
        invoice = create_and_finalize_invoice(
            customer_id=data["customer"],
            currency=data.get("currency", "usd"),
            items=data["items"],
        )
        return jsonify(invoice), 201
    except Exception as e:
        return jsonify(
            {"error": f"Fatura oluşturma ve kesinleştirme başarısız: {str(e)}"}
        ), 500


@admin_invoices_bp.route("", methods=["GET"])
def api_get_invoices():
    limit = int(request.args.get("limit", 50))
    invoices = get_local_invoices(limit=limit)
    return jsonify({"data": invoices})


@admin_invoices_bp.route("/<invoice_id>/pdf", methods=["GET"])
def api_get_invoice_pdf(invoice_id):
    pdf_bytes = get_local_invoice_pdf(invoice_id)
    if pdf_bytes is None:
        return jsonify(
            {"error": "Fatura PDF'i bulunamadı veya diskten okunamadı."}
        ), 404
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=fatura_{invoice_id}.pdf"},
    )
