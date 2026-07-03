import mysql.connector
from contextlib import contextmanager
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def get_connection():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Hata: {err}")
        return None


@contextmanager
def get_db():
    """
    Veritabanı bağlantısını güvenli şekilde yöneten context manager.

    Kullanım:
        with get_db() as cursor:
            cursor.execute(sql, values)

    - Başarılı olursa: commit() çalışır
    - Hata olursa: rollback() yapılır ve hata yukarı fırlatılır
    - Her iki durumda da cursor ve conn otomatik kapatılır
    """
    conn = get_connection()
    if conn is None:
        raise RuntimeError("❌ Veritabanı bağlantısı kurulamadı.")
    
    cursor = conn.cursor()
    try:
        yield cursor          # servis kodu burada çalışır
        conn.commit()         # hata yoksa commit
    except Exception:
        conn.rollback()       # hata varsa geri al
        raise                 # hatayı yukarıya ilet
    finally:
        cursor.close()        # her koşulda kapat
        conn.close()
