from dotenv import load_dotenv
import os 

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
BASE_URL = "https://api.stripe.com/v1"