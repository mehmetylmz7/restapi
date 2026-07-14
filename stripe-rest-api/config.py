from dotenv import load_dotenv
import os

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET_KEY:
    raise EnvironmentError("STRIPE_SECRET_KEY ortam değişkeni tanımlanmamış!")

BASE_URL = "https://api.stripe.com/v1"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "stripe_db")

#mongodb
MONGO_URI        = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME    = os.getenv("MONGO_DB_NAME", "stripe_logs")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "logs")

