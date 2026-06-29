import requests

url= "https://jsonplaceholder.typicode.com/users"

response = requests.get(url)

users = response.json()

user=users[0]

print(user["name"])
print(user["email"])
print(user["address"]["city"])