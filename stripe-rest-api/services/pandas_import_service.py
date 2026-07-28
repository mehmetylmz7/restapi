import json
import re
import io

import pandas as pd

from services.customer_service import create_customer
from services.product_service import create_product, create_price
from services.payment_service import create_payment_intent

# E-posta doğrulama regex — infer_data_types içinde str.match() ile kullanılır
EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"


# ---------------------------------------------------------------------------
# 1. Dosya Ayrıştırma
# ---------------------------------------------------------------------------

def parse_file(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Dosya uzantısına göre JSON veya CSV içeriğini okuyup sözlük listesine
    dönüştürür.

    CSV için pd.read_csv() kullanılır:
      - encoding="utf-8-sig"  → Excel BOM karakterini otomatik temizler
      - dtype=str             → Tüm sütunlar string olarak okunur
      - keep_default_na=False → Boş hücreler NaN yerine "" olarak kalır
      - Sütun adları ve string değerler whitespace'ten arındırılır (strip).
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".json"):
        content = file_bytes.decode("utf-8-sig")
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("JSON dosyası liste (array) formatında olmalıdır.")
        return data

    elif filename_lower.endswith(".csv"):
        df = pd.read_csv(
            io.BytesIO(file_bytes),
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )

        # Sütun adlarındaki başlık/son boşlukları temizle
        df.columns = df.columns.str.strip()

        # Tüm string hücrelerdeki boşlukları temizle
        # Pandas 2.1.0 öncesi sürümler için map yerine applymap gerekebilir, 
        # uyumluluk için try-except ile güvence altına alıyoruz.
        try:
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        except AttributeError:
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        return df.to_dict("records")

    raise ValueError("Yalnızca .csv veya .json uzantılı dosyalar desteklenir.")


# ---------------------------------------------------------------------------
# 2. Veri Tipi Tahmini
# ---------------------------------------------------------------------------

def infer_data_types(records: list) -> dict:
    """
    Kayıt listesini inceleyerek her sütunun veri tipini tahmin eder.

    Pandas tabanlı yaklaşım:
      - str.match(EMAIL_REGEX)             → e-posta tespiti
      - pd.to_numeric(errors="coerce")     → sayısal tip tespiti
      - pd.to_datetime(errors="coerce")    → tarih tespiti
      - Hiçbiri eşleşmezse "string"
    """
    if not records:
        return {}

    df = pd.DataFrame(records)
    inferred: dict = {}

    for col in df.columns:
        # Boş string değerleri NaN'a çevir ve düşür
        values = df[col].replace("", pd.NA).dropna()

        if values.empty:
            inferred[col] = "string"
            continue

        # --- E-posta kontrolü ---
        if values.str.match(EMAIL_REGEX).all():
            inferred[col] = "email"
            continue

        # --- Sayısal kontrol (integer / float) ---
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.notna().all():
            if (numeric % 1 == 0).all():
                inferred[col] = "integer"
            else:
                inferred[col] = "float"
            continue

        # --- Tarih kontrolü ---
        if pd.to_datetime(values, errors="coerce").notna().all():
            inferred[col] = "date"
            continue

        # --- Varsayılan ---
        inferred[col] = "string"

    return inferred


# ---------------------------------------------------------------------------
# 3. Kayıt Doğrulama ve Eşleştirme
# ---------------------------------------------------------------------------

def validate_and_map_records(records: list, target_model: str, mapping: dict) -> dict:
    """
    Kullanıcının belirlediği sütun eşleştirmelerine göre kayıtları filtreler
    ve doğrular.

    Sayısal dönüşümler performans için (döngü içinde Pandas overhead'inden 
    kaçınmak adına) standart Python try-except yapısı ile yönetilir.
    """
    valid_list: list = []
    invalid_list: list = []
    existing_list: list = []

    existing_emails: set = set()
    existing_product_names: set = set()
    existing_payments: set = set()
    existing_prices: set = set()
    existing_invoices: set = set()

    from core.database import get_db

    if target_model == "customers":
        try:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT email FROM customers WHERE email IS NOT NULL AND email != ''"
                )
                existing_emails = {row[0].strip().lower() for row in cursor.fetchall()}
        except Exception as e:
            import logging
            logging.error(f"Error fetching existing customer emails: {e}")

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
            import logging
            logging.error(f"Error fetching existing product names: {e}")

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
            import logging
            logging.error(f"Error fetching existing payments: {e}")

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
            import logging
            logging.error(f"Error fetching existing prices: {e}")

    elif target_model == "invoices":
        try:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT customer_stripe_id, amount, currency, olusturma_tarihi FROM invoices"
                )
                existing_invoices = set()
                for row in cursor.fetchall():
                    c_id = row[0].strip() if row[0] else ""
                    amt = int(row[1]) if row[1] is not None else 0
                    curr = row[2].strip().lower() if row[2] else ""
                    dt = row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else ""
                    existing_invoices.add((c_id, amt, curr, dt))
        except Exception as e:
            import logging
            logging.error(f"Error fetching existing invoices: {e}")


    for idx, record in enumerate(records, start=1):
        mapped: dict = {}
        errors: list = []

        # 1. Eşleştirmelere göre değerleri oku ve temizle
        for field, col_name in mapping.items():
            if not col_name:
                mapped[field] = None
                continue
            val = record.get(col_name)
            mapped[field] = str(val).strip() if val is not None else None

        # 2. Modeline göre doğrulama — Saf Python dönüşümleri ile (Hızlı)
        if target_model == "customers":
            name = mapped.get("name")
            email = mapped.get("email")

            if not name:
                errors.append("İsim (name) alanı boş olamaz.")
            if not email:
                errors.append("E-posta (email) alanı boş olamaz.")
            elif not re.match(EMAIL_REGEX, email):
                errors.append("E-posta formatı geçersiz.")

        elif target_model == "products":
            name = mapped.get("name")
            price_raw = mapped.get("price")

            if not name:
                errors.append("Ürün Adı (name) alanı boş olamaz.")
            if price_raw:
                try:
                    price_val = float(price_raw)
                    if price_val <= 0:
                        errors.append("Fiyat 0'dan büyük olmalıdır.")
                    else:
                        mapped["price"] = price_val
                except ValueError:
                    errors.append("Fiyat geçerli bir sayı olmalıdır.")
            else:
                mapped["price"] = None

        elif target_model == "payments":
            customer_id = mapped.get("customer_id")
            amount_raw = mapped.get("amount")

            if not customer_id:
                errors.append("Müşteri ID (customer_id) boş olamaz.")
            if not amount_raw:
                errors.append("Tutar (amount) boş olamaz.")
            else:
                try:
                    amount_val = float(amount_raw)
                    if amount_val <= 0:
                        errors.append("Tutar 0'dan büyük olmalıdır.")
                    else:
                        mapped["amount"] = amount_val
                except ValueError:
                    errors.append("Tutar geçerli bir sayı olmalıdır.")

            if not mapped.get("currency"):
                mapped["currency"] = "usd"

        elif target_model == "prices":
            product_id = mapped.get("product_id")
            amount_raw = mapped.get("amount")

            if not product_id:
                errors.append("Ürün ID (product_id) boş olamaz.")
            if not amount_raw:
                errors.append("Tutar (amount) boş olamaz.")
            else:
                try:
                    amount_val = float(amount_raw)
                    if amount_val <= 0:
                        errors.append("Tutar 0'dan büyük olmalıdır.")
                    else:
                        mapped["amount"] = amount_val
                except ValueError:
                    errors.append("Tutar geçerli bir sayı olmalıdır.")

            if not mapped.get("currency"):
                mapped["currency"] = "usd"

        elif target_model == "invoices":
            customer_stripe_id = mapped.get("customer_stripe_id")
            amount_raw = mapped.get("amount")

            if not customer_stripe_id:
                errors.append("Müşteri ID (customer_stripe_id) boş olamaz.")
            if not amount_raw:
                errors.append("Tutar (amount) boş olamaz.")
            else:
                try:
                    amount_val = float(amount_raw)
                    if amount_val <= 0:
                        errors.append("Tutar 0'dan büyük olmalıdır.")
                    else:
                        mapped["amount"] = amount_val
                except ValueError:
                    errors.append("Tutar geçerli bir sayı olmalıdır.")

            if not mapped.get("currency"):
                mapped["currency"] = "usd"
            if not mapped.get("status"):
                mapped["status"] = "open"

        else:
            errors.append(f"Bilinmeyen model: {target_model}")

        # 3. Geçersiz kayıtları ayır
        if errors:
            invalid_list.append(
                {
                    "row_index": idx,
                    "raw": record,
                    "mapped": mapped,
                    "reason": ", ".join(errors),
                }
            )
            continue

        # 4. Duplicate / mevcut kayıt kontrolü
        is_existing = False

        if target_model == "customers":
            if mapped.get("email", "").strip().lower() in existing_emails:
                is_existing = True

        elif target_model == "products":
            if mapped.get("name", "").strip().lower() in existing_product_names:
                is_existing = True

        elif target_model == "payments":
            cust_id = mapped.get("customer_id", "").strip()
            amt_val = mapped.get("amount")
            curr = mapped.get("currency", "usd").strip().lower()
            if amt_val is not None:
                # KRİTİK DÜZELTME: Kuruşa/cent'e çevirirken precision kaybını önlemek için round kullanıldı
                amt_cents = int(round(amt_val * 100))
                if (cust_id, amt_cents, curr) in existing_payments:
                    is_existing = True

        elif target_model == "prices":
            prod_id = mapped.get("product_id", "").strip()
            amt_val = mapped.get("amount")
            curr = mapped.get("currency", "usd").strip().lower()
            if amt_val is not None:
                amt_cents = int(round(amt_val * 100))
                if (prod_id, amt_cents, curr) in existing_prices:
                    is_existing = True

        elif target_model == "invoices":
            cust_id = mapped.get("customer_stripe_id", "").strip()
            amt_val = mapped.get("amount")
            curr = mapped.get("currency", "usd").strip().lower()
            
            # format the mapped date to ensure it matches the database string representation
            dt_raw = mapped.get("olusturma_tarihi")
            dt = ""
            if dt_raw:
                try:
                    import pandas as pd
                    dt = pd.to_datetime(dt_raw).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    dt = str(dt_raw).strip()
            
            if amt_val is not None:
                amt_cents = int(round(amt_val * 100))
                if (cust_id, amt_cents, curr, dt) in existing_invoices:
                    is_existing = True

        if is_existing:
            existing_list.append({"row_index": idx, "mapped": mapped})
        else:
            valid_list.append({"row_index": idx, "mapped": mapped})

    return {"valid": valid_list, "invalid": invalid_list, "existing": existing_list}


# ---------------------------------------------------------------------------
# 4. Kayıt Çalıştırma — Stripe & DB Yazma
# ---------------------------------------------------------------------------

def execute_import_record(target_model: str, mapped_data: dict) -> dict:
    """
    Tek bir geçerli kaydı ilgili modelin oluşturma fonksiyonunu çağırarak
    Stripe ve DB'ye yazar. 
    """
    if target_model == "customers":
        cust = create_customer(name=mapped_data["name"], email=mapped_data["email"])
        if cust and cust.get("id"):
            return {"success": True, "id": cust["id"]}
        return {"success": False, "reason": "Stripe Müşteri ID'si döndürmedi."}

    elif target_model == "products":
        prod = create_product(
            name=mapped_data["name"],
            description=mapped_data.get("description") or "",
            price=mapped_data["price"],
        )
        if prod and prod.get("id"):
            return {"success": True, "id": prod["id"]}
        return {"success": False, "reason": "Stripe Ürün ID'si döndürmedi."}

    elif target_model == "payments":
        # KRİTİK DÜZELTME: Yuvarlama hatasını önlemek için round eklendi
        amount_cents = int(round(float(mapped_data["amount"]) * 100))
        pay = create_payment_intent(
            customer_id=mapped_data["customer_id"],
            amount=amount_cents,
            currency=mapped_data["currency"],
            order_id=mapped_data.get("order_id"),
        )
        if pay and pay.get("id"):
            return {"success": True, "id": pay["id"]}
        return {"success": False, "reason": "Stripe Ödeme ID'si döndürmedi."}

    elif target_model == "prices":
        amount_cents = int(round(float(mapped_data["amount"]) * 100))
        price_obj = create_price(
            product_id=mapped_data["product_id"],
            amount=amount_cents,
            currency=mapped_data["currency"],
        )
        if price_obj and price_obj.get("id"):
            return {"success": True, "id": price_obj["id"]}
        return {"success": False, "reason": "Stripe Fiyat ID'si döndürmedi."}

    elif target_model == "invoices":
        amount_cents = int(round(float(mapped_data["amount"]) * 100))
        from services.invoice_service import create_local_imported_invoice

        res = create_local_imported_invoice(
            customer_id=mapped_data["customer_stripe_id"],
            amount=amount_cents,
            currency=mapped_data["currency"],
            status=mapped_data.get("status", "open"),
            invoice_id=mapped_data.get("stripe_invoice_id") or mapped_data.get("invoice_id"),
            olusturma_tarihi=mapped_data.get("olusturma_tarihi") or mapped_data.get("created_at"),
        )
        return res

    return {"success": False, "reason": f"Bilinmeyen model: {target_model}"}