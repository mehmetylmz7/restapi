import requests
import json

url= "https://jsonplaceholder.typicode.com/users"

response = requests.get(url)

print(response.text)