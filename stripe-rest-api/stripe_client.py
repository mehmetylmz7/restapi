import requests 
from config import STRIPE_SECRET_KEY

headers = {
    "Authorization": f"Bearer {STRIPE_SECRET_KEY}"
}

def get(endpoint):
    try: 
        response = requests.get(
            endpoint, 
            headers=headers,
            timeout=10
        )

        # exception firlatilir
        response.raise_for_status()
        
        return response
    
    except requests.exceptions.Timeout:
        print( "sunucu zamaninda cevap vermedi. ")

    except requests.exceptions.ConnectionError:
        print("sunucuya baglanilamadi. ")

    except requests.exceptions.HTTPError as err:
        print("Http hatasi ", err)

    except requests.exceptions.RequestException as err:
        print("Bilinmeyen bir hata olustu: ", err)

    return None

def post(endpoint, data):
    return requests.post(endpoint, headers=headers, data=data)