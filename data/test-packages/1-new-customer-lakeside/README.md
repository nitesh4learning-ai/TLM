# New customer: Lakeside Community Pharmacy

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- Search before create finds no customer at 0.80 or above (Lakeside Pharmacy #2 is related: same owner, different tax ID and address).
- A new Business ready record is created.
- Legal, Procurement and Tax decide on their own: license and DEA active, standard terms, Texas resale certificate in the customer's name.
- Credit stops for a person: about $80,000 a month needs a limit above the agent's $50,000 authority (BR-CR-001); Net 45 is declined for credit tier B and Net 30 applies (BR-PT-001).

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/W-9_Lakeside_Community_Pharmacy.pdf`
- `attachments/TX_Pharmacy_License_TX-PH-481220.pdf`
- `attachments/DEA_Registration_FL4827311.pdf`
- `attachments/TX_Resale_Certificate_Lakeside.pdf`
- `attachments/Bank_Letter_Lakeside.pdf`
