from flask import Blueprint, jsonify, request
from services.file_service import upload_dispute_evidence, list_uploaded_files

admin_files_bp = Blueprint("admin_files", __name__, url_prefix="/api/files")


@admin_files_bp.route("/upload", methods=["POST"])
def api_upload_file():
    """PDF'i multipart/form-data olarak alır, Stripe Files API'ye yükler."""
    payment_intent_id = request.form.get("payment_intent_id", "").strip()
    if "file" not in request.files:
        return jsonify({"error": "Dosya bulunamadı. 'file' alanı eksik."}), 400

    f = request.files["file"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Sadece PDF dosyaları kabul edilmektedir."}), 400

    file_obj = upload_dispute_evidence(
        payment_intent_id=payment_intent_id, file_bytes=f.read(), filename=f.filename
    )
    if file_obj is None:
        return jsonify({"error": "Stripe'a yükleme başarısız."}), 500

    return jsonify(file_obj), 201


@admin_files_bp.route("", methods=["GET"])
def api_list_files():
    """DB'deki yüklü dosyaları listeler."""
    payment_id = request.args.get("payment_intent_id")
    files = list_uploaded_files(payment_id)
    # datetime nesnelerini string'e çevir
    for f in files:
        if "olusturma_tarihi" in f and f["olusturma_tarihi"]:
            f["olusturma_tarihi"] = str(f["olusturma_tarihi"])
    return jsonify({"data": files})
