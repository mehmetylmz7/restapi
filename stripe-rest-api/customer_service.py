from stripe_client import get,post
from config import BASE_URL


def get_customers(limit=10):

    params = {
        "limit": limit
    }

    url = f"{BASE_URL}/customers"
    response = get(url, params=params)

    if response is None:
        return None
    
    return response.json()["data"]

    
def print_customers(customers):

    if not customers:
        print("henuz musteri bulunmuyor")
        return
    
    print("\n--------- Customer List --------- ")

    for customer in customers:
        print(f"""
ID    : {customer['id']}
Name  : {customer.get('name', 'Unknown')}
Email : {customer.get('email', 'Unknown')}
-----------------------------
              
              
              """)


def create_customer(name, email):
    data = {
        "name": name,
        "email": email
    }
    return post(f"{BASE_URL}/customers", data)
