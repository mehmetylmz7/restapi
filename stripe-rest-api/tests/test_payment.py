from services.payment_service import create_payment_intent
from core.utils import format_timestamp

customer_id = "cus_UnWLqlcfUCGj7z"  # yusuf kocaoglu

payment = create_payment_intent(customer_id, 3000)

if payment:
    print("\n------ PAYMENT INTENT ------")

    print(f"ID        : {payment['id']}")
    print(f"Customer  : {payment['customer']}")
    print(f"Amount    : {payment['amount'] / 100:.2f} {payment['currency'].upper()}")
    print(f"Status    : {payment['status']}")
    print(f"Created   : {format_timestamp(payment['created'])}")
