---
id: BR-PT-001
title: Customer payment terms
folder: business-rules
stage: Business rules
agent: Credit
autonomy: B
owner: Finance / Credit
status: Published
version: 1.0
---
# BR-PT-001 Customer payment terms

**Autonomy:** B – Agent decides, human approves above limit · **Agent:** Credit · **Owner:** Finance / Credit

## In plain English

A new customer gets Net 30. Longer terms are allowed only when credit tier, customer type and contract support them. Terms outside the table go to a person.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| Any approved customer | Net 30 | Agent |
| Credit tier A, limit up to $50,000, 12+ months trading | Net 45 | Agent |
| Credit tier A or B, signed contract, limit up to $250,000 | Net 60 | Credit manager |
| Contract names the terms (government, hospital system, GPO) | Terms in the contract | Credit manager |
| Business under 12 months old, or no D&B score | Prepay or Net 15 | Credit manager |
| Past-due balance on the parent | No new terms | Credit manager |
| Request above Net 60 | Held | BU finance director |

## Exceptions

Early-pay discounts follow the contract. Terms are never carried to a successor record (MM-007a).

## Related policies

MM-007a
