# Brand-new business, no certificate, failed bank check: Sunbelt Compounding

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- No existing customer; a new record is created.
- Validation stops for a person: account validation is RED (account closed, name does not match).
- Credit stops for a person: the business started in 2026, so BR-PT-001 sets prepay or Net 15 for a credit manager; payment method falls back to check (BR-PM-001).
- Tax stops for a person: no resale certificate was sent, so the customer is taxable until one arrives (BR-TX-001).

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/W-9_Sunbelt_Compounding.pdf`
- `attachments/TX_Pharmacy_License_TX-PH-655019.pdf`
- `attachments/DEA_Registration_FS2209463.pdf`
