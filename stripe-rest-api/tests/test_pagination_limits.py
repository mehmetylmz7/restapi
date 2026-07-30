import unittest
import sys
import os

# Utf-8 çıktı ayarı
sys.stdout.reconfigure(encoding='utf-8')

from api.web_api import app
from services.customer_service import get_customers
from services.product_service import get_products
from services.payment_service import get_payment_intents
from services.refund_service import get_refunds
from services.invoice_service import get_combined_invoices


class TestPaginationLimits(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    # -------------------------------------------------------------------
    # 1. Servis Düzeyi (limit=None gönderildiğinde varsayılan limit testi)
    # -------------------------------------------------------------------
    def test_customer_service_default_limit(self):
        result = get_customers(limit=None)
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        # Varsayılan limit 25'tir
        self.assertLessEqual(len(result["data"]), 25)

    def test_product_service_default_limit(self):
        result = get_products(limit=None)
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        # Varsayılan limit 10'dur
        self.assertLessEqual(len(result["data"]), 10)

    def test_payment_service_default_limit(self):
        result = get_payment_intents(limit=None)
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        # Varsayılan limit 10'dur
        self.assertLessEqual(len(result["data"]), 10)

    def test_refund_service_default_limit(self):
        result = get_refunds(limit=None)
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        # Varsayılan limit 10'dur
        self.assertLessEqual(len(result["data"]), 10)

    def test_invoice_service_default_limit(self):
        result = get_combined_invoices(limit=None)
        self.assertIsNotNone(result)
        self.assertIn("data", result)
        # Varsayılan limit 10'dur
        self.assertLessEqual(len(result["data"]), 10)

    # -------------------------------------------------------------------
    # 2. Flask Route Düzeyi - Parametresiz İstekler (Backend Kararı)
    # -------------------------------------------------------------------
    def test_route_customers_no_limit_param(self):
        res = self.client.get("/api/customers")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        # Backend varsayılan limiti olan 25 uygulanmalıdır
        self.assertLessEqual(len(data["data"]), 25)

    def test_route_products_no_limit_param(self):
        res = self.client.get("/api/products")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        # Backend varsayılan limiti olan 10 uygulanmalıdır
        self.assertLessEqual(len(data["data"]), 10)

    def test_route_payments_no_limit_param(self):
        res = self.client.get("/api/payments")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        self.assertLessEqual(len(data["data"]), 10)

    def test_route_refunds_no_limit_param(self):
        res = self.client.get("/api/refunds")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        self.assertLessEqual(len(data["data"]), 10)

    def test_route_invoices_no_limit_param(self):
        res = self.client.get("/api/invoices")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        self.assertLessEqual(len(data["data"]), 10)

    # -------------------------------------------------------------------
    # 3. Flask Route Düzeyi - Özel (Explicit) Limit İstekleri
    # -------------------------------------------------------------------
    def test_route_customers_explicit_limit(self):
        res = self.client.get("/api/customers?limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        self.assertLessEqual(len(data["data"]), 5)

    def test_route_products_explicit_limit(self):
        res = self.client.get("/api/products?limit=3")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        self.assertLessEqual(len(data["data"]), 3)

    def test_route_payments_explicit_limit(self):
        res = self.client.get("/api/payments?limit=2")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data", data)
        self.assertLessEqual(len(data["data"]), 2)


if __name__ == "__main__":
    unittest.main()
