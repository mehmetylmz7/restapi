import sys
import os

# core.database modülünü yükleyebilmek için kök dizini sys.path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_db

def create_tables():
    print("⏳ Tablolar oluşturuluyor...")
    
    customers_sql = """
    CREATE TABLE IF NOT EXISTS customers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stripe_id VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255),
        email VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    invoices_sql = """
    CREATE TABLE IF NOT EXISTS invoices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stripe_invoice_id VARCHAR(255) NOT NULL,
        customer_stripe_id VARCHAR(255),
        amount INT,
        currency VARCHAR(10),
        status VARCHAR(50),
        pdf_path VARCHAR(500),
        olusturma_tarihi DATETIME,
        is_deleted TINYINT(1) NOT NULL DEFAULT 0,
        KEY idx_stripe_inv (stripe_invoice_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    try:
        with get_db() as cursor:
            cursor.execute(customers_sql)
            print("✅ 'customers' tablosu hazır.")
            
            cursor.execute(invoices_sql)
            print("✅ 'invoices' tablosu hazır.")
            
        print("🎉 Veritabanı kurulumu başarıyla tamamlandı!")
    except Exception as e:
        print(f"❌ Hata oluştu: {e}")

if __name__ == "__main__":
    create_tables()
