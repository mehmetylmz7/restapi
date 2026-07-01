from stripe_client import get, post
from config import BASE_URL


def create_refund(payment_intent_id, amount=None, reason=None):

    url = f"{BASE_URL}/refunds"

    data = {
        "payment_intent": payment_intent_id
    }

    if amount is not None:
        data["amount"] = int(amount)

    if reason:
        data["reason"] = reason

    response = post(url, data=data)

    if response is None:
        return None

    return response.json()


def get_refund(refund_id):

    url = f"{BASE_URL}/refunds/{refund_id}"

    response = get(url)

    if response is None:
        return None

    return response.json()


def get_refunds(payment_intent_id=None):

    url = f"{BASE_URL}/refunds"

    params = {}

    if payment_intent_id:
        params["payment_intent"] = payment_intent_id

    response = get(url, params=params)

    if response is None:
        return None

    return response.json()["data"]
