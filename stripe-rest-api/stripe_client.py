import requests 
from config import STRIPE_SECRET_KEY
from logger import logger

headers = {
    "Authorization": f"Bearer {STRIPE_SECRET_KEY}"
}

def get(endpoint,params=None):
    try: 
        logger.info(f"GET istegi gonderiliyor: {endpoint}")

        response = requests.get(
            endpoint, 
            headers=headers,
            params=params,
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
        logger.error(f"Http hatasi: {err}")


    except requests.exceptions.RequestException as err:
        logger.error(f"Bilinmeyen bir hata olustu: {err}")

    return None

def post(endpoint, data):
    try:
        logger.info(f"POST isteği gönderiliyor: {endpoint}")
        response = requests.post(
            endpoint, 
            headers=headers, 
            data=data, 
            timeout=10)
        response.raise_for_status()
        logger.info(f"Basarili cevap: {response.status_code}")
        return response
    except requests.exceptions.Timeout:
        logger.error("Sunucu zamanında cevap vermedi.")
    
    except requests.exceptions.ConnectionError:
        logger.error("Sunucuya bağlanılamadı.")

    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP hatası: {err}")

    except requests.exceptions.RequestException as err:
        logger.error(f"Bilinmeyen bir hata oluştu: {err}")
    return None

def delete(endpoint):
    try:
        logger.info(f"DELETE isteği gönderiliyor: {endpoint}")
        response = requests.delete(
            endpoint, 
            headers=headers, 
            timeout=10)
        
        response.raise_for_status()
        logger.info(f"Başarılı cevap: {response.status_code}")

        return response
    
    except requests.exceptions.Timeout:
        logger.error("Sunucu zamanında cevap vermedi.")

    except requests.exceptions.ConnectionError:
        logger.error("Sunucuya bağlanılamadı.")

    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP hatası: {err}")

    except requests.exceptions.RequestException as err:
        logger.error(f"Bilinmeyen bir hata oluştu: {err}")

    return None

def update(endpoint, data=None):

    if data is None:
        data = {}
    try:
        logger.info(f"UPDATE isteği gönderiliyor: {endpoint}")

        response = requests.post(
            endpoint,
            headers=headers,
            data=data,
            timeout=10
        )

        response.raise_for_status()

        logger.info(f"Başarılı cevap: {response.status_code}")

        return response
    
    except requests.exceptions.Timeout:
        logger.error("Sunucu zamanında cevap vermedi.")

    except requests.exceptions.ConnectionError:
        logger.error("Sunucuya bağlanılamadı.")

    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP hatası: {err}")

    except requests.exceptions.RequestException as err:
        logger.error(f"Bilinmeyen bir hata oluştu: {err}")

    return None