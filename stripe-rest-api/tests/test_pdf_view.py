import sys
import os
import webbrowser

# Proje ana dizinini Python path'ine ekle (diğer modülleri import edebilmek için)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_pool, get_db


def view_pdf_from_db(payment_intent_id):
    print("Veritabanı bağlantısı kuruluyor...")
    init_pool()

    print(f"'{payment_intent_id}' için PDF aranıyor...")
    try:
        with get_db() as cursor:
            cursor.execute(
                "SELECT pdf_data FROM payment_pdfs WHERE payment_intent_stripe_id = %s",
                (payment_intent_id,),
            )
            row = cursor.fetchone()
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        return

    if not row or not row[0]:
        print(f"❌ Veritabanında '{payment_intent_id}' için PDF bulunamadı.")
        return

    pdf_bytes = row[0]

    # Geçici dosyaya yaz
    temp_filename = f"view_{payment_intent_id}.pdf"
    temp_filepath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), temp_filename
    )

    with open(temp_filepath, "wb") as f:
        f.write(pdf_bytes)

    print(f"✅ PDF '{temp_filename}' adıyla kaydedildi.")
    print("PDF varsayılan görüntüleyici ile açılıyor...")

    # PDF'i varsayılan uygulama ile aç
    try:
        os.startfile(temp_filepath)  # Sadece Windows'ta çalışır
    except AttributeError:
        webbrowser.open(f"file://{temp_filepath}")  # Mac/Linux alternatifi
    except Exception as e:
        print(f"❌ PDF açılırken hata oluştu: {e}")


if __name__ == "__main__":
    print("--- DB'den PDF Görüntüleme Testi ---")
    payment_id = input(
        "Görüntülemek istediğiniz Payment Intent ID'sini girin (örn: pi_3P...): "
    ).strip()

    if payment_id:
        view_pdf_from_db(payment_id)
    else:
        print("Geçerli bir ID girmediniz.")
