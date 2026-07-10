from stripe_client import post, get
from config import BASE_URL
from database import get_db
from services.pdf_service import generate_payment_pdf

def create_payment_intent(customer_id, amount, currency="usd",order_id=None ):
    
    
    data = {
        "customer": customer_id,
        "amount": int(amount),
        "currency": currency.lower(),
        "automatic_payment_methods[enabled]": "true",
        "metadata[order_id]": "ORD-1001",
        "metadata[source]": "staj-project"

    }
    if order_id:
        data["metadata[order_id]"] = order_id
        
    url=f"{BASE_URL}/payment_intents"

    response = post(
        url,
        data=data
    )

    if response is None:
        return None
    
    payment = response.json()

    # 2. Veritabanına kaydet
    try:
        sql = "INSERT INTO payment_intents (stripe_id, customer_stripe_id, amount, currency, status) VALUES (%s, %s, %s, %s, %s)"
        values = (payment['id'], customer_id, payment['amount'], payment['currency'], payment['status'])

        with get_db() as cursor:
            cursor.execute(sql, values)
        print("✅ Payment intent veritabanına kaydedildi.")

    except Exception as e:
        print(f"❌ Veritabanına kaydedilirken hata oluştu: {e}")

    return payment

def get_payment_intent(payment_intent_id):
    url = f"{BASE_URL}/payment_intents/{payment_intent_id}"

    response = get(url)

    if response is None:
        return None
    
    return response.json()

def get_payment_intents(limit=10, starting_after=None):

    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after

    url = f"{BASE_URL}/payment_intents"

    response = get(url, params=params)

    if response is None:
        return None

    result = response.json()
    return {
        "data": result["data"],
        "has_more": result.get("has_more", False)
    }

def cancel_payment_intent(payment_intent_id,cancellation_reason=None): 
    
    url =f"{BASE_URL}/payment_intents/{payment_intent_id}/cancel"

    data = {}

    if cancellation_reason:
        data["cancellation_reason"] = cancellation_reason

    response = post(url,data=data)

    return response.json()


def pdf_exists(payment_intent_id: str) -> bool:
    """
    Verilen payment_intent_id için DB'de kayıtlı PDF olup olmadığını kontrol eder.
    """
    try:
        sql = "SELECT 1 FROM payment_pdfs WHERE payment_intent_stripe_id = %s LIMIT 1"
        with get_db() as cursor:
            cursor.execute(sql, (payment_intent_id,))
            row = cursor.fetchone()
        return row is not None
    except Exception as e:
        print(f"❌ PDF kontrol hatası: {e}")
        return False


def create_payment_pdf(payment_intent_id: str, force: bool = False) -> bytes | None:
    """
    Stripe'tan ödeme detayını çeker, tek sayfalık PDF üretir ve
    MySQL payment_pdfs tablosuna LONGBLOB olarak kaydeder.

    Args:
        payment_intent_id: Stripe payment intent ID'si
        force: True ise mevcut PDF üzerine yazar; False ise mevcut varsa None döner

    Returns:
        Üretilen PDF bytes'ı döner. Mevcut PDF varsa ve force=False ise None döner.
    """
    # Mevcut PDF var mı kontrol et
    if not force and pdf_exists(payment_intent_id):
        return None  # Üzerine yazma — çağıran katman zaten_var durumunu bilir

    payment = get_payment_intent(payment_intent_id)
    if payment is None:
        return None

    pdf_bytes = generate_payment_pdf(payment)

    try:
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


def get_payment_pdf(payment_intent_id: str) -> bytes | None:
    """
    Daha önce oluşturulmuş PDF'i payment_pdfs tablosundan okur.
    Kayıt yoksa None döner.
    """
    try:
        sql = "SELECT pdf_data FROM payment_pdfs WHERE payment_intent_stripe_id = %s"
        with get_db() as cursor:
            cursor.execute(sql, (payment_intent_id,))
            row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"❌ PDF DB okuma hatası: {e}")
        return None


