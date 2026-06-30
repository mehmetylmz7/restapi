from customer_service import create_customer, get_customer, get_customers,delete_customer


def show_menu():
    print("\n==============================")
    print("   Stripe Customer Manager")
    print("==============================")
    print("1 - Müşterileri Listele")
    print("2 - Müşteri Oluştur")
    print("3 - Müşteri Detayı")
    print("4 - Müşteri Sil")
    print("5 - Çıkış")

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
            print("\nProgram sonlandırıldı.")
            break

        else:
            print("\nGeçersiz seçim.")