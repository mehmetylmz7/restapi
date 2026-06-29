import requests 
from config import STRIPE_SECRET_KEY
from logger import logger

headers = {
    "Authorization": f"Bearer {STRIPE_SECRET_KEY}"
}

def get(endpoint):
    try: 
        logger.info(f"GET istegi gonderiliyor: {endpoint}")

        response = requests.get(
            endpoint, 
            headers=headers,
            timeout=10
        )

        # exception firlatilir
        response.raise_for_status()

        logger.info(f"Basarili cevap: {response.status_code}")
        
        return response
    
    except requests.exceptions.Timeout:
        logger.error("sunucu zamaninda cevap vermedi. ")

    except requests.exceptions.ConnectionError:
        logger.error("sunucuya baglanilamadi. ")

    except requests.exceptions.HTTPError as err:
        logger.error("Http hatasi ", err)

    except requests.exceptions.RequestException as err:
        logger.error("Bilinmeyen bir hata olustu: ", err)

    return None

def post(endpoint, data):
    return requests.post(endpoint, headers=headers, data=data)