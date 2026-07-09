import csv
import json
import io

from services.customer_service import get_customers
from services.product_service import get_products
from services.payment_service import get_payment_intents
from services.refund_service import get_refunds

# ── Kaynak → Stripe fetcher eşleşmesi ─────────────────────────
_FETCHERS = {
    "customers": get_customers,
    "products":  get_products,
    "payments":  get_payment_intents,
    "refunds":   get_refunds,
}

# Her kaynak için JSON'a yazılacak alan sırası (CSV header düzeni)
_CSV_FIELDS = {
    "customers": ["id", "name", "email"],
    "products":  ["id", "name", "description", "active"],
    "payments":  ["id", "customer", "amount", "currency", "status"],
    "refunds":   ["id", "payment_intent", "amount", "currency", "status"],
}


def _fetch_all(resource: str) -> list:
    """
    Tüm kayıtları Stripe'tan sayfa sayfa çeker (cursor pagination).
    has_more=False olana dek döngü devam eder.
    """
    fetcher = _FETCHERS[resource]
    all_data = []
    cursor = None

    while True:
        result = fetcher(limit=100, starting_after=cursor)
        if not result or not result.get("data"):
            break
        all_data.extend(result["data"])
        if not result.get("has_more"):
            break
        cursor = result["data"][-1]["id"]

    return all_data


def _fetch_limited(resource: str, limit: int = 100) -> list:
    """
    Sadece son `limit` kadar kayıt çeker (tek API çağrısı).
    """
    fetcher = _FETCHERS[resource]
    result = fetcher(limit=limit)
    if not result or not result.get("data"):
        return []
    return result["data"]


def export_to_json(resource: str, fetch_all: bool = False) -> bytes:
    """
    Belirtilen kaynağı Stripe'tan çeker ve JSON bytes olarak döner.

    Args:
        resource:  'customers' | 'products' | 'payments' | 'refunds'
        fetch_all: True → tüm kayıtlar (yavaş), False → son 100 (hızlı)

    Returns:
        UTF-8 kodlanmış JSON bytes
    """
    if resource not in _FETCHERS:
        raise ValueError(f"Geçersiz kaynak: {resource}")

    data = _fetch_all(resource) if fetch_all else _fetch_limited(resource)
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def export_to_csv(resource: str, fetch_all: bool = False) -> bytes:
    """
    Belirtilen kaynağı Stripe'tan çeker ve CSV bytes olarak döner.

    Args:
        resource:  'customers' | 'products' | 'payments' | 'refunds'
        fetch_all: True → tüm kayıtlar (yavaş), False → son 100 (hızlı)

    Returns:
        UTF-8 BOM'lu CSV bytes (Excel uyumlu)
    """
    if resource not in _FETCHERS:
        raise ValueError(f"Geçersiz kaynak: {resource}")

    data   = _fetch_all(resource) if fetch_all else _fetch_limited(resource)
    fields = _CSV_FIELDS.get(resource, [])

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        extrasaction="ignore",   # tanımsız alanları sessizce atla
        lineterminator="\r\n"
    )
    writer.writeheader()

    for record in data:
        # amount alanını kuruştan ana para birimine çevir
        row = dict(record)
        if "amount" in row and row["amount"] is not None:
            try:
                row["amount"] = float(row["amount"]) / 100
            except (TypeError, ValueError):
                pass
        writer.writerow(row)

    # UTF-8 BOM ekle (Excel Türkçe karakter sorununu çözer)
    return ("\ufeff" + output.getvalue()).encode("utf-8")
