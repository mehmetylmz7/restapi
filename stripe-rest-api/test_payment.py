from payment_service import create_payment_intent

payment = create_payment_intent(3000)

if payment:
    print("\n------ PAYMENT INTENT ------")
    print(f"ID       : {payment['id']}")
    print(f"Amount   : {payment['amount'] / 100:.2f} {payment['currency'].upper()}")
    print(f"Status   : {payment['status']}")
    print(f"Customer : {payment.get('customer')}")
    print(f"Created  : {payment['created']}")