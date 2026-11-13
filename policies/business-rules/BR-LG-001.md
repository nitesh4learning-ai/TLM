---
id: BR-LG-001
title: Agreements and compliance acknowledgements
folder: business-rules
stage: Business rules
agent: Legal
autonomy: B
owner: Legal
status: Published
version: 1.0
---
# BR-LG-001 Agreements and compliance acknowledgements

**Autonomy:** B – Agent decides, human approves above limit · **Agent:** Legal · **Owner:** Legal

## In plain English

A customer is active only after the standard terms of sale and the compliance acknowledgement are accepted. Standard terms are accepted by the agent. Any change to the terms goes to Legal.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| Standard terms accepted, no edits | Proceed | Agent |
| Customer edited or added terms | Hold for review | Legal counsel |
| Customer in a jurisdiction outside the standard terms | Hold for review | Legal counsel |

## Exceptions

Controlled-substance customers also need RG-CS-001.

## Related policies

RG-CS-001
