from dotenv import load_dotenv
import os 

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET_KEY:
    raise EnvironmentError("STRIPE_SECRET_KEY ortam değişkeni tanımlanmamış!")

BASE_URL = "https://api.stripe.com/v1"