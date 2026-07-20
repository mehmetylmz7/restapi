from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.customer_service import get_customer

user_profile_bp = Blueprint("user_profile", __name__, url_prefix="/api/user")


@user_profile_bp.route("/me", methods=["GET"])
@jwt_required()
def api_user_me():
    customer_id = get_jwt_identity()
    customer = get_customer(customer_id)
    if not customer:
        return jsonify({"error": "Müşteri profili bulunamadı."}), 404
    return jsonify(customer)
