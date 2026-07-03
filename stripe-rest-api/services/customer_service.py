from stripe_client import get,post,delete
from config import BASE_URL
from database import get_connection

def get_customers(limit=10, starting_after=None):

    params = {"limit": limit}
    if starting_after:
        params["starting_after"] = starting_after

    url = f"{BASE_URL}/customers"
    response = get(url, params=params)

    if response is None:
        return None
    
    result = response.json()
    return {
        "data": result["data"],
        "has_more": result.get("has_more", False)
    }

    
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
    # 1. Stripe'a istek at
    data = {"name": name, "email": email}
    response = post(f"{BASE_URL}/customers", data=data)

    if response is None:
        return None
    
    customer = response.json()

    # 2. Veritabanına kaydet
    try:
        conn = get_connection()
        if conn:  # Bağlantının varlığını kontrol ediyoruz
            cursor = conn.cursor()
            
            # Sütun ismi 'stripe_id' olmalı!
            sql = "INSERT INTO customers (stripe_id, name, email) VALUES (%s, %s, %s)"
            values = (customer['id'], customer.get('name'), customer.get('email'))
            
            cursor.execute(sql, values) # execute methodu patlar ise conn kapanmayabilir 
            conn.commit()
            cursor.close()
            conn.close()
            print(f"✅ Customer {customer['id']} veritabanına kaydedildi.")
        else:
            print("❌ Veritabanı bağlantısı kurulamadı.")
            
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

    url= f"{BASE_URL}/customers/{customer_id}"

    response = delete(url)

    if response is None:
        return None
    
    return response.json()

