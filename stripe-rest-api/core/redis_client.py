import json
import logging
from contextlib import contextmanager
from typing import Any, Optional
import redis
from core.config import REDIS_HOST, REDIS_PORT, REDIS_DB

logger = logging.getLogger(__name__)

# Redis bağlantı havuzu (Connection Pool)
_pool = None

def get_redis_pool():
    global _pool
    if _pool is None:
        try:
            _pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
        except Exception as e:
            logger.error(f"❌ Redis ConnectionPool oluşturulamadı: {e}")
    return _pool


def get_redis() -> Optional[redis.Redis]:
    """
    Bağlantı havuzundan hazır bir Redis istemcisi döner.
    Redis erişilemez durumdaysa None döner (hata fırlatmaz, graceful fallback sağlar).
    """
    pool = get_redis_pool()
    if pool is None:
        return None
    try:
        r = redis.Redis(connection_pool=pool)
        # Hızlı bir ping ile canlılığı doğrula
        r.ping()
        return r
    except Exception as e:
        logger.warning(f"⚠️ Redis bağlantısı kurulamadı: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# 1. ÖNBELLEKLEME (CACHING) YARDIMCILARI
# ─────────────────────────────────────────────────────────────

def get_cached_json(key: str) -> Optional[Any]:
    """Redis'ten JSON formatındaki veriyi okur ve dict/list olarak döner."""
    r = get_redis()
    if r is None:
        return None
    try:
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis get cache hatası ({key}): {e}")
    return None


def set_cached_json(key: str, value: Any, ttl: int = 60) -> bool:
    """Veriyi JSON formatında verilen TTL (saniye) süresiyle Redis'e kaydeder."""
    r = get_redis()
    if r is None:
        return False
    try:
        serialized = json.dumps(value)
        r.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f"Redis set cache hatası ({key}): {e}")
        return False


def delete_cache(key: str) -> bool:
    """Belirtilen anahtardaki önbelleği temizler (Cache Invalidation)."""
    r = get_redis()
    if r is None:
        return False
    try:
        r.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis delete cache hatası ({key}): {e}")
        return False


def delete_cache_pattern(pattern: str) -> int:
    """Verilen desene (pattern, örn: 'stats:*') uyan tüm anahtarları siler."""
    r = get_redis()
    if r is None:
        return 0
    try:
        keys = r.keys(pattern)
        if keys:
            return r.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis pattern delete hatası ({pattern}): {e}")
    return 0


# ─────────────────────────────────────────────────────────────
# 2. JWT TOKEN BLACKLIST YARDIMCILARI
# ─────────────────────────────────────────────────────────────

def add_token_to_blacklist(jti: str, expires_in: int) -> bool:
    """
    Kullanıcı çıkış yaptığında token'ın benzersiz kimliğini (jti)
    token'ın kalan geçerlilik süresi (expires_in) kadar kara listeye alır.
    """
    r = get_redis()
    if r is None:
        return False
    try:
        key = f"jwt_blacklist:{jti}"
        # Token süresi kadar TTL atanır, süre dolunca otomatik temizlenir
        r.setex(key, max(int(expires_in), 1), "revoked")
        return True
    except Exception as e:
        logger.error(f"JWT blacklist kayıt hatası (jti={jti}): {e}")
        return False


def is_token_blacklisted(jti: str) -> bool:
    """Token'ın jti değerinin kara listede olup olmadığını kontrol eder."""
    r = get_redis()
    if r is None:
        return False
    try:
        key = f"jwt_blacklist:{jti}"
        return r.exists(key) == 1
    except Exception as e:
        logger.warning(f"JWT blacklist sorgu hatası (jti={jti}): {e}")
        return False


# ─────────────────────────────────────────────────────────────
# 3. DAĞITIK KİLİT (DISTRIBUTED LOCK) YARDIMCISI
# ─────────────────────────────────────────────────────────────

@contextmanager
def redis_lock(lock_name: str, timeout: int = 15, blocking: bool = False):
    """
    Redis tabanlı dağıtık kilit (Distributed Lock) context manager'ı.
    
    Kullanım:
        with redis_lock("lock:customer_sync", timeout=30, blocking=False) as acquired:
            if not acquired:
                return "Başka bir işlem zaten devam ediyor", 409
            # Kritik operasyon...
    """
    r = get_redis()
    if r is None:
        # Redis yoksa kilit alınmış gibi devam et (veya fallback uygula)
        yield True
        return

    lock_key = f"lock:{lock_name}"
    lock = r.lock(lock_key, timeout=timeout, blocking=blocking)
    acquired = False

    try:
        acquired = lock.acquire(blocking=blocking)
        yield acquired
    except Exception as e:
        logger.warning(f"Redis lock hatası ({lock_name}): {e}")
        yield False
    finally:
        if acquired:
            try:
                lock.release()
            except Exception:
                pass  # Kilit süresi dolmuşsa release hata verebilir, yoksayılır
