from flask import Blueprint, jsonify, request
from services.customer_service import get_customers, create_customer, sync_stripe_customers_to_db

admin_customers_bp = Blueprint("admin_customers", __name__, url_prefix="/api/customers")


@admin_customers_bp.route("", methods=["GET"])
def api_customers():
    limit_arg = request.args.get("limit")
    limit = int(limit_arg) if limit_arg is not None else None
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


@admin_customers_bp.route("/sync", methods=["POST"])
def api_sync_customers():
    data = request.get_json(silent=True) or {}
    created_gte = data.get("created_gte") or request.args.get("created_gte")
    created_lte = data.get("created_lte") or request.args.get("created_lte")
    result = sync_stripe_customers_to_db(
        created_gte=created_gte,
        created_lte=created_lte,
    )
    return jsonify(result)
