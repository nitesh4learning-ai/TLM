# New clinic in an existing health system: Brazos Cancer Center – Frisco

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- Search finds Brazos entities but none at this address, so a new customer is created. D&B places it under Brazos Health System – North Texas.
- Procurement: hospital pricing from the IDN contract (BR-PR-001); bill-to and payer at the parent, which confirmed it pays (BR-PF-001).
- Credit stops for two people: about $300,000 a month is above the $250,000 manager limit, so the credit manager and the BU finance director approve (BR-CR-001).
- Open the new record and press Hierarchy to see the Brazos family.

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/W-9_Brazos_Cancer_Center_Frisco.pdf`
- `attachments/TX_Pharmacy_License_TX-PH-604412.pdf`
- `attachments/DEA_Registration_BB4417706.pdf`
- `attachments/TX_Resale_Certificate_Brazos_Cancer_Center.pdf`
