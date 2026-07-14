import json
import csv
import time
import os

from services.customer_service import create_customer


def import_from_json(filepath: str, delay: float = 0.3) -> dict:
    """
    customers.json dosyasındaki kayıtlardan yalnızca name + email alanlarını
    okuyarak her birini create_customer() aracılığıyla Stripe'a gönderir
    ve MySQL customers tablosuna kaydeder.

    Args:
        filepath: customers.json dosyasının yolu
        delay:    Her Stripe isteği arasındaki bekleme süresi (rate limit koruması)

    Returns:
        {'success': int, 'skipped': int, 'failed': int, 'failed_list': list}
    """
    with open(filepath, "r", encoding="utf-8") as f:
        records = json.load(f)

    total = len(records)
    results = {"success": 0, "skipped": 0, "failed": 0, "failed_list": []}

    print(f"\n📂 JSON dosyası yüklendi: {total} kayıt bulundu.")
    print("=" * 55)

    for i, record in enumerate(records, start=1):
        name = (record.get("name") or "").strip()
        email = (record.get("email") or "").strip()

        # Zorunlu alanlar boşsa kayıtı atla
        if not name or not email:
            print(f"[{i}/{total}] ⏭  Atlandı — name veya email boş.")
            results["skipped"] += 1
            continue

        print(f"[{i}/{total}] Oluşturuluyor: {name} <{email}>")

        try:
            customer = create_customer(name=name, email=email)
            if customer and customer.get("id"):
                print(f"         ✅ {customer['id']}")
                results["success"] += 1
            else:
                print(f"         ❌ Stripe yanıt döndürmedi.")
                results["failed"] += 1
                results["failed_list"].append(
                    {"name": name, "email": email, "reason": "Stripe yanıtsız"}
                )
        except Exception as e:
            print(f"         ❌ Hata: {e}")
            results["failed"] += 1
            results["failed_list"].append(
                {"name": name, "email": email, "reason": str(e)}
            )

        # Rate limit koruması
        time.sleep(delay)

    return results


def import_from_csv(filepath: str, delay: float = 0.3) -> dict:
    """
    customers.csv dosyasındaki kayıtlardan yalnızca name + email alanlarını
    okuyarak her birini create_customer() aracılığıyla Stripe'a gönderir
    ve MySQL customers tablosuna kaydeder.

    Args:
        filepath: customers.csv dosyasının yolu
        delay:    Her Stripe isteği arasındaki bekleme süresi (rate limit koruması)

    Returns:
        {'success': int, 'skipped': int, 'failed': int, 'failed_list': list}
    """
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    total = len(records)
    results = {"success": 0, "skipped": 0, "failed": 0, "failed_list": []}

    print(f"\n📂 CSV dosyası yüklendi: {total} kayıt bulundu.")
    print("=" * 55)

    for i, row in enumerate(records, start=1):
        name = (row.get("name") or "").strip()
        email = (row.get("email") or "").strip()

        if not name or not email:
            print(f"[{i}/{total}] ⏭  Atlandı — name veya email boş.")
            results["skipped"] += 1
            continue

        print(f"[{i}/{total}] Oluşturuluyor: {name} <{email}>")

        try:
            customer = create_customer(name=name, email=email)
            if customer and customer.get("id"):
                print(f"         ✅ {customer['id']}")
                results["success"] += 1
            else:
                print(f"         ❌ Stripe yanıt döndürmedi.")
                results["failed"] += 1
                results["failed_list"].append(
                    {"name": name, "email": email, "reason": "Stripe yanıtsız"}
                )
        except Exception as e:
            print(f"         ❌ Hata: {e}")
            results["failed"] += 1
            results["failed_list"].append(
                {"name": name, "email": email, "reason": str(e)}
            )

        time.sleep(delay)

    return results


def save_failed_report(
    failed_list: list, output_path: str = "failed_imports.csv"
) -> None:
    """
    Başarısız import kayıtlarını CSV olarak dışa aktarır.
    """
    if not failed_list:
        return

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email", "reason"])
        writer.writeheader()
        writer.writerows(failed_list)

    print(f"\n📄 Başarısız kayıtlar '{output_path}' dosyasına yazıldı.")
