import time
from core.celery_app import celery
from services.customer_service import sync_stripe_customers_to_db

@celery.task(bind=True, name="background_sync_task")
def background_sync_task(self, created_gte=None, created_lte=None):
    print("⏳ Arka plan senkronizasyonu başlatıldı...")
    try:
        # Gerçek fonksiyonu çağırıyoruz
        result = sync_stripe_customers_to_db(created_gte=created_gte, created_lte=created_lte)
        print(f"✅ Arka plan senkronizasyonu tamamlandı: {result}")
        return result
    except Exception as e:
        print(f"❌ Arka plan senkronizasyonu hatası: {e}")
        raise e
