from flask import Blueprint, jsonify, request
from services.customer_service import get_customers, create_customer

admin_customers_bp = Blueprint("admin_customers", __name__, url_prefix="/api/customers")


@admin_customers_bp.route("", methods=["GET"])
def api_customers():
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


@admin_customers_bp.route("", methods=["POST"])
def api_create_customer():
    data = request.get_json()
    customer = create_customer(
        data["name"],
        data["email"],
    )
    return jsonify(customer), 201
