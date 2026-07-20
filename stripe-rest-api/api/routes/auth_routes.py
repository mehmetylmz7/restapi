from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from core.database import get_db
from services.customer_service import create_customer

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def api_register():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "E-posta ve şifre zorunludur."}), 400

    email = data["email"].strip().lower()
    password = data["password"]
    name = data.get("name", "").strip()

    # Kullanıcı zaten var mı kontrol et
    try:
        with get_db() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"error": "Bu e-posta adresiyle zaten kayıtlı bir kullanıcı var."}), 400
    except Exception as e:
        return jsonify({"error": f"Veritabanı hatası: {str(e)}"}), 500

    # Stripe üzerinde müşteri oluştur
    try:
        stripe_customer = create_customer(name=name or email, email=email)
        if not stripe_customer or not stripe_customer.get("id"):
            return jsonify({"error": "Stripe üzerinde müşteri oluşturulamadı."}), 500
        stripe_customer_id = stripe_customer["id"]
    except Exception as e:
        return jsonify({"error": f"Stripe entegrasyon hatası: {str(e)}"}), 500

    # Şifreyi hash'le ve DB'ye kaydet
    password_hash = generate_password_hash(password)
    try:
        with get_db() as cursor:
            cursor.execute(
                "INSERT INTO users (email, password_hash, stripe_customer_id) VALUES (%s, %s, %s)",
                (email, password_hash, stripe_customer_id)
            )
        return jsonify({"message": "Kullanıcı başarıyla kaydedildi.", "stripe_customer_id": stripe_customer_id}), 201
    except Exception as e:
        return jsonify({"error": f"Veritabanına kaydedilirken hata oluştu: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
def api_login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "E-posta ve şifre zorunludur."}), 400

    email = data["email"].strip().lower()
    password = data["password"]

    try:
        with get_db() as cursor:
            cursor.execute("SELECT password_hash, stripe_customer_id FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Geçersiz e-posta veya şifre."}), 401

        password_hash, stripe_customer_id = row[0], row[1]

        if not check_password_hash(password_hash, password):
            return jsonify({"error": "Geçersiz e-posta veya şifre."}), 401

        # JWT access token oluştur (identity olarak stripe_customer_id kullanıyoruz)
        access_token = create_access_token(identity=stripe_customer_id)
        return jsonify({
            "access_token": access_token,
            "stripe_customer_id": stripe_customer_id,
            "email": email
        }), 200

    except Exception as e:
        return jsonify({"error": f"Giriş hatası: {str(e)}"}), 500
