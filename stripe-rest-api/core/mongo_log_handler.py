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


def log_import_invoice_to_mongo(import_data: dict) -> bool:
    """
    İçe aktarma (Import) işlemi detaylarını 'stripe_logs' veritabanındaki
    'import_invoice_logs' koleksiyonuna doküman olarak yazar.
    """
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "stripe_logs")
    collection_name = os.getenv("MONGO_IMPORT_COLLECTION", "import_invoice_logs")

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db = client[mongo_db_name]
        collection = db[collection_name]

        successful_items = import_data.get("successful_items", [])
        invoice_ids = [
            item.get("invoice_id") or item.get("stripe_id")
            for item in successful_items
            if item.get("invoice_id") or item.get("stripe_id")
        ]
        primary_invoice_id = invoice_ids[0] if invoice_ids else None

        log_document = {
            "timestamp": datetime.now(timezone.utc),
            "filename": import_data.get("filename"),
            "target_model": import_data.get("target_model"),
            "invoice_id": primary_invoice_id,
            "invoice_ids": invoice_ids,
            "total_records": import_data.get("total_records", 0),
            "valid_records_count": import_data.get("valid_count", 0),
            "invalid_records_count": import_data.get("invalid_count", 0),
            "existing_records_count": import_data.get("existing_count", 0),
            "success_count": import_data.get("success_count", 0),
            "failed_count": import_data.get("failed_count", 0),
            "successful_items": successful_items,
            "failed_items": import_data.get("failed_items", []),
            "mapping": import_data.get("mapping", {}),
        }

        result = collection.insert_one(log_document)
        print(f"✅ İçe aktarım logu MongoDB 'import_invoice_logs' koleksiyonuna kaydedildi: ID={result.inserted_id}")
        return True
    except Exception as e:
        print(f"⚠️ MongoDB import_invoice_logs kayıt hatası: {e}")
        return False
