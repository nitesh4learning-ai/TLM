"""Turns uploaded email files (.eml, .msg) and documents into plain text for the Intake agent."""
import email
import io
from email import policy


def pdf_text(data):
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return ""


def doc_text(name, data):
    low = name.lower()
    if low.endswith(".pdf"):
        return pdf_text(data)
    if low.endswith((".txt", ".md", ".csv")):
        return data.decode("utf-8", "replace")
    if low.endswith(".docx"):
        try:
            import zipfile, re
            xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8", "replace")
            return re.sub(r"<[^>]+>", " ", xml)
        except Exception:
            return ""
    return ""


def parse_eml(data):
    msg = email.message_from_bytes(data, policy=policy.default)
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    attachments = []
    for part in msg.iter_attachments():
        name = part.get_filename() or "attachment"
        payload = part.get_payload(decode=True) or b""
        attachments.append({"name": name, "bytes": len(payload), "text": doc_text(name, payload), "data": payload, "type": part.get_content_type()})
    return {"subject": msg.get("subject", ""), "from": msg.get("from", ""), "to": msg.get("to", ""), "date": msg.get("date", ""), "body": text, "attachments": attachments}


def parse_msg(data):
    import extract_msg
    m = extract_msg.Message(io.BytesIO(data))
    atts = [{"name": a.longFilename or a.shortFilename or "attachment", "bytes": len(a.data or b""),
             "text": doc_text(a.longFilename or "", a.data or b""), "data": a.data or b"", "type": ""} for a in m.attachments if getattr(a, "data", None) is not None]
    return {"subject": m.subject or "", "from": m.sender or "", "to": m.to or "", "date": str(m.date or ""), "body": m.body or "", "attachments": atts}


def parse_upload(files):
    """files: list of (name, bytes). The first .eml/.msg is the email; other files are extra attachments."""
    mail, extra = None, []
    for name, data in files:
        low = name.lower()
        if mail is None and low.endswith(".eml"):
            mail = parse_eml(data)
        elif mail is None and low.endswith(".msg"):
            mail = parse_msg(data)
        else:
            extra.append({"name": name, "bytes": len(data), "text": doc_text(name, data), "data": data, "type": ""})
    if mail is None:
        # no .eml/.msg: a plain-text email (e.g. email.txt) becomes the body
        body_file = next((a for a in extra if a["name"].lower().endswith(".txt")), None)
        if body_file:
            extra.remove(body_file)
        mail = {"subject": "", "from": "", "to": "", "date": "", "body": body_file["text"] if body_file else "", "attachments": []}
        if body_file:
            for line in body_file["text"].splitlines()[:6]:
                for k in ("Subject", "From", "To", "Date"):
                    if line.startswith(k + ":"):
                        mail[k.lower()] = line.split(":", 1)[1].strip()
    mail["attachments"] += extra
    return mail


def to_prompt(mail):
    parts = [f"Subject: {mail.get('subject','')}", f"From: {mail.get('from','')}", f"Date: {mail.get('date','')}", "", mail.get("body", "")]
    for a in mail.get("attachments", []):
        parts += ["", f"--- Attachment: {a['name']} ---", a.get("text") or "(no readable text)"]
    return "\n".join(parts)
