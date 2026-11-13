"""Writes .eml files (with PDF attachments) for the three walkthrough requests, for testing email upload."""
import io, os, sys
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from app.samples import SCENARIOS  # noqa: E402

def pdf(title, text):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 14); c.drawString(72, 720, title); c.setFont("Helvetica", 11)
    y = 696
    for chunk in text.split(". "):
        for i in range(0, len(chunk), 90):
            c.drawString(72, y, chunk[i:i + 90]); y -= 16
    c.save(); return buf.getvalue()

out = os.path.dirname(__file__)
for key, s in SCENARIOS.items():
    m = EmailMessage()
    m["Subject"], m["From"], m["To"], m["Date"] = s["email"]["subject"], s["email"]["from"], "onboarding@tlm.example", s["email"]["date"]
    m.set_content(s["email"]["body"])
    for name, text in s["attachments"].items():
        pname = name.replace(".txt", ".pdf")
        m.add_attachment(pdf(pname.replace("_", " ").replace(".pdf", ""), text), maintype="application", subtype="pdf", filename=pname)
    with open(os.path.join(out, f"{key}.eml"), "wb") as f:
        f.write(bytes(m))
    print("wrote", key)
