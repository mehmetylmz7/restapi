from services.product_service import get_products
from core.utils import format_timestamp


def test_get_products():
    res = get_products()
    assert res is not None
    assert "data" in res
    products = res["data"]
    assert isinstance(products, list)
    for product in products:
        print(f"""
ID      : {product["id"]}
Name    : {product["name"]}
Active  : {product["active"]}
Created : {format_timestamp(product["created"])}
""")

