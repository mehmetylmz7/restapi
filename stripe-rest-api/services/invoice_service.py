import requests
from pathlib import Path
from core.stripe_client import post, get
from core.config import BASE_URL
from core.database import get_db

# Faturalar için dizinin mevcut olduğundan emin ol
INVOICES_DIR = Path("data/invoices")
INVOICES_DIR.mkdir(parents=True, exist_ok=True)


def preview_invoice(customer_id, currency, items):
    """
    Stripe'ın Fatura Önizleme API'sini kullanarak fatura oluşturma işlemini simüle eder.
    Önizleme verilerini döndürür (ara toplam, vergi, toplam, satırlar).
    """
    url = f"{BASE_URL}/invoices/create_preview"

    # Standart parametreler
    data = {
        "customer": customer_id,
        "automatic_tax[enabled]": "false",  # Vergi hesaplamasını yapılandırılmadığı sürece basit tut
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
        fallback_params = {"customer": customer_id, "automatic_tax[enabled]": "false"}
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
    invoice_data = {"customer": customer_id, "currency": currency.lower()}

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
                "invoice": invoice_id,
            }
            res_item = post(item_url, data=item_data)
            if not res_item:
                raise RuntimeError(
                    f"Adding invoice item for price {item['price']} failed."
                )

        # Adım 3: Faturayı Onayla
        finalize_url = f"{BASE_URL}/invoices/{invoice_id}/finalize"
        res_finalize = post(finalize_url, data={})
        if not res_finalize:
            raise RuntimeError("Finalizing invoice failed on Stripe.")

        finalized_invoice = res_finalize.json()

        # # [DEPRECATED - LOCAL DISK & MYSQL OPTION]
        # pdf_url = finalized_invoice.get("invoice_pdf")
        # pdf_path = ""
        # if pdf_url:
        #     pdf_res = requests.get(pdf_url, timeout=20)
        #     if pdf_res.status_code == 200:
        #         pdf_filename = f"invoice_{invoice_id}.pdf"
        #         pdf_path = INVOICES_DIR / pdf_filename
        #         with open(pdf_path, "wb") as f:
        #             f.write(pdf_res.content)
        #         print(f"✅ Invoice PDF downloaded: {pdf_path}")
        #     else:
        #         print(f"⚠️ Warning: Could not download PDF from {pdf_url}")
        # 
        # amount_total = finalized_invoice.get("total", 0)
        # currency_res = finalized_invoice.get("currency", currency).upper()
        # status = finalized_invoice.get("status", "open")
        # 
        # sql = """
        #     INSERT INTO invoices (stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path)
        #     VALUES (%s, %s, %s, %s, %s, %s)
        #     ON DUPLICATE KEY UPDATE status = VALUES(status), pdf_path = VALUES(pdf_path)
        # """
        # values = (invoice_id, customer_id, amount_total, currency_res, status, str(pdf_path) if pdf_path else "")
        # 
        # with get_db() as cursor:
        #     cursor.execute(sql, values)
        # print(f"✅ Invoice stored in database: {invoice_id}")

        return finalized_invoice

    except Exception as e:
        # Fatura taslak olduğu için, onaylama öncesi bir hata oluşursa silinebilir;
        # ya da sadece hatayı raporlayabiliriz.
        print(f"❌ Error during invoice creation/finalization: {e}")
        raise e


def get_local_invoices(
    customer_id=None,
    limit=10,
    starting_after=None,
    created_gte=None,
    created_lte=None,
):
    """
    Stripe REST API'den onaylanmış/tüm faturaları canlı olarak çeker.
    Sayfalama (pagination) için limit ve starting_after parametrelerini destekler.
    Tarih filtreleme için created_gte ve created_lte destekler.
    """
    try:
        url = f"{BASE_URL}/invoices"
        params = {"limit": limit}
        if starting_after:
            params["starting_after"] = starting_after
        if customer_id:
            params["customer"] = customer_id
        if created_gte:
            params["created[gte]"] = int(created_gte)
        if created_lte:
            params["created[lte]"] = int(created_lte)

        response = get(url, params=params)
        if response is None:
            return {"data": [], "has_more": False}

        res_json = response.json()
        data = res_json.get("data", [])
        has_more = res_json.get("has_more", False)

        invoices = []
        for inv in data:
            created_ts = inv.get("created")
            if created_ts:
                from datetime import datetime, timezone
                dt_str = datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            else:
                dt_str = ""

            invoices.append(
                {
                    "id": inv.get("id"),
                    "stripe_invoice_id": inv.get("id"),
                    "customer_stripe_id": inv.get("customer"),
                    "amount": inv.get("total", inv.get("amount_due", 0)),
                    "currency": inv.get("currency", "usd"),
                    "status": inv.get("status", "open"),
                    "pdf_path": inv.get("invoice_pdf", ""),
                    "olusturma_tarihi": dt_str,
                    "created": created_ts,
                }
            )
        return {"data": invoices, "has_more": has_more}
    except Exception as e:
        print(f"❌ Stripe API error fetching invoices: {e}")
        return {"data": [], "has_more": False}


def get_local_invoice_pdf(invoice_id, customer_id=None):
    """
    Belirli bir fatura kimliği için Stripe API'den canlı PDF verisini okur.
    (Eski yerel disk okuma mantığı yorum satırına alınmıştır).
    Güvenlik kontrolü için isteğe bağlı customer_id filtresi uygulanır.
    """
    # # [DEPRECATED - LOCAL DISK & MYSQL OPTION]
    # try:
    #     if customer_id:
    #         sql = "SELECT pdf_path FROM invoices WHERE stripe_invoice_id = %s AND customer_stripe_id = %s"
    #         params = (invoice_id, customer_id)
    #     else:
    #         sql = "SELECT pdf_path FROM invoices WHERE stripe_invoice_id = %s"
    #         params = (invoice_id,)
    # 
    #     with get_db() as cursor:
    #         cursor.execute(sql, params)
    #         row = cursor.fetchone()
    # 
    #     if not row or not row[0]:
    #         return None
    # 
    #     pdf_path = Path(row[0])
    #     if pdf_path.exists():
    #         with open(pdf_path, "rb") as f:
    #             return f.read()
    #     return None
    # except Exception as e:
    #     print(f"❌ Error reading local invoice PDF: {e}")
    #     return None

    try:
        url = f"{BASE_URL}/invoices/{invoice_id}"
        response = get(url)
        if response is None:
            return None

        invoice_data = response.json()
        
        # Müşteri güvenlik kontrolü (eğer customer_id belirtilmişse)
        if customer_id and invoice_data.get("customer") != customer_id:
            print(f"⚠️ Security warning: Customer {customer_id} tried to access invoice belonging to {invoice_data.get('customer')}")
            return None

        pdf_url = invoice_data.get("invoice_pdf")
        if not pdf_url:
            return None

        pdf_res = requests.get(pdf_url, timeout=20)
        if pdf_res.status_code == 200:
            return pdf_res.content
        return None
    except Exception as e:
        print(f"❌ Error fetching invoice PDF from Stripe API: {e}")
        return None

