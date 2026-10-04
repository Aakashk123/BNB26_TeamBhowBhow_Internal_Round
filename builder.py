import io
import uuid
from datetime import datetime, timezone

import qrcode
from eth_account import Account
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.config import settings
from app.core.eip712 import recover_report, sign_report


def build(report, key):
    if not key:
        raise ValueError("Certificate issuer key is not configured")
    document = {
        "title": "ModelLedger Provenance Verification Report",
        "certificate_id": "CERT-" + uuid.uuid4().hex,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "report": report,
        "statement": "At the time of verification, ModelLedger validated the listed evidence and bindings for this file.",
    }
    return {
        "document": document,
        "signature": sign_report(document, key),
        "issuer": Account.from_key(key).address,
        "algorithm": "EIP-191(SHA-256(RFC8785))",
    }


def verify(envelope, issuer):
    try:
        recovered = recover_report(envelope["document"], envelope["signature"])
        return recovered.lower() == issuer.lower() == envelope["issuer"].lower()
    except (ValueError, KeyError, TypeError):
        return False


def pdf(envelope):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(595, 842))
    c.setTitle("ModelLedger Provenance Verification Report")
    c.setFillColor(colors.HexColor("#123c38"))
    c.rect(0, 697, 595, 145, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 23)
    c.drawString(40, 786, "ModelLedger")
    c.setFont("Helvetica", 13)
    c.drawString(40, 760, "Provenance Verification Report")
    report = envelope["document"]["report"]
    c.setFont("Helvetica-Bold", 17)
    c.drawString(40, 720, report["status"].replace("_", " "))
    y = 660
    rows = [
        ("Certificate", envelope["document"]["certificate_id"]),
        ("Verification time", report["timestamp"]),
        ("Origin trust", report["origin_trust"]),
        ("Actor", report["origin"].get("actor") or "Unknown"),
        ("Assurance", report["origin"]["assurance"]),
        ("Binding", report["binding"]["tier"]),
        ("Version", report["binding"].get("version_id") or "Unknown"),
        ("Steps", f"{report['counts']['verified']} verified / {report['counts']['unverified']} unverified"),
        ("Gaps / conflicts", f"{report['counts']['gaps']} / {report['counts']['conflicts']}"),
        ("C2PA", report["input"].get("c2pa", {}).get("state", "NOT_CHECKED")),
        ("Chain", str(report["chain"]["chain_id"])),
        ("Contract", str(report["chain"]["contract_address"])),
        ("File SHA-256", report["input"]["sha256"]),
        ("Policy hash", report["policy_hash"]),
        ("Issuer", envelope["issuer"]),
    ]
    for label, value in rows:
        c.setFillColor(colors.HexColor("#667575"))
        c.setFont("Helvetica", 9)
        c.drawString(40, y, label)
        c.setFillColor(colors.HexColor("#142e2c"))
        c.setFont("Helvetica", 9)
        c.drawString(150, y, str(value)[:79])
        y -= 25
    if report.get("simulated"):
        c.setFillColor(colors.HexColor("#a85b00"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y - 8, "SIMULATED provider / witness demo. Not real model evidence.")
    url = settings.public_url + "/certificate/" + report["report_id"]
    qr = qrcode.make(url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), 437, 78, 112, 112)
    c.setFillColor(colors.HexColor("#142e2c"))
    c.setFont("Helvetica", 9)
    c.drawString(40, 157, "This report certifies a verification result, not originality.")
    c.drawString(40, 141, "At the time of verification, ModelLedger validated")
    c.drawString(40, 127, "the listed evidence and bindings for this file.")
    c.drawString(40, 102, "Download signed JSON to independently check the signature.")
    c.drawString(40, 87, "Live report access requires the owner session; unsaved reports expire.")
    c.showPage()
    c.save()
    return out.getvalue()
