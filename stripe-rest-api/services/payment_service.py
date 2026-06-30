from stripe_client import post, get
from config import BASE_URL

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
    
    return response.json()

def get_payment_intent(payment_intent_id):
    url = f"{BASE_URL}/payment_intents/{payment_intent_id}"

    response = get(url)

    if response is None:
        return None
    
    return response.json()

def get_payment_intents():

    url = f"{BASE_URL}/payment_intents"

    response = get(url)

    if response is None:
        return None

    return response.json()["data"]