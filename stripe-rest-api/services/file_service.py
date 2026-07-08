import requests
from config import STRIPE_SECRET_KEY
from database import get_db
from logger import logger

FILES_BASE_URL = "https://files.stripe.com/v1/files"


def upload_dispute_evidence(payment_intent_id: str, file_bytes: bytes, filename: str) -> dict | None:
    """
    PDF'i Stripe Files API'ye yükler (purpose=dispute_evidence),
    sonucu MySQL'e kaydeder.

    - Stripe'a multipart/form-data olarak gönderilir.
    - Başarılıysa Stripe file nesnesi döner ve stripe_files tablosuna kaydedilir.
    - Hata durumunda None döner.
    """
    headers = {"Authorization": f"Bearer {STRIPE_SECRET_KEY}"}

    try:
        logger.info(f"Stripe'a dosya yükleniyor: {filename} (ödeme: {payment_intent_id})")
        response = requests.post(
            FILES_BASE_URL,
            headers=headers,
            files={"file": (filename, file_bytes, "application/pdf")},
            data={"purpose": "dispute_evidence"},
            timeout=30
        )
        response.raise_for_status()
        file_obj = response.json()
        logger.info(f"Stripe'a dosya yüklendi: {file_obj['id']}")
    except requests.exceptions.Timeout:
        logger.error("Stripe Files API zaman aşımı.")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Stripe Files API'ye bağlanılamadı.")
        return None
    except requests.exceptions.HTTPError as err:
        logger.error(f"Stripe Files API HTTP hatası: {err}")
        return None
    except requests.exceptions.RequestException as err:
        logger.error(f"Stripe Files API bilinmeyen hata: {err}")
        return None

    # DB'ye kaydet
    try:
        sql = """
            INSERT INTO stripe_files
                (stripe_file_id, purpose, filename, file_size, payment_intent_stripe_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            file_obj["id"],
            file_obj.get("purpose", "dispute_evidence"),
            file_obj.get("filename", filename),
            file_obj.get("size"),
            payment_intent_id or None,
        )
        with get_db() as cursor:
            cursor.execute(sql, values)
        logger.info(f"Dosya DB'ye kaydedildi: {file_obj['id']}")
    except Exception as e:
        logger.error(f"Dosya DB kayıt hatası: {e}")

    return file_obj


def list_uploaded_files(payment_intent_id: str = None) -> list:
    """
    stripe_files tablosundaki kayıtları döner.
    payment_intent_id verilirse yalnızca o ödemeye ait kayıtlar döner.
    """
    try:
        if payment_intent_id:
            sql    = "SELECT * FROM stripe_files WHERE payment_intent_stripe_id = %s ORDER BY olusturma_tarihi DESC"
            params = (payment_intent_id,)
        else:
            sql    = "SELECT * FROM stripe_files ORDER BY olusturma_tarihi DESC LIMIT 50"
            params = ()

        with get_db() as cursor:
            cursor.execute(sql, params)
            cols = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        logger.error(f"Dosya listeleme hatası: {e}")
        return []
