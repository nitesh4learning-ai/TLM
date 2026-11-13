# Autonomy matrix

| Policy | Title | Folder | Agent | Autonomy |
| --- | --- | --- | --- | --- |
| MM-002 | Duplicate threshold | match-survivorship | Match & merge | B – Agent decides, human approves above limit |
| MM-007a | Ownership change at a known site | match-survivorship | Match & merge | B – Agent decides, human approves above limit |
| SV-001 | Source trust order | match-survivorship | Match & merge | A – Agent decides |
| BR-PT-001 | Customer payment terms | business-rules | Credit | B – Agent decides, human approves above limit |
| BR-PM-001 | Payment method | business-rules | Credit | B – Agent decides, human approves above limit |
| BR-CR-001 | Credit limit approvals | business-rules | Credit | B – Agent decides, human approves above limit |
| BR-TX-001 | Tax status and resale certificates | business-rules | Tax | B – Agent decides, human approves above limit |
| BR-LG-001 | Agreements and compliance acknowledgements | business-rules | Legal | B – Agent decides, human approves above limit |
| BR-PR-001 | Pricing group | business-rules | Procurement | A – Agent decides |
| BR-PF-001 | Partner functions | business-rules | Procurement | A – Agent decides |
| RG-CS-001 | Pharmacy licensure and controlled substances | regulatory | Legal | B – Agent decides, human approves above limit |
| BPO-001 | Supplier onboarding information | bpo-playbooks | Procurement | B – Agent decides, human approves above limit |
| AG-001 | Autonomy matrix | agent-policies | Orchestrator | H – Human decides |
| AG-002 | Confidence thresholds | agent-policies | Orchestrator | B – Agent decides, human approves above limit |
| AG-003 | Citations and audit | agent-policies | Orchestrator | A – Agent decides |
