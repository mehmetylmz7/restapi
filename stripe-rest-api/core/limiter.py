from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.config import REDIS_URL

# Redis tabanlı API hız sınırlayıcı (Rate Limiter)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    storage_options={"socket_connect_timeout": 2.0},
    strategy="fixed-window",
)
