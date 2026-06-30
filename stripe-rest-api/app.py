from customer_service import get_customers,print_customers,create_customer


def show_menu():
    print("\n==============================")
    print("   Stripe Customer Manager")
    print("==============================")
    print("1 - Müşterileri Listele")
    print("2 - Müşteri Oluştur")
    print("3 - Çıkış")


while True:

    show_menu()

    choice = input("\nSeçiminiz: ")

    if choice == "1":

        customers = get_customers()

        if not customers:
            print("\nKayıtlı müşteri bulunamadı.")
            continue

        print("\n------ CUSTOMER LIST ------")

        for customer in customers:

            print(f"""
ID    : {customer['id']}
Name  : {customer.get('name', 'Unknown')}
Email : {customer.get('email', 'Unknown')}
-----------------------------
""")

    elif choice == "2":

        name = input("Müşteri Adı: ")
        email = input("E-posta: ")

        customer = create_customer(name, email)

        if customer:
            print("\n✅ Müşteri başarıyla oluşturuldu!\n")
            print(f"ID    : {customer['id']}")
            print(f"Name  : {customer['name']}")
            print(f"Email : {customer['email']}")

    elif choice == "3":

        print("\nProgram sonlandırıldı.")
        break

    else:
        print("\nGeçersiz seçim.")

