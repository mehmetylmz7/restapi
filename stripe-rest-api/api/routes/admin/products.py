from flask import Blueprint, jsonify, request
from services.product_service import get_products, create_product

admin_products_bp = Blueprint("admin_products", __name__, url_prefix="/api/products")


@admin_products_bp.route("", methods=["GET"])
def api_products():
    limit = int(request.args.get("limit", 10))
    starting_after = request.args.get("starting_after", None)
    result = get_products(limit=limit, starting_after=starting_after)
    return jsonify(result)


@admin_products_bp.route("", methods=["POST"])
def api_create_product():
    data = request.get_json()
    product = create_product(
        data["name"], data.get("description"), price=data.get("price")
    )
    return jsonify(product), 201
