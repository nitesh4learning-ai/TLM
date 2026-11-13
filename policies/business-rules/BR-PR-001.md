---
id: BR-PR-001
title: Pricing group
folder: business-rules
stage: Business rules
agent: Procurement
autonomy: A
owner: Pricing and contracts
status: Published
version: 1.0
---
# BR-PR-001 Pricing group

**Autonomy:** A – Agent decides · **Agent:** Procurement · **Owner:** Pricing and contracts

## In plain English

The pricing group follows the customer type and contract. A customer with no contract gets the standard group for its type. A named contract or GPO membership sets the group the contract names.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| Independent retail pharmacy, no contract | Independent retail | Agent |
| Hospital or health system with an IDN contract | Group named in the contract | Agent |
| GPO member with membership verified | GPO tier from the membership | Agent |
| Contract found but group not named | Hold for pricing team | Pricing analyst |

## Exceptions

Special price lists always go to the pricing team.

## Related policies

None
