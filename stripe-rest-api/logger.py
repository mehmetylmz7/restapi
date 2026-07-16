# stripe-rest-api/logger.py  (güncellenmiş)

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from mongo_log_handler import MongoDBHandler

load_dotenv()

# ── Dizin ve dosya ayarları ───────────────────────────────────────────────────
current_dir = Path(__file__).resolve().parent
logs_dir = current_dir / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

# ── Logger oluştur ────────────────────────────────────────────────────────────
logger = logging.getLogger("stripe_api")
logger.setLevel(logging.INFO)

log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Handler 1: Dosya (mevcut, korunuyor)
file_handler = logging.FileHandler(logs_dir / "stripe_api.log")
file_handler.setFormatter(log_format)

# Handler 2: MongoDB (yeni)
mongo_uri        = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_db_name    = os.getenv("MONGO_DB_NAME", "stripe_logs")
mongo_collection = os.getenv("MONGO_COLLECTION", "logs")

mongo_handler = MongoDBHandler(
    uri=mongo_uri,
    db_name=mongo_db_name,
    collection=mongo_collection,
)
mongo_handler.setFormatter(log_format)

# Her iki handler'ı logger'a ekle
logger.addHandler(file_handler)
logger.addHandler(mongo_handler)
