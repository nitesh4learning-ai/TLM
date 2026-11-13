# Near-duplicate needs a steward: Palo Duro Drugs

## How to test

1. Start the app and add ANTHROPIC_API_KEY to backend/.env.
2. Go to Intake and either:
   - upload `email.eml` alone (the PDFs are inside it), or
   - upload `email.txt` together with every file in `attachments/`.
3. Press Submit to agents. The Request journey opens.

## What should happen

- Search finds PALO DURO DRUG CO (SAP 0001205514) at the same address with a different tax ID; the score falls in the review band (0.80 to 0.95).
- D&B reports no ownership change, so MM-007a does not apply. Match & merge stops for a data steward to decide (MM-002).
- In Business ready record you can open the record, compare sources in the cross-reference table, and merge or unmerge.

## Files

- `email.eml`: the whole email thread with the PDFs attached
- `email.txt`: the same thread as plain text
- `attachments/W-9_Palo_Duro_Drugs.pdf`
- `attachments/TX_Pharmacy_License_TX-PH-177450.pdf`
- `attachments/DEA_Registration_FP7712384.pdf`
- `attachments/TX_Resale_Certificate_Palo_Duro.pdf`
