import os
import requests
from stripe_client import post, get
from config import BASE_URL
from database import get_db

# Faturalar için dizinin mevcut olduğundan emin ol
INVOICES_DIR = "data/invoices"
os.makedirs(INVOICES_DIR, exist_ok=True)

def preview_invoice(customer_id, currency, items):
    """
    Stripe'ın Fatura Önizleme API'sini kullanarak fatura oluşturma işlemini simüle eder.
    Önizleme verilerini döndürür (ara toplam, vergi, toplam, satırlar).
    """
    url = f"{BASE_URL}/invoices/create_preview"
    
    # Standart parametreler
    data = {
        "customer": customer_id,
        "automatic_tax[enabled]": "false"  # Vergi hesaplamasını yapılandırılmadığı sürece basit tut
    }
    
    # Satır kalemlerini biçimlendir
    for idx, item in enumerate(items):
        price_id = item.get("price")
        quantity = item.get("quantity", 1)
        data[f"invoice_items[{idx}][price]"] = price_id
        data[f"invoice_items[{idx}][quantity]"] = int(quantity)

    response = post(url, data=data)
    if response is None:
        # POST create_preview başarısız olursa veya API sürümünde desteklenmiyorsa
        # GET /v1/invoices/upcoming yoluna geri dön
        fallback_url = f"{BASE_URL}/invoices/upcoming"
        fallback_params = {
            "customer": customer_id,
            "automatic_tax[enabled]": "false"
        }
        for idx, item in enumerate(items):
            price_id = item.get("price")
            quantity = item.get("quantity", 1)
            fallback_params[f"invoice_items[{idx}][price]"] = price_id
            fallback_params[f"invoice_items[{idx}][quantity]"] = int(quantity)
        
        response = get(fallback_url, params=fallback_params)
        if response is None:
            return None

    return response.json()


def create_and_finalize_invoice(customer_id, currency, items):
    """
    1. Taslak fatura oluşturur.
    2. Bu taslak faturaya seçilen satır kalemlerini ekler.
    3. Faturayı onaylar (PDF bağlantısı oluşturur).
    4. PDF'yi yerelde indirir.
    5. Meta verileri ve PDF yolunu MySQL veritabanına kaydeder.
    """
    # Adım 1: Taslak Fatura Oluştur
    invoice_url = f"{BASE_URL}/invoices"
    invoice_data = {
        "customer": customer_id,
        "currency": currency.lower()
    }
    
    response_invoice = post(invoice_url, data=invoice_data)
    if not response_invoice:
        raise RuntimeError("Draft invoice creation failed on Stripe.")
    
    invoice = response_invoice.json()
    invoice_id = invoice["id"]

    try:
        # Adım 2: Bu Taslak Faturaya Fatura Kalemleri Ekle
        for item in items:
            item_url = f"{BASE_URL}/invoiceitems"
            item_data = {
                "customer": customer_id,
                "pricing[price]": item["price"],
                "quantity": int(item.get("quantity", 1)),
                "invoice": invoice_id
            }
            res_item = post(item_url, data=item_data)
            if not res_item:
                raise RuntimeError(f"Adding invoice item for price {item['price']} failed.")

        # Adım 3: Faturayı Onayla
        finalize_url = f"{BASE_URL}/invoices/{invoice_id}/finalize"
        res_finalize = post(finalize_url, data={})
        if not res_finalize:
            raise RuntimeError("Finalizing invoice failed on Stripe.")
        
        finalized_invoice = res_finalize.json()
        
        # Adım 4: PDF İndir
        pdf_url = finalized_invoice.get("invoice_pdf")
        pdf_path = ""
        if pdf_url:
            pdf_res = requests.get(pdf_url, timeout=20)
            if pdf_res.status_code == 200:
                pdf_filename = f"invoice_{invoice_id}.pdf"
                pdf_path = os.path.join(INVOICES_DIR, pdf_filename)
                with open(pdf_path, "wb") as f:
                    f.write(pdf_res.content)
                print(f"✅ Invoice PDF downloaded: {pdf_path}")
            else:
                print(f"⚠️ Warning: Could not download PDF from {pdf_url}")
        
        # Adım 5: MySQL Veritabanına Kaydet
        amount_total = finalized_invoice.get("total", 0)
        currency_res = finalized_invoice.get("currency", currency).upper()
        status = finalized_invoice.get("status", "open")
        
        sql = """
            INSERT INTO invoices (stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status), pdf_path = VALUES(pdf_path)
        """
        values = (invoice_id, customer_id, amount_total, currency_res, status, pdf_path)
        
        with get_db() as cursor:
            cursor.execute(sql, values)
        print(f"✅ Invoice stored in database: {invoice_id}")
        
        return finalized_invoice

    except Exception as e:
        # Fatura taslak olduğu için, onaylama öncesi bir hata oluşursa silinebilir;
        # ya da sadece hatayı raporlayabiliriz.
        print(f"❌ Error during invoice creation/finalization: {e}")
        raise e


def get_local_invoices(limit=50):
    """
    Yerel MySQL veritabanındaki onaylanmış faturaları listeler.
    """
    try:
        sql = """
            SELECT id, stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path, olusturma_tarihi
            FROM invoices
            ORDER BY olusturma_tarihi DESC
            LIMIT %s
        """
        with get_db() as cursor:
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()
            
        invoices = []
        for r in rows:
            invoices.append({
                "id": r[0],
                "stripe_invoice_id": r[1],
                "customer_stripe_id": r[2],
                "amount": r[3],
                "currency": r[4],
                "status": r[5],
                "pdf_path": r[6],
                "olusturma_tarihi": str(r[7])
            })
        return invoices
    except Exception as e:
        print(f"❌ Database error fetching local invoices: {e}")
        return []


def get_local_invoice_pdf(invoice_id):
    """
    Belirli bir fatura kimliği için yerelde indirilen PDF dosyasını okur.
    """
    try:
        # Veritabanında yol için arama yap
        sql = "SELECT pdf_path FROM invoices WHERE stripe_invoice_id = %s"
        with get_db() as cursor:
            cursor.execute(sql, (invoice_id,))
            row = cursor.fetchone()
            
        if not row or not row[0]:
            return None
            
        pdf_path = row[0]
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                return f.read()
        return None
    except Exception as e:
        print(f"❌ Error reading local invoice PDF: {e}")
        return None
