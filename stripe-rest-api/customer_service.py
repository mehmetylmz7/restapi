from stripe_client import get,post

BASE_URL = "https://api.stripe.com/v1"

def get_customers():
    return get(f"{BASE_URL}/customers")


def create_customer(name, email):
    data = {
        "name": name,
        "email": email
    }
    return post(f"{BASE_URL}/customers", data)
