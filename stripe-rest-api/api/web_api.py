from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from core.config import JWT_SECRET_KEY

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

from api.routes.user.profile import user_profile_bp
from api.routes.user.payments import user_payments_bp
from api.routes.user.refunds import user_refunds_bp
from api.routes.user.invoices import user_invoices_bp

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_TOKEN_LOCATION"] = ["headers", "query_string"]
jwt = JWTManager(app)
CORS(app)

# ── Blueprint Kayıtları (Register) ──────────────────────────────────────────
# Ana & Auth Rotaları
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

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
