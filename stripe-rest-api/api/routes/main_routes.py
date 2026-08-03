from flask import Blueprint, jsonify, render_template
from core.database import get_db
from core.stripe_client import get
from core.config import BASE_URL

main_bp = Blueprint("main", __name__)


@main_bp.route("/api/stats", methods=["GET"])
def api_stats():
    """
    Dashboard istatistiklerini döndürür.
    - customers : yerel MySQL'den COUNT (Stripe çağrısı yok)
    - invoices  : yerel MySQL'den COUNT, is_deleted=0 olanlar
    - payments  : Stripe'a limit=1 ile tek istek → total_count
    - products  : Stripe'a limit=1 ile tek istek → total_count
    """
    stats = {"customers": 0, "payments": 0, "refunds": 0, "products": 0}

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
            # Stripe total_count döndürmez; has_more varsa en az 1 var demek
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


