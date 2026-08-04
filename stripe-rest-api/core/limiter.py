from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.config import REDIS_URL

# Redis tabanlı API hız sınırlayıcı (Rate Limiter)
# Redis kapalı veya erişilemez olduğunda swallow_errors=True ve in_memory_fallback_enabled=True
# sayesinde uygulama 500 hatası vermez, bellekte (in-memory) güvenle çalışmaya devam eder.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    storage_options={"socket_connect_timeout": 1.0, "socket_timeout": 1.0},
    strategy="fixed-window",
    in_memory_fallback_enabled=True,
    swallow_errors=True,
)

