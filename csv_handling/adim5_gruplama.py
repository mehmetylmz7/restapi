from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "temizlenmis_satislar.csv"

df = pd.read_csv(CSV_PATH)
df['tarih'] = pd.to_datetime(df['tarih'])
df['toplam_tutar'] = df['adet'] * df['birim_fiyat']

# ==========================================
# ADIM 5.1: Bolgeye Gore Gruplama
# ==========================================
# groupby('bolge')['toplam_tutar'].sum() -> tek sutun uzerinde islem yaptigi icin
# sonuc bir Series doner (cikti: "Name: toplam_tutar, dtype: float64")
print("--- Bolgeye Gore Toplam Satis ---")
print(df.groupby('bolge')['toplam_tutar'].sum())

print("\n--- Bolgeye Gore Ortalama Satis ---")
print(df.groupby('bolge')['toplam_tutar'].mean())

# .agg(['sum','mean','count']) -> birden fazla istatistik istendigi icin
# sonuc bir DataFrame doner (her istatistik kendi sutununda, tablo seklinde)
print("\n--- Bolgeye Gore Birden Fazla Istatistik (agg) ---")
print(df.groupby('bolge')['toplam_tutar'].agg(['sum', 'mean', 'count']))

# ==========================================
# ADIM 5.2: Pivot Table
# ==========================================
# fill_value belirtilmezse: bir bolge-urun kombinasyonu hic satilmamissa
# (ornegin Bursa'da Laptop) o hucre NaN olarak gorunur ("bilinmiyor" anlaminda)
print("\n--- Pivot Table: Bolge x Urun (fill_value YOK -> NaN gorunur) ---")
pivot_nan = df.pivot_table(values='toplam_tutar', index='bolge', columns='urun', aggfunc='sum')
print(pivot_nan)

# fill_value=0 belirtilirse: NaN yerine 0 yazilir
# raporlama/analiz icin genelde tercih edilir, cunku "satis yok" ile "veri eksik"
# anlamlarini ayirmak faydali olur (0 = kesinlikle satis olmadi)
print("\n--- Pivot Table: Bolge x Urun (fill_value=0 -> 0 gorunur) ---")
pivot_dolu = df.pivot_table(values='toplam_tutar', index='bolge', columns='urun', aggfunc='sum', fill_value=0)
print(pivot_dolu)

# ==========================================
# ADIM 5.3: Merge - Musteri Bilgisi Tablosuyla Birlestirme
# ==========================================
musteri_bilgi = pd.DataFrame({
    'musteri': ['Ahmet Yilmaz', 'Zeynep Kaya', 'Mehmet Demir', 'Ali Veli', 'Fatma Ozturk'],
    'segment': ['VIP', 'Standart', 'Standart', 'VIP', 'Standart'],
    'uyelik_yili': [2019, 2021, 2020, 2018, 2022]
})
print("\n--- Musteri Bilgi Tablosu ---")
print(musteri_bilgi)
# Not: musteri_bilgi tablosunda "Can Aydin" bilerek yok - merge davranisini
# gozlemlemek icin.

# how='inner' (varsayilan): sadece HER IKI tabloda da ortak bulunan musterileri alir.
# Can Aydin df'de var ama musteri_bilgi'de yok -> satiri tamamen kaybolur.
# Orijinal df 8 satirdi, inner merge sonucu 7 satira dustu.
print("\n--- Merge (inner - varsayilan) ---")
df_birlesik = df.merge(musteri_bilgi, on='musteri', how='inner')
print(df_birlesik[['musteri', 'urun', 'toplam_tutar', 'segment', 'uyelik_yili']])

# how='left': sol tablodaki (df) TUM satirlar korunur.
# Can Aydin'in satiri durur ama segment/uyelik_yili sutunlarinda NaN gorunur,
# cunku musteri_bilgi tablosunda onun icin eslesen bir satir yok.
print("\n--- Merge (left) ---")
df_left = df.merge(musteri_bilgi, on='musteri', how='left')
print(df_left[['musteri', 'urun', 'toplam_tutar', 'segment', 'uyelik_yili']])