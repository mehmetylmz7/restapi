from flask import Blueprint, jsonify, request, render_template

rabbitmq_demo_bp = Blueprint("rabbitmq_demo", __name__)


@rabbitmq_demo_bp.route("/test-rabbitmq")
def test_rabbitmq_page():
    """RabbitMQ demo sayfasini render eder."""
    return render_template("test_rabbitmq.html")


@rabbitmq_demo_bp.route("/api/rabbitmq/send-task", methods=["POST"])
def send_task():
    """
    Belirtilen task tipini RabbitMQ kuyruguna gonderir.
    body: { "task_type": "customers" | "invoices", "limit": 10, "starting_after": null }
    """
    from tasks import fetch_customers_task, fetch_invoices_task

    data = request.get_json(silent=True) or {}
    task_type = data.get("task_type", "customers")
    limit = int(data.get("limit", 10))
    starting_after = data.get("starting_after") or None

    if task_type == "customers":
        task = fetch_customers_task.delay(limit=limit, starting_after=starting_after)
        label = "Musteriler"
    elif task_type == "invoices":
        task = fetch_invoices_task.delay(limit=limit, starting_after=starting_after)
        label = "Faturalar"
    else:
        return jsonify({"error": "Gecersiz task_type"}), 400

    return jsonify({
        "success": True,
        "task_id": task.id,
        "task_type": task_type,
        "label": label,
        "message": f"{label} gorevi RabbitMQ kuyruguna gonderildi!",
    }), 202


@rabbitmq_demo_bp.route("/api/rabbitmq/queue-status", methods=["GET"])
def queue_status():
    """
    Celery inspect ile aktif ve bekleyen gorevleri listeler.
    RabbitMQ dashboard'undaki kuyruk durumunu yansitir.
    """
    from core.celery_app import celery

    try:
        inspect = celery.control.inspect(timeout=2.0)
        active_raw = inspect.active() or {}
        reserved_raw = inspect.reserved() or {}

        active_tasks = []
        for worker, tasks in active_raw.items():
            for t in tasks:
                active_tasks.append({
                    "id": t.get("id", "")[:20] + "...",
                    "full_id": t.get("id", ""),
                    "name": t.get("name", "?").replace("fetch_", "").replace("_task", ""),
                    "worker": worker.split("@")[1][:12] if "@" in worker else worker,
                    "args": str(t.get("kwargs", {})),
                })

        reserved_tasks = []
        for worker, tasks in reserved_raw.items():
            for t in tasks:
                reserved_tasks.append({
                    "id": t.get("id", "")[:20] + "...",
                    "name": t.get("name", "?").replace("fetch_", "").replace("_task", ""),
                    "worker": worker.split("@")[1][:12] if "@" in worker else worker,
                })

        workers = list(active_raw.keys()) or list(reserved_raw.keys())

        return jsonify({
            "online": len(workers) > 0,
            "workers": [w.split("@")[1][:16] if "@" in w else w for w in workers],
            "active_count": len(active_tasks),
            "reserved_count": len(reserved_tasks),
            "active_tasks": active_tasks,
            "reserved_tasks": reserved_tasks,
        })

    except Exception as e:
        return jsonify({
            "online": False,
            "workers": [],
            "active_count": 0,
            "reserved_count": 0,
            "active_tasks": [],
            "reserved_tasks": [],
            "error": str(e),
        })


@rabbitmq_demo_bp.route("/api/rabbitmq/task-result/<task_id>", methods=["GET"])
def task_result(task_id):
    """
    Verilen task_id icin sonucu dondurur.
    Not: CELERY_RESULT_BACKEND tanimli degilse sonuc alinamaz,
    ancak worker logu uzerinden dogrulanabilir.
    """
    from core.celery_app import celery
    from celery.result import AsyncResult

    try:
        result = AsyncResult(task_id, app=celery)
        status = result.status

        if status == "SUCCESS":
            return jsonify({
                "status": "SUCCESS",
                "result": result.result,
            })
        elif status == "FAILURE":
            return jsonify({
                "status": "FAILURE",
                "error": str(result.result),
            })
        else:
            return jsonify({"status": status})

    except Exception as e:
        return jsonify({"status": "UNKNOWN", "error": str(e)})
