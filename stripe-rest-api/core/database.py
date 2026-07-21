import mysql.connector
from contextlib import contextmanager
from core.config import (
    DB_HOST, DB_USER, DB_PASSWORD, DB_NAME,
    TIDB_HOST, TIDB_PORT, TIDB_USER, TIDB_PASSWORD, TIDB_NAME, TIDB_CA_PATH,
)

# Pool'un adı — get_connection() bu isimle havuzdan bağlantı alır
_POOL_NAME = "stripe_pool"
_TIDB_POOL_NAME = "tidb_pool"


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


def init_tidb_pool(pool_size=5):
    """
    TiDB Cloud için bağlantı havuzu. payment_pdfs tablosuna erişim için kullanılır.
    SSL/TLS zorunludur; CA sertifikası TIDB_CA_PATH değişkeninden okunur.
    """
    mysql.connector.connect(
        pool_name=_TIDB_POOL_NAME,
        pool_size=pool_size,
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
    print(
        f"✅ TiDB bağlantı havuzu oluşturuldu (pool_name='{_TIDB_POOL_NAME}', host='{TIDB_HOST}')"
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


def _get_tidb_connection():
    """TiDB havuzundan bir bağlantı kiralar."""
    try:
        return mysql.connector.connect(pool_name=_TIDB_POOL_NAME)
    except mysql.connector.Error as err:
        print(f"❌ TiDB pool'dan bağlantı alınamadı: {err}")
        return None


@contextmanager
def get_db():
    """
    Yerel MySQL veritabanı bağlantısını güvenli şekilde yöneten context manager.

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


@contextmanager
def get_tidb():
    """
    TiDB Cloud bağlantısını güvenli şekilde yöneten context manager.
    payment_pdfs tablosuna okuma/yazma işlemleri için kullanılır.

    Kullanım:
        with get_tidb() as cursor:
            cursor.execute(sql, values)
    """
    conn = _get_tidb_connection()
    if conn is None:
        raise RuntimeError("❌ TiDB bağlantısı kurulamadı.")

    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
