from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "temizlenmis_satislar.csv"

df = pd.read_csv(CSV_PATH)
df['tarih'] = pd.to_datetime(df['tarih'])

# ==========================================
# ADIM 4.1: Kosullu Filtreleme
# ==========================================
print("--- Birim fiyati 1000'den buyuk olan satirlar ---")
print(df[df['birim_fiyat'] > 1000])

print("\n--- Ayni filtre .query() ile ---")
print(df.query('birim_fiyat > 1000'))


print("\n--- Iki Kosul Birden (AND) ---")
print(df[(df['birim_fiyat'] > 1000) & (df['bolge'] == 'Istanbul')])

print("\n--- Iki Kosul Birden (OR) ---")
print(df[(df['bolge'] == 'Istanbul') | (df['bolge'] == 'Ankara')])


# Yontem 1: Dogrudan vektorel islem (en hizli, en tercih edilen)
df['toplam_tutar'] = df['adet'] * df['birim_fiyat']
print("\n--- Yontem 1: Vektorel Islem ---")
print(df[['urun', 'adet', 'birim_fiyat', 'toplam_tutar']])

# Yontem 2: apply + lambda (satir satir, daha yavas ama daha esnek)
df['toplam_tutar_v2'] = df.apply(lambda row: row['adet'] * row['birim_fiyat'], axis=1)
print("\n--- Yontem 2: apply + lambda ---")
print(df[['urun', 'toplam_tutar', 'toplam_tutar_v2']])

# Yontem 3: map ile kategori esleme (tek sutun uzerinde)
kategori_map = {'Laptop': 'Elektronik-Buyuk', 'Monitor': 'Elektronik-Buyuk', 'Mouse': 'Aksesuar', 'Klavye': 'Aksesuar'}
df['kategori'] = df['urun'].map(kategori_map)
print("\n--- Yontem 3: map ile kategori ---")
print(df[['urun', 'kategori']])


print("\n--- En Yuksek Toplam Tutara Gore Siralama ---")
print(df.sort_values('toplam_tutar', ascending=False)[['urun', 'musteri', 'toplam_tutar']])

print("\n--- Once Bolgeye, Sonra Toplam Tutara Gore Siralama ---")
print(df.sort_values(['bolge', 'toplam_tutar'], ascending=[True, False])[['bolge', 'urun', 'toplam_tutar']])