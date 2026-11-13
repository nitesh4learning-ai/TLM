# TLM

Agentic master data management for customers: requests flow through core MDM agents
(Intake, Search before create, Match & merge, Enrichment, Validation) and then through
function agents (Legal, Procurement, Credit, Tax). Every decision cites the policy that drove it.

## Layout

| Folder | Contents |
| --- | --- |
| `artifact/` | Source of the Agentic MDM screens (design canvas files) |
| `data/` | Reference data: source systems (SAP, legacy), D&B, LexisNexis, account validation, hierarchy, scenarios |
| `policies/` | Policy library, grouped by folder, with an autonomy level on each policy |
| `docs/` | Backlog and design decisions |

## Terminology

Use **Business ready record**. Do not use "golden record".

## Run locally

Needs Python 3.11+ and Node 18+.

```bash
# backend (http://127.0.0.1:8000, docs at /docs)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then put your ANTHROPIC_API_KEY in .env
uvicorn app.main:app --reload --port 8000

# frontend (http://localhost:5173), in a second terminal
cd frontend
npm install
npm run dev
```

Without a key, the three walkthrough requests still run (Intake uses the sample's key values); email upload and policy upload need the key.
Sample emails to upload: `data/samples/*.eml`. Tests: `cd backend && pytest`.
