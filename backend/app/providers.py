"""Third-party data providers.

Each provider runs in one of two modes:
  - "test": answers come from the reference files under data/ (mock data)
  - "live": the agent calls the provider's real API with the configuration saved in the workbench

Configuration (URLs, auth type, field mapping, mode) is saved in store/providers.json.
Secrets (API keys, client secrets) are saved separately in backend/secrets.local.json, which is git-ignored,
written with owner-only permissions, and never returned by the API.
"""
import json
import os
import re
import time

from . import store
from .reference import DATA, dnb_lookup, lexis_lookup, avs_account, avs_address, name_sim

SECRETS = os.environ.get("TLM_SECRETS_FILE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "secrets.local.json")))

with open(os.path.join(DATA, "irs", "tin-match.json")) as f:
    TIN = json.load(f)["records"]

# internal fields each provider must return, so agents do not depend on a vendor's response shape
CATALOG = {
    "dnb": {"name": "Dun & Bradstreet", "purpose": "Identity resolution, firmographics, family tree", "agent": "Enrichment",
            "fields": ["duns", "primaryName", "parent", "globalUltimate", "naics", "startDate", "employees", "failureScoreClass", "confidenceCode", "ownershipChangeDate", "priorOwner"],
            "default": {"baseUrl": "https://plus.dnb.com", "authType": "oauth_client_credentials", "tokenUrl": "https://plus.dnb.com/v3/token",
                        "method": "GET", "path": "/v1/match/cleanseMatch?name={name}&streetAddressLine1={street}&countryISOAlpha2Code=US",
                        "mapping": {"duns": "matchCandidates.0.organization.duns", "primaryName": "matchCandidates.0.organization.primaryName",
                                    "confidenceCode": "matchCandidates.0.matchQualityInformation.confidenceCode"}}},
    "lexisnexis": {"name": "LexisNexis", "purpose": "Business registration and exclusion screening (OFAC, OIG LEIE, SAM.gov)", "agent": "Validation",
                   "fields": ["ofac", "oig", "sam", "registrationStatus"],
                   "default": {"baseUrl": "", "authType": "api_key_header", "headerName": "x-api-key", "method": "POST", "path": "/screening", "mapping": {}}},
    "dea": {"name": "DEA registration", "purpose": "Controlled substance registration status and schedules", "agent": "Validation",
            "fields": ["number", "status", "expires", "schedules"],
            "default": {"baseUrl": "", "authType": "api_key_header", "headerName": "x-api-key", "method": "GET", "path": "/registrations/{dea}", "mapping": {}}},
    "state_board": {"name": "State Board of Pharmacy", "purpose": "Pharmacy license status", "agent": "Validation",
                    "fields": ["number", "status", "expires"],
                    "default": {"baseUrl": "", "authType": "none", "method": "GET", "path": "/licenses/{license}", "mapping": {}}},
    "avs_account": {"name": "Account validation (AVS)", "purpose": "Bank account status and owner name match", "agent": "Validation",
                    "fields": ["code", "accountStatus", "nameMatch"],
                    "default": {"baseUrl": "", "authType": "bearer", "method": "POST", "path": "/v2/account/verify", "mapping": {}}},
    "address": {"name": "Address validation", "purpose": "Deliverability (USPS CASS) and standardized address", "agent": "Validation",
                "fields": ["standardized", "deliverable", "dpv", "poBox"],
                "default": {"baseUrl": "", "authType": "api_key_query", "queryName": "key", "method": "GET", "path": "/v1/address?street={street}&city={city}", "mapping": {}}},
    "irs_tin": {"name": "IRS TIN matching", "purpose": "EIN and legal name match", "agent": "Validation",
                "fields": ["result"],
                "default": {"baseUrl": "", "authType": "certificate", "method": "POST", "path": "/tin-match", "mapping": {}}},
}

DEFAULT_DISCLAIMER = "Results from providers marked Test data are based on mock data, not on calls to the provider."


# ------------------------------------------------------------------ configuration and secrets
def configs():
    saved = store.read("providers", {})
    out = {}
    for key, cat in CATALOG.items():
        c = dict(cat["default"], mode="test", timeoutMs=8000, retries=1, lastTest=None)
        c.update(saved.get(key, {}))
        out[key] = c
    return out


def save_config(key, values):
    saved = store.read("providers", {})
    cur = saved.get(key, {})
    allowed = {"mode", "baseUrl", "authType", "tokenUrl", "headerName", "queryName", "method", "path", "mapping", "timeoutMs", "retries", "scope", "notes", "lastTest"}
    cur.update({k: v for k, v in values.items() if k in allowed})
    saved[key] = cur
    store.write("providers", saved)


def _secrets():
    if not os.path.exists(SECRETS):
        return {}
    with open(SECRETS) as f:
        return json.load(f)


def save_secrets(key, values):
    s = _secrets()
    cur = s.get(key, {})
    for k, v in values.items():
        if v is None:
            continue
        if v == "":
            cur.pop(k, None)
        else:
            cur[k] = v
    s[key] = cur
    tmp = SECRETS + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(s, f)
    os.replace(tmp, SECRETS)


def masked_secrets(key):
    out = {}
    for k, v in _secrets().get(key, {}).items():
        out[k] = ("••••" + str(v)[-4:]) if len(str(v)) > 6 else "••••"
    return out


def settings():
    return store.read("provider_settings", {"disclaimer": DEFAULT_DISCLAIMER})


def save_settings(values):
    s = settings()
    s.update({k: v for k, v in values.items() if k in ("disclaimer",)})
    store.write("provider_settings", s)
    return s


# ------------------------------------------------------------------ live HTTP calls
def _get_path(obj, path):
    for part in path.split("."):
        if isinstance(obj, list):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def _auth(cfg, sec, client):
    headers, params = {}, {}
    t = cfg.get("authType")
    if t == "api_key_header":
        headers[cfg.get("headerName") or "x-api-key"] = sec.get("apiKey", "")
    elif t == "api_key_query":
        params[cfg.get("queryName") or "key"] = sec.get("apiKey", "")
    elif t == "bearer":
        headers["Authorization"] = "Bearer " + sec.get("token", "")
    elif t == "oauth_client_credentials":
        r = client.post(cfg["tokenUrl"], data={"grant_type": "client_credentials", **({"scope": cfg["scope"]} if cfg.get("scope") else {})},
                        auth=(sec.get("clientId", ""), sec.get("clientSecret", "")))
        r.raise_for_status()
        tok = r.json().get("access_token") or r.json().get("accessToken")
        headers["Authorization"] = "Bearer " + (tok or "")
    elif t == "certificate":
        raise RuntimeError("Certificate (mutual TLS) authentication is not supported yet in this workbench.")
    return headers, params


def _client(cfg):
    import httpx
    return httpx.Client(timeout=(cfg.get("timeoutMs") or 8000) / 1000)


def live_call(key, cfg, query):
    if not cfg.get("baseUrl"):
        raise RuntimeError("No base URL configured")
    sec = _secrets().get(key, {})
    path = cfg.get("path") or ""
    for k, v in query.items():
        from urllib.parse import quote
        path = path.replace("{" + k + "}", quote(str(v or ""), safe=""))
    url = cfg["baseUrl"].rstrip("/") + path
    last = None
    for _ in range(max(1, int(cfg.get("retries") or 0) + 1)):
        try:
            with _client(cfg) as client:
                headers, params = _auth(cfg, sec, client)
                if (cfg.get("method") or "GET").upper() == "POST":
                    r = client.post(url, json=query, headers=headers, params=params)
                else:
                    r = client.get(url, headers=headers, params=params)
                r.raise_for_status()
                body = r.json()
            mapping = cfg.get("mapping") or {}
            if not mapping:
                raise RuntimeError("No field mapping configured: map the response to " + ", ".join(CATALOG[key]["fields"]))
            return {f: _get_path(body, p) for f, p in mapping.items()}
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def test_connection(key):
    cfg = configs()[key]
    t0 = time.perf_counter()
    try:
        if not cfg.get("baseUrl"):
            raise RuntimeError("No base URL configured")
        sec = _secrets().get(key, {})
        with _client(cfg) as client:
            headers, params = _auth(cfg, sec, client)
            r = client.get(cfg["baseUrl"], headers=headers, params=params)
        ok, msg = r.status_code < 500, f"HTTP {r.status_code}"
    except Exception as e:  # noqa: BLE001
        ok, msg = False, str(e)[:300]
    res = {"ok": ok, "message": msg, "ms": round((time.perf_counter() - t0) * 1000), "at": time.strftime("%Y-%m-%d %H:%M")}
    save_config(key, {"lastTest": res})
    return res


# ------------------------------------------------------------------ test-data answers
def test_answer(key, q):
    name = q.get("name", "")
    if key == "dnb":
        return dnb_lookup(name)
    if key in ("lexisnexis", "dea", "state_board"):
        lx = lexis_lookup(name)
        if not lx:
            return None
        c = lx["checks"]
        if key == "lexisnexis":
            return {"ofac": c.get("ofac", {}).get("result"), "oig": c.get("oig_leie", {}).get("result"), "sam": c.get("sam_gov", {}).get("result"),
                    "registrationStatus": c.get("businessRegistration", {}).get("status", "Active")}
        if key == "dea":
            d = c.get("dea") or {}
            return {"number": d.get("number"), "status": d.get("status"), "expires": d.get("expires"), "schedules": d.get("schedules")} if d else None
        s = c.get("stateLicense") or {}
        return {"number": s.get("number"), "status": s.get("status"), "expires": s.get("expires")} if s else None
    if key == "avs_account":
        a = avs_account(name)
        return {"code": a["result"]["code"], "accountStatus": a["result"]["accountStatus"], "nameMatch": a["result"]["nameMatch"],
                "routing": a["routing"], "last4": a["accountLast4"]} if a else None
    if key == "address":
        a = avs_address(q.get("address", ""))
        return {"standardized": a["standardized"], "deliverable": a["deliverable"], "dpv": a["dpvConfirmation"], "poBox": a["poBox"]} if a else None
    if key == "irs_tin":
        digits = re.sub(r"\D", "", q.get("tin") or "")
        if not digits:
            return {"result": "no tin"}
        recs = [r for r in TIN if re.sub(r"\D", "", r["ein"]) == digits]
        if not recs:
            return {"result": "not found"}
        best = max(name_sim(name, r["name"]) for r in recs)
        return {"result": "match" if best >= 0.85 else "name mismatch", "nameOnFile": recs[0]["name"]}
    return None


def lookup(key, query):
    """Returns (answer or None, meta) where meta = {provider, source, mode, ms, error}."""
    cfg = configs()[key]
    t0 = time.perf_counter()
    err = None
    if cfg["mode"] == "live":
        try:
            ans = live_call(key, cfg, query)
        except Exception as e:  # noqa: BLE001
            ans, err = None, str(e)[:200]
        source = f"{CATALOG[key]['name']} API"
    else:
        ans = test_answer(key, query)
        source = f"{CATALOG[key]['name']} · test data"
    return ans, {"provider": key, "source": source, "mode": cfg["mode"], "ms": round((time.perf_counter() - t0) * 1000, 1), "error": err}
