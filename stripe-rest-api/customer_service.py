from stripe_client import get,post,delete
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

    response = post(
        f"{BASE_URL}/customers",
        data=data
    )

    if response is None:
        return None

    return response.json()

def get_customer(customer_id):

    url = f"{BASE_URL}/customers/{customer_id}"
    response = get(url)

    if response is None:
        return None

    return response.json()

def delete_customer(customer_id):

    url= f"{BASE_URL}/customers/{customer_id}"

    response = delete(url)

    if response is None:
        return None
    
    return response.json()

