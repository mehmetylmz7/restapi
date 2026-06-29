from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

secret_key = os.getenv("STRIPE_SECRET_KEY")

url= "https://api.stripe.com/v1/customers"

headers = {
    "Authorization": f"Bearer {secret_key}"
}

# stripe bu endpoint icin form verisi bekliyor

data = {
    "name": "Mehmet Yilmaz",
    "email": "mehmet.yilmaz@example.com"
}

data2 = {
    "name": "Zeynep Yilmaz",
    "email": "zeynep.yilmaz@example.com"
}

response = requests.post(url, headers=headers, data=data2)

response_json = response.json()
print(json.dumps(response_json, indent=4))