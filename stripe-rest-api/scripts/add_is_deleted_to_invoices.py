import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.database import init_pool, get_db

def migrate_is_deleted():
    init_pool()
    with get_db() as cursor:
        # 1. is_deleted sütununu ekle (yoksa)
        try:
            cursor.execute("""
                ALTER TABLE invoices
                ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0
            """)
            print("✅ 'is_deleted' sütunu 'invoices' tablosuna başarıyla eklendi.")
        except Exception as e:
            if "Duplicate column name" in str(e) or "already exists" in str(e):
                print("ℹ️ 'is_deleted' sütunu zaten mevcut.")
            else:
                print(f"⚠️ Sütun eklenirken uyarı/hata: {e}")

        # 2. Tüm mevcut kayıtlarda is_deleted alanını 0 olarak güncelle
        try:
            cursor.execute("UPDATE invoices SET is_deleted = 0 WHERE is_deleted IS NULL OR is_deleted != 1")
            print(f"✅ Mevcut fatura kayıtları güncellendi (is_deleted = 0).")
        except Exception as e:
            print(f"❌ Kayıtlar güncellenirken hata: {e}")

if __name__ == "__main__":
    migrate_is_deleted()
