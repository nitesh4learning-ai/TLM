# Customer already exists: Cedar Park Family Pharmacy

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- Search before create finds the existing customer BRR-0004417 at about 0.99; the other hits are its SAP, Oracle EBS and AS/400 cross-references.
- No new customer is created. The request is linked to BRR-0004417 and the Specialty sales area is added.
- Every stage is decided by an agent: the request is touchless.
- Open BRR-0004417 in Business ready records to see the 5 cross-references, the winning values and the new sales area.

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/W-9_Cedar_Park_Family_Pharmacy.pdf`
- `attachments/TX_Pharmacy_License_TX-PH-337905.pdf`
- `attachments/GPO_Membership_Keystone.pdf`
