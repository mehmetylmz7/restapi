from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
import datetime


def generate_payment_pdf(payment_data: dict) -> bytes:
    """
    Stripe payment_intent verisinden tek sayfalık fatura PDF'i üretir.
    Diske yazmaz — bytes döner.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4  # 595 x 842 pt

    # ── Üst başlık bandı ────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#635bff"))  # Stripe mor
    c.rect(0, height - 90, width, 90, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(2 * cm, height - 45, "ODEME FATURASI")

    c.setFont("Helvetica", 10)
    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    c.drawRightString(width - 2 * cm, height - 30, f"Olusturma: {now_str}")
    c.drawRightString(width - 2 * cm, height - 45, "Stripe REST API Manager")

    # ── Ödeme ID kutucuğu ────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#f6f8fa"))
    c.roundRect(2 * cm, height - 145, width - 4 * cm, 42, 6, fill=True, stroke=False)

    c.setFillColor(colors.HexColor("#30313d"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5 * cm, height - 120, "Odeme ID:")
    c.setFont("Helvetica", 10)
    payment_id = payment_data.get("id", "-")
    c.drawString(6 * cm, height - 120, payment_id)

    # ── Ayraç çizgisi ────────────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#e0e0e0"))
    c.setLineWidth(1)
    c.line(2 * cm, height - 160, width - 2 * cm, height - 160)

    # ── Detay alanları ───────────────────────────────────────────────
    def draw_field(label, value, y):
        c.setFillColor(colors.HexColor("#687385"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2.5 * cm, y, label)
        c.setFillColor(colors.HexColor("#30313d"))
        c.setFont("Helvetica", 10)
        c.drawString(9 * cm, y, str(value))

    amount_raw = payment_data.get("amount", 0)
    try:
        amount_val = float(amount_raw) / 100
    except (TypeError, ValueError):
        amount_val = 0.0

    currency = payment_data.get("currency", "").upper()
    status   = payment_data.get("status", "-")
    customer = payment_data.get("customer") or "-"
    meta     = payment_data.get("metadata", {})
    order_id = meta.get("order_id", "-") if isinstance(meta, dict) else "-"

    base_y = height - 195
    fields = [
        ("Musteri ID:",   customer),
        ("Tutar:",        f"{amount_val:.2f} {currency}"),
        ("Para Birimi:",  currency),
        ("Durum:",        status),
        ("Siparis ID:",   order_id),
    ]
    for label, val in fields:
        draw_field(label, val, base_y)
        base_y -= 28

    # ── Durum rozeti ─────────────────────────────────────────────────
    status_lower = status.lower()
    if status_lower == "succeeded":
        badge_color = colors.HexColor("#228403")
        badge_text  = "BASARILI"
    elif status_lower in ("canceled", "cancelled"):
        badge_color = colors.HexColor("#df1b41")
        badge_text  = "IPTAL"
    else:
        badge_color = colors.HexColor("#c84801")
        badge_text  = "BEKLEMEDE"

    badge_y = base_y - 15
    c.setFillColor(badge_color)
    c.roundRect(2.5 * cm, badge_y - 6, 3.5 * cm, 22, 4, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(4.25 * cm, badge_y + 5, badge_text)

    # ── Alt ayraç & not ──────────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#e0e0e0"))
    c.line(2 * cm, 3.5 * cm, width - 2 * cm, 3.5 * cm)

    c.setFillColor(colors.HexColor("#687385"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 2.8 * cm, "Bu belge Stripe REST API Manager tarafindan otomatik olarak uretilmistir.")
    c.drawCentredString(width / 2, 2.2 * cm, "Herhangi bir sorun icin sistem yoneticinizle iletisime gecin.")

    # ── Alt logo bandı ───────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#635bff"))
    c.rect(0, 0, width, 1 * cm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, 0.35 * cm, "Stripe REST API Manager  |  Gizli Belge")

    c.showPage()
    c.save()
    return buffer.getvalue()
