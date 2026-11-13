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
