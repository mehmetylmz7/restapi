from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ornek_satislar.csv"
OUTPUT_CSV_PATH = BASE_DIR / "temizlenmis_satislar.csv"

df = pd.read_csv(CSV_PATH)
df['tarih'] = pd.to_datetime(df['tarih'], format='mixed')

# ==========================================
# ADIM 3.1: Eksik Deger Analizi ve Silme
# ==========================================
print("--- Sutun Basina Eksik Deger Sayisi ---")
print(df.isna().sum())

print("\n--- dropna() Oncesi/Sonrasi Satir Sayisi ---")
print(len(df))
df_temiz = df.dropna()
print(len(df_temiz))

# ==========================================
# ADIM 3.2: Duplicate Satirlari Silme
# ==========================================
print("\n--- Duplicate Satir Sayisi ---")
print(df_temiz.duplicated().sum())

df_temiz = df_temiz.drop_duplicates()
print("\n--- drop_duplicates() Sonrasi Satir Sayisi ---")
print(len(df_temiz))

# ==========================================
# ADIM 3.3: Case Tutarsizligi Duzeltme
# ==========================================
print("\n--- Duzeltme Oncesi Benzersiz Degerler ---")
print(df_temiz['urun'].unique())
print(df_temiz['bolge'].unique())

df_temiz['urun'] = df_temiz['urun'].str.capitalize()
df_temiz['bolge'] = df_temiz['bolge'].str.capitalize()

print("\n--- Duzeltme Sonrasi Benzersiz Degerler ---")
print(df_temiz['urun'].unique())
print(df_temiz['bolge'].unique())

# ==========================================
# ADIM 3.4: Temizlenmis Veriyi Kaydetme
# ==========================================
print("\n--- Temizlenmis Veri ---")
print(df_temiz)

df_temiz.to_csv(OUTPUT_CSV_PATH, index=False)
print(f"\nTemizlenmis veri kaydedildi: {OUTPUT_CSV_PATH}")