"""Claude calls used by the agents: intake extraction, decision explanations and policy drafting."""
import json
import os
import re

MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5-5")


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _client():
    import anthropic
    return anthropic.Anthropic()


def _json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def complete(system, prompt, max_tokens=2000, model=None):
    msg = _client().messages.create(model=model or MODEL, max_tokens=max_tokens, system=system,
                                    messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


FIELDS = [
    ("legal_name", "Customer.LegalName"), ("dba", "Customer.DBA"), ("address", "Address"), ("tax_id", "TaxNumber1 (EIN)"),
    ("dea", "Regulatory.DEA"), ("state_license", "Regulatory.StateLicense"), ("request_type", "Request.Type"),
    ("sales_area", "SalesArea"), ("customer_type", "Customer.Type"), ("contact_name", "Contact.Primary"),
    ("contact_email", "Contact.Email"), ("contact_phone", "Contact.Phone"), ("requested_terms", "Requested.PaymentTerms"),
    ("expected_monthly_volume", "Requested.Volume"), ("controlled_substances", "Requested.ControlledSchedules"),
    ("resale_certificate", "Tax.ResaleCertificate"), ("resale_certificate_name", "Tax.ResaleCertificateHolder"),
    ("bank_routing", "Bank.Routing"), ("bank_account_last4", "Bank.Account"), ("gpo", "Customer.GPO"),
    ("edited_terms", "Legal.EditedTerms"), ("w9_provided", "Tax.W9Received"),
]

INTAKE_SYSTEM = """You are the Intake agent in a customer master data management platform for a pharmaceutical distributor.
You read an onboarding request (an email thread and its attachments, or a form) and extract key values.
Return ONLY a JSON object: {"fields": {"<field>": {"value": <string or null>, "confidence": <0..1>, "source": "<message or attachment it came from>"}}, "summary": "<one sentence>"}.
Use exactly these field names: """ + ", ".join(f for f, _ in FIELDS) + """.
Rules: request_type is one of "New customer", "Add sales area", "Change". sales_area is like "Pharma · US01" or "Specialty · US02".
customer_type is like "Independent retail pharmacy", "Hospital", "Infusion center". expected_monthly_volume is a number in USD (no symbols).
controlled_substances is "yes" or "no". w9_provided is "yes" only if a signed IRS Form W-9 is attached or its contents are given. edited_terms is "yes" only if the customer changed the standard terms of sale.
Use null for anything not stated. Confidence reflects how clearly the value is stated. Never invent values."""


def extract_intake(text):
    out = _json(complete(INTAKE_SYSTEM, "Request:\n\n" + text[:60000], max_tokens=3000))
    return out.get("fields", {}), out.get("summary", "")


EXPLAIN_SYSTEM = """You write short, plain-English explanations of decisions taken by agents in a master data platform.
For each stage you get the decision and the policy IDs applied. Write one or two sentences per stage, cite policy IDs in brackets, no hedging, no marketing.
Return ONLY JSON: {"<stage key>": "<explanation>"}."""


def explain(stages):
    payload = [{"key": s["key"], "name": s["name"], "status": s["status"], "summary": s["summary"], "policies": s["policies"],
                "checks": [r for sec in s["sections"] if sec["kind"] == "checks" for r in sec["rows"]]} for s in stages]
    return _json(complete(EXPLAIN_SYSTEM, json.dumps(payload), max_tokens=2500))


POLICY_SYSTEM = """You fill in a master data policy form from a policy document, for the governance team to review.
Fill a field ONLY when the document states it. Never invent values. For every field you fill, give the passage it came from.
Return ONLY JSON:
{"fields": {
  "title": str, "folder": one of ["match-survivorship","business-rules","regulatory","bpo-playbooks","agent-policies"],
  "owner": str, "steward": str, "effective": "YYYY-MM-DD", "effectiveTo": "YYYY-MM-DD",
  "appliesTo": [agent names from: Intake, Search before create, Match & merge, Enrichment, Validation, Legal, Procurement, Credit, Tax, Orchestrator, or "All agents"],
  "roles": [people's roles], "recordTypes": ["Customer"|"Supplier"], "regions": [str], "triggers": ["Create"|"Change"|"Periodic"],
  "level": "A"|"B"|"H", "approverRole": str, "escalation": str, "slaHours": number,
  "text": "plain-English statement, 2-4 sentences", "exceptions": str, "source": "regulation or document cited",
  "params": [{"key": "snake_case", "value": number or str, "help": str}],
  "rows": [["condition", "action", "decided by: Agent or a role"]],
  "rules": [{"when": [{"attr": one of ATTRS, "op": one of ["=","!=","<","<=",">",">=","contains","in","exists","not exists"], "value": any}],
             "then": {"<output attribute>": value}, "decidedBy": "Agent" or a role, "note": str}]
 },
 "sources": {"<field>": {"quote": "<short passage from the document>", "confidence": 0..1}}}
Leave out any field the document does not state. Level A = agent decides, B = agent decides and a person approves above a limit, H = a person decides."""


def draft_policy(doc_text, attrs):
    out = _json(complete(POLICY_SYSTEM.replace("ATTRS", ", ".join(attrs)), doc_text[:60000], max_tokens=4000))
    return out.get("fields", {}), out.get("sources", {})


ADDRESS_SYSTEM = """You standardize US postal addresses to USPS Publication 28 style for a master data platform.
You do not know whether an address is deliverable; only standardize and flag problems you can see in the text.
Return ONLY JSON: {"standardized": "<STREET LINE, CITY ST ZIP or ZIP+4 in capitals>", "poBox": true|false,
"issues": ["<short problem, e.g. missing suite number, ZIP does not match city, abbreviation corrected>"], "confidence": <0..1>}."""


def standardize_address(address):
    return _json(complete(ADDRESS_SYSTEM, address, max_tokens=400))


ASSISTANT_SYSTEM = """You are the assistant inside Touchless MDM, a master data platform where AI agents process customer and supplier requests under governance policies.
Answer the user's question using ONLY the context below (the screen they are on, the request's decision trace, records, policies and thresholds).
Rules: answer first, in two or three sentences at most. Cite policy IDs in square brackets, e.g. [MM-002]. Quote numbers (scores, thresholds, limits) exactly as they appear.
If the context does not contain the answer, say "The trace doesn't show that." and suggest where to look. You are read-only: you explain and point to screens; you never approve, edit, reject or publish anything, and never claim to."""


def assistant(question, context, model=None):
    return complete(ASSISTANT_SYSTEM, f"CONTEXT:\n{context[:50000]}\n\nQUESTION: {question}", max_tokens=400, model=model).strip()


EMAIL_SYSTEM = """You draft a short, polite email from a pharmaceutical distributor's customer onboarding team to a requester, asking them to resend their onboarding request with specific missing information.
Plain text. Under 140 words. Name exactly what is missing and why it is needed. No marketing. Sign as "Customer Onboarding". Return ONLY JSON: {"subject": str, "body": str}."""


def draft_reject_email(to, legal, missing, reason):
    return _json(complete(EMAIL_SYSTEM, json.dumps({"to": to, "company": legal, "missing": missing, "reason": reason}), max_tokens=500))
