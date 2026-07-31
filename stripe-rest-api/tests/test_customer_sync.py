import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.database import init_pool, get_db
from services.customer_service import get_customers, sync_stripe_customers_to_db, create_customer

def test_customer_db_sync_and_listing():
    init_pool()

    print("1. Stripe müşterileri veritabanına senkronize ediliyor...")
    sync_res = sync_stripe_customers_to_db()
    print(f"   Senkronizasyon sonucu: {sync_res}")
    assert sync_res.get("success") is True, "Customer sync should succeed"

    print("2. get_customers veritabanı odaklı çağrılıyor...")
    res = get_customers(limit=10)
    print(f"   Çekilen müşteri sayısı: {len(res.get('data', []))}, has_more: {res.get('has_more')}")
    assert isinstance(res.get("data"), list), "Data should be a list"

    print("3. Yerel test müşterisi ekleniyor...")
    with get_db() as cursor:
        cursor.execute(
            "INSERT INTO customers (stripe_id, name, email) VALUES (%s, %s, %s)",
            ("cus_local_test_12345", "Yerel Test Müşterisi", "yerel_test@example.com")
        )

    print("4. get_customers tekrar çağrılarak yerel müşterinin dahil edildiği doğrulanıyor...")
    res_after = get_customers(limit=100)
    found_local = any(c.get("email") == "yerel_test@example.com" for c in res_after.get("data", []))
    print(f"   Yerel müşteri listede bulundu mu? {found_local}")
    assert found_local is True, "Local customer should be present in get_customers list"

    # Temizlik
    with get_db() as cursor:
        cursor.execute("DELETE FROM customers WHERE stripe_id = %s", ("cus_local_test_12345",))
    print("✅ Tüm müşteri senkronizasyon testleri başarıyla tamamlandı!")

if __name__ == "__main__":
    test_customer_db_sync_and_listing()
