from customer_service import get_customers, print_customers, create_customer, get_customer ,delete_customer


def show_menu():
    print("\n==============================")
    print("   Stripe Customer Manager")
    print("==============================")
    print("1 - Müşterileri Listele")
    print("2 - Müşteri Oluştur")
    print("3 - Müşteri Detayı")
    print("4 - Müşteri Sil")
    print("5 - Çıkış")

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
-----------------------------""")

    elif choice == "2":
        name = input("Müşteri Adı: ")
        email = input("E-posta: ")
 
        response = create_customer(name, email)
        
        if response and response.status_code == 200:
            customer = response.json()
            print("\n✅ Müşteri başarıyla oluşturuldu!\n")
            print(f"ID    : {customer['id']}")
            print(f"Name  : {customer.get('name', 'Unknown')}")
            print(f"Email : {customer.get('email', 'Unknown')}")
        else:
            print("\n❌ Müşteri oluşturulamadı.")

    elif choice == "3":
        customer_id = input("Müşteri ID: ")
        customer = get_customer(customer_id)

        if customer:
            print("\n------ CUSTOMER ------")
            print(f"ID    : {customer['id']}")
            print(f"Name  : {customer.get('name', 'Unknown')}")
            print(f"Email : {customer.get('email', 'Unknown')}")
        else:
            print("\n❌ Müşteri bulunamadı.")

    elif choice == "4":
        customer_id = input("Silinecek Müşteri ID: ")
        result = delete_customer(customer_id)

        if result:
            print("\n✅ Müşteri başarıyla silindi!")
            print(f"Silinen Müşteri ID: {result['id']}")
            print(f"deleted: {result['deleted']}")
        else:
            print("\n❌ Müşteri silinemedi.")

    elif choice == "5":
        print("\nProgram sonlandırıldı.")
        break  

    else:
        print("\n⚠️ Geçersiz seçim, lütfen tekrar deneyin.")