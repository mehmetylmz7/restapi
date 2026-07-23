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


def create_invoice_with_amount(customer_id: str, amount: int, currency: str = "usd", status: str = "open") -> dict:
    """
    Tutar (kuruş/cent cinsinden) vererek Stripe üzerinde taslak fatura ve kalemi oluşturur.
    status 'draft' değilse faturayı finalize eder.
    """
    invoice_url = f"{BASE_URL}/invoices"
    invoice_data = {"customer": customer_id, "currency": currency.lower()}

    response_invoice = post(invoice_url, data=invoice_data)
    if not response_invoice:
        raise RuntimeError("Draft invoice creation failed on Stripe.")

    invoice = response_invoice.json()
    invoice_id = invoice["id"]

    try:
        item_url = f"{BASE_URL}/invoiceitems"
        item_data = {
            "customer": customer_id,
            "amount": int(amount),
            "currency": currency.lower(),
            "invoice": invoice_id,
            "description": "Fatura Kalemi",
        }
        res_item = post(item_url, data=item_data)
        if not res_item:
            raise RuntimeError(f"Adding invoice item with amount {amount} failed.")

        if str(status).lower() != "draft":
            finalize_url = f"{BASE_URL}/invoices/{invoice_id}/finalize"
            res_finalize = post(finalize_url, data={})
            if res_finalize:
                return res_finalize.json()

        return invoice
    except Exception as e:
        print(f"❌ Error during invoice creation with amount: {e}")
        raise e


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
    Belirli bir fatura kimliği için öncelikle yerel diskteki (data/invoices) PDF dosyasını açmaya çalışır.
    Yerel dosya bulunamazsa veya açılırken hata alınırsa Stripe API üzerinden canlı PDF çekilir,
    yerel yola kaydedilir ve veritabanındaki pdf_path yerel yol olarak güncellenir.
    """
    # 1. Veritabanındaki pdf_path kaydı kontrolü
    db_local_path = None
    try:
        if customer_id:
            sql = "SELECT pdf_path FROM invoices WHERE stripe_invoice_id = %s AND customer_stripe_id = %s"
            params = (invoice_id, customer_id)
        else:
            sql = "SELECT pdf_path FROM invoices WHERE stripe_invoice_id = %s"
            params = (invoice_id,)

        with get_db() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        if row and row[0]:
            db_local_path = row[0]
    except Exception as e:
        print(f"⚠️ Veritabanı PDF yolu sorgu hatası ({invoice_id}): {e}")

    # 2. Yerel dosya adaylarını sırayla dene ve aç
    candidate_paths = []
    if db_local_path:
        candidate_paths.append(Path(db_local_path))
    candidate_paths.append(INVOICES_DIR / f"invoice_{invoice_id}.pdf")
    candidate_paths.append(INVOICES_DIR / f"{invoice_id}.pdf")

    for path in candidate_paths:
        if path.exists() and path.is_file():
            try:
                with open(path, "rb") as f:
                    print(f"✅ PDF yerel dosyadan açıldı: {path}")
                    return f.read()
            except Exception as file_err:
                print(f"⚠️ Yerel PDF okunurken hata ({path}): {file_err}")

    # 3. Yerel dosya yoksa Stripe API Fallback -> İndir, Yerele Kaydet, DB Güncelle
    print(f"ℹ️ Yerel PDF bulunamadı ({invoice_id}). Stripe API'den indirilip yerel dizine kaydedilecek...")
    try:
        url = f"{BASE_URL}/invoices/{invoice_id}"
        response = get(url)
        if response is None:
            return None

        invoice_data = response.json()
        
        # Müşteri güvenlik kontrolü (eğer customer_id belirtilmişse)
        if customer_id and invoice_data.get("customer") != customer_id:
            print(f"⚠️ Güvenlik uyarısı: Müşteri {customer_id}, başka müşterinin ({invoice_data.get('customer')}) faturasına erişmeye çalıştı")
            return None

        pdf_url = invoice_data.get("invoice_pdf")
        if not pdf_url:
            return None

        pdf_res = requests.get(pdf_url, timeout=20)
        if pdf_res.status_code == 200:
            target_local_path = INVOICES_DIR / f"invoice_{invoice_id}.pdf"
            try:
                with open(target_local_path, "wb") as f:
                    f.write(pdf_res.content)
                saved_local_path_str = str(target_local_path).replace("\\", "/")
                print(f"✅ PDF Stripe'tan indirildi ve yerel yola kaydedildi: {saved_local_path_str}")

                # Veritabanındaki pdf_path'i yerel yol olarak güncelle / ekle
                with get_db() as cursor:
                    cursor.execute(
                        "SELECT id FROM invoices WHERE stripe_invoice_id = %s LIMIT 1",
                        (invoice_id,),
                    )
                    r = cursor.fetchone()
                    if r:
                        cursor.execute(
                            "UPDATE invoices SET pdf_path = %s WHERE stripe_invoice_id = %s",
                            (saved_local_path_str, invoice_id),
                        )
                    else:
                        amount = invoice_data.get("total", invoice_data.get("amount_due", 0))
                        currency = invoice_data.get("currency", "usd")
                        status = invoice_data.get("status", "open")
                        cust_id = invoice_data.get("customer", customer_id or "")
                        cursor.execute(
                            "INSERT INTO invoices (stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path) VALUES (%s, %s, %s, %s, %s, %s)",
                            (invoice_id, cust_id, amount, currency, status, saved_local_path_str),
                        )
            except Exception as save_err:
                print(f"⚠️ Yerel kayıt / DB güncelleme hatası: {save_err}")

            return pdf_res.content
        return None
    except Exception as e:
        print(f"❌ Stripe API üzerinden PDF çekilirken hata: {e}")
        return None


def save_invoices_to_db(customer_id, created_gte=None, created_lte=None):
    """
    Stripe API'den müşteriye ait canlı faturaları çeker,
    PDF'lerini yerel 'data/invoices' dizinine indirir,
    MySQL 'invoices' tablosuna yerel pdf_path ile kaydeder ve günceller.
    """
    # 1. Tablonun varlığından emin ol
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS invoices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        stripe_invoice_id VARCHAR(255) NOT NULL UNIQUE,
        customer_stripe_id VARCHAR(255) NOT NULL,
        amount INT NOT NULL,
        currency VARCHAR(10) NOT NULL,
        status VARCHAR(50) NOT NULL,
        pdf_path VARCHAR(255),
        olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    try:
        with get_db() as cursor:
            cursor.execute(create_table_sql)
    except Exception as e:
        print(f"❌ invoices tablosu kontrol edilirken hata: {e}")

    # 2. Stripe API'den faturaları çek (has_more döngüsü ile tüm sayfalar)
    try:
        url = f"{BASE_URL}/invoices"
        params = {"limit": 100, "customer": customer_id}
        if created_gte:
            params["created[gte]"] = int(created_gte)
        if created_lte:
            params["created[lte]"] = int(created_lte)

        stripe_invoices = []
        while True:
            response = get(url, params=params)
            if response is None:
                return {
                    "total_fetched": 0,
                    "saved_count": 0,
                    "existing_count": 0,
                    "message": "Stripe API'den fatura çekilemedi.",
                }
            res_json = response.json()
            page_data = res_json.get("data", [])
            stripe_invoices.extend(page_data)

            if res_json.get("has_more") and page_data:
                params["starting_after"] = page_data[-1]["id"]
            else:
                break

        print(f"✅ Stripe'tan toplam {len(stripe_invoices)} fatura çekildi.")
    except Exception as e:
        print(f"❌ Stripe API error during save_invoices_to_db: {e}")
        return {
            "total_fetched": 0,
            "saved_count": 0,
            "existing_count": 0,
            "message": f"Fatura çekilirken hata oluştu: {e}",
        }

    total_fetched = len(stripe_invoices)
    saved_count = 0
    updated_count = 0

    # 3. PDF'leri indir ve yerel pdf_path ile Veritabanına kaydet / güncelle
    for inv in stripe_invoices:
        inv_id = inv.get("id")
        amount = inv.get("total", inv.get("amount_due", 0))
        currency = inv.get("currency", "usd")
        status = inv.get("status", "open")
        pdf_url = inv.get("invoice_pdf", "") or ""

        local_pdf_path_str = ""
        if pdf_url:
            pdf_filename = f"invoice_{inv_id}.pdf"
            file_path = INVOICES_DIR / pdf_filename
            try:
                if not file_path.exists():
                    pdf_res = requests.get(pdf_url, timeout=20)
                    if pdf_res.status_code == 200:
                        with open(file_path, "wb") as f:
                            f.write(pdf_res.content)
                        print(f"✅ Invoice PDF downloaded locally: {file_path}")
                        local_pdf_path_str = str(file_path).replace("\\", "/")
                    else:
                        print(f"⚠️ Could not download PDF from {pdf_url} (HTTP {pdf_res.status_code})")
                else:
                    local_pdf_path_str = str(file_path).replace("\\", "/")
            except Exception as download_err:
                print(f"⚠️ Error downloading PDF for {inv_id}: {download_err}")

        saved_pdf_path = local_pdf_path_str if local_pdf_path_str else pdf_url

        try:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT id FROM invoices WHERE stripe_invoice_id = %s LIMIT 1",
                    (inv_id,),
                )
                row = cursor.fetchone()

                if row:
                    update_sql = """
                        UPDATE invoices
                        SET pdf_path = %s, status = %s, amount = %s, currency = %s
                        WHERE stripe_invoice_id = %s
                    """
                    cursor.execute(
                        update_sql,
                        (saved_pdf_path, status, amount, currency, inv_id),
                    )
                    updated_count += 1
                else:
                    insert_sql = """
                        INSERT INTO invoices (stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        insert_sql,
                        (inv_id, customer_id, amount, currency, status, saved_pdf_path),
                    )
                    saved_count += 1
        except Exception as err:
            print(f"❌ Fatura DB kayıt hatası ({inv_id}): {err}")

    message = f"{total_fetched} fatura işlendi ({saved_count} yeni kaydedildi, {updated_count} güncellendi). PDF'ler yerel diske indirildi ve yolları kaydedildi."
    return {
        "total_fetched": total_fetched,
        "saved_count": saved_count,
        "updated_count": updated_count,
        "message": message,
    }

