"""Sample onboarding requests for the three walkthrough scenarios.

`emails` are the raw requests the Intake agent reads. `fallback` holds the key values used only when no
ANTHROPIC_API_KEY is configured, so the rest of the pipeline can still be exercised.
"""

def F(value, confidence=0.98, source="Email body"):
    return {"value": value, "confidence": confidence, "source": source}


SCENARIOS = {
    "new-customer": {
        "title": "New customer", "party": "Lakeside Community Pharmacy",
        "email": {"subject": "New account request - Lakeside Community Pharmacy", "from": "Dana Whitfield <purchasing@lakesiderx.com>",
                  "date": "Thu, 12 Nov 2026 09:10:00 -0600",
                  "body": """Hi team,

Following up on my email from yesterday - attached is our Texas resale certificate as requested.

To recap: we'd like to open an account for Lakeside Community Pharmacy, LLC (we trade as Lakeside Pharmacy).
Address: 1420 S Broadway Ave, Ste 200, Tyler, TX 75701
EIN: 15-3939212
DEA: FL4827311 (schedules II-V), Texas pharmacy license TX-PH-481220.
We are an independent retail pharmacy and will order brand and generic Rx, including controlled substances.
Expected volume is about $60,000-$80,000 a month. We'd prefer Net 45 terms if possible.
Bank: routing 111000025, account ending 7302.

Thanks,
Dana Whitfield, Owner
(903) 555-0148

-----Original Message-----
From: Onboarding
Sent: Wednesday, November 11, 2026 4:40 PM
Thanks, Dana. Please send your resale certificate as well.

-----Original Message-----
From: Dana Whitfield
Sent: Wednesday, November 11, 2026 4:02 PM
We'd like to open an account for Lakeside Community Pharmacy in Tyler. W-9, license and DEA certificate attached."""},
        "attachments": {
            "W-9.txt": "Form W-9. Name: Lakeside Community Pharmacy, LLC. Business name/disregarded entity: Lakeside Pharmacy. Federal tax classification: LLC (partnership). Address: 1420 S Broadway Ave, Ste 200, Tyler, TX 75701. Employer identification number: 15-3939212.",
            "TX_Pharmacy_License.txt": "Texas State Board of Pharmacy. Class A (Community) Pharmacy License TX-PH-481220. Licensee: Lakeside Community Pharmacy, LLC. Expires: 06/30/2027.",
            "DEA_Certificate.txt": "DEA Registration Certificate. Registration number FL4827311. Business activity: Retail Pharmacy. Schedules: 2, 2N, 3, 3N, 4, 5. Expiration: 06/30/2027. Name: Lakeside Community Pharmacy, LLC.",
            "TX_Resale_Certificate.txt": "Texas Sales and Use Tax Resale Certificate (Form 01-339). Purchaser: Lakeside Community Pharmacy, LLC. Texas taxpayer number 01-728-4410. Issued 2026-10-02.",
        },
        "fallback": {"legal_name": F("Lakeside Community Pharmacy, LLC", 0.99, "W-9.txt"), "dba": F("Lakeside Pharmacy", 0.82),
                     "address": F("1420 S Broadway Ave, Ste 200, Tyler, TX 75701", 0.98), "tax_id": F("15-3939212", 0.97, "W-9.txt"),
                     "dea": F("FL4827311", 0.99, "DEA_Certificate.txt"), "state_license": F("TX-PH-481220", 0.98, "TX_Pharmacy_License.txt"),
                     "request_type": F("New customer", 0.97), "sales_area": F("Pharma · US01", 0.95), "customer_type": F("Independent retail pharmacy", 0.96),
                     "contact_name": F("Dana Whitfield", 0.98), "contact_phone": F("(903) 555-0148", 0.96), "requested_terms": F("Net 45", 0.92),
                     "expected_monthly_volume": F("80000", 0.88), "controlled_substances": F("yes", 0.97),
                     "resale_certificate": F("TX 01-728-4410", 0.94, "TX_Resale_Certificate.txt"),
                     "resale_certificate_name": F("Lakeside Community Pharmacy, LLC", 0.95, "TX_Resale_Certificate.txt"),
                     "bank_routing": F("111000025", 0.99), "bank_account_last4": F("7302", 0.99), "w9_provided": F("yes", 0.99, "W-9.txt")},
    },
    "existing-customer": {
        "title": "Customer already exists", "party": "Cedar Park Family Pharmacy",
        "email": {"subject": "Add Specialty account - Cedar Park Family Pharmacy", "from": "Accounts Payable <ap@cedarparkfamilyrx.com>",
                  "date": "Thu, 12 Nov 2026 14:07:00 -0600",
                  "body": """Hello,

Legal name is Cedar Park Family Pharmacy LLC. W-9 and license attached.

-----Original Message-----
From: Onboarding
Can you confirm the legal name and attach your current pharmacy license and W-9?

-----Original Message-----
From: Accounts Payable
Please add a specialty account for Cedar Park Family Pharmacy, 1200 E Whitestone Blvd, Cedar Park TX 78613.
We will order specialty oncology drugs through our GPO, Keystone Purchasing Alliance. EIN 62-1415846."""},
        "attachments": {"W-9.txt": "Form W-9. Name: Cedar Park Family Pharmacy LLC. Address: 1200 E Whitestone Blvd, Cedar Park, TX 78613. EIN: 62-1415846.",
                        "TX_Pharmacy_License.txt": "Texas State Board of Pharmacy. Class A Pharmacy License TX-PH-337905. Expires 03/31/2027."},
        "fallback": {"legal_name": F("Cedar Park Family Pharmacy LLC", 0.99), "address": F("1200 E Whitestone Blvd, Cedar Park, TX 78613", 0.98),
                     "tax_id": F("62-1415846", 0.98, "W-9.txt"), "request_type": F("Add sales area", 0.96), "sales_area": F("Specialty · US02", 0.97),
                     "customer_type": F("Independent retail pharmacy", 0.95), "gpo": F("Keystone Purchasing Alliance", 0.93), "controlled_substances": F("yes", 0.9), "w9_provided": F("yes", 0.99, "W-9.txt")},
    },
    "new-owner": {
        "title": "Existing site, new owner", "party": "Westbrook Infusion Partners",
        "email": {"subject": "New customer setup - Westbrook Infusion Partners LP", "from": "Priya Raman <finance@westbrookinfusion.com>",
                  "date": "Thu, 12 Nov 2026 15:30:00 -0600",
                  "body": """Hi,

Westbrook Infusion Partners LP acquired the Westbrook Infusion Center in Plano in September and we need a new customer account.
Address: 4500 W Park Blvd Ste 120, Plano, TX 75093. EIN 44-3670896.
Please keep the same ship-to and delivery instructions (Dock 2, 7am-3pm).
We expect about $120,000 a month. Bank routing 111000614, account ending 9051.
Our resale certificate is attached.

Priya Raman, Finance"""},
        "attachments": {"W-9.txt": "Form W-9. Name: Westbrook Infusion Partners LP. Federal tax classification: Partnership. Address: 4500 W Park Blvd, Ste 120, Plano, TX 75093. EIN: 44-3670896.",
                        "TX_Resale_Certificate.txt": "Texas Sales and Use Tax Resale Certificate. Purchaser: Westbrook Infusion Center LLC. Texas taxpayer number 01-552-9071. Issued 2024-04-15."},
        "fallback": {"legal_name": F("Westbrook Infusion Partners LP", 0.99), "address": F("4500 W Park Blvd Ste 120, Plano, TX 75093", 0.99),
                     "tax_id": F("44-3670896", 0.98), "request_type": F("New customer", 0.99), "sales_area": F("Specialty · US02", 0.9),
                     "customer_type": F("Infusion center", 0.95), "expected_monthly_volume": F("120000", 0.93), "controlled_substances": F("yes", 0.85),
                     "resale_certificate": F("TX 01-552-9071", 0.94, "TX_Resale_Certificate.txt"),
                     "resale_certificate_name": F("Westbrook Infusion Center LLC", 0.96, "TX_Resale_Certificate.txt"),
                     "bank_routing": F("111000614", 0.99), "bank_account_last4": F("9051", 0.99), "w9_provided": F("yes", 0.99, "W-9.txt")},
    },
}


def mail_for(key):
    s = SCENARIOS[key]
    m = dict(s["email"])
    m["attachments"] = [{"name": n, "bytes": len(t), "text": t} for n, t in s["attachments"].items()]
    return m
