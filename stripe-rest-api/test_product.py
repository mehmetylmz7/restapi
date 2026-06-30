from product_service import get_products ,deactivate_product, create_product
from utils import format_timestamp


products = get_products()

for product in products:

    print(f"""
ID      : {product['id']}
Name    : {product['name']}
Active  : {product['active']}
Created : {format_timestamp(product['created'])}
""")
    

