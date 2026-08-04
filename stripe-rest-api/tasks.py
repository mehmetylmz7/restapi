import time
from core.celery_app import celery
from core.redis_client import redis_lock, delete_cache
from services.customer_service import sync_stripe_customers_to_db


@celery.task(bind=True, name="background_sync_task")
def background_sync_task(self, created_gte=None, created_lte=None):
    """
    Stripe müşterilerini arka planda veritabanına senkronize eder.
    Redis Dağıtık Kilit (Distributed Lock):
    - Aynı anda birden fazla worker'ın veya isteğin aynı senkronizasyonu
      çalıştırmasını engeller (Race Condition koruması).
    """
    print("Arka plan senkronizasyonu başlatılıyor...")
    
    with redis_lock("customer_sync_task", timeout=60, blocking=False) as acquired:
        if not acquired:
            msg = "⚠️ Başka bir senkronizasyon görevi zaten devam ediyor. Çakışma önlendi."
            print(msg)
            return {"success": False, "skipped": True, "message": msg}

        try:
            result = sync_stripe_customers_to_db(created_gte=created_gte, created_lte=created_lte)
            # Senkronizasyon sonrası dashboard istatistik önbelleğini temizle
            delete_cache("dashboard:stats")
            print(f"Arka plan senkronizasyonu tamamlandı: {result}")
            return result
        except Exception as e:
            print(f"Arka plan senkronizasyonu hatası: {e}")
            raise e



@celery.task(bind=True, name="fetch_customers_task")
def fetch_customers_task(self, limit=10, starting_after=None):
    """
    Stripe'tan limit kadar musteri ceker ve sonuclari dondurur.
    RabbitMQ demo sayfasi icin: kuyruga gonderilir, worker isler, sonuc alinir.
    """
    from core.stripe_client import get
    from core.config import BASE_URL

    print(f"[RabbitMQ Demo] fetch_customers_task basliyor | limit={limit}")
    time.sleep(1)  # Kuyruk aktivitesini RabbitMQ dashboard'da gormek icin kisa bekleme

    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after

    response = get(f"{BASE_URL}/customers", params=params)
    if response is None:
        return {"success": False, "error": "Stripe API yanit vermedi", "data": []}

    res_json = response.json()
    customers = res_json.get("data", [])
    has_more = res_json.get("has_more", False)

    result = {
        "success": True,
        "type": "customers",
        "count": len(customers),
        "has_more": has_more,
        "data": [
            {
                "id": c.get("id"),
                "name": c.get("name") or "(isimsiz)",
                "email": c.get("email") or "",
                "created": c.get("created"),
            }
            for c in customers
        ],
    }
    print(f"[RabbitMQ Demo] fetch_customers_task tamamlandi | {len(customers)} musteri getirildi")
    return result


@celery.task(bind=True, name="fetch_invoices_task")
def fetch_invoices_task(self, limit=10, starting_after=None):
    """
    Stripe'tan limit kadar fatura ceker ve sonuclari dondurur.
    RabbitMQ demo sayfasi icin: kuyruga gonderilir, worker isler, sonuc alinir.
    """
    from core.stripe_client import get
    from core.config import BASE_URL

    print(f"[RabbitMQ Demo] fetch_invoices_task basliyor | limit={limit}")
    time.sleep(1)  # Kuyruk aktivitesini RabbitMQ dashboard'da gormek icin kisa bekleme

    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after

    response = get(f"{BASE_URL}/invoices", params=params)
    if response is None:
        return {"success": False, "error": "Stripe API yanit vermedi", "data": []}

    res_json = response.json()
    invoices = res_json.get("data", [])
    has_more = res_json.get("has_more", False)

    result = {
        "success": True,
        "type": "invoices",
        "count": len(invoices),
        "has_more": has_more,
        "data": [
            {
                "id": inv.get("id"),
                "customer": inv.get("customer"),
                "amount_due": (inv.get("amount_due") or 0) / 100,
                "currency": (inv.get("currency") or "usd").upper(),
                "status": inv.get("status"),
                "created": inv.get("created"),
            }
            for inv in invoices
        ],
    }
    print(f"[RabbitMQ Demo] fetch_invoices_task tamamlandi | {len(invoices)} fatura getirildi")
    return result
