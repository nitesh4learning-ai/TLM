"""TLM API: policies, agents, requests and the agent pipeline, Business ready records, hierarchy."""
import datetime
import json
import mimetypes
import os
import re
import uuid

from dotenv import load_dotenv

if not os.environ.get("TLM_TESTING"):  # tests never read your .env or call Claude
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


# ------------------------------------------------------------------ policies (runtime store)
from . import policystore  # noqa: E402


def view(p):
    q = {k: v for k, v in p.items()}
    q["completeness"] = policystore.completeness(p)
    q["levelName"] = policystore.levels().get(q.get("level"), "")
    q["folderName"] = FOLDERS.get(q.get("folder"), q.get("folder"))
    return q


def policies():
    return [view(p) for p in policystore.all_policies().values()]


@app.get("/api/policies")
def list_policies():
    from . import rules
    return {"folders": [{"key": k, "name": v} for k, v in FOLDERS.items()], "levels": policystore.levels(), "policies": policies(),
            "agents": [policystore.ALL] + policystore.AGENT_NAMES, "attributes": rules.ATTRIBUTES, "ops": rules.OPS,
            "required": policystore.REQUIRED}


@app.get("/api/policies/{pid}")
def get_policy(pid: str):
    p = policystore.all_policies().get(pid)
    if not p:
        raise HTTPException(404, "No such policy")
    return view(p)


class PolicyEdit(BaseModel):
    title: str | None = None
    folder: str | None = None
    stage: str | None = None
    level: str | None = None
    owner: str | None = None
    text: str | None = None
    rows: list | None = None
    exceptions: str | None = None
    cites: list | None = None
    appliesTo: list | None = None
    roles: list | None = None
    params: list | None = None
    effective: str | None = None
    status: str | None = None
    publish: bool | None = None
    steward: str | None = None
    effectiveTo: str | None = None
    recordTypes: list | None = None
    regions: list | None = None
    triggers: list | None = None
    inputs: list | None = None
    rules: list | None = None
    approverRole: str | None = None
    escalation: str | None = None
    slaHours: float | None = None
    priority: int | None = None
    complianceFloor: bool | None = None
    citationRequired: bool | None = None
    testCases: list | None = None
    source: str | None = None


@app.put("/api/policies/{pid}")
def edit_policy(pid: str, body: PolicyEdit):
    if body.level and body.level not in ("A", "B", "H"):
        raise HTTPException(400, "Autonomy level must be A, B or H")
    if body.appliesTo is not None and not body.appliesTo:
        raise HTTPException(400, "Assign the policy to at least one agent, or to All agents")
    try:
        return view(policystore.save(pid, body.model_dump()))
    except KeyError:
        raise HTTPException(404, "No such policy")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/policies/{pid}/test")
def test_policy(pid: str, body: PolicyEdit | None = None):
    """Runs the policy's test cases through the rules engine; pass a draft in the body to test unsaved edits."""
    from . import rules
    p = policystore.all_policies().get(pid)
    if not p:
        raise HTTPException(404, "No such policy")
    draft = dict(p)
    if body:
        draft.update({k: v for k, v in body.model_dump().items() if v is not None})
    return {"results": rules.run_tests(draft)}


@app.post("/api/policies")
def new_policy(body: PolicyEdit):
    return view(policystore.create({k: v for k, v in body.model_dump().items() if v is not None}))


@app.post("/api/policies/upload")
async def upload_policy(file: UploadFile = File(...)):
    data = await file.read()
    text = emailparse.doc_text(file.filename, data)
    if not text.strip():
        raise HTTPException(400, "Could not read text from the file. Upload a .pdf, .docx, .md or .txt.")
    if not llm.available():
        raise HTTPException(503, "Set ANTHROPIC_API_KEY in backend/.env so the policy agent can draft rules from the document.")
    from . import rules
    fields, sources = llm.draft_policy(text, list(rules.ATTRIBUTES))
    form = ["title", "folder", "owner", "steward", "effective", "effectiveTo", "appliesTo", "roles", "recordTypes", "regions", "triggers",
            "level", "approverRole", "escalation", "slaHours", "text", "exceptions", "source", "params", "rows", "rules"]
    fs = {}
    for k in form:
        if fields.get(k) not in (None, "", []):
            fs[k] = {"from": "document", "quote": (sources.get(k) or {}).get("quote", ""), "confidence": (sources.get(k) or {}).get("confidence")}
        else:
            fs[k] = {"from": "governance"}
    values = {k: fields[k] for k in form if fields.get(k) not in (None, "", [])}
    values.update({"prefix": "UP", "status": "Draft", "fieldSources": fs, "source": fields.get("source") or file.filename,
                   "engine": bool(fields.get("rules"))})
    if "rows" in values:
        values["rows"] = [list(r)[:3] for r in values["rows"]]
    p = policystore.create(values)
    return view(p)


# ------------------------------------------------------------------ agents
@app.get("/api/agents")
def list_agents():
    changes = store.read("agent_changes", {})
    pol = policies()
    out = []
    for a in AGENTS:
        c = changes.get(a["name"])
        mine = policystore.for_agent(a["name"])
        out.append(dict(a, policies=[p["id"] for p in mine if policystore.ALL not in p.get("appliesTo", [])],
                        universal=[p["id"] for p in mine if policystore.ALL in p.get("appliesTo", [])], pendingChange=c))
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


def run_from_mail(mail, channel, mode="auto"):
    rid = new_request_id()
    if llm.available():
        try:
            fields, summary = llm.extract_intake(emailparse.to_prompt(mail))
        except Exception as e:
            raise HTTPException(502, f"Intake agent could not reach Claude: {str(e)[:300]}")
    else:
        raise HTTPException(503, "Set ANTHROPIC_API_KEY in backend/.env to let the Intake agent read uploaded emails.")
    return pipeline.run(rid, fields, summary, mail=mail, channel=channel, mode=mode)


@app.get("/api/scenarios")
def scenarios():
    return [{"key": k, "title": s["title"], "party": s["party"], "subject": s["email"]["subject"],
             "attachments": list(s["attachments"].keys())} for k, s in SCENARIOS.items()]


@app.post("/api/scenarios/{key}/run")
def run_scenario(key: str, mode: str = "auto"):
    if key not in SCENARIOS:
        raise HTTPException(404, "No such scenario")
    mail = mail_for(key)
    if llm.available():
        return run_from_mail(mail, "Email to the onboarding inbox", mode)
    rid = new_request_id()
    req = pipeline.run(rid, SCENARIOS[key]["fallback"], "Key values from the sample (Claude not configured).", mail=mail, channel="Email to the onboarding inbox", mode=mode)
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
def submit_upload(uid: str, mode: str = "auto"):
    meta = load_upload(uid)
    req = run_from_mail(meta, "Uploaded email", mode)
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
    mode: str = "auto"


@app.post("/api/requests/text")
def text_request(body: TextRequest):
    return run_from_mail({"subject": "", "from": "", "date": "", "body": body.text, "attachments": []}, "Pasted text", body.mode)


@app.post("/api/requests/{rid}/next")
def next_agent(rid: str):
    r = store.requests().get(rid)
    if not r:
        raise HTTPException(404, "No such request")
    try:
        return pipeline.advance(r)
    except pipeline.StepBlocked as e:
        raise HTTPException(409, str(e))


@app.get("/api/requests")
def list_requests():
    reqs = sorted(store.requests().values(), key=lambda r: int(r["id"].split("-")[1]), reverse=True)
    return [{k: r.get(k) for k in ("id", "created", "legalName", "requestType", "recordId", "status", "touchless", "decision", "channel", "mode")} for r in reqs]


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
        for s in r["stages"][: r.get("revealed", len(r["stages"]))]:
            if s["state"] == "waiting":
                out.append({"requestId": r["id"], "legalName": r["legalName"], "stage": s["key"], "stageName": s["name"],
                            "waitingFor": s["waitingFor"], "summary": s["summary"], "policies": s["policies"]})
    return out


# ------------------------------------------------------------------ records and hierarchy
@app.get("/api/records")
def list_records():
    recs = store.records().values()
    return [{k: r.get(k) for k in ("id", "legalName", "status", "address", "type", "duns", "hierarchyNode", "parent")} | {"sources": len(r.get("crossReferences", []))}
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
    waiting = sum(1 for r in reqs for s in r["stages"][: r.get("revealed", len(r["stages"]))] if s["state"] == "waiting")
    return {"requests": len(reqs), "touchless": sum(1 for r in reqs if r.get("touchless")), "waiting": waiting,
            "records": len(store.records()), "policies": len(policies()), "agents": len(AGENTS), "llm": llm.available()}


@app.post("/api/reset-requests")
def reset_requests():
    """Clears requests and records but keeps policies, providers and agent settings."""
    import shutil
    shutil.rmtree(UPLOADS, ignore_errors=True)
    for name in ("requests", "records"):
        p = store._path(name)
        if os.path.exists(p):
            os.remove(p)
    return {"ok": True}


@app.post("/api/reset")
def reset():
    import shutil
    shutil.rmtree(UPLOADS, ignore_errors=True)
    for name in ("requests", "records", "policy_drafts", "policy_store", "agent_changes"):
        p = store._path(name)
        if os.path.exists(p):
            os.remove(p)
    return {"ok": True}


# ------------------------------------------------------------------ third-party data providers (workbench)
from . import providers  # noqa: E402


def provider_view(key, cfg):
    cat = providers.CATALOG[key]
    return {"key": key, "name": cat["name"], "purpose": cat["purpose"], "agent": cat["agent"], "fields": cat["fields"],
            "config": cfg, "secrets": providers.masked_secrets(key)}


@app.get("/api/providers")
def list_providers():
    cfgs = providers.configs()
    return {"settings": providers.settings(), "providers": [provider_view(k, c) for k, c in cfgs.items()]}


class ProviderUpdate(BaseModel):
    config: dict = {}
    secrets: dict = {}


@app.put("/api/providers/{key}")
def update_provider(key: str, body: ProviderUpdate):
    if key not in providers.CATALOG:
        raise HTTPException(404, "No such provider")
    if body.config.get("mode") not in (None, "test", "live"):
        raise HTTPException(400, "mode must be test or live")
    providers.save_config(key, body.config)
    allowed = {"apiKey", "token", "clientId", "clientSecret"}
    providers.save_secrets(key, {k: v for k, v in body.secrets.items() if k in allowed})
    return provider_view(key, providers.configs()[key])


@app.post("/api/providers/{key}/test")
def test_provider(key: str):
    if key not in providers.CATALOG:
        raise HTTPException(404, "No such provider")
    return providers.test_connection(key)


class ProviderSettings(BaseModel):
    disclaimer: str


@app.put("/api/provider-settings")
def provider_settings(body: ProviderSettings):
    return providers.save_settings(body.model_dump())


# ------------------------------------------------------------------ hierarchy search
@app.get("/api/hierarchies/search")
def search_hierarchies(q: str = ""):
    from .reference import name_sim
    qn = q.strip().lower()
    nodes = HIERARCHY["nodes"]
    root = nodes[0]
    out = []
    for n in nodes:
        if not qn or qn in n["name"].lower() or (n.get("duns") or "").replace("-", "").startswith(qn.replace("-", "")):
            out.append({"id": n["id"], "name": n["name"], "kind": n["kind"], "family": root["name"], "familyId": "brazos", "city": n.get("city"), "status": n["status"]})
    # standalone customers (no corporate family in the hub)
    for r in store.records().values():
        if r.get("hierarchyNode"):
            continue
        if not qn or qn in r["legalName"].lower():
            out.append({"id": r["id"], "name": r["legalName"], "kind": r.get("type") or "Customer", "family": r.get("parent") or "No corporate family",
                        "familyId": "record:" + r["id"], "city": None, "status": r["status"]})
    out.sort(key=lambda x: (0 if x["name"].lower().startswith(qn) else 1, x["name"]))
    return out[:50]


@app.get("/api/hierarchies/{fid}")
def get_family(fid: str):
    if fid == "brazos":
        return hierarchy()
    if fid.startswith("record:"):
        r = store.records().get(fid.split(":", 1)[1])
        if not r:
            raise HTTPException(404, "No such record")
        nodes = []
        if r.get("parent"):
            nodes.append({"id": "P", "level": 0, "kind": "Parent (from D&B)", "name": r["parent"], "parent": None, "status": "Not in hub", "city": "", "state": ""})
        nodes.append({"id": r["id"], "level": 1 if r.get("parent") else 0, "kind": r.get("type") or "Customer", "name": r["legalName"],
                      "parent": "P" if r.get("parent") else None, "status": r["status"], "address": r["address"], "duns": r.get("duns"), "recordId": r["id"],
                      "city": "", "state": ""})
        return {"summary": {"legalEntities": len(nodes), "shipToAccounts": 0, "nodes": len(nodes)}, "nodes": nodes}
    raise HTTPException(404, "No such hierarchy")


# ------------------------------------------------------------------ agent activity
STAGE_FOR = {"Intake": "intake", "Search before create": "search", "Match & merge": "match", "Enrichment": "enrich", "Validation": "validate",
             "Legal": "legal", "Procurement": "procurement", "Credit": "credit", "Tax": "tax", "Orchestrator": "record"}


@app.get("/api/agents/stats")
def agent_stats():
    reqs = list(store.requests().values())
    out = {}
    for name, key in STAGE_FOR.items():
        st = [s for r in reqs for s in r["stages"] if s["key"] == key]
        out[name] = {"runs": len(st), "auto": sum(1 for s in st if s["actor"] == "agent"), "people": sum(1 for s in st if s["actor"] == "human")}
    cfgs = providers.configs()
    uses = {}
    for k, c in providers.CATALOG.items():
        uses.setdefault(c["agent"], []).append({"key": k, "name": c["name"], "mode": cfgs[k]["mode"]})
    return {"stats": out, "providers": uses}
