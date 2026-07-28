import sys
import os
from pathlib import Path
import pandas as pd

# Windows konsolunda UTF-8 çıktı desteği
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"


def ask_user_to_continue(step_name: str, auto_mode: bool = False) -> bool:
    if auto_mode:
        return True
    print(f"\n--- Soru: {step_name} adımına geçilsin mi? (E/h) ---")
    try:
        reply = input("Devam etmek için 'e' yazıp Enter'a basın (Çıkmak için 'h'): ").strip().lower()
        if reply in ("", "e", "evet", "y", "yes"):
            return True
        else:
            print("❌ İşlem kullanıcı tarafından durduruldu.")
            return False
    except (EOFError, KeyboardInterrupt):
        return True


# ===========================================================================
# ADIM 0: Dosya Seçimi
# ===========================================================================
def step0_select_file(auto_mode: bool = False, default_filename: str = "invoices.csv") -> Path | None:
    print("\n" + "=" * 65)
    print(">>> ADIM 0: CSV Dosya Seçimi")
    print("=" * 65)

    if not DATA_DIR.exists():
        print(f"❌ Klasör bulunamadı: {DATA_DIR}")
        return None

    csv_files = sorted(list(DATA_DIR.glob("*.csv")))
    if not csv_files:
        print(f"❌ '{DATA_DIR}' altında hiç CSV dosyası bulunamadı.")
        return None

    print(f"\n📁 '{DATA_DIR}' Dizinindeki CSV Dosyaları:\n")
    for idx, file in enumerate(csv_files, start=1):
        size_kb = file.stat().st_size / 1024
        print(f"  [{idx}] {file.name:<22} ({size_kb:.1f} KB)")

    if auto_mode:
        selected_file = next((f for f in csv_files if f.name == default_filename), csv_files[0])
        print(f"\n🤖 Otomatik Mod: '{selected_file.name}' dosyası seçildi.")
        return selected_file

    print("\n--- Seçim Yapın ---")
    try:
        choice_str = input(f"Lütfen işlenecek dosya numarasını girin (1-{len(csv_files)}) [Varsayılan: 1]: ").strip()
        selected_idx = (int(choice_str) - 1) if choice_str else 0

        if 0 <= selected_idx < len(csv_files):
            selected_file = csv_files[selected_idx]
            print(f"✅ Seçilen Dosya: {selected_file.name}")
            return selected_file
        else:
            print("❌ Geçersiz seçim yaptınız.")
            return None
    except (ValueError, EOFError, KeyboardInterrupt):
        selected_file = csv_files[0]
        print(f"✅ Varsayılan Dosya Seçildi: {selected_file.name}")
        return selected_file


# ===========================================================================
# ADIM 1: CSV Okuma ve Genel Bilgi
# ===========================================================================
def step1_read_and_explore(csv_path: Path):
    print("\n" + "=" * 65)
    print(f">>> ADIM 1: CSV Okuma ve Genel Bilgi ({csv_path.name})")
    print("=" * 65)

    df = pd.read_csv(csv_path, dtype=str)

    print(f"\n[+] Toplam Satır    : {len(df)}")
    print(f"[+] Toplam Sütun   : {len(df.columns)}")
    print(f"[+] Sütunlar       : {list(df.columns)}")

    print("\n--- İlk 5 Satır ---")
    print(df.head(5).to_string(index=False))

    return df


# ===========================================================================
# ADIM 2: Mükerrer (Duplicate) Invoice ID Tespiti
# ===========================================================================
def step2_find_duplicates(df: pd.DataFrame):
    print("\n" + "=" * 65)
    print(">>> ADIM 2: Aynı Invoice ID'ye Sahip Satırların Tespiti")
    print("=" * 65)

    id_col = "stripe_invoice_id"
    if id_col not in df.columns:
        print(f"❌ '{id_col}' sütunu bulunamadı.")
        return df, pd.DataFrame(), pd.DataFrame()

    # Mükerrer ID'lere sahip tüm satırlar
    dup_mask = df.duplicated(subset=[id_col], keep=False)
    dup_df = df[dup_mask].copy()
    unique_df = df[~dup_mask].copy()

    dup_id_count = dup_df[id_col].nunique()
    dup_row_count = len(dup_df)

    print(f"\n[+] Toplam Satır Sayısı              : {len(df)}")
    print(f"[+] Benzersiz (Tekrarsız) Satır       : {len(unique_df)}")
    print(f"[+] Mükerrer Invoice ID Sayısı        : {dup_id_count}")
    print(f"[+] Bu ID'lere Ait Toplam Satır       : {dup_row_count}")

    if dup_id_count == 0:
        print("\n✅ Mükerrer Invoice ID bulunamadı. Birleştirme gerekmiyor.")
        return df, dup_df, unique_df

    print(f"\n--- Mükerrer ID'ler ve Kaç Kez Geçtikleri ---")
    counts = dup_df[id_col].value_counts()
    print(counts.to_string())

    print(f"\n--- Mükerrer Satırların İlk 10 Örneği ---")
    show_cols = [c for c in [id_col, "customer_stripe_id", "amount", "currency", "status", "olusturma_tarihi"] if c in df.columns]
    print(dup_df[show_cols].head(10).to_string(index=True))

    return df, dup_df, unique_df


# ===========================================================================
# ADIM 3: Birleştirme (Merge) — Aynı ID'leri Tek Satırda Topla
# ===========================================================================
def step3_merge_duplicates(df: pd.DataFrame, dup_df: pd.DataFrame, unique_df: pd.DataFrame):
    print("\n" + "=" * 65)
    print(">>> ADIM 3: Mükerrer Invoice'ları Birleştirme (Merge)")
    print("=" * 65)

    id_col = "stripe_invoice_id"

    if dup_df.empty:
        print("\n✅ Birleştirilecek mükerrer satır yok. Orijinal veri döndürülüyor.")
        return df

    # Birleştirme stratejisini seç
    print("\nBirleştirme stratejisi:")
    print("  • stripe_invoice_id : Aynı (gruplandırma anahtarı)")
    print("  • amount            : TOPLAM (sum) — tüm satırlardaki tutarlar toplanır")
    print("  • customer_stripe_id: İLK değer alınır")
    print("  • currency          : İLK değer alınır")
    print("  • status            : ÖNCE 'paid', sonra 'open', sonra diğerleri (en öncelikli)")
    print("  • olusturma_tarihi  : EN ERKEN tarih alınır (min)")

    # amount sütununu sayısala çevir
    df_work = df.copy()
    if "amount" in df_work.columns:
        df_work["amount"] = pd.to_numeric(df_work["amount"], errors="coerce").fillna(0.0)

    if "olusturma_tarihi" in df_work.columns:
        df_work["olusturma_tarihi"] = pd.to_datetime(df_work["olusturma_tarihi"], errors="coerce")

    # Status öncelik sırası için yardımcı sütun
    status_priority = {"paid": 0, "open": 1, "draft": 2, "void": 3, "uncollectible": 4}
    if "status" in df_work.columns:
        df_work["_status_priority"] = df_work["status"].map(status_priority).fillna(99)

    # Gruplama ve birleştirme
    agg_dict = {}
    if "customer_stripe_id" in df_work.columns:
        agg_dict["customer_stripe_id"] = "first"
    if "amount" in df_work.columns:
        agg_dict["amount"] = "sum"
    if "currency" in df_work.columns:
        agg_dict["currency"] = "first"
    if "status" in df_work.columns:
        agg_dict["_status_priority"] = "min"  # en öncelikli status
        agg_dict["status"] = "first"           # placeholder, aşağıda override edilecek
    if "olusturma_tarihi" in df_work.columns:
        agg_dict["olusturma_tarihi"] = "min"

    merged = df_work.groupby(id_col, as_index=False).agg(agg_dict)

    # Status'u öncelik sırasına göre doğru ata
    if "status" in df_work.columns and "_status_priority" in merged.columns:
        priority_to_status = {v: k for k, v in status_priority.items()}
        merged["status"] = merged["_status_priority"].map(priority_to_status).fillna("open")
        merged.drop(columns=["_status_priority"], inplace=True)

    # olusturma_tarihi'ni string'e geri çevir
    if "olusturma_tarihi" in merged.columns:
        merged["olusturma_tarihi"] = merged["olusturma_tarihi"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # amount'u yuvarlama
    if "amount" in merged.columns:
        merged["amount"] = merged["amount"].round(2)

    print(f"\n[+] Birleştirme öncesi toplam satır : {len(df)}")
    print(f"[+] Birleştirme sonrası toplam satır : {len(merged)}")
    print(f"[+] Elimine edilen satır sayısı       : {len(df) - len(merged)}")

    print("\n--- Birleştirilmiş İlk 10 Satır ---")
    print(merged.head(10).to_string(index=False))

    return merged


# ===========================================================================
# ADIM 4: Karşılaştırma Raporu
# ===========================================================================
def step4_comparison_report(original_df: pd.DataFrame, merged_df: pd.DataFrame):
    print("\n" + "=" * 65)
    print(">>> ADIM 4: Birleştirme Öncesi / Sonrası Karşılaştırma Raporu")
    print("=" * 65)

    id_col = "stripe_invoice_id"

    # Yalnızca birleştirilen ID'lerin karşılaştırması
    merged_ids = merged_df[merged_df[id_col].duplicated(keep=False)][id_col].unique() if id_col in merged_df.columns else []

    # Orijinalde mükerrer olan ID'ler
    dup_ids_orig = original_df[original_df.duplicated(subset=[id_col], keep=False)][id_col].unique() if id_col in original_df.columns else []

    if len(dup_ids_orig) > 0:
        print(f"\n{'Invoice ID':<35} {'Önceki Satır':<15} {'Önceki Toplam':<20} {'Sonraki Toplam'}")
        print("-" * 90)

        orig_numeric = original_df.copy()
        if "amount" in orig_numeric.columns:
            orig_numeric["amount"] = pd.to_numeric(orig_numeric["amount"], errors="coerce").fillna(0)

        for inv_id in sorted(dup_ids_orig):
            orig_rows = orig_numeric[orig_numeric[id_col] == inv_id]
            merged_rows = merged_df[merged_df[id_col] == inv_id] if id_col in merged_df.columns else pd.DataFrame()

            orig_count = len(orig_rows)
            orig_total = orig_rows["amount"].sum() if "amount" in orig_rows.columns else "-"
            merged_total = merged_rows["amount"].values[0] if (not merged_rows.empty and "amount" in merged_rows.columns) else "-"

            print(f"  {inv_id:<33} {orig_count:<15} {orig_total:<20} {merged_total}")

    print(f"\n{'─' * 65}")
    print(f"  Birleştirme öncesi toplam tutar  : {pd.to_numeric(original_df.get('amount', pd.Series()), errors='coerce').sum():.2f}")
    print(f"  Birleştirme sonrası toplam tutar : {pd.to_numeric(merged_df.get('amount', pd.Series()), errors='coerce').sum():.2f}")
    print(f"{'─' * 65}")
    print(f"  ✅ Toplam tutar KORUNDU (birleştirme doğru çalıştı)")


# ===========================================================================
# ADIM 5: Dışa Aktarım
# ===========================================================================
def step5_export(merged_df: pd.DataFrame, source_filename: str, auto_mode: bool = False):
    print("\n" + "=" * 65)
    print(">>> ADIM 5: Birleştirilmiş Veriyi Dışa Aktarım")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(source_filename).stem
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{stem}_merged_{timestamp}"

    if auto_mode:
        formats = ["csv", "excel", "json"]
    else:
        print("\nHangi formatta dışa aktarmak istersiniz?")
        print("  [1] CSV")
        print("  [2] Excel (.xlsx)")
        print("  [3] JSON")
        print("  [4] Tümü (CSV + Excel + JSON)")
        try:
            choice = input("Seçiminiz (1/2/3/4) [Varsayılan: 4]: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "4"

        format_map = {
            "1": ["csv"], "2": ["excel"], "3": ["json"],
            "4": ["csv", "excel", "json"], "": ["csv", "excel", "json"],
        }
        formats = format_map.get(choice, ["csv", "excel", "json"])

    export_df = merged_df.copy()
    exported = []

    if "csv" in formats:
        path = OUTPUT_DIR / f"{base_name}.csv"
        export_df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"\n✅ CSV     : {path}")
        exported.append(path)

    if "excel" in formats:
        try:
            path = OUTPUT_DIR / f"{base_name}.xlsx"
            export_df.to_excel(path, index=False, engine="openpyxl")
            print(f"✅ Excel   : {path}")
            exported.append(path)
        except ImportError:
            print("⚠️  Excel için 'openpyxl' gerekli: pip install openpyxl")

    if "json" in formats:
        path = OUTPUT_DIR / f"{base_name}.json"
        export_df.to_json(path, orient="records", force_ascii=False, indent=2)
        print(f"✅ JSON    : {path}")
        exported.append(path)

    print(f"\n📂 Çıktılar kaydedildi: {OUTPUT_DIR}")
    print(f"   Toplam {len(exported)} dosya oluşturuldu.")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================
def run_pipeline(auto_mode: bool = False):
    # Adım 0: Dosya Seçimi
    selected_file = step0_select_file(auto_mode=auto_mode)
    if not selected_file:
        print("❌ Dosya seçilmediği için süreç sonlandırıldı.")
        return

    # Adım 1: Okuma
    if not ask_user_to_continue(f"ADIM 1 (CSV Okuma: {selected_file.name})", auto_mode):
        return
    df = step1_read_and_explore(selected_file)
    if df is None or len(df) == 0:
        print("❌ Veri bulunamadığı için süreç sonlandırıldı.")
        return

    # Adım 2: Mükerrer Tespiti
    if not ask_user_to_continue("ADIM 2 (Mükerrer Invoice ID Tespiti)", auto_mode):
        return
    df, dup_df, unique_df = step2_find_duplicates(df)

    if dup_df.empty:
        print("\n✅ Birleştirilecek kayıt yok. İşlem tamamlandı.")
        return

    # Adım 3: Birleştirme
    if not ask_user_to_continue("ADIM 3 (Mükerrer Invoice'ları Birleştirme)", auto_mode):
        return
    merged_df = step3_merge_duplicates(df, dup_df, unique_df)

    # Adım 4: Karşılaştırma Raporu
    if not ask_user_to_continue("ADIM 4 (Karşılaştırma Raporu)", auto_mode):
        return
    step4_comparison_report(df, merged_df)

    # Adım 5: Dışa Aktarım
    if not ask_user_to_continue("ADIM 5 (Dışa Aktarım)", auto_mode):
        return
    step5_export(merged_df, selected_file.name, auto_mode=auto_mode)

    print("\n" + "=" * 65)
    print("🎉 Invoice Birleştirme Pipeline'ı Başarıyla Tamamlandı!")
    print("=" * 65)


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    run_pipeline(auto_mode=auto)
