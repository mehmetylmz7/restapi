from stripe_client import get,post
from config import BASE_URL


def get_customers():
    url = f"{BASE_URL}/customers"
    return get(url)


def create_customer(name, email):
    data = {
        "name": name,
        "email": email
    }
    return post(f"{BASE_URL}/customers", data)
