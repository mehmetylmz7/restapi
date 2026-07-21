from api.web_api import app
from core.database import init_pool, init_tidb_pool

# Uygulama başlarken bağlantı havuzlarını oluştur (bir kez çalışır)
init_pool(pool_size=5)        # Yerel MySQL (stripe_db)
init_tidb_pool(pool_size=5)   # TiDB Cloud (flaskdb — payment_pdfs tablosu)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
