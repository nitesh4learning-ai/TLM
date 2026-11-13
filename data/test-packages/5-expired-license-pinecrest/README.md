# Expired pharmacy license: Pinecrest Apothecary

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- No existing customer; a new record is created.
- Validation stops for a person: the Texas State Board of Pharmacy shows the license expired on Sep 30, 2026 (LexisNexis test data).
- Legal stops for a person: RG-CS-001 holds the customer with no ordering until the license is renewed (Regulatory compliance).
- Credit, Procurement and Tax decide on their own (limit $30,000, Net 30, ACH, exempt for resale).

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/W-9_Pinecrest_Apothecary.pdf`
- `attachments/TX_Pharmacy_License_TX-PH-298140.pdf`
- `attachments/DEA_Registration_FP5528193.pdf`
- `attachments/TX_Resale_Certificate_Pinecrest.pdf`
