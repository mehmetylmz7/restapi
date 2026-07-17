"""
Stripe Toplu Müşteri Aktarım Scripti
=====================================
Kullanım:
    poetry run python scripts/run_import.py

Kaynak dosyalar:
    data/json/customers.json  — ~100 kayıt
    data/csv/customers.csv    — ~100  kayıt

Aktarılan alanlar:
    name + email  (id, created vb. atlanır — Stripe yeni ID üretir)
"""

import sys
from pathlib import Path

# Proje ana dizinini Python path'ine ekle
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from core.database import init_pool
from services.bulk_import_service import (
    import_from_json,
    import_from_csv,
    save_failed_report,
)

# ── Dosya yolları ──────────────────────────────────────────────
JSON_PATH = BASE_DIR / "data" / "json" / "customers.json"
CSV_PATH = BASE_DIR / "data" / "csv" / "customers.csv"


def print_summary(results: dict) -> None:
    print("\n" + "=" * 55)
    print("           IMPORT TAMAMLANDI — ÖZET")
    print("=" * 55)
    print(f"  ✅ Başarılı  : {results['success']}")
    print(f"  ⏭  Atlanan   : {results['skipped']}")
    print(f"  ❌ Hatalı    : {results['failed']}")
    print("=" * 55)


if __name__ == "__main__":
    print("\n=== Stripe Toplu Müşteri Aktarımı ===")
    print("1 - JSON'dan aktar  (data/json/customers.json — ~1000 kayıt)")
    print("2 - CSV'den aktar   (data/csv/customers.csv  — ~100  kayıt)")
    print("q - Çıkış")

    choice = input("\nSeçiminiz (1/2/q): ").strip().lower()

    if choice not in ("1", "2"):
        print("Çıkılıyor.")
        sys.exit(0)

    # Onay al
    source = "JSON (1000 kayıt)" if choice == "1" else "CSV (100 kayıt)"
    confirm = (
        input(f"\n⚠️  {source} → Stripe'a aktarılacak. Devam edilsin mi? (evet/hayir): ")
        .strip()
        .lower()
    )

    if confirm != "evet":
        print("İptal edildi.")
        sys.exit(0)

    # Veritabanı bağlantı havuzunu başlat
    init_pool()

    # Import çalıştır
    if choice == "1":
        results = import_from_json(JSON_PATH, delay=0.3)
    else:
        results = import_from_csv(CSV_PATH, delay=0.3)

    # Özet yazdır
    print_summary(results)

    # Başarısız kayıtları dışa aktar
    if results["failed_list"]:
        failed_path = BASE_DIR / "data" / "failed_imports.csv"
        save_failed_report(results["failed_list"], output_path=str(failed_path))
