import os
import tempfile

os.environ["TLM_STORE_DIR"] = tempfile.mkdtemp()
os.environ["TLM_TESTING"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["TLM_SECRETS_FILE"] = os.path.join(os.environ["TLM_STORE_DIR"], "secrets.json")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app)


def stages(req):
    return {s["key"]: s for s in req["stages"]}


def test_new_customer():
    r = c.post("/api/scenarios/new-customer/run").json()
    s = stages(r)
    assert r["decision"] == "new"
    assert s["credit"]["actor"] == "human"            # $80,000 is above the $50,000 agent authority
    assert s["legal"]["actor"] == "agent" and s["tax"]["actor"] == "agent"
    assert r["recordId"].startswith("BRR-")


def test_existing_customer_is_touchless():
    r = c.post("/api/scenarios/existing-customer/run").json()
    assert r["decision"] == "link" and r["recordId"] == "BRR-0004417"
    assert r["touchless"], [(x["key"], x["actor"]) for x in r["stages"]]
    rec = c.get("/api/records/BRR-0004417").json()
    assert any(sa["area"] == "Specialty · US02" for sa in rec["salesAreas"])


def test_new_owner_successor_and_approvals():
    r = c.post("/api/scenarios/new-owner/run").json()
    s = stages(r)
    assert r["decision"] == "successor"
    assert s["validate"]["actor"] == "human" and s["tax"]["actor"] == "human" and s["credit"]["actor"] == "human"
    for key in [k for k, v in s.items() if v["state"] == "waiting"]:
        r = c.post(f"/api/requests/{r['id']}/stages/{key}/approve", json={"who": "Test steward"}).json()
    assert r["status"] == "Complete"
    assert c.get(f"/api/records/{r['recordId']}").json()["status"] == "Active"


def test_policies_and_edit():
    p = c.get("/api/policies").json()
    assert len(p["policies"]) == 20 and sum(x["status"] == "Draft" for x in p["policies"]) == 4
    e = c.put("/api/policies/BR-PT-001", json={"text": "Edited text"}).json()
    assert e["status"] == "Active" and e["text"] == "Edited text" and e["version"] == 2


def test_upload_needs_key():
    r = c.post("/api/requests/upload", files=[("files", ("a.eml", b"Subject: hi\n\nhello", "message/rfc822"))])
    assert r.status_code == 503


def test_delete_undoes_effects():
    r = c.post("/api/scenarios/new-customer/run").json()
    rec_id = r["recordId"]
    assert c.get(f"/api/records/{rec_id}").status_code == 200
    assert c.delete(f"/api/requests/{r['id']}").status_code == 200
    assert c.get(f"/api/records/{rec_id}").status_code == 404
    r2 = c.post("/api/scenarios/existing-customer/run").json()
    c.post("/api/requests/delete", json={"ids": [r2["id"]]})
    rec = c.get("/api/records/BRR-0004417").json()
    assert all(sa.get("addedBy") != r2["id"] for sa in rec["salesAreas"])
    assert r2["id"] not in [x["id"] for x in c.get("/api/requests").json()]


def test_upload_preview_and_files():
    data = open(os.path.join(os.path.dirname(__file__), "..", "..", "data", "test-packages", "1-new-customer-lakeside", "email.eml"), "rb").read()
    r = c.post("/api/uploads", files=[("files", ("email.eml", data, "message/rfc822"))]).json()
    assert r["subject"].startswith("RE: New account request")
    assert "Dana" in r["body"] and len(r["attachments"]) == 5
    f = c.get(r["attachments"][0]["url"])
    assert f.status_code == 200 and f.content[:4] == b"%PDF"
    assert c.get(f"/api/uploads/{r['id']}/files/meta.json").status_code == 404
    assert c.post(f"/api/uploads/{r['id']}/submit").status_code == 503   # needs the Claude key


def test_step_mode_commits_record_at_the_end():
    c.post("/api/reset")
    r = c.post("/api/scenarios/new-customer/run?mode=step").json()
    assert r["revealed"] == 1 and c.get(f"/api/records/{r['recordId']}").status_code == 404
    while True:
        x = c.post(f"/api/requests/{r['id']}/next")
        if x.status_code == 409:
            break
        r = x.json()
    r = c.post(f"/api/requests/{r['id']}/stages/credit/approve", json={"who": "T"}).json()
    while r["revealed"] < len(r["stages"]):
        r = c.post(f"/api/requests/{r['id']}/next").json()
    assert r["status"] == "Complete" and c.get(f"/api/records/{r['recordId']}").json()["status"] == "Active"


def test_validation_names_its_sources():
    r = c.post("/api/scenarios/new-owner/run").json()
    v = next(s for s in r["stages"] if s["key"] == "validate")
    srcs = [row["cells"][3]["v"] for row in v["sections"][0]["rows"]]
    assert all("test data" in s for s in srcs) and r["testData"]


def test_provider_secrets_are_masked():
    p = c.put("/api/providers/lexisnexis", json={"config": {"baseUrl": "https://example.invalid"}, "secrets": {"apiKey": "super-secret-key-1234"}}).json()
    assert p["secrets"]["apiKey"] == "••••1234"
    assert "super-secret" not in str(c.get("/api/providers").json())



def _credit(r):
    return next(s for s in r["stages"] if s["key"] == "credit")


def test_policy_edits_change_agent_decisions_at_runtime():
    c.post("/api/reset")
    assert _credit(c.post("/api/scenarios/new-customer/run").json())["actor"] == "human"   # $80,000 above $50,000
    p = c.get("/api/policies/BR-CR-001").json()
    params = [dict(x, value=100000) if x["key"] == "agent_limit" else x for x in p["params"]]
    c.put("/api/policies/BR-CR-001", json={"params": params})
    c.post("/api/reset-requests")
    r = c.post("/api/scenarios/new-customer/run").json()
    assert _credit(r)["actor"] == "agent" and _credit(r)["policyVersions"]["BR-CR-001"] == 2


def test_unassigned_policy_routes_to_a_person():
    c.post("/api/reset")
    c.put("/api/policies/MM-002", json={"appliesTo": ["Search before create"]})
    r = c.post("/api/scenarios/existing-customer/run").json()
    m = next(s for s in r["stages"] if s["key"] == "match")
    assert m["actor"] == "human" and m["status"] == "No policy assigned"


def test_autonomy_level_h_forces_a_person():
    c.post("/api/reset")
    c.put("/api/policies/BR-PR-001", json={"level": "H"})
    r = c.post("/api/scenarios/existing-customer/run").json()
    assert next(s for s in r["stages"] if s["key"] == "procurement")["actor"] == "human"


def test_rules_engine_test_cases_pass():
    for pid in ["BR-CR-001", "BR-PT-001", "BR-PM-001", "BR-TX-001", "BR-PR-001", "RG-CS-001"]:
        res = c.post(f"/api/policies/{pid}/test").json()["results"]
        assert res and all(r["passed"] for r in res), (pid, res)


def test_uploaded_document_fills_the_form(monkeypatch):
    from app import llm
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "draft_policy", lambda text, attrs: (
        {"title": "Wire payments", "level": "B", "text": "Payments above $250,000 go by wire.", "params": [{"key": "wire_above", "value": 250000, "help": "USD"}],
         "rules": [{"when": [{"attr": "proposed_limit", "op": ">", "value": "${wire_above}"}], "then": {"payment_method": "Wire"}, "decidedBy": "Treasury"}]},
        {"title": {"quote": "Wire payments policy", "confidence": 0.9}}))
    p = c.post("/api/policies/upload", files={"file": ("wire.txt", b"Wire payments policy. Payments above $250,000 go by wire.", "text/plain")}).json()
    assert p["status"] == "Draft" and p["fieldSources"]["title"]["from"] == "document"
    assert set(p["completeness"]["missing"]) >= {"owner", "appliesTo", "effective"}
    assert c.put(f"/api/policies/{p['id']}", json={"status": "Active"}).status_code == 400   # incomplete
    ok = c.put(f"/api/policies/{p['id']}", json={"owner": "Treasury", "appliesTo": ["Credit"], "effective": "2026-12-01", "status": "Active"}).json()
    assert ok["status"] == "Active" and ok["completeness"]["score"] == 100



def test_missing_w9_blocks_then_edit_resubmits():
    c.post("/api/reset")
    from app import samples
    import copy
    f = copy.deepcopy(samples.SCENARIOS["new-customer"]["fallback"]); f.pop("w9_provided")
    samples.SCENARIOS["blocked-test"] = dict(samples.SCENARIOS["new-customer"], fallback=f)
    r = c.post("/api/scenarios/blocked-test/run").json()
    assert r["decision"] == "blocked" and r["status"].startswith("Blocked at intake") and len(r["stages"]) == 1
    r = c.post(f"/api/requests/{r['id']}/resubmit", json={"fields": {"w9_provided": "yes"}, "who": "J. Ortiz"}).json()
    assert r["decision"] == "new" and len(r["stages"]) == 10 and r["history"][-1]["action"] == "Edited and resubmitted"
    del samples.SCENARIOS["blocked-test"]


def test_reject_with_email_undoes_the_record():
    c.post("/api/reset")
    r = c.post("/api/scenarios/new-customer/run").json()
    d = c.post(f"/api/requests/{r['id']}/reject-draft", json={"reason": "Bank letter unreadable", "missing": ["Bank letter"]}).json()
    assert "Bank letter" in d["body"]
    x = c.post(f"/api/requests/{r['id']}/reject", json={"reason": "Bank letter unreadable", "action": "email", "missing": ["Bank letter"], "subject": d["subject"], "body": d["body"]}).json()
    assert x["status"].startswith("Rejected") and x["rejected"]["email"]["body"]
    assert c.get(f"/api/records/{r['recordId']}").status_code == 404
    assert not [q for q in c.get("/api/queue").json() if q["requestId"] == r["id"]]


def test_agents_record_old_and_new_values():
    c.post("/api/reset")
    r = c.post("/api/scenarios/new-owner/run").json()
    ch = {x["attribute"]: x for x in r["changes"]}
    assert ch["Credit limit"]["old"] == "$120,000" and ch["Tax class"]["new"] == "Taxable" and ch["Tax class"]["policy"] == "BR-TX-001"


def test_xref_survivorship_merge_unmerge():
    c.post("/api/reset")
    rec = c.get("/api/records/BRR-0004417").json()
    x = rec["xref"]
    assert len(x["rows"]) == 7                     # 3 SAP, Oracle EBS, AS/400, D&B, address validation
    sv = {s["key"]: s for s in x["survivors"]}
    assert sv["legalName"]["system"] == "D&B" and sv["address"]["system"] == "Address validation" and sv["paymentTerms"]["value"] == "Net 30"
    r = c.post("/api/scenarios/existing-customer/run").json()
    rows = c.get("/api/records/BRR-0004417").json()["xref"]["rows"]
    assert any(row["kind"] == "intake" and row["sourceKey"] == r["id"] for row in rows)
    assert any(row["kind"] == "agent" and row["policy"] == "BR-PR-001" for row in rows)
    u = c.post("/api/records/BRR-0004417/unmerge", json={"xid": "AS/400 Order Entry:AS4-30771"}).json()
    new = u["newRecord"]
    assert c.get(f"/api/records/{new}").json()["xref"]["rows"][0]["system"] == "AS/400 Order Entry"
    m = c.post("/api/records/BRR-0004417/merge", json={"other": new}).json()
    assert any(row["system"] == "AS/400 Order Entry" for row in m["xref"]["rows"])
    # survivorship rules are editable policy: make the most recent source win the legal name
    p = c.get("/api/policies/SV-001").json()
    rules = [dict(x, method="most recent") if x["attribute"] == "legalName" else x for x in p["survivorship"]]
    c.put("/api/policies/SV-001", json={"survivorship": rules})
    c.post("/api/records/BRR-0004417/unmerge", json={"xid": "AS/400 Order Entry:AS4-30771"})   # any write re-runs survivorship
    sv = {s["key"]: s for s in c.get("/api/records/BRR-0004417").json()["xref"]["survivors"]}
    assert sv["legalName"]["reason"].startswith("Most recent")


def _actors(r):
    return {s["key"]: s["actor"] for s in r["stages"]}


def test_packages_4_to_8():
    c.post("/api/reset")
    r = c.post("/api/scenarios/missing-w9/run").json()
    assert r["decision"] == "blocked"
    r = c.post(f"/api/requests/{r['id']}/resubmit", json={"fields": {"w9_provided": "yes"}}).json()
    assert r["status"] == "Complete" and r["touchless"]
    r = c.post("/api/scenarios/expired-license/run").json()
    assert _actors(r)["validate"] == "human" and _actors(r)["legal"] == "human" and _actors(r)["credit"] == "agent"
    r = c.post("/api/scenarios/health-system-clinic/run").json()
    proc = next(s for s in r["stages"] if s["key"] == "procurement")
    assert "parent" in str(proc["sections"]) and next(s for s in r["stages"] if s["key"] == "credit")["waitingFor"] == "Credit manager and BU finance director"
    r = c.post("/api/scenarios/near-duplicate/run").json()
    assert r["decision"] == "review" and _actors(r)["match"] == "human"
    r = c.post("/api/scenarios/new-business/run").json()
    a = _actors(r)
    assert a["validate"] == a["credit"] == a["tax"] == "human" and "Prepay" in next(s for s in r["stages"] if s["key"] == "credit")["summary"]
