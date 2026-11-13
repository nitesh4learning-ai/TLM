---
id: RG-CS-001
title: Pharmacy licensure and controlled substances
folder: regulatory
stage: Validation
agent: Legal
autonomy: B
owner: Regulatory compliance
status: Published
version: 1.0
---
# RG-CS-001 Pharmacy licensure and controlled substances

**Autonomy:** B – Agent decides, human approves above limit · **Agent:** Legal · **Owner:** Regulatory compliance

## In plain English

Before a pharmacy or other dispenser can order, we verify a valid state license and, for controlled substances, an active DEA registration for the schedules it will order. Trading partners must be licensed or registered for their role under the Drug Supply Chain Security Act.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| State license active and DEA active for requested schedules | Controlled ordering on | Agent |
| State license active, no DEA | Controlled ordering off; non-controlled only | Agent |
| DEA or state license lapsing within 60 days | Active with a renewal reminder | Agent |
| License expired, suspended or not found | Hold; no ordering | Regulatory compliance |
| Ship-to is a PO box and controlled items are requested | Reject the ship-to | Data steward |

## Exceptions

Exclusion-list hits (OIG, SAM, OFAC) block the customer until a person clears them.

## Related policies

AG-002

Source: https://www.fda.gov/drugs/drug-supply-chain-security-act/are-you-ready-drug-supply-chain-security-act
