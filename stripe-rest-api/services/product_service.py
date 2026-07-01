from stripe_client import get, post,update
from config import BASE_URL
from database import get_connection

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
    
    product = response.json()

    # Veritabanına kaydet
    try:
        conn=get_connection()
        cursor=conn.cursor()
        sql="INSERT INTO products (stripe_id, name, description, active) VALUES (%s, %s, %s, %s)"
        values=(product['id'], product.get('name'), product.get('description'), product.get('active'))

        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Ürün veritabanına kaydedildi: {product['id']}")

    except Exception as e:
        print(f"❌ Veritabanına kaydedilirken hata oluştu: {e}")
    
    return product
    


def get_prices(product_id=None):

    url = f"{BASE_URL}/prices"
    params = {}

    if product_id:
        params["product"] = product_id

    response = get(url, params=params)

    if response is None:
        return None
    
    data = response.json().get("data", [])
    return data


def create_price(product_id, amount,currency="usd"):
    # 100 dolar icin 10000 cent olarak gonderilmelidir. Bu nedenle amount'u int'e ceviriyoruz.
    data={
        "currency": currency.lower(),
        "unit_amount": int(amount),
        "product": product_id,
        "active": True
    }
    
    url=f"{BASE_URL}/prices"

    response = post(url,data=data)

    if response is None:
        return None
    return response.json()
