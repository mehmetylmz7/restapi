import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from core.stripe_client import post, get, delete
from core.config import BASE_URL
from core.database import get_db

try:
    from pymongo import MongoClient
except ImportError:  # pymongo bu ortamda opsiyonel bağımlılık olabilir
    MongoClient = None

# Faturalar için dizinin mevcut olduğundan emin ol
INVOICES_DIR = Path("data/invoices")
INVOICES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Ortak yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

# Stripe API isteği için fatura kalemlerini 'invoice_items[i][...]' formatına dönüştürür
def _build_indexed_items_params(items: list, price_key: str = "price") -> dict:
    """
    Stripe'a gönderilecek 'invoice_items[i][...]' tarzı indeksli parametreleri
    tek bir yerden üretir (preview / create akışları arasındaki tekrarı önler).
    """
    params = {}
    for idx, item in enumerate(items):
        params[f"invoice_items[{idx}][{price_key}]"] = item.get("price")
        params[f"invoice_items[{idx}][quantity]"] = int(item.get("quantity", 1))
    return params


# Fatura ID'sine göre yerel diskteki PDF dosya yolunu (Path) oluşturur
def _local_pdf_path(invoice_id: str) -> Path:
    return INVOICES_DIR / f"invoice_{invoice_id}.pdf"


# Stripe PDF URL'sinden dosyayı indirir ve yerel data/invoices dizinine kaydeder
def _download_pdf(pdf_url: str, invoice_id: str) -> Optional[str]:
    """
    Verilen Stripe PDF URL'sini indirir, yerel diske kaydeder ve
    kaydedilen dosyanın yolunu (string) döner. Başarısızlıkta None döner.
    """
    if not pdf_url:
        return None

    target_path = _local_pdf_path(invoice_id)
    try:
        response = requests.get(pdf_url, timeout=20)
        if response.status_code != 200:
            print(f"⚠️ PDF indirilemedi ({pdf_url}) - HTTP {response.status_code}")
            return None

        with open(target_path, "wb") as f:
            f.write(response.content)

        local_path_str = str(target_path).replace("\\", "/")
        print(f"✅ PDF indirildi ve kaydedildi: {local_path_str}")
        return local_path_str
    except Exception as e:
        print(f"⚠️ PDF indirme hatası ({invoice_id}): {e}")
        return None


# MySQL 'invoices' tablosuna fatura kaydını ekler veya mevcutsa günceller (UPSERT)
def _upsert_invoice_row(
    invoice_id: str,
    customer_id: str,
    amount: int,
    currency: str,
    status: str,
    pdf_path: str = "",
    olusturma_tarihi: Optional[str] = None,
) -> None:
    """
    'invoices' tablosuna tek bir satırı ekler ya da mevcutsa günceller.
    sync/import akışlarındaki ayrı INSERT/UPDATE bloklarının yerini alır.
    """
    olusturma_tarihi_val = None
    if olusturma_tarihi:
        olusturma_tarihi_str = str(olusturma_tarihi).strip()
        if olusturma_tarihi_str:
            if olusturma_tarihi_str.isdigit() and len(olusturma_tarihi_str) == 10:
                try:
                    ts = int(olusturma_tarihi_str)
                    olusturma_tarihi_val = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    olusturma_tarihi_val = olusturma_tarihi_str
            else:
                olusturma_tarihi_val = olusturma_tarihi_str

    if olusturma_tarihi_val:
        sql = """
            INSERT INTO invoices (stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path, olusturma_tarihi)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                amount = VALUES(amount),
                currency = VALUES(currency),
                pdf_path = IF(VALUES(pdf_path) = '', pdf_path, VALUES(pdf_path)),
                olusturma_tarihi = VALUES(olusturma_tarihi)
        """
        params = (
            invoice_id,
            customer_id,
            int(amount),
            currency.lower(),
            status.lower(),
            pdf_path,
            olusturma_tarihi_val,
        )
    else:
        sql = """
            INSERT INTO invoices (stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                amount = VALUES(amount),
                currency = VALUES(currency),
                pdf_path = IF(VALUES(pdf_path) = '', pdf_path, VALUES(pdf_path))
        """
        params = (
            invoice_id,
            customer_id,
            int(amount),
            currency.lower(),
            status.lower(),
            pdf_path,
        )

    with get_db() as cursor:
        cursor.execute(sql, params)


# ---------------------------------------------------------------------------
# Fatura önizleme / oluşturma
# ---------------------------------------------------------------------------

# Stripe Önizleme API'si ile fatura tutar ve kalemlerini simüle eder
def preview_invoice(customer_id: str, currency: str, items: list) -> Optional[dict]:
    """
    Stripe'ın Fatura Önizleme API'sini kullanarak fatura oluşturma işlemini simüle eder.
    Önizleme verilerini döndürür (ara toplam, vergi, toplam, satırlar).
    """
    url = f"{BASE_URL}/invoices/create_preview"
    data = {
        "customer": customer_id,
        "automatic_tax[enabled]": "false",  # Vergi hesaplamasını yapılandırılmadığı sürece basit tut
        **_build_indexed_items_params(items),
    }

    response = post(url, data=data)
    if response is not None:
        return response.json()

    # POST create_preview başarısız olursa ya da API sürümünde desteklenmiyorsa
    # GET /v1/invoices/upcoming yoluna geri dön
    fallback_url = f"{BASE_URL}/invoices/upcoming"
    fallback_params = {
        "customer": customer_id,
        "automatic_tax[enabled]": "false",
        **_build_indexed_items_params(items),
    }
    response = get(fallback_url, params=fallback_params)
    return response.json() if response is not None else None


# CSV/JSON ile içe aktarılan faturaları Stripe API'ye gitmeden doğrudan yerel MySQL veritabanına kaydeder
def create_local_imported_invoice(
    customer_id: str,
    amount: int,
    currency: str = "usd",
    status: str = "open",
    invoice_id: Optional[str] = None,
    olusturma_tarihi: Optional[str] = None,
) -> dict:
    """
    İthal edilen bir faturayı Stripe API'ye istek atmadan doğrudan yerel MySQL 'invoices' tablosuna kaydeder.
    """
    invoice_id = invoice_id or f"inv_imp_{uuid.uuid4().hex[:14]}"
    try:
        _upsert_invoice_row(
            invoice_id,
            customer_id,
            amount,
            currency,
            status,
            olusturma_tarihi=olusturma_tarihi,
        )
        print(f"✅ Fatura doğrudan MySQL veritabanına kaydedildi: {invoice_id}")
        return {"success": True, "id": invoice_id}
    except Exception as e:
        print(f"❌ MySQL'e fatura kaydetme hatası: {e}")
        return {"success": False, "reason": str(e)}


# Belirli bir tutar belirterek Stripe üzerinde taslak fatura ve kalemini oluşturur, gerekirse kesinleştirir
def create_invoice_with_amount(
    customer_id: str, amount: int, currency: str = "usd", status: str = "open"
) -> dict:
    """
    Tutar (kuruş/cent cinsinden) vererek Stripe üzerinde taslak fatura ve kalemi oluşturur.
    status 'draft' değilse faturayı finalize eder.
    """
    invoice = _create_draft_invoice(customer_id, currency)
    invoice_id = invoice["id"]

    item_data = {
        "customer": customer_id,
        "amount": int(amount),
        "currency": currency.lower(),
        "invoice": invoice_id,
        "description": "Fatura Kalemi",
    }
    res_item = post(f"{BASE_URL}/invoiceitems", data=item_data)
    if not res_item:
        raise RuntimeError(f"Adding invoice item with amount {amount} failed.")

    if str(status).lower() != "draft":
        return _finalize_invoice(invoice_id)

    return invoice


# Ürün kalemlerini seçerek Stripe üzerinde taslak fatura oluşturur, kalemleri ekler ve faturayı onaylar
def create_and_finalize_invoice(customer_id: str, currency: str, items: list) -> dict:
    """
    1. Taslak fatura oluşturur.
    2. Bu taslak faturaya seçilen satır kalemlerini ekler.
    3. Faturayı onaylar (PDF bağlantısı oluşturur).
    """
    invoice = _create_draft_invoice(customer_id, currency)
    invoice_id = invoice["id"]

    for item in items:
        item_data = {
            "customer": customer_id,
            "pricing[price]": item["price"],
            "quantity": int(item.get("quantity", 1)),
            "invoice": invoice_id,
        }
        res_item = post(f"{BASE_URL}/invoiceitems", data=item_data)
        if not res_item:
            raise RuntimeError(f"Adding invoice item for price {item['price']} failed.")

    return _finalize_invoice(invoice_id)


# Stripe REST API'ye HTTP POST isteği göndererek müşteri adına taslak fatura (draft invoice) açar
def _create_draft_invoice(customer_id: str, currency: str) -> dict:
    invoice_data = {"customer": customer_id, "currency": currency.lower()}
    response_invoice = post(f"{BASE_URL}/invoices", data=invoice_data)
    if not response_invoice:
        raise RuntimeError("Draft invoice creation failed on Stripe.")
    return response_invoice.json()


# Stripe üzerindeki taslak faturayı onaylar (finalize eder) ve kesinleşmiş fatura nesnesini döner
def _finalize_invoice(invoice_id: str) -> dict:
    res_finalize = post(f"{BASE_URL}/invoices/{invoice_id}/finalize", data={})
    if not res_finalize:
        raise RuntimeError("Finalizing invoice failed on Stripe.")
    return res_finalize.json()


# ---------------------------------------------------------------------------
# İçe aktarılmış (import edilmiş) faturaların tespiti (MongoDB)
# ---------------------------------------------------------------------------

# MongoDB import_invoice_logs koleksiyonunu sorgulayarak CSV/JSON ile yüklenen faturaların ID kümesini (set) döner
def check_imported_invoices(invoice_ids: list) -> set:
    """
    Stripe fatura ID listesini MongoDB 'stripe_logs.import_invoice_logs' koleksiyonunda sorgular.
    MongoDB'de olan (yani CSV/JSON ile içe aktarılmış) fatura ID'lerinin set'ini döner.
    """
    if not invoice_ids or MongoClient is None:
        return set()

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "stripe_logs")
    collection_name = os.getenv("MONGO_IMPORT_COLLECTION", "import_invoice_logs")

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        collection = client[mongo_db_name][collection_name]

        query = {
            "$or": [
                {"invoice_id": {"$in": invoice_ids}},
                {"invoice_ids": {"$in": invoice_ids}},
                {"successful_items.invoice_id": {"$in": invoice_ids}},
                {"successful_items.stripe_id": {"$in": invoice_ids}},
            ]
        }
        cursor = collection.find(query, {"invoice_id": 1, "invoice_ids": 1, "successful_items": 1})

        imported_set = set()
        invoice_id_set = set(invoice_ids)
        for doc in cursor:
            candidates = [doc.get("invoice_id")]
            candidates.extend(doc.get("invoice_ids") or [])
            candidates.extend(
                item.get("invoice_id") or item.get("stripe_id")
                for item in doc.get("successful_items", [])
            )
            imported_set.update(c for c in candidates if c in invoice_id_set)

        return imported_set
    except Exception as e:
        print(f"⚠️ MongoDB check error in get_combined_invoices: {e}")
        return set()


# ---------------------------------------------------------------------------
# Fatura listeleme (Stripe API + yerel MySQL birleşimi)
# ---------------------------------------------------------------------------

# Stripe API'den gelen fatura nesnesini ön yüzün beklediği standart sözlük formatına dönüştürür
def _format_stripe_invoice(inv: dict, source: str) -> dict:
    created_ts = inv.get("created")
    created_str = (
        datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if created_ts
        else ""
    )
    return {
        "id": inv.get("id"),
        "stripe_invoice_id": inv.get("id"),
        "customer_stripe_id": inv.get("customer"),
        "amount": inv.get("total", inv.get("amount_due", 0)),
        "currency": inv.get("currency", "usd"),
        "status": inv.get("status", "open"),
        "pdf_path": inv.get("invoice_pdf", ""),
        "olusturma_tarihi": created_str,
        "created": created_ts,
        "source": source,
        "is_imported": source == "CSV/JSON",
        "lines": inv.get("lines", {}).get("data", [])
    }


# Stripe API sonucunda bulunmayan, sadece yerel MySQL veritabanında saklanan faturaları filtreleyerek getirir
def _fetch_local_only_invoices(
    customer_id: Optional[str],
    seen_ids: set,
    created_gte: Optional[int],
    created_lte: Optional[int],
    status: Optional[str] = None,
) -> list:
    """MySQL'de olup Stripe API sonucunda görülmemiş (yalnızca yerel) faturaları döner."""
    local_invoices = []
    try:
        sql = "SELECT stripe_invoice_id, customer_stripe_id, amount, currency, status, pdf_path, olusturma_tarihi FROM invoices WHERE 1=1"
        params = []
        if customer_id:
            sql += " AND customer_stripe_id = %s"
            params.append(customer_id)
        if status:
            sql += " AND status = %s"
            params.append(status)
        sql += " ORDER BY id DESC"

        with get_db() as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        for r in rows:
            db_inv_id = r[0]
            if db_inv_id in seen_ids:
                continue

            dt_val = r[6]
            db_created_ts = None
            if dt_val:
                try:
                    db_created_ts = int(dt_val.timestamp())
                except Exception:
                    pass

            if created_gte and db_created_ts and db_created_ts < int(created_gte):
                continue
            if created_lte and db_created_ts and db_created_ts > int(created_lte):
                continue

            local_invoices.append(
                {
                    "id": db_inv_id,
                    "stripe_invoice_id": db_inv_id,
                    "customer_stripe_id": r[1],
                    "amount": r[2],
                    "currency": r[3],
                    "status": r[4],
                    "pdf_path": r[5] or "",
                    "olusturma_tarihi": str(dt_val) if dt_val else "",
                    "created": db_created_ts,
                    "source": "CSV/JSON",
                    "is_imported": True,
                    "lines": [],
                }
            )
            seen_ids.add(db_inv_id)
    except Exception as db_err:
        print(f"⚠️ MySQL faturaları çekilirken hata: {db_err}")

    return local_invoices


# Stripe canlı faturaları ile yerel MySQL faturalarını birleştirir, tarih filtresi uygular ve tarihe göre sıralar
def get_combined_invoices(
    customer_id: Optional[str] = None,
    limit: int = 10,
    starting_after: Optional[str] = None,
    created_gte: Optional[int] = None,
    created_lte: Optional[int] = None,
    status: Optional[str] = None,
) -> dict:
    """
    Stripe REST API'den canlı faturaları ve MySQL veritabanında saklanan yerel (ithal edilmiş) faturaları çeker.
    MongoDB import_invoice_logs koleksiyonunu kontrol ederek faturanın
    CSV/JSON ile mi yoksa Stripe API ile mi geldiğini belirler.
    Sayfalama (pagination) ve tarih filtreleme destekler.
    """
    try:
        params = {"limit": limit}
        if starting_after:
            params["starting_after"] = starting_after
        if customer_id:
            params["customer"] = customer_id
        if created_gte:
            params["created[gte]"] = int(created_gte)
        if created_lte:
            params["created[lte]"] = int(created_lte)
        if status:
            params["status"] = status

        response = get(f"{BASE_URL}/invoices", params=params)
        stripe_data, has_more = [], False
        if response is not None:
            res_json = response.json()
            stripe_data = res_json.get("data", [])
            has_more = res_json.get("has_more", False)

        raw_invoice_ids = [inv.get("id") for inv in stripe_data if inv.get("id")]
        imported_set = check_imported_invoices(raw_invoice_ids)

        invoices = []
        seen_ids = set()
        for inv in stripe_data:
            source = "CSV/JSON" if inv.get("id") in imported_set else "Stripe API"
            invoices.append(_format_stripe_invoice(inv, source))
            seen_ids.add(inv.get("id"))

        invoices.extend(_fetch_local_only_invoices(customer_id, seen_ids, created_gte, created_lte, status))
        invoices.sort(key=lambda x: x.get("created") or 0, reverse=True)

        return {"data": invoices, "has_more": has_more}
    except Exception as e:
        print(f"❌ Stripe API error fetching invoices: {e}")
        return {"data": [], "has_more": False}


# ---------------------------------------------------------------------------
# PDF erişimi ve senkronizasyon
# ---------------------------------------------------------------------------

# MySQL veritabanından faturaya ait kaydedilmiş PDF yerel dosya yolunu sorgular
def _get_db_pdf_path(invoice_id: str, customer_id: Optional[str]) -> Optional[str]:
    if customer_id:
        sql = "SELECT pdf_path FROM invoices WHERE stripe_invoice_id = %s AND customer_stripe_id = %s"
        params = (invoice_id, customer_id)
    else:
        sql = "SELECT pdf_path FROM invoices WHERE stripe_invoice_id = %s"
        params = (invoice_id,)

    try:
        with get_db() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        return row[0] if row and row[0] else None
    except Exception as e:
        print(f"⚠️ Veritabanı PDF yolu sorgu hatası ({invoice_id}): {e}")
        return None


# Faturanın PDF içeriğini döndürür; yerel diskte yoksa Stripe'tan canlı indirip MySQL'e kaydeder
def get_local_invoice_pdf(invoice_id: str, customer_id: Optional[str] = None) -> Optional[bytes]:
    """
    Belirli bir fatura kimliği için öncelikle yerel diskteki (data/invoices) PDF dosyasını açmaya çalışır.
    Yerel dosya bulunamazsa veya açılırken hata alınırsa Stripe API üzerinden canlı PDF çekilir,
    yerel yola kaydedilir ve veritabanındaki pdf_path yerel yol olarak güncellenir.
    """
    # 1. Olası yerel dosya yolları (DB kaydı + iki adlandırma varyasyonu)
    candidate_paths = []
    db_local_path = _get_db_pdf_path(invoice_id, customer_id)
    if db_local_path:
        candidate_paths.append(Path(db_local_path))
    candidate_paths.append(_local_pdf_path(invoice_id))
    candidate_paths.append(INVOICES_DIR / f"{invoice_id}.pdf")

    for path in candidate_paths:
        if path.exists() and path.is_file():
            try:
                with open(path, "rb") as f:
                    print(f"✅ PDF yerel dosyadan açıldı: {path}")
                    return f.read()
            except Exception as file_err:
                print(f"⚠️ Yerel PDF okunurken hata ({path}): {file_err}")

    # 2. Yerel dosya yoksa Stripe API'den çek, indir ve DB'yi güncelle
    print(f"ℹ️ Yerel PDF bulunamadı ({invoice_id}). Stripe API'den indirilip yerel dizine kaydedilecek...")
    response = get(f"{BASE_URL}/invoices/{invoice_id}")
    if response is None:
        return None

    invoice_data = response.json()

    if customer_id and invoice_data.get("customer") != customer_id:
        print(
            f"⚠️ Güvenlik uyarısı: Müşteri {customer_id}, "
            f"başka müşterinin ({invoice_data.get('customer')}) faturasına erişmeye çalıştı"
        )
        return None

    pdf_url = invoice_data.get("invoice_pdf")
    if not pdf_url:
        return None

    saved_path = _download_pdf(pdf_url, invoice_id)
    if saved_path:
        try:
            _upsert_invoice_row(
                invoice_id,
                invoice_data.get("customer", customer_id or ""),
                invoice_data.get("total", invoice_data.get("amount_due", 0)),
                invoice_data.get("currency", "usd"),
                invoice_data.get("status", "open"),
                saved_path,
            )
        except Exception as save_err:
            print(f"⚠️ DB güncelleme hatası: {save_err}")

    # DB güncellemesi başarısız olsa bile, indirilen PDF içeriğini döneriz
    pdf_path_to_read = Path(saved_path) if saved_path else None
    if pdf_path_to_read and pdf_path_to_read.exists():
        with open(pdf_path_to_read, "rb") as f:
            return f.read()
    return None


# Stripe API'deki canlı faturaları ve PDF dosyalarını çekip yerel MySQL veritabanı ile senkronize eder
def sync_stripe_invoices_to_db(
    customer_id: str, created_gte: Optional[int] = None, created_lte: Optional[int] = None
) -> dict:
    """
    Stripe API'den müşteriye ait canlı faturaları çeker,
    PDF'lerini yerel 'data/invoices' dizinine indirir,
    MySQL 'invoices' tablosuna yerel pdf_path ile kaydeder ve günceller.
    """
    try:
        stripe_invoices = _fetch_all_pages(customer_id, created_gte, created_lte)
        print(f"✅ Stripe'tan toplam {len(stripe_invoices)} fatura çekildi.")
    except Exception as e:
        print(f"❌ Stripe API error during sync_stripe_invoices_to_db: {e}")
        return {
            "total_fetched": 0,
            "saved_count": 0,
            "existing_count": 0,
            "message": f"Fatura çekilirken hata oluştu: {e}",
        }

    saved_count = 0
    updated_count = 0

    for inv in stripe_invoices:
        inv_id = inv.get("id")
        amount = inv.get("total", inv.get("amount_due", 0))
        currency = inv.get("currency", "usd")
        status = inv.get("status", "open")
        pdf_url = inv.get("invoice_pdf", "") or ""

        local_path = str(_local_pdf_path(inv_id)) if _local_pdf_path(inv_id).exists() else None
        if not local_path and pdf_url:
            local_path = _download_pdf(pdf_url, inv_id)

        is_new = _row_exists(inv_id) is False
        try:
            _upsert_invoice_row(inv_id, customer_id, amount, currency, status, local_path or pdf_url)
            if is_new:
                saved_count += 1
            else:
                updated_count += 1
        except Exception as err:
            print(f"❌ Fatura DB kayıt hatası ({inv_id}): {err}")

    total_fetched = len(stripe_invoices)
    message = (
        f"{total_fetched} fatura işlendi ({saved_count} yeni kaydedildi, {updated_count} güncellendi). "
        "PDF'ler yerel diske indirildi ve yolları kaydedildi."
    )
    return {
        "total_fetched": total_fetched,
        "saved_count": saved_count,
        "updated_count": updated_count,
        "message": message,
    }


# Stripe /v1/invoices endpoint'indeki tüm sayfaları (pagination) sonuna kadar döngüyle çeker
def _fetch_all_pages(
    customer_id: str, created_gte: Optional[int], created_lte: Optional[int]
) -> list:
    """Stripe /invoices uç noktasını has_more bitene kadar sayfalayarak tüm faturaları döner."""
    params = {"limit": 100, "customer": customer_id}
    if created_gte:
        params["created[gte]"] = int(created_gte)
    if created_lte:
        params["created[lte]"] = int(created_lte)

    all_invoices = []
    while True:
        response = get(f"{BASE_URL}/invoices", params=params)
        if response is None:
            raise RuntimeError("Stripe API'den fatura çekilemedi.")

        res_json = response.json()
        page_data = res_json.get("data", [])
        all_invoices.extend(page_data)

        if res_json.get("has_more") and page_data:
            params["starting_after"] = page_data[-1]["id"]
        else:
            break

    return all_invoices


# Belirtilen fatura ID'sinin MySQL veritabanında daha önce var olup olmadığını kontrol eder
def _row_exists(invoice_id: str) -> bool:
    with get_db() as cursor:
        cursor.execute(
            "SELECT id FROM invoices WHERE stripe_invoice_id = %s LIMIT 1", (invoice_id,)
        )
        return cursor.fetchone() is not None


def delete_invoice(invoice_id: str, customer_id: Optional[str] = None) -> dict:
    """
    Faturayı siler veya iptal eder (void).
    - Stripe'ta draft ise DELETE edilir, open ise VOID edilir.
    - Stripe faturası ise yerel veritabanında tamamen silinmez, status='void' (veya deleted) yapılır.
    - Sadece yerel (CSV) fatura ise yerel veritabanından tamamen silinir.
    """
    try:
        is_stripe = invoice_id.startswith("in_")
        
        if is_stripe:
            # Stripe API'den faturayı çek
            response = get(f"{BASE_URL}/invoices/{invoice_id}")
            if response is None:
                # Stripe'ta bulunamadıysa (örneğin daha önceden silinmişse)
                pass
            else:
                inv = response.json()
                
                # Müşteri doğrulaması
                if customer_id and inv.get("customer") != customer_id:
                    return {"success": False, "error": "Bu faturayı silme yetkiniz yok."}
                
                status = inv.get("status")
                
                if status == "draft":
                    # Stripe draft'ı silebiliriz
                    delete(f"{BASE_URL}/invoices/{invoice_id}")
                elif status in ["open", "uncollectible"]:
                    # Void (İptal)
                    post(f"{BASE_URL}/invoices/{invoice_id}/void", data={})
                elif status == "void":
                    # Zaten iptal edilmiş
                    pass
                else:
                    # Paid faturalar void edilemez doğrudan refund edilebilir vs.
                    # Eğer Stripe hata verirse catch bloğuna düşer.
                    return {"success": False, "error": f"Stripe faturası bu durumda silinemez/iptal edilemez: {status}"}
            
            # DB'de status='void' olarak güncelle (silme yapma)
            with get_db() as cursor:
                cursor.execute(
                    "UPDATE invoices SET status = 'void' WHERE stripe_invoice_id = %s",
                    (invoice_id,)
                )
        else:
            # Sadece yerel (CSV) fatura ise, yerel DB'den tamamen sil.
            # Admin vs müşteri kontrolü yerel fatura için
            with get_db() as cursor:
                if customer_id:
                    cursor.execute(
                        "DELETE FROM invoices WHERE stripe_invoice_id = %s AND customer_stripe_id = %s",
                        (invoice_id, customer_id)
                    )
                else:
                    cursor.execute(
                        "DELETE FROM invoices WHERE stripe_invoice_id = %s",
                        (invoice_id,)
                    )
        
        return {"success": True, "message": "Fatura başarıyla silindi veya iptal edildi."}
    except Exception as e:
        print(f"Delete invoice error: {e}")
        return {"success": False, "error": str(e)}