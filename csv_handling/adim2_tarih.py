from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ornek_satislar.csv"

df = pd.read_csv(CSV_PATH)

# ==========================================
# ADIM 2: Tarih Sutunu Kontrolu ve Donusumu
# ==========================================
print("--- Tarih Sutunu Kontrolu ---")
print(df['tarih'].dtype)
print(df['tarih'].unique())

# Karisik format icerdigi icin format='mixed' kullaniyoruz
print("\n--- to_datetime (format='mixed') ---")
df['tarih'] = pd.to_datetime(df['tarih'], format='mixed')
print(df[['tarih']])
print(df['tarih'].dtype)