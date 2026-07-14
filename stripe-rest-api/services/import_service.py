import csv
import json
import re
import io
from services.customer_service import create_customer
from services.product_service import create_product, create_price
from services.payment_service import create_payment_intent

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

# deneme


# Dosya içeriğini okur ve sözlük listesine dönüştürür
def parse_file(file_bytes: bytes, filename: str) -> list:
    """
    Dosya uzantısına göre JSON veya CSV içeriğini okuyup sözlük listesine dönüştürür.
    """
    filename_lower = filename.lower()
    if filename_lower.endswith(".json"):
        content = file_bytes.decode("utf-8-sig")
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("JSON dosyası liste (array) formatında olmalıdır.")
        return data
    elif filename_lower.endswith(".csv"):
        content = file_bytes.decode("utf-8-sig")
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file)
        return [row for row in reader]
    else:
        raise ValueError("Yalnızca .csv veya .json uzantılı dosyalar desteklenir.")


# her bir sutunun veri tipini tahmin eder
def infer_data_types(records: list) -> dict:
    """
    Kayıt listesini inceleyerek her bir sütunun (anahtar) veri tipini tahmin eder.
    Sırasıyla email, integer, float, date ve string olarak gruplar.
    """
    if not records:
        return {}

    columns = records[0].keys()
    inferred_types = {}

    for col in columns:
        sample_values = [
            str(r.get(col)).strip() for r in records[:20] if r.get(col) is not None
        ]
        non_empty_values = [v for v in sample_values if v != ""]

        if not non_empty_values:
            inferred_types[col] = "string"
            continue

        is_email = True
        is_int = True
        is_float = True
        is_date = True

        for val in non_empty_values:
            # Email kontrolü
            if not EMAIL_REGEX.match(val):
                is_email = False
            # Integer kontrolü
            try:
                int(val)
            except ValueError:
                is_int = False
            # Float kontrolü
            try:
                float(val)
            except ValueError:
                is_float = False
            # Tarih kontrolü (YYYY-MM-DD formatı veya Unix Timestamp)
            # Basit kontrol: YYYY-MM-DD veya YYYY/MM/DD veya Unix Timestamp
            date_match = re.match(r"^\d{4}[-/]\d{2}[-/]\d{2}$", val) or (
                val.isdigit() and len(val) == 10
            )
            if not date_match:
                is_date = False

        if is_email:
            inferred_types[col] = "email"
        elif is_int:
            inferred_types[col] = "integer"
        elif is_float:
            inferred_types[col] = "float"
        elif is_date:
            inferred_types[col] = "date"
        else:
            inferred_types[col] = "string"

    return inferred_types


# Sütun eşleştirmelerini uygular, verileri doğrular ve kayıtları ayırır.
def validate_and_map_records(records: list, target_model: str, mapping: dict) -> dict:
    """
    Kullanıcının belirlediği sütun eşleştirmelerine göre kayıtları filtreler ve doğrular.
    Geçerli, geçersiz ve sistemde zaten mevcut olan kayıt listelerini döner.
    """
    valid_list = []
    invalid_list = []
    existing_list = []

    # Pre-fetch existing items from database or Stripe to check for duplicates
    existing_emails = set()
    existing_product_names = set()
    existing_payments = set()
    existing_prices = set()

    from database import get_db

    if target_model == "customers":
        try:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT email FROM customers WHERE email IS NOT NULL AND email != ''"
                )
                existing_emails = {row[0].strip().lower() for row in cursor.fetchall()}
        except Exception as e:
            print(f"Error fetching existing customer emails: {e}")

    elif target_model == "products":
        try:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT name FROM products WHERE name IS NOT NULL AND name != ''"
                )
                existing_product_names = {
                    row[0].strip().lower() for row in cursor.fetchall()
                }
        except Exception as e:
            print(f"Error fetching existing product names: {e}")

    elif target_model == "payments":
        try:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT customer_stripe_id, amount, currency FROM payment_intents"
                )
                existing_payments = {
                    (
                        row[0].strip() if row[0] else "",
                        int(row[1]),
                        row[2].strip().lower() if row[2] else "",
                    )
                    for row in cursor.fetchall()
                }
        except Exception as e:
            print(f"Error fetching existing payments: {e}")

    elif target_model == "prices":
        try:
            from services.product_service import get_prices

            prices_list = get_prices() or []
            for p in prices_list:
                p_prod = p.get("product")
                p_amount = p.get("unit_amount")
                p_curr = p.get("currency")
                if p_prod and p_amount is not None and p_curr:
                    existing_prices.add((p_prod, int(p_amount), p_curr.strip().lower()))
        except Exception as e:
            print(f"Error fetching existing prices: {e}")

    for idx, record in enumerate(records, start=1):
        mapped = {}
        errors = []

        # 1. Eşleştirmelere göre değerleri oku ve temizle
        for field, col_name in mapping.items():
            if not col_name:  # Eşleştirilmemiş alan
                mapped[field] = None
                continue
            val = record.get(col_name)
            mapped[field] = str(val).strip() if val is not None else None

        # 2. Modeline göre doğrulama yap
        if target_model == "customers":
            name = mapped.get("name")
            email = mapped.get("email")

            if not name:
                errors.append("İsim (name) alanı boş olamaz.")
            if not email:
                errors.append("E-posta (email) alanı boş olamaz.")
            elif not EMAIL_REGEX.match(email):
                errors.append("E-posta formatı geçersiz.")

        elif target_model == "products":
            name = mapped.get("name")
            price = mapped.get("price")

            if not name:
                errors.append("Ürün Adı (name) alanı boş olamaz.")
            if price:
                try:
                    price_val = float(price)
                    if price_val <= 0:
                        errors.append("Fiyat 0'dan büyük olmalıdır.")
                    mapped["price"] = price_val
                except ValueError:
                    errors.append("Fiyat geçerli bir sayı olmalıdır.")
            else:
                mapped["price"] = None

        elif target_model == "payments":
            customer_id = mapped.get("customer_id")
            amount = mapped.get("amount")

            if not customer_id:
                errors.append("Müşteri ID (customer_id) boş olamaz.")
            if not amount:
                errors.append("Tutar (amount) boş olamaz.")
            else:
                try:
                    amount_val = float(amount)
                    if amount_val <= 0:
                        errors.append("Tutar 0'dan büyük olmalıdır.")
                    mapped["amount"] = amount_val
                except ValueError:
                    errors.append("Tutar geçerli bir sayı olmalıdır.")

            # Para birimi varsayılanı
            if not mapped.get("currency"):
                mapped["currency"] = "usd"

        elif target_model == "prices":
            product_id = mapped.get("product_id")
            amount = mapped.get("amount")

            if not product_id:
                errors.append("Ürün ID (product_id) boş olamaz.")
            if not amount:
                errors.append("Tutar (amount) boş olamaz.")
            else:
                try:
                    amount_val = float(amount)
                    if amount_val <= 0:
                        errors.append("Tutar 0'dan büyük olmalıdır.")
                    mapped["amount"] = amount_val
                except ValueError:
                    errors.append("Tutar geçerli bir sayı olmalıdır.")

            # Para birimi varsayılanı
            if not mapped.get("currency"):
                mapped["currency"] = "usd"

        else:
            errors.append(f"Bilinmeyen model: {target_model}")

        if errors:
            invalid_list.append(
                {
                    "row_index": idx,
                    "raw": record,
                    "mapped": mapped,
                    "reason": ", ".join(errors),
                }
            )
        else:
            # Check duplication / existence
            is_existing = False
            if target_model == "customers":
                email_val = mapped.get("email", "").strip().lower()
                if email_val in existing_emails:
                    is_existing = True
            elif target_model == "products":
                name_val = mapped.get("name", "").strip().lower()
                if name_val in existing_product_names:
                    is_existing = True
            elif target_model == "payments":
                cust_id = mapped.get("customer_id", "").strip()
                amt = mapped.get("amount")
                curr = mapped.get("currency", "usd").strip().lower()
                try:
                    amt_cents = int(float(amt) * 100) if amt else 0
                    if (cust_id, amt_cents, curr) in existing_payments:
                        is_existing = True
                except ValueError:
                    pass
            elif target_model == "prices":
                prod_id = mapped.get("product_id", "").strip()
                amt = mapped.get("amount")
                curr = mapped.get("currency", "usd").strip().lower()
                try:
                    amt_cents = int(float(amt) * 100) if amt else 0
                    if (prod_id, amt_cents, curr) in existing_prices:
                        is_existing = True
                except ValueError:
                    pass

            if is_existing:
                existing_list.append({"row_index": idx, "mapped": mapped})
            else:
                valid_list.append({"row_index": idx, "mapped": mapped})

    return {"valid": valid_list, "invalid": invalid_list, "existing": existing_list}


# Hedef modele göre uygun servis fonksiyonunu çağırır
def execute_import_record(target_model: str, mapped_data: dict) -> dict:
    """
    Tek bir geçerli kaydı ilgili modelin oluşturma fonksiyonunu çağırarak Stripe ve DB'ye yazar.
    """
    if target_model == "customers":
        cust = create_customer(name=mapped_data["name"], email=mapped_data["email"])
        if cust and cust.get("id"):
            return {"success": True, "id": cust["id"]}
        else:
            return {"success": False, "reason": "Stripe Müşteri ID'si döndürmedi."}

    elif target_model == "products":
        prod = create_product(
            name=mapped_data["name"],
            description=mapped_data.get("description") or "",
            price=mapped_data["price"],
        )
        if prod and prod.get("id"):
            return {"success": True, "id": prod["id"]}
        else:
            return {"success": False, "reason": "Stripe Ürün ID'si döndürmedi."}

    elif target_model == "payments":
        # Stripe tutarları cent/kuruş cinsinden bekler
        amount_cents = int(float(mapped_data["amount"]) * 100)
        pay = create_payment_intent(
            customer_id=mapped_data["customer_id"],
            amount=amount_cents,
            currency=mapped_data["currency"],
            order_id=mapped_data.get("order_id"),
        )
        if pay and pay.get("id"):
            return {"success": True, "id": pay["id"]}
        else:
            return {"success": False, "reason": "Stripe Ödeme ID'si döndürmedi."}

    elif target_model == "prices":
        amount_cents = int(float(mapped_data["amount"]) * 100)
        price_obj = create_price(
            product_id=mapped_data["product_id"],
            amount=amount_cents,
            currency=mapped_data["currency"],
        )
        if price_obj and price_obj.get("id"):
            return {"success": True, "id": price_obj["id"]}
        else:
            return {"success": False, "reason": "Stripe Fiyat ID'si döndürmedi."}

    return {"success": False, "reason": f"Bilinmeyen model: {target_model}"}
