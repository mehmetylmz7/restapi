from typing import Optional
from core.stripe_client import get, post, delete
from core.config import BASE_URL
from core.database import get_db
from core.redis_client import delete_cache



def sync_stripe_customers_to_db(created_gte: Optional[int] = None, created_lte: Optional[int] = None) -> dict:
    """
    Stripe API'deki tüm canlı müşterileri sayfalayarak (pagination) çeker ve
    MySQL 'customers' tablosuna (stripe_id, name, email) ekler/günceller (UPSERT).
    """
    try:
        params = {"limit": 100}
        if created_gte:
            params["created[gte]"] = int(created_gte)
        if created_lte:
            params["created[lte]"] = int(created_lte)

        all_customers = []
        while True:
            response = get(f"{BASE_URL}/customers", params=params)
            if response is None:
                break
            res_json = response.json()
            page_data = res_json.get("data", [])
            all_customers.extend(page_data)

            if res_json.get("has_more") and page_data:
                params["starting_after"] = page_data[-1]["id"]
            else:
                break

        saved_count = 0
        sql = """
            INSERT INTO customers (stripe_id, name, email)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = COALESCE(VALUES(name), name),
                email = COALESCE(VALUES(email), email)
        """
        with get_db() as cursor:
            for c in all_customers:
                cid = c.get("id")
                cname = c.get("name")
                cemail = c.get("email")
                if cid:
                    cursor.execute(sql, (cid, cname, cemail))
                    saved_count += 1

        return {
            "success": True,
            "total_fetched": len(all_customers),
            "saved_count": saved_count,
            "message": f"{len(all_customers)} müşteri Stripe API'den veritabanına senkronize edildi.",
        }
    except Exception as e:
        print(f"❌ Stripe customer sync error: {e}")
        return {"success": False, "error": str(e)}


def get_customers(limit=75, starting_after=None, created_gte=None, created_lte=None):
    """
    Stripe canlı müşterilerini veritabanı ile senkronize eder, ardından
    hem Stripe hem de yerel (CSV/JSON) kaynaklı tüm müşterileri yerel MySQL veritabanından döndürür.
    """
    # Öncesinde Stripe canlı müşterilerini veritabanı ile senkronize et
    sync_stripe_customers_to_db(created_gte=created_gte, created_lte=created_lte)

    try:
        query = "SELECT id, stripe_id, name, email, created_at FROM customers"
        conditions = []
        params = []
        
        if created_gte:
            conditions.append("created_at >= FROM_UNIXTIME(%s)")
            params.append(int(created_gte))
        if created_lte:
            conditions.append("created_at <= FROM_UNIXTIME(%s)")
            params.append(int(created_lte))
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY id DESC"
        
        with get_db() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        customers = []
        for r in rows:
            created_ts = None
            if r[4]:
                try:
                    created_ts = int(r[4].timestamp())
                except Exception:
                    pass

            customers.append({
                "id": r[1] or f"cus_local_{r[0]}",
                "stripe_id": r[1],
                "name": r[2] or "",
                "email": r[3] or "",
                "created": created_ts,
                "created_at": str(r[4]) if r[4] else "",
            })

        start_idx = 0
        if starting_after:
            for idx, c in enumerate(customers):
                if c["id"] == starting_after:
                    start_idx = idx + 1
                    break

        sliced = customers[start_idx:]
        if limit is not None and limit > 0:
            data = sliced[:limit]
            has_more = len(sliced) > limit
        else:
            data = sliced
            has_more = False

        return {"data": data, "has_more": has_more}
    except Exception as e:
        print(f"❌ Error fetching customers from DB: {e}")
        return {"data": [], "has_more": False}


def create_customer(name, email):
    # 1. Stripe'a istek at
    data = {"name": name, "email": email}
    response = post(f"{BASE_URL}/customers", data=data)

    if response is None:
        return None

    customer = response.json()

    # 2. Veritabanına kaydet (UPSERT)
    try:
        sql = """
            INSERT INTO customers (stripe_id, name, email)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                email = VALUES(email)
        """
        values = (customer["id"], customer.get("name"), customer.get("email"))

        with get_db() as cursor:
            cursor.execute(sql, values)
        print(f"✅ Customer {customer['id']} veritabanına kaydedildi.")
        delete_cache("dashboard:stats")

    except Exception as e:
        print(f"❌ Veritabanına kaydedilirken hata oluştu: {e}")

    return customer


def get_customer(customer_id):
    url = f"{BASE_URL}/customers/{customer_id}"
    response = get(url)

    if response is None:
        return None

    return response.json()


def delete_customer(customer_id):
    url = f"{BASE_URL}/customers/{customer_id}"
    response = delete(url)

    if response is None:
        return None

    res = response.json()

    if res and not res.get("error"):
        try:
            sql = "DELETE FROM customers WHERE stripe_id = %s"
            with get_db() as cursor:
                cursor.execute(sql, (customer_id,))
            print(f"✅ Customer {customer_id} veritabanından silindi.")
            delete_cache("dashboard:stats")
        except Exception as e:
            print(f"❌ Veritabanından silinirken hata oluştu: {e}")

    return res
