from stripe_client import post, get
from config import BASE_URL
from database import get_db

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


