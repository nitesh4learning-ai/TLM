---
id: BR-PM-001
title: Payment method
folder: business-rules
stage: Business rules
agent: Credit
autonomy: B
owner: Treasury / AP
status: Published
version: 1.0
---
# BR-PM-001 Payment method

**Autonomy:** B – Agent decides, human approves above limit · **Agent:** Credit · **Owner:** Treasury / AP

## In plain English

Electronic payment (ACH) is the default. Check and wire are used only for the reasons below. Bank details must pass account validation before any electronic method is set.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| Account validation GREEN | ACH | Agent |
| Account validation AMBER (partial name match) | Hold; steward confirms account holder | Data steward |
| Account validation RED, or no bank details | Check | Agent |
| Customer asks for check without a reason | Check, flagged for review | Credit manager |
| Single payment above $250,000, or foreign bank | Wire | Treasury |

## Exceptions

A change of bank details on an existing customer always needs a call-back to a known contact.

## Related policies

AG-001
