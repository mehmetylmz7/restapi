from customer_service import get_customers, create_customer

response = create_customer("zeynep", "zeynep@example.com")

print(response.status_code)
print(response.json())
