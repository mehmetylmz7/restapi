import sys
import os
from pathlib import Path
import pandas as pd

# Windows konsolunda UTF-8 çıktı desteği
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Proje ana dizinini (stripe-rest-api) sys.path'e ekle
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent / "stripe-rest-api"
sys.path.append(str(PROJECT_ROOT))

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"


def ask_user_to_continue(step_name: str, auto_mode: bool = False) -> bool:
    """Kullanıcıya sonraki adıma geçip geçmek istemediğini sorar."""
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
        if not choice_str:
            selected_idx = 0
        else:
            selected_idx = int(choice_str) - 1

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
# ADIM 1: Pandas ile CSV Verisini Okuma ve Keşif
# ===========================================================================
def step1_read_and_explore(csv_path: Path):
    print("\n" + "=" * 65)
    print(f">>> ADIM 1: Pandas ile CSV Verisini Okuma ve Keşif ({csv_path.name})")
    print("=" * 65)

    df = pd.read_csv(csv_path, dtype=str)
    print(f"\n[+] CSV Başarıyla Okundu! Toplam Satır Sayısı: {len(df)}")
    print(f"[+] Toplam Sütun Sayısı: {len(df.columns)}")
    print(f"[+] Sütunlar: {list(df.columns)}")

    print("\n--- İlk 5 Satır ---")
    print(df.head(5).to_string(index=False))

    print("\n--- Sütun Veri Tipleri ---")
    print(df.dtypes)

    print("\n--- Sütun Başına Eksik (Null / Boş) Değer Sayısı ---")
    null_counts = (df.isna() | (df == "")).sum()
    print(null_counts)

    return df


# ===========================================================================
# ADIM 2: Veri Temizleme ve Format Dönüştürme
# ===========================================================================
def step2_clean_and_transform(df: pd.DataFrame):
    print("\n" + "=" * 65)
    print(">>> ADIM 2: Veri Temizleme ve Format Dönüştürme (Pandas)")
    print("=" * 65)

    cleaned_df = df.copy()

    # 1. Tüm metin sütunlarındaki baş/son boşlukları temizle
    for col in cleaned_df.columns:
        cleaned_df[col] = cleaned_df[col].astype(str).str.strip()

    # 2. Mükerrer satır tespiti ve raporu
    dup_count = cleaned_df.duplicated().sum()
    print(f"\n[+] Tespit Edilen Mükerrer (Duplicate) Satır Sayısı: {dup_count}")
    if dup_count > 0:
        print("    ℹ️  Mükerrer satırlar raporda gösterildi ancak silinmedi.")
        print(cleaned_df[cleaned_df.duplicated()].to_string(index=True))

    # 3. Boş değerleri doldur (fillna): sayısal → 0, metin → 'bilinmiyor'
    for col in cleaned_df.columns:
        if cleaned_df[col].str.replace(".", "", 1).str.isnumeric().all():
            cleaned_df[col] = cleaned_df[col].replace("nan", "0").replace("", "0")
        else:
            cleaned_df[col] = cleaned_df[col].replace("nan", "bilinmiyor").replace("", "bilinmiyor")

    # 4. Sayısal ve tarihsel alanları dönüştür (invoice alanları)
    if "amount" in cleaned_df.columns:
        cleaned_df["amount_float"] = pd.to_numeric(cleaned_df["amount"], errors="coerce").fillna(0.0)
        cleaned_df["amount_cents"] = (cleaned_df["amount_float"] * 100).round().astype(int)

    if "currency" in cleaned_df.columns:
        cleaned_df["currency"] = cleaned_df["currency"].replace("bilinmiyor", "usd").str.lower()

    if "status" in cleaned_df.columns:
        cleaned_df["status"] = cleaned_df["status"].replace("bilinmiyor", "open").str.lower()

    if "olusturma_tarihi" in cleaned_df.columns:
        cleaned_df["olusturma_tarihi_dt"] = pd.to_datetime(
            cleaned_df["olusturma_tarihi"], errors="coerce"
        )
        cleaned_df["olusturma_tarihi_formatted"] = cleaned_df["olusturma_tarihi_dt"].dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    print(f"\n[+] Temizleme ve dönüşümler tamamlandı.")
    print("\n--- Temizlenmiş İlk 5 Satır ---")
    print(cleaned_df.head(5).to_string(index=False))

    return cleaned_df


# ===========================================================================
# ADIM 3: Filtreleme ve Doğrulama
# ===========================================================================
def step3_filter_and_validate(cleaned_df: pd.DataFrame, filename: str):
    print("\n" + "=" * 65)
    print(">>> ADIM 3: Filtreleme ve Doğrulama")
    print("=" * 65)

    initial_count = len(cleaned_df)

    if "amount_cents" in cleaned_df.columns:
        df_valid = cleaned_df[cleaned_df["amount_cents"] > 0].copy()
    else:
        df_valid = cleaned_df.copy()

    invalid_count = initial_count - len(df_valid)

    print(f"\n[+] Toplam Satır Sayısı       : {initial_count}")
    print(f"[+] Geçersiz Satır (Elenen)   : {invalid_count}  (amount = 0 veya boş)")
    print(f"✅ Geçerli Satır Sayısı        : {len(df_valid)}")

    return df_valid


# ===========================================================================
# ADIM 4: İstatistiksel Analiz
# ===========================================================================
def step4_statistical_analysis(df: pd.DataFrame):
    print("\n" + "=" * 65)
    print(">>> ADIM 4: İstatistiksel Analiz")
    print("=" * 65)

    # 4a. describe() - sayısal sütunlar için özet istatistik
    numeric_cols = df.select_dtypes(include="number")
    if not numeric_cols.empty:
        print("\n--- 📊 Sayısal Sütunlar: Özet İstatistik (describe) ---")
        print(numeric_cols.describe().round(2).to_string())
    else:
        # amount_float varsa onu kullan
        if "amount_float" in df.columns:
            print("\n--- 📊 amount_float: Özet İstatistik (describe) ---")
            print(pd.to_numeric(df["amount_float"], errors="coerce").describe().round(2))

    # 4b. value_counts() - tekrar eden değerlerin sayımı
    categorical_candidates = ["status", "currency", "bolge", "urun", "musteri"]
    for col in categorical_candidates:
        if col in df.columns:
            print(f"\n--- 🔢 '{col}' Sütunu: Değer Sayımı (value_counts) ---")
            print(df[col].value_counts().to_string())

    # 4c. groupby + sum/mean - fatura verileri için
    if "amount_float" in df.columns and "customer_stripe_id" in df.columns:
        print("\n--- 👥 Müşteri Bazlı Toplam Tutar (groupby + sum) ---")
        grp = (
            pd.to_numeric(df["amount_float"], errors="coerce")
            .groupby(df["customer_stripe_id"])
            .agg(["sum", "mean", "count"])
            .round(2)
            .sort_values("sum", ascending=False)
            .head(10)
        )
        grp.columns = ["Toplam Tutar", "Ortalama Tutar", "Fatura Sayısı"]
        print(grp.to_string())

    # 4d. sort_values - en yüksek tutarlı faturalar
    if "amount_float" in df.columns:
        df["amount_float_num"] = pd.to_numeric(df["amount_float"], errors="coerce")
        print("\n--- 🔝 En Yüksek Tutarlı İlk 5 Kayıt (sort_values) ---")
        top5 = df.sort_values("amount_float_num", ascending=False).head(5)
        show_cols = [c for c in ["stripe_invoice_id", "customer_stripe_id", "amount_float", "status", "olusturma_tarihi"] if c in df.columns]
        print(top5[show_cols].to_string(index=False) if show_cols else top5.head(5).to_string(index=False))
        df.drop(columns=["amount_float_num"], inplace=True)

    # 4e. pivot_table - durum x para birimi çapraz tablo
    if "status" in df.columns and "currency" in df.columns and "amount_float" in df.columns:
        df["amount_float_num"] = pd.to_numeric(df["amount_float"], errors="coerce")
        print("\n--- 📋 Durum x Para Birimi Pivot Tablo (pivot_table) ---")
        try:
            pivot = df.pivot_table(
                values="amount_float_num",
                index="status",
                columns="currency",
                aggfunc="sum",
                fill_value=0
            ).round(2)
            print(pivot.to_string())
        except Exception:
            pass
        df.drop(columns=["amount_float_num"], inplace=True)

    return df


# ===========================================================================
# ADIM 5: Anomali Tespiti
# ===========================================================================
def step5_anomaly_detection(df: pd.DataFrame):
    print("\n" + "=" * 65)
    print(">>> ADIM 5: Anomali Tespiti")
    print("=" * 65)

    anomalies_found = False

    # 5a. Negatif değer kontrolü
    numeric_candidates = ["amount_float", "amount_cents", "adet", "birim_fiyat"]
    for col in numeric_candidates:
        if col in df.columns:
            num_series = pd.to_numeric(df[col], errors="coerce")
            negative = df[num_series < 0]
            if not negative.empty:
                print(f"\n⚠️  Negatif Değer Tespit Edildi! Sütun: '{col}' → {len(negative)} satır")
                print(negative.to_string(index=True))
                anomalies_found = True

    # 5b. Aşırı sapma (outlier) tespiti - IQR yöntemi
    for col in numeric_candidates:
        if col in df.columns:
            num_series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(num_series) < 4:
                continue
            Q1 = num_series.quantile(0.25)
            Q3 = num_series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers = df[pd.to_numeric(df[col], errors="coerce").lt(lower) | pd.to_numeric(df[col], errors="coerce").gt(upper)]
            if not outliers.empty:
                print(f"\n📉 Aşırı Sapma (Outlier) Tespit Edildi! Sütun: '{col}'")
                print(f"   Normal Aralık: [{lower:.2f}  —  {upper:.2f}]")
                print(f"   Sapma Gösteren Satır Sayısı: {len(outliers)}")
                show_cols = [col] + [c for c in ["stripe_invoice_id", "customer_stripe_id", "status"] if c in df.columns]
                print(outliers[show_cols].head(5).to_string(index=True))
                anomalies_found = True

    # 5c. Boş / eksik zorunlu alan kontrolü
    required_cols = {
        "stripe_invoice_id": "Fatura ID",
        "customer_stripe_id": "Müşteri ID",
        "amount": "Tutar",
    }
    for col, label in required_cols.items():
        if col in df.columns:
            missing = df[df[col].isna() | (df[col] == "") | (df[col] == "bilinmiyor")]
            if not missing.empty:
                print(f"\n⚠️  Eksik Zorunlu Alan: '{label}' ({col}) → {len(missing)} satırda boş")
                anomalies_found = True

    if not anomalies_found:
        print("\n✅ Anomali tespit edilmedi. Veriler temiz görünüyor.")

    return df


# ===========================================================================
# ADIM 6: Dışa Aktarım (CSV / Excel / JSON)
# ===========================================================================
def step6_export(df: pd.DataFrame, source_filename: str, auto_mode: bool = False):
    print("\n" + "=" * 65)
    print(">>> ADIM 6: Dışa Aktarım (CSV / Excel / JSON)")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(source_filename).stem
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{stem}_islenmiş_{timestamp}"

    if auto_mode:
        # Otomatik modda tüm formatları dışa aktar
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
            "1": ["csv"],
            "2": ["excel"],
            "3": ["json"],
            "4": ["csv", "excel", "json"],
            "":  ["csv", "excel", "json"],
        }
        formats = format_map.get(choice, ["csv", "excel", "json"])

    # Dışa aktarım için sütun temizliği (datetime nesnelerini stringe çevir)
    export_df = df.copy()
    for col in export_df.columns:
        if pd.api.types.is_datetime64_any_dtype(export_df[col]):
            export_df[col] = export_df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    exported_files = []

    if "csv" in formats:
        csv_path = OUTPUT_DIR / f"{base_name}.csv"
        export_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n✅ CSV kaydedildi     : {csv_path}")
        exported_files.append(csv_path)

    if "excel" in formats:
        try:
            excel_path = OUTPUT_DIR / f"{base_name}.xlsx"
            export_df.to_excel(excel_path, index=False, engine="openpyxl")
            print(f"✅ Excel kaydedildi   : {excel_path}")
            exported_files.append(excel_path)
        except ImportError:
            print("⚠️  Excel aktarımı için 'openpyxl' paketi gerekli: pip install openpyxl")

    if "json" in formats:
        json_path = OUTPUT_DIR / f"{base_name}.json"
        export_df.to_json(json_path, orient="records", force_ascii=False, indent=2)
        print(f"✅ JSON kaydedildi    : {json_path}")
        exported_files.append(json_path)

    print(f"\n📂 Tüm çıktılar '{OUTPUT_DIR}' klasörüne kaydedildi.")
    print(f"   Toplam {len(exported_files)} dosya oluşturuldu.")

    return exported_files


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================
def run_pipeline(auto_mode: bool = False):
    # Adım 0: Dosya Seçimi
    selected_file = step0_select_file(auto_mode=auto_mode)
    if not selected_file:
        print("❌ Dosya seçilmediği için süreç sonlandırıldı.")
        return

    # Adım 1: Okuma ve Keşif
    if not ask_user_to_continue(f"ADIM 1 (CSV Okuma: {selected_file.name})", auto_mode):
        return
    df = step1_read_and_explore(selected_file)
    if df is None or len(df) == 0:
        print("❌ Veri bulunamadığı için süreç sonlandırıldı.")
        return

    # Adım 2: Temizleme ve Formatlama
    if not ask_user_to_continue("ADIM 2 (Veri Temizleme ve Formatlama)", auto_mode):
        return
    cleaned_df = step2_clean_and_transform(df)

    # Adım 3: Filtreleme ve Doğrulama
    if not ask_user_to_continue("ADIM 3 (Filtreleme ve Doğrulama)", auto_mode):
        return
    valid_df = step3_filter_and_validate(cleaned_df, selected_file.name)

    # Adım 4: İstatistiksel Analiz
    if not ask_user_to_continue("ADIM 4 (İstatistiksel Analiz)", auto_mode):
        return
    analyzed_df = step4_statistical_analysis(valid_df)

    # Adım 5: Anomali Tespiti
    if not ask_user_to_continue("ADIM 5 (Anomali Tespiti)", auto_mode):
        return
    final_df = step5_anomaly_detection(analyzed_df)

    # Adım 6: Dışa Aktarım
    if not ask_user_to_continue("ADIM 6 (Dışa Aktarım)", auto_mode):
        return
    step6_export(final_df, selected_file.name, auto_mode=auto_mode)

    print("\n" + "=" * 65)
    print("🎉 Pipeline başarıyla tamamlandı!")
    print("=" * 65)


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    run_pipeline(auto_mode=auto)
