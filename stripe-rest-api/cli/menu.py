from services.customer_service import (
    create_customer,
    get_customer,
    get_customers,
    delete_customer,
)
from services.product_service import (
    get_products,
    get_prices,
    create_product,
    deactivate_product,
    get_product,
    create_price,
)
from services.payment_service import (
    create_payment_intent,
    get_payment_intent,
    get_payment_intents,
    cancel_payment_intent,
)
from services.refund_service import create_refund, get_refund, get_refunds

from core.utils import format_timestamp


def show_menu():
    print("\n===================================")
    print("      Stripe REST API Manager")
    print("===================================")

    print("\n----- Customer -----")
    print("1 - Müşterileri Listele")
    print("2 - Müşteri Oluştur")
    print("3 - Müşteri Detayı")
    print("4 - Müşteri Sil")

    print("\n----- Product -----")
    print("5 - Ürünleri Listele")
    print("6 - Ürün Oluştur")
    print("7 - Ürün Detayı")
    print("8 - Ürünü Pasifleştir")
    print("9 - Fiyatları Listele")
    print("10 - Fiyat Oluştur")

    print("\n----- Payment -----")
    print("11 - Ödeme Oluştur")
    print("12 - Ödemeleri Listele")
    print("13 - Ödeme Detayı")
    print("14 - Ödemeyi İptal Et")

    print("\n----- Refund -----")
    print("15 - İade Oluştur")
    print("16 - İadeleri Listele")
    print("17 - İade Detayı")

    print("\n0 - Çıkış")


def list_customers():

    customers = get_customers()

    if not customers:
        print("\nKayıtlı müşteri bulunamadı.")
        return

    print("\n------ CUSTOMER LIST ------")

    for customer in customers:
        print(f"""
ID    : {customer["id"]}
Name  : {customer.get("name", "Unknown")}
Email : {customer.get("email", "Unknown")}
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
ID      : {product["id"]}
Name    : {product["name"]}
Active  : {product["active"]}
Created : {format_timestamp(product["created"])}
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

    product_id = input("Ürün ID (boş bırakırsan tüm fiyatlar listelenir): ").strip()

    prices = get_prices(product_id if product_id else None)

    if not prices:
        print("\nFiyat bulunamadı.")
        return

    print("\n------ PRICE LIST ------")

    for price in prices:
        amount = price["unit_amount"] / 100

        print(f"""
Price ID : {price["id"]}
Product  : {price["product"]}
Amount   : {amount:.2f} {price["currency"].upper()}
Active   : {price["active"]}
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
        print(
            f"Amount   : {price['unit_amount'] / 100:.2f} {price['currency'].upper()}"
        )


def list_payments():

    payments = get_payment_intents()

    if not payments:
        print("\nKayıtlı ödeme bulunamadı.")
        return

    print("\n------ PAYMENT INTENT LIST ------")

    for payment in payments:
        print(f"""
ID       : {payment["id"]}
Customer : {payment.get("customer", "-")}
Amount   : {payment["amount"] / 100:.2f} {payment["currency"].upper()}
Status   : {payment["status"]}
Created  : {format_timestamp(payment["created"])}
-----------------------------
""")


def show_payment():

    payment_id = input("Payment Intent ID: ")

    payment = get_payment_intent(payment_id)

    if payment:
        print("\n------ PAYMENT DETAIL ------")

        print(f"ID              : {payment['id']}")
        print(f"Customer        : {payment.get('customer', '-')}")
        print(
            f"Amount          : {payment['amount'] / 100:.2f} {payment['currency'].upper()}"
        )
        print(f"Status          : {payment['status']}")
        print(f"Capture Method  : {payment['capture_method']}")
        print(f"Created         : {format_timestamp(payment['created'])}")

        print("\nPayment Methods:")

        for method in payment["payment_method_types"]:
            print(f" - {method}")


def create_payment_menu():

    customer_id = input("Müşteri ID: ")

    amount = float(input("Tutar (Örn: 30.50): "))
    amount = int(amount * 100)

    currency = input("Para Birimi (USD/TRY): ").strip() or "usd"

    payment = create_payment_intent(customer_id, amount, currency)

    if payment:
        print("\n✅ Ödeme Intent başarıyla oluşturuldu!")

        print(f"ID       : {payment['id']}")
        print(f"Customer : {payment.get('customer', '-')}")
        print(f"Amount   : {payment['amount'] / 100:.2f} {payment['currency'].upper()}")
        print(f"Status   : {payment['status']}")
        print(f"Created  : {format_timestamp(payment['created'])}")


def cancel_payment_menu():

    payment_id = input("İptal edilecek Payment Intent ID: ").strip()
    reason = input("İptal nedeni (opsiyonel): ").strip() or None

    payment = cancel_payment_intent(payment_id, reason)

    if payment:
        print("\n✅ Ödeme Intent başarıyla iptal edildi!")

        print(f"ID       : {payment.get('id', '-')}")
        print(f"Status   : {payment.get('status', '-')}")
        print(f"Reason   : {payment.get('cancellation_reason', '-')}")
    else:
        print("\nİşlem başarısız oldu.")


def create_refund_menu():

    payment_intent_id = input("Payment Intent ID: ").strip()
    amount = input("Tutar (opsiyonel, boş bırakılırsa tam tutar): ").strip()

    print("\nİade Nedeni Seçin:")
    print("1 - duplicate")
    print("2 - fraudulent")
    print("3 - requested_by_customer")
    print("4 - Boş bırak")

    reasons = {"1": "duplicate", "2": "fraudulent", "3": "requested_by_customer"}

    choice = input("Seçim: ").strip()
    reason = reasons.get(choice)

    try:
        refund_amount = int(float(amount) * 100) if amount else None
    except ValueError:
        print("\nGeçersiz tutar girişi. Tam tutar kullanılacak.")
        refund_amount = None

    refund = create_refund(payment_intent_id, refund_amount, reason)

    if refund:
        print("\n✅ İade başarıyla oluşturuldu!")
        print(f"ID       : {refund.get('id', '-')}")
        print(f"Status   : {refund.get('status', '-')}")
        print(
            f"Amount   : {refund.get('amount', 0) / 100:.2f} {refund.get('currency', 'USD').upper()}"
        )
    else:
        print("\nİşlem başarısız oldu.")


def list_refunds_menu():

    payment_intent_id = (
        input("Payment Intent ID (opsiyonel, boş bırakılırsa tüm iadeler): ").strip()
        or None
    )
    refunds = get_refunds(payment_intent_id)

    if not refunds:
        print("\nİade bulunamadı.")
        return

    print("\n------ REFUND LIST ------")

    for refund in refunds:
        print(f"""
ID       : {refund["id"]}
Payment  : {refund.get("payment_intent", "-")}
Amount   : {refund.get("amount", 0) / 100:.2f} {refund.get("currency", "USD").upper()}
Status   : {refund.get("status", "-")}
-----------------------------
""")


def show_refund_menu():

    refund_id = input("Refund ID: ").strip()
    refund = get_refund(refund_id)

    if refund:
        print("\n------ REFUND DETAIL ------")
        print(f"ID       : {refund.get('id', '-')}")
        print(f"Payment  : {refund.get('payment_intent', '-')}")
        print(
            f"Amount   : {refund.get('amount', 0) / 100:.2f} {refund.get('currency', 'USD').upper()}"
        )
        print(f"Status   : {refund.get('status', '-')}")
        print(f"Reason   : {refund.get('reason', '-')}")
    else:
        print("\nİade bulunamadı.")


def run_menu():

    while True:
        show_menu()

        choice = input("\nSeçiminiz: ")

        # Customer Operations
        if choice == "1":
            list_customers()

        elif choice == "2":
            create_customer_menu()

        elif choice == "3":
            show_customer_menu()

        elif choice == "4":
            delete_customer_menu()

        # Product Operations
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

        # Payment Operations
        elif choice == "11":
            create_payment_menu()

        elif choice == "12":
            list_payments()

        elif choice == "13":
            show_payment()

        elif choice == "14":
            cancel_payment_menu()

        elif choice == "15":
            create_refund_menu()

        elif choice == "16":
            list_refunds_menu()

        elif choice == "17":
            show_refund_menu()

        elif choice == "0":
            print("\nÇıkış yapılıyor...")
            break

        else:
            print("\nGeçersiz seçim.")
