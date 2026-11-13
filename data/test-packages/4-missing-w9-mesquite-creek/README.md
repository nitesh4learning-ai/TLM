# Missing W-9: Mesquite Creek Pharmacy

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- Intake reads the thread and attachments, but there is no W-9.
- DQ-INT-001 (required fields) blocks the request at intake; no other agent runs. The journey shows the rule and what is missing.
- Option A: Edit request → set W-9 form to 'Yes, provided' → Resubmit. Every agent runs again and the request completes touchless (limit $45,000, Net 30, ACH, exempt for resale).
- Option B: Reject → Email the requester → the drafted email asks for the signed W-9.

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/TX_Pharmacy_License_TX-PH-512877.pdf`
- `attachments/DEA_Registration_FM3817542.pdf`
- `attachments/TX_Resale_Certificate_Mesquite_Creek.pdf`
- `attachments/Bank_Letter_Mesquite_Creek.pdf`
