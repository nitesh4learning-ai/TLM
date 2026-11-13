---
id: BR-TX-001
title: Tax status and resale certificates
folder: business-rules
stage: Business rules
agent: Tax
autonomy: A
owner: Tax
status: Published
version: 1.0
---
# BR-TX-001 Tax status and resale certificates

**Autonomy:** A – Agent decides · **Agent:** Tax · **Owner:** Tax

## In plain English

A customer buying for resale is tax-exempt only with a valid resale certificate for the ship-to state. Without one, the customer is taxable and a person is asked to collect the certificate.

## Conditions and actions

| Condition | Action | Decided by |
| --- | --- | --- |
| Resale certificate present, state matches ship-to, not expired | Exempt for resale | Agent |
| Certificate missing or expired | Taxable; request certificate | Tax specialist |
| Certificate state differs from ship-to state | Taxable until corrected | Tax specialist |

## Exceptions

Government and non-profit exemptions need a person to review the document.

## Related policies

None
