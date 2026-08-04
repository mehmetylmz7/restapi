from flask import Blueprint, jsonify, render_template
from core.database import get_db
from core.stripe_client import get
from core.config import BASE_URL
from core.redis_client import get_cached_json, set_cached_json

main_bp = Blueprint("main", __name__)


@main_bp.route("/api/stats", methods=["GET"])
def api_stats():
    """
    Dashboard istatistiklerini döndürür.
    Redis Önbellekleme (TTL: 60 saniye):
    - Önce Redis'te 'dashboard:stats' anahtarı kontrol edilir (1 ms altı yanıt).
    - Cache yoksa MySQL COUNT ve Stripe API'den hesaplanır ve Redis'e yazılır.
    """
    cache_key = "dashboard:stats"
    cached_stats = get_cached_json(cache_key)
    if cached_stats is not None:
        cached_stats["_cached"] = True
        return jsonify(cached_stats)

    stats = {"customers": 0, "payments": 0, "refunds": 0, "products": 0, "_cached": False}

    # ── customers: DB'den direkt say ─────────────────────────
    try:
        with get_db() as cursor:
            cursor.execute("SELECT COUNT(*) FROM customers")
            stats["customers"] = cursor.fetchone()[0]
    except Exception as e:
        print(f"Stats customers DB error: {e}")

    # ── invoices → payments alanına yansıt (DB'den) ───────────
    try:
        with get_db() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM invoices WHERE is_deleted = 0 OR is_deleted IS NULL"
            )
            stats["payments"] = cursor.fetchone()[0]
    except Exception as e:
        print(f"Stats invoices DB error: {e}")

    # ── refunds: Stripe'a limit=1 ile hafif tek istek ─────────
    try:
        res = get(f"{BASE_URL}/refunds", params={"limit": 1})
        if res:
            data = res.json()
            stats["refunds"] = 1 if data.get("data") else 0
    except Exception as e:
        print(f"Stats refunds error: {e}")

    # ── products: Stripe'a limit=1 ile hafif tek istek ────────
    try:
        res = get(f"{BASE_URL}/products", params={"limit": 1})
        if res:
            data = res.json()
            stats["products"] = 1 if data.get("data") else 0
    except Exception as e:
        print(f"Stats products error: {e}")

    # Hesaplanan istatistikleri 60 saniye boyunca Redis'e önbelleğe al
    set_cached_json(cache_key, stats, ttl=60)

    return jsonify(stats)



@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.route("/test-mode")
@main_bp.route("/test-mode/<int:mode_id>")
def test_mode(mode_id=1):
    if mode_id not in (1, 2, 3):
        mode_id = 1
    return render_template("test_mode.html", mode_id=mode_id)


