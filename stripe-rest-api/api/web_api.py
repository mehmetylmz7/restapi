from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from core.config import JWT_SECRET_KEY
from core.limiter import limiter
from core.redis_client import is_token_blacklisted

# Rota Blueprint'lerinin içe aktarılması
from api.routes.main_routes import main_bp
from api.routes.auth_routes import auth_bp
from api.routes.admin.customers import admin_customers_bp
from api.routes.admin.products import admin_products_bp
from api.routes.admin.payments import admin_payments_bp
from api.routes.admin.refunds import admin_refunds_bp
from api.routes.admin.invoices import admin_invoices_bp
from api.routes.admin.files import admin_files_bp
from api.routes.admin.data_ops import admin_data_ops_bp
from api.routes.rabbitmq_demo import rabbitmq_demo_bp

from api.routes.user.profile import user_profile_bp
from api.routes.user.payments import user_payments_bp
from api.routes.user.refunds import user_refunds_bp
from api.routes.user.invoices import user_invoices_bp

from tests.test_routes import test_bp

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_TOKEN_LOCATION"] = ["headers", "query_string"]
jwt = JWTManager(app)
CORS(app)

# Redis tabanlı Rate Limiter'ı uygulamaya bağla
limiter.init_app(app)


# ── JWT Token Blacklist (Oturum İptal Kontrolü) ──────────────────────────────
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    """Her korumalı istekte JWT kimliğinin (jti) Redis kara listesinde olup olmadığını denetler."""
    jti = jwt_payload.get("jti")
    if not jti:
        return False
    return is_token_blacklisted(jti)


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload: dict):
    """Kara listedeki (çıkış yapılmış) bir token kullanıldığında dönecek yanıt."""
    return jsonify({
        "error": "Bu token iptal edilmiştir (oturum sonlandırıldı). Lütfen tekrar giriş yapın."
    }), 401


# ── 429 Rate Limit Aşıldı Hata Yakalayıcı ─────────────────────────────────────
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Çok fazla istek gönderildi (Rate Limit aşıldı). Lütfen bir süre sonra tekrar deneyin.",
        "details": str(e.description)
    }), 429


# ── Blueprint Kayıtları (Register) ──────────────────────────────────────────
# Ana & Auth Rotaları
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(rabbitmq_demo_bp)

# Test Rotaları (Sadece geliştirme aşaması için)
app.register_blueprint(test_bp)

# Admin / Genel API Rotaları
app.register_blueprint(admin_customers_bp)
app.register_blueprint(admin_products_bp)
app.register_blueprint(admin_payments_bp)
app.register_blueprint(admin_refunds_bp)
app.register_blueprint(admin_invoices_bp)
app.register_blueprint(admin_files_bp)
app.register_blueprint(admin_data_ops_bp)

# Kullanıcı Paneli Rotaları (@jwt_required)
app.register_blueprint(user_profile_bp)
app.register_blueprint(user_payments_bp)
app.register_blueprint(user_refunds_bp)
app.register_blueprint(user_invoices_bp)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
