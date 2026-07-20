import json
import time
from flask import Blueprint, jsonify, request, Response
from services.export_service import export_data
from services.import_service import (
    parse_file,
    infer_data_types,
    validate_and_map_records,
    execute_import_record,
)

admin_data_ops_bp = Blueprint("admin_data_ops", __name__, url_prefix="/api")


@admin_data_ops_bp.route("/export", methods=["POST"])
def api_export():
    """
    Stripe'tan veri çekip JSON veya CSV olarak tarayıcıya indirir.
    body: { "resource": "customers", "format": "json", "limit": "100", "created_gte": 1720000000, "created_lte": 1730000000, "fields": ["id", "name"] }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body bekleniyor."}), 400

    resource = data.get("resource", "")
    fmt = data.get("format", "json")
    limit_val = data.get("limit", "100")
    created_gte = data.get("created_gte")
    created_lte = data.get("created_lte")
    fields = data.get("fields")

    valid_resources = ("customers", "products", "payments", "refunds")
    if resource not in valid_resources:
        return jsonify({"error": f"Geçersiz kaynak. Geçerli: {valid_resources}"}), 400
    if fmt not in ("json", "csv"):
        return jsonify({"error": "Geçersiz format. 'json' veya 'csv' kullanın."}), 400

    try:
        content = export_data(
            resource=resource,
            fmt=fmt,
            limit_val=limit_val,
            created_gte=created_gte,
            created_lte=created_lte,
            fields=fields,
        )
        if fmt == "json":
            mimetype = "application/json"
            filename = f"{resource}.json"
        else:
            mimetype = "text/csv; charset=utf-8"
            filename = f"{resource}.csv"
    except Exception as e:
        return jsonify({"error": f"Export hatası: {str(e)}"}), 500

    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_data_ops_bp.route("/import/analyze", methods=["POST"])
def api_import_analyze():
    """
    Yüklenen dosyayı okur, veri tiplerini analiz eder ve ilk 3 satırın önizlemesini döner.
    """
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]  # elimizde Flaskın FileStorage nesnesi var
    filename = file.filename  # name alinma sebebi json mi csv mi onu anlamak icin

    try:
        file_bytes = file.read()
        records = parse_file(file_bytes, filename)
        if not records:
            return jsonify({"error": "Dosya boş veya okunamadı."}), 400

        inferred_types = infer_data_types(records)
        preview = records[:3]

        return jsonify(
            {
                "filename": filename,
                "total_rows": len(records),
                "columns": list(inferred_types.keys()),
                "inferred_types": inferred_types,
                "preview": preview,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Dosya analiz hatası: {str(e)}"}), 400


@admin_data_ops_bp.route("/import/preview", methods=["POST"])
def api_import_preview():
    """
    Dosyayı ve eşleştirme şemasını alır, geçerli/geçersiz kayıtları doğrular.
    """
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]
    target_model = request.form.get("model")
    mapping_str = request.form.get("mapping")

    if not target_model or not mapping_str:
        return jsonify({"error": "Model ve eşleştirme bilgisi zorunludur."}), 400

    try:
        mapping = json.loads(mapping_str)
        file_bytes = file.read()
        records = parse_file(file_bytes, file.filename)

        result = validate_and_map_records(records, target_model, mapping)
        return jsonify(
            {
                "total_records": len(records),
                "valid_count": len(result["valid"]),
                "invalid_count": len(result["invalid"]),
                "existing_count": len(result["existing"]),
                "valid": result["valid"][:10],  # Önizleme için ilk 10 adet geçerli
                "invalid": result["invalid"][:10],  # Önizleme için ilk 10 adet geçersiz
                "existing": result["existing"][:10],  # Önizleme için ilk 10 adet mevcut
            }
        )
    except Exception as e:
        return jsonify({"error": f"Önizleme oluşturma hatası: {str(e)}"}), 400


@admin_data_ops_bp.route("/import/execute", methods=["POST"])
def api_import_execute():
    """
    Dosyayı ve eşleştirme şemasını alır, geçerli kayıtları Stripe ve veritabanına aktarır.
    """
    if "file" not in request.files:
        return jsonify({"error": "Dosya yüklenmedi."}), 400

    file = request.files["file"]
    target_model = request.form.get("model")
    mapping_str = request.form.get("mapping")

    if not target_model or not mapping_str:
        return jsonify({"error": "Model ve eşleştirme bilgisi zorunludur."}), 400

    try:
        mapping = json.loads(mapping_str)
        file_bytes = file.read()
        records = parse_file(file_bytes, file.filename)

        validation = validate_and_map_records(records, target_model, mapping)
        valid_records = validation["valid"]

        results = {"success": 0, "failed": 0, "failed_list": []}

        for item in valid_records:
            time.sleep(0.3)  # Rate limit koruması
            mapped_data = item["mapped"]
            res = execute_import_record(target_model, mapped_data)

            if res["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_list"].append(
                    {
                        "row_index": item["row_index"],
                        "mapped": mapped_data,
                        "reason": res["reason"],
                    }
                )

        # Geçersiz kayıtları da hata raporuna ekle
        for item in validation["invalid"]:
            results["failed"] += 1
            results["failed_list"].append(
                {
                    "row_index": item["row_index"],
                    "mapped": item["mapped"],
                    "reason": f"Doğrulama Hatası: {item['reason']}",
                }
            )

        return jsonify({"message": "Aktarım tamamlandı.", "stats": results})
    except Exception as e:
        return jsonify({"error": f"Aktarım hatası: {str(e)}"}), 400
