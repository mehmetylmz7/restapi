# stripe-rest-api/mongo_log_handler.py

import logging
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


class MongoDBHandler(logging.Handler):
    """
    Python logging modülü için özel MongoDB handler.
    Her log kaydını MongoDB koleksiyonuna bir doküman olarak yazar.
    """

    def __init__(self, uri: str, db_name: str, collection: str):
        super().__init__()
        self.collection = None
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            # Bağlantıyı test et
            client.admin.command("ping")
            db = client[db_name]
            self.collection = db[collection]
            print(f"✅ MongoDB log handler bağlandı: {db_name}.{collection}")
        except ConnectionFailure as e:
            print(f"⚠️  MongoDB bağlantısı kurulamadı, log sadece dosyaya yazılacak: {e}")

    def emit(self, record: logging.LogRecord):
        """Her log kaydı için çağrılır."""
        if self.collection is None:
            return  # MongoDB yoksa sessizce geç

        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc),
                "level": record.levelname,          # INFO, ERROR, WARNING...
                "message": self.format(record),     # Formatlanmış mesaj
                "logger_name": record.name,         # logger'ın adı
                "module": record.module,            # Hangi dosyadan geldi
                "function": record.funcName,        # Hangi fonksiyondan
                "line": record.lineno,              # Kaç. satır
                "raw_message": record.getMessage(), # Ham mesaj
            }
            self.collection.insert_one(log_entry)
        except Exception as e:
            # MongoDB yazma hatası uygulamayı durdurmamalı
            print(f"⚠️  MongoDB log yazma hatası: {e}")
