from stripe_client import get, post,update
from config import BASE_URL

def get_products():

    url = f"{BASE_URL}/products"
    response= get(url)
    
    if response is None:
        return None
    
    return response.json()["data"]

def get_product(product_id):

    url =f"{BASE_URL}/products/{product_id}"
    response = get(url)

    if response is None:
        return None
    return response.json()

def deactivate_product(product_id):

    url = f"{BASE_URL}/products/{product_id}"

    data = {
        "active": False
    }
    response = update(url, data=data)

    if response is None:
        return None
    
    return response.json()

def create_product(name, description, active=True):

    data = {
        "name": name,
        "description": description,
        "active": active
    }

    response = post(
        f"{BASE_URL}/products",
        data=data
    )

    if response is None:
        return None
    
    return response.json()

