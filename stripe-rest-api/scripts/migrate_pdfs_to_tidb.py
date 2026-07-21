"""
Tek seferlik migrasyon scripti:
Yerel MySQL (stripe_db.payment_pdfs) -> TiDB Cloud (flaskdb.payment_pdfs)

Kullanim:
    cd stripe-rest-api
    python scripts/migrate_pdfs_to_tidb.py
"""

import sys
import os

# Proje kok dizinini sys.path'e ekle (servis import'lari icin)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import mysql.connector
from core.config import (
    DB_HOST, DB_USER, DB_PASSWORD, DB_NAME,
    TIDB_HOST, TIDB_PORT, TIDB_USER, TIDB_PASSWORD, TIDB_NAME, TIDB_CA_PATH,
)


def main():
    print("=" * 60)
    print("payment_pdfs Migrasyon: MySQL -> TiDB Cloud")
    print("=" * 60)

    # 1. Yerel MySQL baglantisi
    print("\n[1/4] Yerel MySQL'e baglaniliyor...")
    try:
        local_conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        local_cursor = local_conn.cursor()
        print(f"  OK Yerel MySQL baglandi ({DB_HOST}/{DB_NAME})")
    except Exception as e:
        print(f"  HATA Yerel MySQL baglanti hatasi: {e}")
        sys.exit(1)

    # 2. TiDB Cloud baglantisi
    print("\n[2/4] TiDB Cloud'a baglaniliyor...")
    try:
        tidb_conn = mysql.connector.connect(
            host=TIDB_HOST,
            port=TIDB_PORT,
            user=TIDB_USER,
            password=TIDB_PASSWORD,
            database=TIDB_NAME,
            ssl_ca=TIDB_CA_PATH,
            ssl_verify_cert=True,
            ssl_verify_identity=True,
            use_pure=True,  # Windows'ta C extension SSL uyumsuzlugunu onler
        )
        tidb_cursor = tidb_conn.cursor()
        print(f"  OK TiDB Cloud baglandi ({TIDB_HOST}/{TIDB_NAME})")
    except Exception as e:
        print(f"  HATA TiDB baglanti hatasi: {e}")
        local_conn.close()
        sys.exit(1)

    # 3. Yerel MySQL'den tum PDF kayitlarini oku
    print("\n[3/4] Yerel MySQL'den payment_pdfs okunuyor...")
    try:
        local_cursor.execute(
            "SELECT payment_intent_stripe_id, pdf_data, olusturma_tarihi FROM payment_pdfs"
        )
        rows = local_cursor.fetchall()
        print(f"  {len(rows)} kayit bulundu.")
    except Exception as e:
        print(f"  HATA Okuma hatasi: {e}")
        local_conn.close()
        tidb_conn.close()
        sys.exit(1)

    if not rows:
        print("\n  Aktarilacak veri yok. Islem tamamlandi.")
        local_conn.close()
        tidb_conn.close()
        return

    # 4. TiDB'ye yaz
    print("\n[4/4] TiDB Cloud'a yaziliyor...")
    insert_sql = """
        INSERT INTO payment_pdfs (payment_intent_stripe_id, pdf_data, olusturma_tarihi)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE pdf_data = VALUES(pdf_data)
    """

    migrated = 0
    errors = 0

    for row in rows:
        payment_intent_stripe_id, pdf_data, olusturma_tarihi = row
        try:
            tidb_cursor.execute(insert_sql, (payment_intent_stripe_id, pdf_data, olusturma_tarihi))
            tidb_conn.commit()
            migrated += 1
            print(f"  OK [{migrated}/{len(rows)}] {payment_intent_stripe_id}")
        except Exception as e:
            errors += 1
            print(f"  HATA [{payment_intent_stripe_id}]: {e}")

    # Ozet
    print("\n" + "=" * 60)
    print("Migrasyon Tamamlandi")
    print(f"  Toplam kayit : {len(rows)}")
    print(f"  Aktarilan    : {migrated}")
    print(f"  Hata         : {errors}")
    print("=" * 60)

    local_cursor.close()
    local_conn.close()
    tidb_cursor.close()
    tidb_conn.close()


if __name__ == "__main__":
    main()
