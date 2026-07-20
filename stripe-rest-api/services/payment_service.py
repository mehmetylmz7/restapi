from core.stripe_client import post, get
from core.config import BASE_URL
from core.database import get_db
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
    Verilen payment_intent_id için DB'de kayıtlı PDF olup olmadığını kontrol eder.
    Giriş yapan kullanıcı kısıtlaması varsa sahipliğini de kontrol eder.
    """
    try:
        if customer_id:
            sql = """
                SELECT 1 FROM payment_pdfs p
                JOIN payment_intents i ON p.payment_intent_stripe_id = i.stripe_id
                WHERE p.payment_intent_stripe_id = %s AND i.customer_stripe_id = %s LIMIT 1
            """
            with get_db() as cursor:
                cursor.execute(sql, (payment_intent_id, customer_id))
                row = cursor.fetchone()
            if row is not None:
                return True

            # Eğer JOIN ile bulunamadıysa ama payment_pdfs tablosunda varsa, Stripe API ile sahiplik doğrula
            sql_pdf = "SELECT 1 FROM payment_pdfs WHERE payment_intent_stripe_id = %s LIMIT 1"
            with get_db() as cursor:
                cursor.execute(sql_pdf, (payment_intent_id,))
                has_pdf = cursor.fetchone() is not None

            if has_pdf:
                payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
                if payment:
                    _sync_payment_intent_to_db(payment)
                    return True
            return False
        else:
            sql = "SELECT 1 FROM payment_pdfs WHERE payment_intent_stripe_id = %s LIMIT 1"
            params = (payment_intent_id,)
            with get_db() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
            return row is not None
    except Exception as e:
        print(f"❌ PDF kontrol hatası: {e}")
        return False


def create_payment_pdf(payment_intent_id: str, force: bool = False, customer_id: str = None) -> bytes | None:
    """
    Stripe'tan ödeme detayını çeker, tek sayfalık PDF üretir ve
    MySQL payment_pdfs tablosuna LONGBLOB olarak kaydeder.
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
        # 1. Önce payment_intents tablosunu senkronize et
        _sync_payment_intent_to_db(payment)

        # 2. PDF verisini kaydet
        sql = """
            INSERT INTO payment_pdfs (payment_intent_stripe_id, pdf_data)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE pdf_data = VALUES(pdf_data)
        """
        with get_db() as cursor:
            cursor.execute(sql, (payment_intent_id, pdf_bytes))
        print(f"✅ PDF veritabanına kaydedildi: {payment_intent_id}")
    except Exception as e:
        print(f"❌ PDF DB kayıt hatası: {e}")

    return pdf_bytes


def get_payment_pdf(payment_intent_id: str, customer_id: str = None) -> bytes | None:
    """
    Daha önce oluşturulmuş PDF'i payment_pdfs tablosundan okur.
    Kayıt yoksa veya kullanıcı yetkisizse None döner.
    """
    try:
        if customer_id:
            sql = """
                SELECT p.pdf_data FROM payment_pdfs p
                JOIN payment_intents i ON p.payment_intent_stripe_id = i.stripe_id
                WHERE p.payment_intent_stripe_id = %s AND i.customer_stripe_id = %s
            """
            with get_db() as cursor:
                cursor.execute(sql, (payment_intent_id, customer_id))
                row = cursor.fetchone()

            if row:
                return row[0]

            # Eğer JOIN ile bulunamadıysa (yerel payment_intents kaydı eksikse):
            # 1. PDF yerel veritabanında var mı bak
            sql_pdf = "SELECT pdf_data FROM payment_pdfs WHERE payment_intent_stripe_id = %s"
            with get_db() as cursor:
                cursor.execute(sql_pdf, (payment_intent_id,))
                pdf_row = cursor.fetchone()

            if not pdf_row:
                return None

            # 2. PDF var, Stripe API üzerinden kullanıcının bu ödemeye erişim yetkisini doğrula
            payment = get_payment_intent(payment_intent_id, customer_id=customer_id)
            if not payment:
                return None  # Yetkisiz işlem veya ödeme bu müşteriye ait değil

            # 3. Yetkili: Yerel payment_intents veritabanını senkronize et ve PDF verisini döndür
            _sync_payment_intent_to_db(payment)
            return pdf_row[0]

        else:
            sql = "SELECT pdf_data FROM payment_pdfs WHERE payment_intent_stripe_id = %s"
            with get_db() as cursor:
                cursor.execute(sql, (payment_intent_id,))
                row = cursor.fetchone()
            return row[0] if row else None

    except Exception as e:
        print(f"❌ PDF DB okuma hatası: {e}")
        return None

