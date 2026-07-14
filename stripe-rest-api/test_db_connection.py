from database import get_connection


def test_connection():
    conn = get_connection()
    if conn:
        print("✅ Başarılı! MySQL veritabanına bağlanıldı.")
        conn.close()
    else:
        print(
            "❌ Hata! Veritabanına bağlanılamadı. Lütfen .env dosyanı ve şifreni kontrol et."
        )


if __name__ == "__main__":
    test_connection()
