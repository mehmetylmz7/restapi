import os
from celery import Celery

# Celery konfigürasyonu
def make_celery(app_name=__name__):
    broker_url = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
    backend_url = os.getenv("CELERY_RESULT_BACKEND", None) # Gerekirse eklenebilir
    
    celery = Celery(
        app_name,
        broker=broker_url,
        backend=backend_url,
        include=['tasks'] # İşçilerin (worker) görevleri nerede bulacağını belirtiyoruz
    )
    
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Europe/Istanbul',
        enable_utc=True,
    )
    
    return celery

celery = make_celery()
