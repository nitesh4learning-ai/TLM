# Existing site, new owner: Westbrook Infusion Partners

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- Search before create finds Westbrook Infusion Center LLC at the same address with a different tax ID (about 0.87).
- D&B reports an ownership change on Sep 2, 2026, so Match & merge creates a new customer linked as successor of BRR-0003388 (MM-007a). It does not merge.
- Validation stops for a person: account validation is AMBER because the bank account still shows the prior owner's name (BR-PM-001).
- Credit stops for a person: the limit resets after an ownership change and about $120,000 is above agent authority (BR-CR-001, MM-007a).
- Tax stops for a person: the resale certificate is in the prior owner's name (BR-TX-001).
- Approve the three stages in Request journey; the new record becomes Active.

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/W-9_Westbrook_Infusion_Partners.pdf`
- `attachments/Ownership_Change_Letter_Westbrook.pdf`
- `attachments/TX_Pharmacy_License_TX-PH-552018.pdf`
- `attachments/Bank_Letter_Westbrook.pdf`
- `attachments/TX_Resale_Certificate_Westbrook.pdf`
