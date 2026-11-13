"""TLM API: policies, agents, requests and the agent pipeline, Business ready records, hierarchy."""
import datetime
import json
import mimetypes
import os
import re
import uuid

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, File, HTTPException, UploadFile, Form  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from . import emailparse, llm, pipeline, store  # noqa: E402
from .agents import AGENTS  # noqa: E402
from .reference import HIERARCHY, load_policies  # noqa: E402
from .samples import SCENARIOS, mail_for  # noqa: E402

app = FastAPI(title="TLM · Agentic MDM API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

FOLDERS = {"match-survivorship": "Match & survivorship", "business-rules": "Business rules · extended attributes",
           "regulatory": "Regulatory", "bpo-playbooks": "BPO playbooks", "agent-policies": "Agent policies"}


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm.available(), "model": llm.MODEL if llm.available() else None}


# ------------------------------------------------------------------ policies
def policies():
    base = load_policies()
    drafts = store.read("policy_drafts", {})
    out = []
    for p in base["policies"] + [d for d in drafts.values() if d.get("new")]:
        d = drafts.get(p["id"], {})
        q = dict(p, **{k: v for k, v in d.items() if k != "new"})
        q["status"] = "Draft" if d else "Published"
        q["version"] = d.get("version", "1.0")
        q["levelName"] = base["levels"][q["level"]]
        q["folderName"] = FOLDERS.get(q["folder"], q["folder"])
        out.append(q)
    return out


@app.get("/api/policies")
def list_policies():
    return {"folders": [{"key": k, "name": v} for k, v in FOLDERS.items()], "levels": load_policies()["levels"], "policies": policies()}


class PolicyEdit(BaseModel):
    text: str | None = None
    level: str | None = None
    rows: list | None = None
    exceptions: str | None = None


@app.put("/api/policies/{pid}")
def edit_policy(pid: str, body: PolicyEdit):
    if not any(p["id"] == pid for p in policies()):
        raise HTTPException(404, "No such policy")
    drafts = store.read("policy_drafts", {})
    d = drafts.get(pid, {})
    d.update({k: v for k, v in body.model_dump().items() if v is not None})
    d["version"] = "1.1"
    d["editedAt"] = datetime.datetime.now().isoformat(timespec="minutes")
    drafts[pid] = d
    store.write("policy_drafts", drafts)
    return next(p for p in policies() if p["id"] == pid)


@app.post("/api/policies/upload")
async def upload_policy(file: UploadFile = File(...)):
    data = await file.read()
    text = emailparse.doc_text(file.filename, data)
    if not text.strip():
        raise HTTPException(400, "Could not read text from the file. Upload a .pdf, .docx, .md or .txt.")
    if not llm.available():
        raise HTTPException(503, "Set ANTHROPIC_API_KEY in backend/.env so the policy agent can draft rules from the document.")
    draft = llm.draft_policy(text)
    drafts = store.read("policy_drafts", {})
    n = len([k for k in drafts if k.startswith("UP-")]) + 1
    pid = f"UP-{n:03d}"
    draft.update({"id": pid, "new": True, "cites": [], "version": "0.1", "source": file.filename})
    draft["rows"] = [list(r)[:3] for r in draft.get("rows", [])]
    drafts[pid] = draft
    store.write("policy_drafts", drafts)
    return next(p for p in policies() if p["id"] == pid)


# ------------------------------------------------------------------ agents
@app.get("/api/agents")
def list_agents():
    changes = store.read("agent_changes", {})
    pol = policies()
    out = []
    for a in AGENTS:
        c = changes.get(a["name"])
        out.append(dict(a, policies=[p["id"] for p in pol if p["agent"] == a["name"]], pendingChange=c))
    return out


class AgentChange(BaseModel):
    model: str | None = None
    stops: str | None = None


@app.patch("/api/agents/{name}")
def change_agent(name: str, body: AgentChange):
    if not any(a["name"] == name for a in AGENTS):
        raise HTTPException(404, "No such agent")
    changes = store.read("agent_changes", {})
    changes[name] = dict(body.model_dump(), status="Waiting for governance approval", submitted=datetime.datetime.now().isoformat(timespec="minutes"))
    store.write("agent_changes", changes)
    return changes[name]


# ------------------------------------------------------------------ requests
def new_request_id():
    reqs = store.requests()
    nums = [int(k.split("-")[1]) for k in reqs] or [10481]
    return f"REQ-{max(nums) + 1}"


def run_from_mail(mail, channel):
    rid = new_request_id()
    if llm.available():
        try:
            fields, summary = llm.extract_intake(emailparse.to_prompt(mail))
        except Exception as e:
            raise HTTPException(502, f"Intake agent could not reach Claude: {str(e)[:300]}")
    else:
        raise HTTPException(503, "Set ANTHROPIC_API_KEY in backend/.env to let the Intake agent read uploaded emails.")
    return pipeline.run(rid, fields, summary, mail=mail, channel=channel)


@app.get("/api/scenarios")
def scenarios():
    return [{"key": k, "title": s["title"], "party": s["party"], "subject": s["email"]["subject"],
             "attachments": list(s["attachments"].keys())} for k, s in SCENARIOS.items()]


@app.post("/api/scenarios/{key}/run")
def run_scenario(key: str):
    if key not in SCENARIOS:
        raise HTTPException(404, "No such scenario")
    mail = mail_for(key)
    if llm.available():
        return run_from_mail(mail, "Email to the onboarding inbox")
    rid = new_request_id()
    req = pipeline.run(rid, SCENARIOS[key]["fallback"], "Key values from the sample (Claude not configured).", mail=mail, channel="Email to the onboarding inbox")
    req["llm"] = False
    store.save_request(req)
    return req


UPLOADS = os.path.join(store.STORE_DIR, "uploads")
SAFE = re.compile(r"[^A-Za-z0-9._ -]")


def _safe(name):
    return SAFE.sub("_", os.path.basename(name or "file")) or "file"


def save_upload(mail):
    uid = uuid.uuid4().hex[:12]
    d = os.path.join(UPLOADS, uid)
    os.makedirs(d, exist_ok=True)
    atts, seen = [], set()
    for a in mail["attachments"]:
        name = _safe(a["name"])
        while name in seen:
            name = "copy-" + name
        seen.add(name)
        with open(os.path.join(d, name), "wb") as f:
            f.write(a.get("data") or b"")
        atts.append({"name": name, "bytes": a["bytes"], "text": a.get("text", ""), "url": f"/api/uploads/{uid}/files/{name}"})
    meta = {k: mail.get(k, "") for k in ("subject", "from", "to", "date", "body")}
    meta.update({"id": uid, "attachments": atts})
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta


def load_upload(uid):
    p = os.path.join(UPLOADS, _safe(uid), "meta.json")
    if not os.path.exists(p):
        raise HTTPException(404, "No such upload")
    with open(p) as f:
        return json.load(f)


def public(meta):
    return {k: v for k, v in meta.items() if k != "attachments"} | {"attachments": [{k: a[k] for k in ("name", "bytes", "url")} for a in meta["attachments"]]}


@app.post("/api/uploads")
async def preview_upload(files: list[UploadFile] = File(...)):
    """Parses an uploaded email and its attachments and keeps them, so the Intake page can show them before submitting."""
    items = [(f.filename, await f.read()) for f in files]
    mail = emailparse.parse_upload(items)
    if not (mail["body"] or mail["attachments"]):
        raise HTTPException(400, "No readable email or documents in the upload.")
    return public(save_upload(mail))


@app.get("/api/uploads/{uid}")
def get_upload(uid: str):
    return public(load_upload(uid))


@app.get("/api/uploads/{uid}/files/{name}")
def upload_file(uid: str, name: str):
    p = os.path.join(UPLOADS, _safe(uid), _safe(name))
    if not os.path.exists(p) or name == "meta.json":
        raise HTTPException(404, "No such file")
    mt = mimetypes.guess_type(p)[0] or "application/octet-stream"
    return FileResponse(p, media_type=mt, headers={"Content-Disposition": f'inline; filename="{_safe(name)}"'})


@app.post("/api/uploads/{uid}/submit")
def submit_upload(uid: str):
    meta = load_upload(uid)
    req = run_from_mail(meta, "Uploaded email")
    req["uploadId"] = uid
    store.save_request(req)
    return req


@app.post("/api/requests/upload")
async def upload_request(files: list[UploadFile] = File(...)):
    items = [(f.filename, await f.read()) for f in files]
    mail = emailparse.parse_upload(items)
    if not (mail["body"] or mail["attachments"]):
        raise HTTPException(400, "No readable email or documents in the upload.")
    meta = save_upload(mail)
    req = run_from_mail(meta, "Uploaded email")
    req["uploadId"] = meta["id"]
    store.save_request(req)
    return req


class TextRequest(BaseModel):
    text: str


@app.post("/api/requests/text")
def text_request(body: TextRequest):
    return run_from_mail({"subject": "", "from": "", "date": "", "body": body.text, "attachments": []}, "Pasted text")


@app.get("/api/requests")
def list_requests():
    reqs = sorted(store.requests().values(), key=lambda r: int(r["id"].split("-")[1]), reverse=True)
    return [{k: r.get(k) for k in ("id", "created", "legalName", "requestType", "recordId", "status", "touchless", "decision", "channel")} for r in reqs]


@app.delete("/api/requests/{rid}")
def delete_request(rid: str):
    r = store.requests().get(rid)
    if not r:
        raise HTTPException(404, "No such request")
    pipeline.delete(r)
    return {"deleted": rid, "undid": r.get("effects") or {}}


class DeleteMany(BaseModel):
    ids: list[str]


@app.post("/api/requests/delete")
def delete_many(body: DeleteMany):
    done = []
    for rid in body.ids:
        r = store.requests().get(rid)
        if r:
            pipeline.delete(r)
            done.append(rid)
    return {"deleted": done}


@app.get("/api/requests/{rid}")
def get_request(rid: str):
    r = store.requests().get(rid)
    if not r:
        raise HTTPException(404, "No such request")
    return r


class Approval(BaseModel):
    who: str = "Data steward"
    note: str = ""


@app.post("/api/requests/{rid}/stages/{key}/approve")
def approve(rid: str, key: str, body: Approval):
    r = store.requests().get(rid)
    if not r:
        raise HTTPException(404, "No such request")
    return pipeline.approve(r, key, body.who, body.note)


@app.get("/api/queue")
def queue():
    out = []
    for r in store.requests().values():
        for s in r["stages"]:
            if s["state"] == "waiting":
                out.append({"requestId": r["id"], "legalName": r["legalName"], "stage": s["key"], "stageName": s["name"],
                            "waitingFor": s["waitingFor"], "summary": s["summary"], "policies": s["policies"]})
    return out


# ------------------------------------------------------------------ records and hierarchy
@app.get("/api/records")
def list_records():
    recs = store.records().values()
    return [{k: r.get(k) for k in ("id", "legalName", "status", "address", "type")} | {"sources": len(r.get("crossReferences", []))}
            for r in sorted(recs, key=lambda r: (-len(r.get("crossReferences", [])), r["id"]))]


@app.get("/api/records/{rid}")
def get_record(rid: str):
    r = store.records().get(rid)
    if not r:
        raise HTTPException(404, "No such record")
    return r


@app.get("/api/hierarchy")
def hierarchy():
    recs = {r.get("hierarchyNode"): r["id"] for r in store.records().values() if r.get("hierarchyNode")}
    return dict(HIERARCHY, nodes=[dict(n, recordId=recs.get(n["id"])) for n in HIERARCHY["nodes"]])


@app.get("/api/summary")
def summary():
    reqs = list(store.requests().values())
    waiting = sum(1 for r in reqs for s in r["stages"] if s["state"] == "waiting")
    return {"requests": len(reqs), "touchless": sum(1 for r in reqs if r.get("touchless")), "waiting": waiting,
            "records": len(store.records()), "policies": len(policies()), "agents": len(AGENTS), "llm": llm.available()}


@app.post("/api/reset")
def reset():
    import shutil
    shutil.rmtree(UPLOADS, ignore_errors=True)
    for name in ("requests", "records", "policy_drafts", "agent_changes"):
        p = store._path(name)
        if os.path.exists(p):
            os.remove(p)
    return {"ok": True}
