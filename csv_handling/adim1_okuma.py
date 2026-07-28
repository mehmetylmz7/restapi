from pathlib import Path
import pandas as pd

# Dosya yollarını belirleyelim
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ornek_satislar.csv"

# ==========================================
# ADIM 1: CSV Verisini Yukleme ve Kesif
# ==========================================
print("--- Ham Veri Yukleme ---")
df = pd.read_csv(CSV_PATH)
print(df)

# ilk 5 satiri goruntuleme
print("\n--- ilk 5 Satir ---")
print(df.head(5))

# sutun tipleri, eksik deger sayisi
print("\n--- Sutun Tipleri ve Eksik Degerler ---")
print(df.info())

# sayisal sutunlar icin istatistik
print("\n--- Sayisal Sutunlar icin istatistik ---")
print(df.describe())

# (satir, sutun) sayisi
print("\n--- Veri Seti Boyutu ---")
print(df.shape)

# her sutunun veri tipi
print("\n--- Sutun Veri Tipleri ---")
print(df.dtypes)