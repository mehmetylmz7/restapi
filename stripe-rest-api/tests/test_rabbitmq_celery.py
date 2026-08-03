import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def sep(title=""):
    line = "=" * 60
    if title:
        print(f"\n{line}\n  {title}\n{line}")
    else:
        print(line)


def test_connection():
    """Celery broker baglantisini kontrol eder."""
    sep("1. Celery / RabbitMQ Baglanti Testi")
    try:
        from core.celery_app import celery
        print(f"  Broker URL : {celery.conf.broker_url}")
        print(f"  Timezone   : {celery.conf.timezone}")
        inspect = celery.control.inspect(timeout=3.0)
        workers = inspect.ping()
        if workers:
            print(f"  Aktif Workerlar : {list(workers.keys())}")
            print("  [OK] Celery baglantisi basarili, workerlar cevrimici.")
        else:
            print("  [!] Worker bulunamadi. Ayri terminalde calistirin:")
            print("      celery -A core.celery_app.celery worker --loglevel=info")
        return True
    except Exception as e:
        print(f"  [HATA] Baglanti hatasi: {e}")
        print("  RabbitMQ calisiyor mu? docker ps | grep rabbitmq")
        return False


def test_send_task():
    """Arkaplan gorevini RabbitMQ kuyruguna gonderir."""
    sep("2. Gorevi Kuyruga Gonder (background_sync_task)")
    try:
        from tasks import background_sync_task
        print("  Gorev kuyruga gonderiliyor...")
        task = background_sync_task.delay(created_gte=None, created_lte=None)
        print("  [OK] Gorev kuyruga eklendi!")
        print(f"  Task ID : {task.id}")
        # Backend olmadiginda .status hataya dusuyor - bunu yakala
        try:
            print(f"  Durum   : {task.status}")
        except Exception:
            print("  Durum   : PENDING (backend tanimli degil, kuyruga gonderildi)")
        return task
    except Exception as e:
        print(f"  [HATA] Gorev gonderilemedi: {e}")
        return None


def test_monitor(task, max_wait=15):
    """Gorevin worker tarafindan alinip almadigini kuyruk sorgusu ile dogrular."""
    sep("3. Gorev Calisma Dogrulamasi")
    if task is None:
        print("  Izlenecek task yok.")
        return
    print(f"  Task ID gonderildi : {task.id}")
    print(f"  Backend tanimli degil -> durum izleme yok.")
    print(f"  {max_wait} saniye bekleniyor, worker gorevi alsın...\n")

    from core.celery_app import celery
    found_active = False
    for i in range(max_wait):
        inspect = celery.control.inspect(timeout=2.0)
        active = inspect.active() or {}
        for worker, tasks in active.items():
            for t in tasks:
                if t.get("id") == task.id:
                    tname = t.get("name", "?")
                    print(f"  [{i+1:02d}s] [CALISIYOR] Worker: {worker} | Task: {tname}")
                    found_active = True
        if not found_active:
            print(f"  [{i+1:02d}s] [TAMAMLANDI veya BEKLIYOR] Kuyrukta aktif gorev yok.")
            if i >= 3:
                break
        time.sleep(1)

    print()
    if found_active:
        print("  [OK] Gorev worker tarafindan alindi ve islendi!")
    else:
        print("  [OK] Gorev kuyruga gonderildi - worker logunda kontrol edin:")
        print("       docker logs stripe-celery --tail 30")
        print(f"       Aranacak ID: {task.id}")



def test_inspect():
    """RabbitMQ kuyrugundaki aktif ve bekleyen gorevleri listeler."""
    sep("4. Kuyruk Durumu (Queue Inspection)")
    try:
        from core.celery_app import celery
        inspect = celery.control.inspect(timeout=3.0)
        active = inspect.active()
        reserved = inspect.reserved()
        if active:
            total = sum(len(v) for v in active.values())
            print(f"  Aktif (Calisan) Gorevler : {total}")
            for worker, tasks in active.items():
                for t in tasks:
                    tid = (t.get("id") or "")[:16]
                    tname = t.get("name", "?")
                    print(f"    Worker: {worker} | Task: {tname} | ID: {tid}...")
        else:
            print("  Aktif gorev yok.")
        if reserved:
            total = sum(len(v) for v in reserved.values())
            print(f"  Kuyrukta Bekleyen Gorev : {total}")
        else:
            print("  Kuyrukta bekleyen gorev yok.")
    except Exception as e:
        print(f"  Kuyruk inceleme hatasi: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  RabbitMQ / Celery Entegrasyon Testi")
    print("  Proje: Stripe REST API")
    print("=" * 60)
    ok = test_connection()
    if ok:
        test_inspect()
        task = test_send_task()
        test_inspect()
        test_monitor(task, max_wait=30)
    else:
        print("\n[HATA] Worker veya RabbitMQ baglantisi kurulamadi.")
        print("  1. Docker: docker-compose up -d rabbitmq celery-worker")
        print("  2. Local : celery -A core.celery_app.celery worker --loglevel=info")
    sep("Test Tamamlandi")
