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


def complete(system, prompt, max_tokens=2000):
    msg = _client().messages.create(model=MODEL, max_tokens=max_tokens, system=system,
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
    ("edited_terms", "Legal.EditedTerms"),
]

INTAKE_SYSTEM = """You are the Intake agent in a customer master data management platform for a pharmaceutical distributor.
You read an onboarding request (an email thread and its attachments, or a form) and extract key values.
Return ONLY a JSON object: {"fields": {"<field>": {"value": <string or null>, "confidence": <0..1>, "source": "<message or attachment it came from>"}}, "summary": "<one sentence>"}.
Use exactly these field names: """ + ", ".join(f for f, _ in FIELDS) + """.
Rules: request_type is one of "New customer", "Add sales area", "Change". sales_area is like "Pharma · US01" or "Specialty · US02".
customer_type is like "Independent retail pharmacy", "Hospital", "Infusion center". expected_monthly_volume is a number in USD (no symbols).
controlled_substances is "yes" or "no". edited_terms is "yes" only if the customer changed the standard terms of sale.
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


POLICY_SYSTEM = """You turn a policy document into a structured policy for a master data platform's policy store.
Return ONLY JSON: {"title": str, "folder": one of ["match-survivorship","business-rules","regulatory","bpo-playbooks","agent-policies"],
"agent": one of ["Intake","Match & merge","Validation","Legal","Procurement","Credit","Tax","Orchestrator"], "level": one of ["A","B","H"],
"owner": str, "stage": str, "text": "<plain-English statement, 2-4 sentences>", "rows": [["condition","action","decided by (Agent or a role)"]],
"exceptions": str}. Level A = agent decides, B = agent decides and a person approves above a limit, H = a person decides."""


def draft_policy(doc_text):
    return _json(complete(POLICY_SYSTEM, doc_text[:60000], max_tokens=2500))
