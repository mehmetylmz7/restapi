from stripe_client import get, post, delete
from product_service import create_price
from config import BASE_URL

create_price(product_id="prod_UnXSp1Cc17RxeM", amount=3000, currency="usd")
