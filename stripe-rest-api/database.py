import mysql.connector
from contextlib import contextmanager
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

# Pool'un adı — get_connection() bu isimle havuzdan bağlantı alır
_POOL_NAME = "stripe_pool"


def init_pool(pool_size=5):
    """
    Uygulama başlarken bir kez çağrılır.
    mysql-connector-python, pool_name üzerinden bu havuzu global olarak yönetir.
    """
    mysql.connector.connect(
        pool_name=_POOL_NAME,
        pool_size=pool_size,
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    print(
        f"✅ Bağlantı havuzu oluşturuldu (pool_name='{_POOL_NAME}', pool_size={pool_size})"
    )


def get_connection():
    """
    Pool'dan hazır bir bağlantı kiralar.
    Artık her çağrıda yeni TCP bağlantısı açılmaz.
    conn.close() çağrıldığında bağlantı kapatılmaz — pool'a iade edilir.
    """
    try:
        return mysql.connector.connect(pool_name=_POOL_NAME)
    except mysql.connector.Error as err:
        print(f"❌ Pool'dan bağlantı alınamadı: {err}")
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
    - Her iki durumda da cursor ve conn otomatik kapatılır (pool'a iade edilir)
    """
    conn = get_connection()
    if conn is None:
        raise RuntimeError("❌ Veritabanı bağlantısı kurulamadı.")

    cursor = conn.cursor()
    try:
        yield cursor  # servis kodu burada çalışır
        conn.commit()  # hata yoksa commit
    except Exception:
        conn.rollback()  # hata varsa geri al
        raise  # hatayı yukarıya ilet
    finally:
        cursor.close()  # her koşulda kapat
        conn.close()  # pool'a iade eder, gerçekten kapatmaz
