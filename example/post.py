import requests

url = "https://jsonplaceholder.typicode.com/posts"

data = {"title": "Staj", "body": "Bugün ilk günüm.", "userId": 1}

response = requests.post(url, json=data)

print(response.json())
