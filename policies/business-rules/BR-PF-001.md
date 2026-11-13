---
id: BR-PF-001
title: Partner functions
folder: business-rules
stage: Business rules
agent: Procurement
autonomy: A
owner: Customer master governance
status: Published
version: 1.0
---
# BR-PF-001 Partner functions

**Autonomy:** A – Agent decides · **Agent:** Procurement · **Owner:** Customer master governance

## In plain English

A new customer gets sold-to, bill-to and payer set to the same account, with one ship-to. Separate bill-to or payer accounts need a named parent and approval from the parent.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| Single site, no parent | Sold-to = bill-to = payer; one ship-to | Agent |
| Site in a corporate family, parent confirms billing | Bill-to and payer at the parent | Agent |
| Parent does not confirm billing | Hold for steward | Data steward |

## Exceptions

Additional ship-tos are added by request, not inferred.

## Related policies

None
