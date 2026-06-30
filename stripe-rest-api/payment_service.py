from stripe_client import post
from config import BASE_URL

def create_payment_intent(amount, currency="usd" ):
    
    data = {
        "amount": int(amount),
        "currency": currency.lower(),
        "automatic_payment_methods[enabled]": "true"

    }

    url=f"{BASE_URL}/payment_intents"

    response = post(
        url,
        data=data
    )

    if response is None:
        return None
    
    return response.json()