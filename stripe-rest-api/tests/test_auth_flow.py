import requests
import random
import string

BASE_URL = "http://127.0.0.1:5000/api"

def random_email():
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_str}@example.com"

def run_tests():
    email = random_email()
    password = "SecurePassword123!"
    name = "Auth Test User"

    print(f"1. Kayıt testi başlatılıyor: {email}...")
    reg_payload = {"email": email, "password": password, "name": name}
    reg_res = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    
    if reg_res.status_code != 201:
        print(f"❌ Kayıt hatası (Status: {reg_res.status_code}): {reg_res.text}")
        return
    
    reg_data = reg_res.json()
    print(f"✅ Kayıt başarılı! Stripe Customer ID: {reg_data.get('stripe_customer_id')}")
    
    print("\n2. Giriş (Login) testi başlatılıyor...")
    login_payload = {"email": email, "password": password}
    login_res = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    
    if login_res.status_code != 200:
        print(f"❌ Giriş hatası (Status: {login_res.status_code}): {login_res.text}")
        return
        
    login_data = login_res.json()
    token = login_data.get("access_token")
    print(f"✅ Giriş başarılı! Token alındı (ilk 15 hane): {token[:15]}...")

    headers = {"Authorization": f"Bearer {token}"}

    print("\n3. Profil bilgisini çekme (/api/customers/me) testi...")
    me_res = requests.get(f"{BASE_URL}/customers/me", headers=headers)
    if me_res.status_code == 200:
        print(f"✅ Profil bilgisi başarıyla çekildi: {me_res.json().get('email')}")
    else:
        print(f"❌ Profil çekme hatası (Status: {me_res.status_code}): {me_res.text}")

    print("\n4. Yetkisiz istek testi (Token'sız ödemeleri çekme)...")
    fail_res = requests.get(f"{BASE_URL}/payments")
    if fail_res.status_code == 401:
        print("✅ Başarılı! Token gönderilmeyince 401 Unauthorized alındı.")
    else:
        print(f"❌ HATA! Token'sız istekte 401 bekleniyordu ancak {fail_res.status_code} alındı.")

    print("\n5. Yetkili istek testi (Token ile ödemeleri çekme)...")
    success_res = requests.get(f"{BASE_URL}/payments", headers=headers)
    if success_res.status_code == 200:
        payments_data = success_res.json()
        print(f"✅ Başarılı! Ödemeler listelendi. Toplam kayıt sayısı: {len(payments_data.get('data', []))}")
    else:
        print(f"❌ Ödeme listeleme hatası (Status: {success_res.status_code}): {success_res.text}")

if __name__ == "__main__":
    run_tests()
