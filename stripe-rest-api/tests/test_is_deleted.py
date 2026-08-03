import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.database import init_pool, get_db
from services.invoice_service import delete_invoice, get_combined_invoices, _upsert_invoice_row

def test_soft_delete_and_filtering():
    init_pool()

    test_inv_id = "test_inv_softdel_999"
    test_cust_id = "cus_test_softdel_999"

    print("1. Test verisi oluşturuluyor...")
    # is_deleted = 0 olarak fatura ekle
    _upsert_invoice_row(
        invoice_id=test_inv_id,
        customer_id=test_cust_id,
        amount=5000,
        currency="usd",
        status="open"
    )

    with get_db() as cursor:
        cursor.execute("SELECT status, is_deleted FROM invoices WHERE stripe_invoice_id = %s", (test_inv_id,))
        row = cursor.fetchone()
        print(f"   Eklenen fatura -> status: {row[0]}, is_deleted: {row[1]}")
        assert row[1] == 0, "is_deleted initial value should be 0"

    print("2. get_combined_invoices kontrol ediliyor (görünmeli)...")
    res = get_combined_invoices(customer_id=test_cust_id)
    found_before = any(inv.get("id") == test_inv_id for inv in res.get("data", []))
    print(f"   Fatura listede bulundu mu? {found_before}")
    assert found_before is True, "Invoice should be listed when is_deleted=0"

    print("3. delete_invoice çağrılıyor...")
    del_res = delete_invoice(test_inv_id)
    print(f"   Delete sonucu: {del_res}")

    with get_db() as cursor:
        cursor.execute("SELECT status, is_deleted FROM invoices WHERE stripe_invoice_id = %s", (test_inv_id,))
        row_after = cursor.fetchone()
        print(f"   Silme sonrası fatura -> status: {row_after[0]}, is_deleted: {row_after[1]}")
        assert row_after[0] == "open", "status should NOT be modified"
        assert row_after[1] == 1, "is_deleted should be 1"

    print("4. get_combined_invoices tekrar kontrol ediliyor (görünmemeli)...")
    res_after = get_combined_invoices(customer_id=test_cust_id)
    found_after = any(inv.get("id") == test_inv_id for inv in res_after.get("data", []))
    print(f"   Fatura listede bulundu mu? {found_after}")
    assert found_after is False, "Invoice should NOT be listed when is_deleted=1"

    print("5. Yeniden faturaları getir (upsert) çağrılıyor...")
    _upsert_invoice_row(
        invoice_id=test_inv_id,
        customer_id=test_cust_id,
        amount=5000,
        currency="usd",
        status="open"
    )

    with get_db() as cursor:
        cursor.execute("SELECT id, is_deleted FROM invoices WHERE stripe_invoice_id = %s ORDER BY id ASC", (test_inv_id,))
        rows = cursor.fetchall()
        print(f"   Veritabanındaki tüm satırlar: {rows}")
        assert len(rows) == 2, f"2 satır bekleniyordu (1 silinmiş geçmiş kaydı, 1 yeni aktif kayıt), bulunan: {len(rows)}"
        assert rows[0][1] == 1, "İlk (eski) satırın is_deleted değeri 1 olarak KALMALI (güncellenmemeli)."
        assert rows[1][1] == 0, "İkinci (yeni) satırın is_deleted değeri 0 olarak EKLENMELİ."

    res_restored = get_combined_invoices(customer_id=test_cust_id)
    found_restored = any(inv.get("id") == test_inv_id for inv in res_restored.get("data", []))
    print(f"   Yeniden getirme sonrası fatura listede bulundu mu? {found_restored}")
    assert found_restored is True, "Invoice SHOULD be listed again when active is_deleted=0 row exists"

    # Temizlik
    with get_db() as cursor:
        cursor.execute("DELETE FROM invoices WHERE stripe_invoice_id = %s", (test_inv_id,))
    print("✅ Tüm test adımları başarıyla tamamlandı!")

if __name__ == "__main__":
    test_soft_delete_and_filtering()
