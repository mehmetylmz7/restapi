from customer_service import get_customers,print_customers,create_customer

print("=== Stripe Customer Olustur ===")

name = input("Musteri ismi giriniz: ")
email = input("Musteri email giriniz: ")

customer= create_customer(name,email)

if customer :
    print("\n --- Yeni Musteri Olusturuldu --- \n")
    print(f"ID    : {customer['id']}")
    print(f"Name  : {customer.get('name', 'Unknown')}")
    print(f"Email : {customer.get('email', 'Unknown')}")

else:
    print("Musteri olusturulurken bir hata olustu.")



