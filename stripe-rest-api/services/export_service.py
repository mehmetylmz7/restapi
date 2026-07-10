import csv
import json
import io
import datetime

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

_DEFAULT_FIELDS = {
    "customers": ["id", "name", "email", "created"],
    "products":  ["id", "name", "description", "active", "price", "created"],
    "payments":  ["id", "customer", "amount", "currency", "status", "created"],
    "refunds":   ["id", "payment_intent", "amount", "currency", "status", "created"],
}


def map_record_fields(record: dict, resource: str, fields: list) -> dict:
    """
    Ham Stripe kaydını sadece istenen alanları barındıran ve
    gerekli biçimlendirmeleri (para birimi, kuruş çevrimi, tarih formatlama) yapılmış bir sözlüğe eşler.
    """
    row = {}
    for f in fields:
        if f == "price" and resource == "products":
            price_obj = record.get("default_price")
            if price_obj and isinstance(price_obj, dict):
                amount = price_obj.get("unit_amount", 0) / 100
                currency = price_obj.get("currency", "").upper()
                row["price"] = f"{amount:.2f} {currency}"
            else:
                row["price"] = "-"
        elif f == "amount" and resource in ("payments", "refunds"):
            val = record.get("amount")
            if val is not None:
                try:
                    row["amount"] = float(val) / 100
                except (TypeError, ValueError):
                    row["amount"] = val
            else:
                row["amount"] = "-"
        elif f == "created":
            val = record.get("created")
            if val:
                row["created"] = datetime.datetime.fromtimestamp(val).strftime("%d.%m.%Y %H:%M:%S")
            else:
                row["created"] = "-"
        else:
            row[f] = record.get(f, "-")
    return row


def _fetch_all(resource: str, created_gte=None, created_lte=None) -> list:
    """
    Tüm kayıtları Stripe'tan sayfa sayfa çeker. Tarih filtresi varsa API veya bellek düzeyinde filtreler.
    """
    fetcher = _FETCHERS[resource]
    all_data = []
    cursor = None

    kwargs = {}
    if resource in ("customers", "payments") and (created_gte or created_lte):
        if created_gte: kwargs["created_gte"] = created_gte
        if created_lte: kwargs["created_lte"] = created_lte

    while True:
        result = fetcher(limit=100, starting_after=cursor, **kwargs)
        if not result or not result.get("data"):
            break
        all_data.extend(result["data"])
        if not result.get("has_more"):
            break
        cursor = result["data"][-1]["id"]

    # Ürünler için tarih filtresi bellek düzeyinde yapılır (Stripe API'si ürün aramada created filtresini direkt desteklemez)
    if resource == "products" and (created_gte or created_lte):
        filtered = []
        for item in all_data:
            created = item.get("created")
            if created:
                if created_gte and created < int(created_gte):
                    continue
                if created_lte and created > int(created_lte):
                    continue
            filtered.append(item)
        return filtered

    return all_data


def _fetch_limited(resource: str, limit: int = 100, created_gte=None, created_lte=None) -> list:
    """
    Belirtilen adette kayıt çeker. Tarih filtresi varsa API veya bellek düzeyinde filtreler.
    """
    fetcher = _FETCHERS[resource]
    kwargs = {}
    if resource in ("customers", "payments") and (created_gte or created_lte):
        if created_gte: kwargs["created_gte"] = created_gte
        if created_lte: kwargs["created_lte"] = created_lte

    result = fetcher(limit=limit, **kwargs)
    if not result or not result.get("data"):
        return []

    all_data = result["data"]
    if resource == "products" and (created_gte or created_lte):
        filtered = []
        for item in all_data:
            created = item.get("created")
            if created:
                if created_gte and created < int(created_gte):
                    continue
                if created_lte and created > int(created_lte):
                    continue
            filtered.append(item)
        return filtered

    return all_data


def export_data(resource: str, fmt: str = "json", limit_val: str = "100", created_gte=None, created_lte=None, fields: list = None) -> bytes:
    """
    Filtrelenmiş ve seçilmiş alanları içeren verileri JSON veya CSV bytes olarak dışa aktarır.
    """
    if resource not in _FETCHERS:
        raise ValueError(f"Geçersiz kaynak: {resource}")

    if not fields:
        fields = _DEFAULT_FIELDS.get(resource, [])

    if limit_val == "all" or limit_val == "date":
        data = _fetch_all(resource, created_gte=created_gte, created_lte=created_lte)
    else:
        try:
            limit = int(limit_val)
        except ValueError:
            limit = 100
        data = _fetch_limited(resource, limit=limit, created_gte=created_gte, created_lte=created_lte)

    mapped_data = [map_record_fields(record, resource, fields) for record in data]

    if fmt == "json":
        return json.dumps(mapped_data, ensure_ascii=False, indent=2).encode("utf-8")
    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\r\n"
        )
        writer.writeheader()
        for row in mapped_data:
            writer.writerow(row)
        return ("\ufeff" + output.getvalue()).encode("utf-8")
    else:
        raise ValueError(f"Geçersiz format: {fmt}")
