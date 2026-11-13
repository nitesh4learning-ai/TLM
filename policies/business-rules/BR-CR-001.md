---
id: BR-CR-001
title: Credit limit approvals
folder: business-rules
stage: Business rules
agent: Credit
autonomy: B
owner: Credit risk
status: Published
version: 1.0
---
# BR-CR-001 Credit limit approvals

**Autonomy:** B – Agent decides, human approves above limit · **Agent:** Credit · **Owner:** Credit risk

## In plain English

The Credit agent proposes a limit from the D&B score, trading history and parent exposure. The limit is approved at the level below. Children of a parent share the parent's limit.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| Up to $50,000 | Approve | Agent |
| Above $50,000 up to $250,000 | Approve | Credit manager |
| Above $250,000 | Approve | Credit manager and BU finance director |
| No D&B score, or score class 5 | Prepay terms; limit set by Credit | Credit manager |

## Exceptions

A limit reset after an ownership change always goes to Credit (MM-007a).

## Related policies

MM-007a
