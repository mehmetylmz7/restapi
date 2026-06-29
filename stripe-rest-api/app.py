from customer_service import get_customers

response = get_customers()

if response:

    customers = response.json()

    print(customers)