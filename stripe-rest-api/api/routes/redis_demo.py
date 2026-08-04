import time
import threading
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import create_access_token, decode_token, jwt_required, get_jwt
from core.limiter import limiter
from core.redis_client import (
    get_redis,
    get_cached_json,
    set_cached_json,
    delete_cache,
    redis_lock,
    add_token_to_blacklist,
    is_token_blacklisted,
)

redis_demo_bp = Blueprint("redis_demo", __name__)

# Global test kilidi durumu için takip değişkeni (Demo görselleştirme amaçlı)
_active_lock_info = {"locked": False, "holder": None, "acquired_at": None, "timeout": 0}


@redis_demo_bp.route("/test-redis")
def test_redis_page():
    """Redis interaktif canlı test ve eğitim panelini render eder."""
    return render_template("test_redis.html")


# ── 1. REDIS SUNUCU VE SAĞLIK DURUMU ──────────────────────────────────────────
@redis_demo_bp.route("/api/redis/server-info", methods=["GET"])
def api_redis_server_info():
    """Redis sunucusunun çalışma durumunu, bellek kullanımını ve anahtar sayısını döner."""
    start_time = time.time()
    r = get_redis()
    
    if r is None:
        return jsonify({
            "status": "offline",
            "connected": False,
            "message": "Redis sunucusuna ulaşılamıyor (Fallback modunda çalışılıyor).",
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "keys_count": 0,
            "used_memory_human": "0B",
            "version": "N/A",
            "uptime_days": 0,
        }), 200

    try:
        info = r.info()
        dbsize = r.dbsize()
        latency_ms = round((time.time() - start_time) * 1000, 2)

        return jsonify({
            "status": "online",
            "connected": True,
            "latency_ms": latency_ms,
            "keys_count": dbsize,
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "used_memory_peak_human": info.get("used_memory_peak_human", "N/A"),
            "version": info.get("redis_version", "N/A"),
            "connected_clients": info.get("connected_clients", 1),
            "uptime_days": info.get("uptime_in_days", 0),
            "role": info.get("role", "master"),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "connected": False,
            "error": str(e)
        }), 500


# ── 2. CACHING & TTL SİMÜLATÖRÜ ──────────────────────────────────────────────
@redis_demo_bp.route("/api/redis/cache-demo", methods=["GET"])
def api_cache_demo():
    """
    Önbellekleme simülatörü.
    İlk istek veritabanını simüle eder (350ms gecikme), sonraki istekler Redis'ten gelir (0.5ms).
    """
    cache_key = "demo:dashboard_stats"
    ttl = 30 # 30 saniye TTL

    start_time = time.perf_counter()
    cached_data = get_cached_json(cache_key)

    if cached_data is not None:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Redis'teki kalan TTL süresini al
        r = get_redis()
        ttl_remaining = r.ttl(cache_key) if r else 0

        return jsonify({
            "source": "Redis Önbelleği (Cache HIT)",
            "is_cached": True,
            "elapsed_ms": elapsed_ms,
            "ttl_remaining": ttl_remaining,
            "ttl_total": ttl,
            "data": cached_data,
            "saved_time_ms": max(0, round(350 - elapsed_ms, 2))
        })

    # Önbellekte yoksa DB / Stripe API sorgusunu simüle et (350ms)
    time.sleep(0.35)
    
    mock_data = {
        "active_users": 1420,
        "total_revenue_usd": 89450.00,
        "total_transactions": 3840,
        "successful_rate": "%98.6",
        "generated_at": datetime.now().strftime("%H:%M:%S")
    }

    set_cached_json(cache_key, mock_data, ttl=ttl)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return jsonify({
        "source": "MySQL / Stripe Sorgusu (Cache MISS)",
        "is_cached": False,
        "elapsed_ms": elapsed_ms,
        "ttl_remaining": ttl,
        "ttl_total": ttl,
        "data": mock_data,
        "saved_time_ms": 0
    })


@redis_demo_bp.route("/api/redis/cache-clear", methods=["POST"])
def api_cache_clear():
    """Önbelleği anında temizler."""
    delete_cache("demo:dashboard_stats")
    delete_cache("dashboard:stats")
    return jsonify({"success": True, "message": "Önbellek başarıyla temizlendi! Sonraki istek DB'den hesaplanacak."})


# ── 3. RATE LIMITING SİMÜLATÖRÜ ───────────────────────────────────────────────
@redis_demo_bp.route("/api/redis/rate-limit-demo", methods=["POST"])
@limiter.limit("5 per 15 second")
def api_rate_limit_demo():
    """
    Kullanıcının peş peşe tıklayarak 5 istek sınırını test edebileceği rota.
    15 saniye içinde 5 istekten fazlası 429 döner.
    """
    return jsonify({
        "success": True,
        "status": "İstek Kabul Edildi ✅",
        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "message": "İstek başarıyla işlendi. Limit: 15 saniyede maksimum 5 istek."
    })


# ── 4. DAĞITIK KİLİT (DISTRIBUTED LOCK) SİMÜLATÖRÜ ────────────────────────────
@redis_demo_bp.route("/api/redis/lock-demo", methods=["POST"])
def api_lock_demo():
    """
    İki farklı worker/kullanıcının aynı kaynağı kitleme yarışını simüle eder.
    """
    global _active_lock_info
    data = request.get_json(silent=True) or {}
    worker_name = data.get("worker_name", "Worker-A")
    hold_seconds = int(data.get("hold_seconds", 5))

    r = get_redis()
    lock_name = "demo_resource_lock"

    if r is None:
        return jsonify({"acquired": False, "message": "Redis bağlı değil, kilit testi yapılamıyor."}), 200

    lock = r.lock(f"lock:{lock_name}", timeout=hold_seconds, blocking=False)
    acquired = lock.acquire(blocking=False)

    if acquired:
        _active_lock_info = {
            "locked": True,
            "holder": worker_name,
            "acquired_at": datetime.now().strftime("%H:%M:%S"),
            "timeout": hold_seconds
        }

        # Kilidi arka planda hold_seconds sonra serbest bırakacak thread
        def release_after(l, sec):
            time.sleep(sec)
            try:
                l.release()
            except Exception:
                pass
            global _active_lock_info
            _active_lock_info = {"locked": False, "holder": None, "acquired_at": None, "timeout": 0}

        t = threading.Thread(target=release_after, args=(lock, hold_seconds), daemon=True)
        t.start()

        return jsonify({
            "acquired": True,
            "holder": worker_name,
            "hold_seconds": hold_seconds,
            "message": f"🔒 Kilit {worker_name} tarafından BAŞARIYLA ALINDI! ({hold_seconds} saniye boyunca rezerve edildi)."
        }), 200
    else:
        return jsonify({
            "acquired": False,
            "holder": _active_lock_info.get("holder", "Bilinmeyen Worker"),
            "message": f"⛔ Kilit ALINAMADI! Kaynak şu anda '{_active_lock_info.get('holder', 'Başka bir işlem')}' tarafından kullanılıyor. Race condition engellendi!"
        }), 409


@redis_demo_bp.route("/api/redis/lock-status", methods=["GET"])
def api_lock_status():
    """Mevcut kilit durumunu döner."""
    global _active_lock_info
    r = get_redis()
    if r:
        exists = r.exists("lock:demo_resource_lock")
        if not exists:
            _active_lock_info = {"locked": False, "holder": None, "acquired_at": None, "timeout": 0}
            
    return jsonify(_active_lock_info)


# ── 5. JWT BLACKLIST SİMÜLATÖRÜ ──────────────────────────────────────────────
@redis_demo_bp.route("/api/redis/jwt-demo/generate", methods=["POST"])
def api_jwt_demo_generate():
    """Demo için test JWT token'ı üretir."""
    token = create_access_token(identity="demo_user_redis_test")
    decoded = decode_token(token)
    return jsonify({
        "token": token,
        "jti": decoded.get("jti"),
        "exp": decoded.get("exp"),
        "expires_in_minutes": 15
    })


@redis_demo_bp.route("/api/redis/jwt-demo/protected", methods=["GET"])
@jwt_required()
def api_jwt_demo_protected():
    """Korumalı rota. Token iptal edilmişse @jwt.token_in_blocklist_loader 401 döndürür."""
    jwt_data = get_jwt()
    return jsonify({
        "status": "success",
        "message": "🔓 Giriş Başarılı! Token geçerli ve Redis kara listesinde DEĞİL.",
        "jti": jwt_data.get("jti"),
        "user": jwt_data.get("sub")
    }), 200


@redis_demo_bp.route("/api/redis/jwt-demo/revoke", methods=["POST"])
def api_jwt_demo_revoke():
    """Verilen token'ı Redis kara listesine ekleyerek oturumu sonlandırır."""
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    if not token:
        return jsonify({"error": "Token gönderilmedi."}), 400

    try:
        decoded = decode_token(token)
        jti = decoded.get("jti")
        exp = decoded.get("exp")
        now = datetime.now(timezone.utc).timestamp()
        remaining = max(1, int(exp - now))

        add_token_to_blacklist(jti, remaining)

        return jsonify({
            "success": True,
            "message": f"🚫 Token (JTI: {jti[:10]}...) başarıyla Redis kara listesine eklendi! Kalan {remaining} saniye boyunca bu token ile korumalı isteklere erişilemez.",
            "jti": jti,
            "blacklisted_ttl": remaining
        })
    except Exception as e:
        return jsonify({"error": f"Token çözümlenemedi: {str(e)}"}), 400
