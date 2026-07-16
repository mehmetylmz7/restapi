import requests
from config import STRIPE_SECRET_KEY
from logger import logger

headers = {"Authorization": f"Bearer {STRIPE_SECRET_KEY}"}


def _request(method: str, endpoint: str, **kwargs):
    try:
        logger.info(f"{method} isteği gönderiliyor: {endpoint}")

        response = requests.request(method, endpoint, headers=headers, timeout=10, **kwargs)

        response.raise_for_status()

        logger.info(f"Başarılı cevap: {response.status_code}")

        return response

    except requests.exceptions.Timeout:
        logger.error(f"Sunucu zamanında cevap vermedi: {endpoint}")

    except requests.exceptions.ConnectionError:
        logger.error(f"Sunucuya bağlanılamadı: {endpoint}")

    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP hatası: {err}")

    except requests.exceptions.RequestException as err:
        logger.error(f"Bilinmeyen hata: {err}")

    return None


def get(endpoint, params=None):
    return _request("GET", endpoint, params=params)


def post(endpoint, data):
    return _request("POST", endpoint, data=data)


def delete(endpoint):
    return _request("DELETE", endpoint)


def update(endpoint, data=None):
    return _request("POST", endpoint, data=data or {})