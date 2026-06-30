from customer_service import create_customer, get_customer, get_customers,delete_customer
from product_service import get_products, get_prices, create_product, deactivate_product, get_product, create_price

from utils import format_timestamp

def show_menu():
    print("\n==============================")
    print("   Stripe Customer Manager")
    print("==============================")
    print("1 - Müşterileri Listele")
    print("2 - Müşteri Oluştur")
    print("3 - Müşteri Detayı")
    print("4 - Müşteri Sil")
    print("5 - Ürünleri Listele")
    print("6 - Ürün Oluştur")   
    print("7 - Ürün Detayı")
    print("8 - Ürünü Pasifleştir")
    print("9 - Fiyatları Listele")
    print("10 - Fiyat Oluştur")
    print("0 - Çıkış")
    

def list_customers():

    customers = get_customers()

    if not customers:
        print("\nKayıtlı müşteri bulunamadı.")
        return

    print("\n------ CUSTOMER LIST ------")

    for customer in customers:

        print(f"""
ID    : {customer['id']}
Name  : {customer.get('name', 'Unknown')}
Email : {customer.get('email', 'Unknown')}
-----------------------------
""")
        
def create_customer_menu():

    name = input("Müşteri Adı: ")
    email = input("E-posta: ")

    customer = create_customer(name, email)

    if customer:

        print("\n✅ Müşteri başarıyla oluşturuldu!")

        print(f"ID    : {customer['id']}")
        print(f"Name  : {customer['name']}")
        print(f"Email : {customer['email']}")

def show_customer_menu():

    customer_id = input("Müşteri ID: ")

    customer = get_customer(customer_id)

    if customer:

        print("\n------ CUSTOMER ------")

        print(f"ID    : {customer['id']}")
        print(f"Name  : {customer.get('name', 'Unknown')}")
        print(f"Email : {customer.get('email', 'Unknown')}")

def delete_customer_menu():

    customer_id = input("Silinecek müşteri ID: ")

    result = delete_customer(customer_id)

    if result:

        print("\n✅ Müşteri başarıyla silindi.")

        print(f"ID      : {result['id']}")
        print(f"Deleted : {result['deleted']}")

def list_products_menu():

    products = get_products()

    if not products:
        print("\nKayıtlı ürün bulunamadı.")
        return

    print("\n------ PRODUCT LIST ------")

    for product in products:

        print(f"""
ID      : {product['id']}
Name    : {product['name']}
Active  : {product['active']}
Created : {format_timestamp(product['created'])}
-----------------------------
""")

def create_product_menu():

    name = input("Ürün Adı: ")
    description = input("Açıklama: ")

    product = create_product(name, description)

    if product:

        print("\n✅ Ürün başarıyla oluşturuldu!")

        print(f"ID   : {product['id']}")
        print(f"Name : {product['name']}")

def show_product_menu():

    product_id = input("Ürün ID: ")

    product = get_product(product_id)

    if product:

        print("\n------ PRODUCT ------")

        print(f"ID          : {product['id']}")
        print(f"Name        : {product['name']}")
        print(f"Description : {product.get('description', '-')}")
        print(f"Active      : {product['active']}")

def deactivate_product_menu():

    product_id = input("Pasifleştirilecek Ürün ID: ")

    product = deactivate_product(product_id)

    if product:

        print("\n✅ Ürün pasif hale getirildi.")

        print(f"ID     : {product['id']}")
        print(f"Active : {product['active']}")

def list_prices_menu():

    product_id = input(
        "Ürün ID (boş bırakırsan tüm fiyatlar listelenir): "
    ).strip()

    prices = get_prices(product_id if product_id else None)

    if not prices:
        print("\nFiyat bulunamadı.")
        return

    print("\n------ PRICE LIST ------")

    for price in prices:

        amount = price["unit_amount"] / 100

        print(f"""
Price ID : {price['id']}
Product  : {price['product']}
Amount   : {amount:.2f} {price['currency'].upper()}
Active   : {price['active']}
-----------------------------
""")

def create_price_menu():

    product_id = input("Ürün ID: ")
    amount = float(input("Fiyat (Örn: 30.50): "))

    amount = int(amount * 100)

    currency = input("Para Birimi (USD/TRY): ").strip() or "usd"

    price = create_price(product_id, amount, currency)

    if price:

        print("\n✅ Fiyat başarıyla oluşturuldu!")

        print(f"Price ID : {price['id']}")
        print(f"Amount   : {price['unit_amount'] / 100:.2f} {price['currency'].upper()}")


def run_menu():

    while True:

        show_menu()

        choice = input("\nSeçiminiz: ")

        if choice == "1":
            list_customers()

        elif choice == "2":
            create_customer_menu()

        elif choice == "3":
            show_customer_menu()

        elif choice == "4":
            delete_customer_menu()

        elif choice == "5":
            list_products_menu()

        elif choice == "6":
            create_product_menu()

        elif choice == "7":
            show_product_menu()

        elif choice == "8":
            deactivate_product_menu()

        elif choice == "9":
            list_prices_menu()

        elif choice == "10":
            create_price_menu()

        elif choice == "0":
            print("\nProgram sonlandırıldı.")
            break

        else:
            print("\nGeçersiz seçim.")