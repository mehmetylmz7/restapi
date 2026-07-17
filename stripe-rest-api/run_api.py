from api.web_api import app
from core.database import init_pool

# Uygulama başlarken bağlantı havuzunu oluştur (bir kez çalışır)
init_pool(pool_size=5)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
