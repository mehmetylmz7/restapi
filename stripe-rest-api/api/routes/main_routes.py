from flask import Blueprint, jsonify, render_template
from services.export_service import _fetch_all

main_bp = Blueprint("main", __name__)


@main_bp.route("/api/stats", methods=["GET"])
def api_stats():
    stats = {"customers": 0, "payments": 0, "refunds": 0, "products": 0}
    try:
        # Fetch counts from Stripe API (sayfa sayfa dolaşılarak)
        stats["customers"] = len(_fetch_all("customers"))
        stats["payments"] = len(_fetch_all("payments"))
        stats["refunds"] = len(_fetch_all("refunds"))
        stats["products"] = len(_fetch_all("products"))
    except Exception as e:
        print(f"Stats fetch error: {e}")
    return jsonify(stats)


@main_bp.route("/")
def home():
    return render_template("index.html")
