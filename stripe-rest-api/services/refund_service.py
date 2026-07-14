from stripe_client import get, post
from config import BASE_URL
from database import get_db


def create_refund(payment_intent_id, amount=None, reason=None):
    url = f"{BASE_URL}/refunds"

    data = {"payment_intent": payment_intent_id}

    if amount is not None:
        data["amount"] = int(amount)

    if reason:
        data["reason"] = reason

    response = post(url, data=data)

    if response is None:
        return None

    refund = response.json()

    # MySQL'e kaydet
    try:
        sql = "INSERT INTO refunds (stripe_id, payment_intent_stripe_id, amount, currency, status, reason) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (
            refund["id"],
            refund.get("payment_intent"),
            refund.get("amount"),
            refund.get("currency"),
            refund.get("status"),
            refund.get("reason"),
        )

        with get_db() as cursor:
            cursor.execute(sql, values)
        print("✅ İade kaydı veritabanına başarıyla eklendi.")

    except Exception as e:
        print(f"❌ İade veritabanına kaydedilirken hata oluştu: {e}")

    return refund


def get_refund(refund_id):

    url = f"{BASE_URL}/refunds/{refund_id}"

    response = get(url)

    if response is None:
        return None

    return response.json()


def get_refunds(payment_intent_id=None, limit=10, starting_after=None):

    url = f"{BASE_URL}/refunds"

    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after

    if payment_intent_id:
        params["payment_intent"] = payment_intent_id

    response = get(url, params=params)

    if response is None:
        return None

    result = response.json()
    return {"data": result["data"], "has_more": result.get("has_more", False)}
