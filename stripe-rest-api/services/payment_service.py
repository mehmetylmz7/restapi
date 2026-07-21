from core.stripe_client import post, get
from core.config import BASE_URL
from core.database import get_db, get_tidb
from services.pdf_service import generate_payment_pdf


def create_payment_intent(customer_id, amount, currency="usd", order_id=None):

    data = {
        "customer": customer_id,
        "amount": int(amount),
        "currency": currency.lower(),
        "automatic_payment_methods[enabled]": "true",
        "metadata[order_id]": "ORD-1001",
        "metadata[source]": "staj-project",
    }
    if order_id:
        data["metadata[order_id]"] = order_id

    url = f"{BASE_URL}/payment_intents"

    response = post(url, data=data)

    if response is None:
        return None

    payment = response.json()

    # 2. Veritabanına kaydet
    try:
        sql = "INSERT INTO payment_intents (stripe_id, customer_stripe_id, amount, currency, status) VALUES (%s, %s, %s, %s, %s)"
        values = (
            payment["id"],
            customer_id,
            payment["amount"],
            payment["currency"],
            payment["status"],
        )

        with get_db() as cursor:
            cursor.execute(sql, values)
        print("✅ Payment intent veritabanına kaydedildi.")

    except Exception as e:
        print(f"❌ Veritabanına kaydedilirken hata oluştu: {e}")

    return payment


def get_payment_intent(payment_intent_id, customer_id=None):
    url = f"{BASE_URL}/payment_intents/{payment_intent_id}"

    response = get(url)

    if response is None:
        return None

    payment = response.json()
    
    # Eğer customer_id belirtilmişse ve Stripe'tan dönen müşteri eşleşmiyorsa erişimi engelle
    if customer_id and payment.get("customer") != customer_id:
        return None

    return payment


def get_payment_intents(
    limit=10, starting_after=None, created_gte=None, created_lte=None, customer_id=None
):

    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after
    if created_gte:
        params["created[gte]"] = created_gte
    if created_lte:
        params["created[lte]"] = created_lte
    if customer_id:
        params["customer"] = customer_id

    url = f"{BASE_URL}/payment_intents"

    response = get(url, params=params)

    if response is None:
        return None

    result = response.json()
    return {"data": result["data"], "has_more": result.get("has_more", False)}


def cancel_payment_intent(payment_intent_id, cancellation_reason=None, customer_id=None):
    # İptal etmeden önce sahipliği doğrula
    payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
    if not payment:
        return None

    url = f"{BASE_URL}/payment_intents/{payment_intent_id}/cancel"

    data = {}

    if cancellation_reason:
        data["cancellation_reason"] = cancellation_reason

    response = post(url, data=data)

    return response.json()


def _sync_payment_intent_to_db(payment: dict):
    """
    Stripe'tan gelen payment intent nesnesini yerel payment_intents tablosuna kaydeder/günceller.
    """
    if not payment or "id" not in payment:
        return
    try:
        sql = """
            INSERT INTO payment_intents (stripe_id, customer_stripe_id, amount, currency, status)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE customer_stripe_id = VALUES(customer_stripe_id), status = VALUES(status)
        """
        values = (
            payment["id"],
            payment.get("customer"),
            payment.get("amount"),
            payment.get("currency"),
            payment.get("status"),
        )
        with get_db() as cursor:
            cursor.execute(sql, values)
    except Exception as e:
        print(f"❌ Payment intent DB senkronizasyon hatası: {e}")


def pdf_exists(payment_intent_id: str, customer_id: str = None) -> bool:
    """
    Verilen payment_intent_id için TiDB'de kayıtlı PDF olup olmadığını kontrol eder.
    Sahiplik kontrolü için Stripe API kullanılır (JOIN yerine).
    """
    try:
        # 1. TiDB'de PDF kaydı var mı?
        with get_tidb() as cursor:
            cursor.execute(
                "SELECT 1 FROM payment_pdfs WHERE payment_intent_stripe_id = %s LIMIT 1",
                (payment_intent_id,),
            )
            has_pdf = cursor.fetchone() is not None

        if not has_pdf:
            return False

        # 2. Sahiplik kontrolü: Stripe API üzerinden doğrula
        if customer_id:
            payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
            return payment is not None  # None ise bu müşteriye ait değil

        return True
    except Exception as e:
        print(f"❌ PDF kontrol hatası: {e}")
        return False


def create_payment_pdf(payment_intent_id: str, force: bool = False, customer_id: str = None) -> bytes | None:
    """
    Stripe'tan ödeme detayını çeker, tek sayfalık PDF üretir ve
    TiDB Cloud payment_pdfs tablosuna LONGBLOB olarak kaydeder.
    """
    # Mevcut PDF var mı kontrol et
    if not force and pdf_exists(payment_intent_id, customer_id=customer_id):
        return None

    # Sahiplik kontrolü get_payment_intent içinde otomatik yapılır
    payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
    if payment is None:
        return None

    pdf_bytes = generate_payment_pdf(payment)

    try:
        # 1. Yerel MySQL payment_intents tablosunu senkronize et
        _sync_payment_intent_to_db(payment)

        # 2. PDF verisini TiDB Cloud'a kaydet
        sql = """
            INSERT INTO payment_pdfs (payment_intent_stripe_id, pdf_data)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE pdf_data = VALUES(pdf_data)
        """
        with get_tidb() as cursor:
            cursor.execute(sql, (payment_intent_id, pdf_bytes))
        print(f"✅ PDF TiDB'ye kaydedildi: {payment_intent_id}")
    except Exception as e:
        print(f"❌ TiDB PDF kayıt hatası: {e}")

    return pdf_bytes


def get_payment_pdf(payment_intent_id: str, customer_id: str = None) -> bytes | None:
    """
    Daha önce oluşturulmuş PDF'i TiDB Cloud payment_pdfs tablosundan okur.
    Sahiplik kontrolü Stripe API üzerinden yapılır (JOIN yerine).
    Kayıt yoksa veya kullanıcı yetkisizse None döner.
    """
    try:
        # 1. Sahiplik kontrolü: Stripe API üzerinden doğrula
        if customer_id:
            payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
            if not payment:
                return None  # Yetkisiz işlem veya ödeme bu müşteriye ait değil

        # 2. TiDB'den PDF verisini oku
        with get_tidb() as cursor:
            cursor.execute(
                "SELECT pdf_data FROM payment_pdfs WHERE payment_intent_stripe_id = %s",
                (payment_intent_id,),
            )
            row = cursor.fetchone()
        return row[0] if row else None

    except Exception as e:
        print(f"❌ TiDB PDF okuma hatası: {e}")
        return None

