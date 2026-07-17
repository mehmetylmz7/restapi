import sys
from pathlib import Path

# Proje ana dizinini Python path'ine ekle
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.database import init_pool, get_db

def create_users_table():
    init_pool()
    
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        stripe_customer_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (stripe_customer_id) REFERENCES customers(stripe_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    try:
        with get_db() as cursor:
            cursor.execute(sql)
        print("✅ users tablosu başarıyla oluşturuldu veya zaten mevcut.")
    except Exception as e:
        print(f"❌ users tablosu oluşturulurken hata: {e}")

if __name__ == "__main__":
    create_users_table()
