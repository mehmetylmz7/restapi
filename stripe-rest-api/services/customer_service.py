from core.stripe_client import get, post, delete
from core.config import BASE_URL
from core.database import get_db

# deneme2


def get_customers(limit=10, starting_after=None, created_gte=None, created_lte=None):

    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after
    if created_gte:
        params["created[gte]"] = created_gte
    if created_lte:
        params["created[lte]"] = created_lte

    url = f"{BASE_URL}/customers"
    response = get(url, params=params)

    if response is None:
        return None

    result = response.json()
    return {"data": result["data"], "has_more": result.get("has_more", False)}


def print_customers(customers):

    if not customers:
        print("henuz musteri bulunmuyor")
        return

    print("\n--------- Customer List --------- ")

    for customer in customers:
        print(f"""
ID    : {customer["id"]}
Name  : {customer.get("name", "Unknown")}
Email : {customer.get("email", "Unknown")}
-----------------------------
              
              
              """)


def create_customer(name, email):
    # 1. Stripe'a istek at
    data = {"name": name, "email": email}
    response = post(f"{BASE_URL}/customers", data=data)

    if response is None:
        return None

    customer = response.json()

    # 2. Veritabanına kaydet
    try:
        sql = "INSERT INTO customers (stripe_id, name, email) VALUES (%s, %s, %s)"
        values = (customer["id"], customer.get("name"), customer.get("email"))

        with get_db() as cursor:
            cursor.execute(sql, values)
        # with bloğu kapanınca commit() ve conn.close() otomatik çalışır
        print(f"✅ Customer {customer['id']} veritabanına kaydedildi.")

    except Exception as e:
        print(f"❌ Veritabanına kaydedilirken hata oluştu: {e}")

    return customer


def get_customer(customer_id):

    url = f"{BASE_URL}/customers/{customer_id}"
    response = get(url)

    if response is None:
        return None

    return response.json()


def delete_customer(customer_id):

    url = f"{BASE_URL}/customers/{customer_id}"

    response = delete(url)

    if response is None:
        return None

    return response.json()
