import os
import tempfile

os.environ["TLM_STORE_DIR"] = tempfile.mkdtemp()
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
    assert len(p["policies"]) == 15
    e = c.put("/api/policies/BR-PT-001", json={"text": "Edited text"}).json()
    assert e["status"] == "Draft" and e["text"] == "Edited text"


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
