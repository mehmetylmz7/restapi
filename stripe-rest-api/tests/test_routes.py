import time
import uuid
import concurrent.futures
from flask import Blueprint, render_template, request, jsonify, current_app
from services.customer_service import create_customer, delete_customer

test_bp = Blueprint("test_routes", __name__)


@test_bp.before_request
def log_test_request():
    request_data = request.get_json(silent=True)
    print("[TEST-ROUTE] Incoming request:", request.method, request.path)
    if request.args:
        print("[TEST-ROUTE]   query:", dict(request.args))
    if request_data is not None:
        print("[TEST-ROUTE]   json:", request_data)
    elif request.data:
        try:
            print("[TEST-ROUTE]   body:", request.data.decode("utf-8"))
        except Exception:
            print("[TEST-ROUTE]   body (raw):", request.data)


# ---------------------------------------------------------------------------
# Sayfa: Test arayüzü
# ---------------------------------------------------------------------------
@test_bp.route("/test-thread")
def test_thread():
    return render_template("test_thread.html")


# ---------------------------------------------------------------------------
# Yardımcı fonksiyon: Test için sahte müşteri verisi üretir
# ---------------------------------------------------------------------------
def generate_mock_customers(count=30):
    """
    'count' adet sahte müşteri kaydı oluşturur.
    run_id: aynı testi tekrar çalıştırdığında email'lerin çakışmaması için
    her çalıştırmaya özel kısa bir kimlik (örn: 'a1b2c3d4').
    """
    run_id = str(uuid.uuid4())[:8]
    return [
        {
            "name": f"Mock User {i} ({run_id})",
            "email": f"mockuser{i}_{run_id}@example.com",
        }
        for i in range(1, count + 1)
    ]


# ---------------------------------------------------------------------------
# 1) SIRALI (sequential) çalışma modu
#    30 müşteri, tek tek, birbirini bekleyerek oluşturulur.
#    Thread YOK -> her istek bitmeden diğeri başlamaz.
# ---------------------------------------------------------------------------
@test_bp.route("/api/test-thread/run-sequential", methods=["POST"])
def run_sequential():
    customers_data = generate_mock_customers(30)
    results = []
    errors = []
    start_time = time.time()

    for c in customers_data:
        try:
            res = create_customer(c["name"], c["email"])
            results.append(res)
        except Exception as e:
            # Bir müşteri hata verse bile diğerlerine devam et,
            # hatayı ayrı bir listede topla.
            errors.append({"email": c["email"], "error": str(e)})

    elapsed = time.time() - start_time

    return jsonify({
        "success": True,
        "mode": "sequential",
        "elapsed_seconds": round(elapsed, 2),
        "created_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    })


# ---------------------------------------------------------------------------
# 2) PARALEL (threaded) çalışma modu
#    30 müşteri, aynı anda en fazla 10 thread ile oluşturulur.
#
#    NEDEN THREAD İŞE YARAR?
#    create_customer() büyük olasılıkla Stripe API çağrısı + MySQL yazma
#    yapıyor -> bu I/O bekleme süresi boyunca Python GIL'i serbest kalır,
#    yani thread'ler gerçekten paralel ilerleyebilir. Bu yüzden CPU-bound
#    (hesaplama ağırlıklı) değil, I/O-bound işler için thread kullanımı
#    doğru bir seçim.
#
#    DİKKAT: create_customer() içinde Flask'ın current_app / g gibi
#    context nesnelerine veya request-scoped bir DB session'ına
#    erişiliyorsa, worker thread'lerin bu context'e sahip olmadığını
#    unutma. Bu yüzden context'i açıkça thread'e taşıyoruz.
# ---------------------------------------------------------------------------
@test_bp.route("/api/test-thread/run-threaded", methods=["POST"])
def run_threaded():
    customers_data = generate_mock_customers(30)
    results = []
    errors = []
    start_time = time.time()

    # Ana thread'deki gerçek app nesnesini alıyoruz, çünkü current_app
    # bir proxy'dir ve worker thread içinde doğrudan kullanılamaz.
    app_obj = current_app._get_current_object()

    def create_c(c_data):
        # Her worker thread, kendi app context'ini kendisi açar.
        # Böylece create_customer() içinde current_app / g / db session
        # kullanımı thread içinde de güvenli çalışır.
        with app_obj.app_context():
            return create_customer(c_data["name"], c_data["email"])

    # future -> hangi müşteriye ait olduğunu bilmek için mapping kuruyoruz.
    # (as_completed sırası, customers_data sırasıyla AYNI DEĞİLDİR.)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_customer = {
            executor.submit(create_c, c): c for c in customers_data
        }

        for future in concurrent.futures.as_completed(future_to_customer):
            c = future_to_customer[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                # Bir thread hata alsa bile diğer thread'ler etkilenmez,
                # ve tüm request 500 hatasıyla çökmez.
                errors.append({"email": c["email"], "error": str(e)})

    elapsed = time.time() - start_time

    return jsonify({
        "success": True,
        "mode": "threaded",
        "elapsed_seconds": round(elapsed, 2),
        "created_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    })


# ---------------------------------------------------------------------------
# 3) Test müşterilerini silme (paralel)
# ---------------------------------------------------------------------------
@test_bp.route("/api/test-thread/delete", methods=["POST"])
def delete_test_customers():
    data = request.json or {}
    customer_ids = data.get("customer_ids", [])

    if not customer_ids:
        return jsonify({"success": False, "error": "No customer IDs provided"}), 400

    results = []
    app_obj = current_app._get_current_object()

    def del_c(cid):
        with app_obj.app_context():
            return delete_customer(cid)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_id = {executor.submit(del_c, cid): cid for cid in customer_ids}

        for future in concurrent.futures.as_completed(future_to_id):
            cid = future_to_id[future]
            try:
                future.result()
                results.append({"id": cid, "deleted": True})
            except Exception as e:
                results.append({"id": cid, "deleted": False, "error": str(e)})

    return jsonify({"success": True, "results": results})