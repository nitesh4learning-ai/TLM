#!/usr/bin/env python3
"""Builds three upload test packages: an email thread (.eml and .txt) plus the PDFs a requester would attach.

Documents follow the layout and fields of the real forms (IRS Form W-9, Texas pharmacy license, DEA registration
certificate, Texas resale certificate Form 01-339, bank letter, ownership-change letter). Companies, numbers and
people are fictional. Each document carries a small "specimen" footer so it can never pass as a real credential.

Run: python3 data/test-packages/build_packages.py
"""
import os
import shutil
import zipfile
from email.message import EmailMessage
from email.utils import make_msgid

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT = os.path.dirname(os.path.abspath(__file__))
W, H = letter
GREY = HexColor("#555555")
LIGHT = HexColor("#EEEEEE")
SPECIMEN = "Specimen for TLM testing. Fictional company and numbers. Not a valid document."


def footer(c):
    c.setFont("Helvetica", 7)
    c.setFillColor(GREY)
    c.drawCentredString(W / 2, 22, SPECIMEN)
    c.setFillColor(black)


def box(c, x, y, w, h, label, value="", size=10, label_size=6.5):
    c.setLineWidth(0.6)
    c.rect(x, y, w, h)
    c.setFont("Helvetica", label_size)
    c.drawString(x + 3, y + h - 8, label)
    c.setFont("Helvetica", size)
    c.drawString(x + 4, y + 5, value)


def check(c, x, y, label, on=False):
    c.rect(x, y, 7, 7)
    if on:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 1, y + 1, "X")
    c.setFont("Helvetica", 7)
    c.drawString(x + 10, y + 1, label)


# ------------------------------------------------------------------ IRS Form W-9 (Rev. March 2024 layout)
def w9(path, d):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Form W-9 " + d["name"])
    top = H - 40
    c.setLineWidth(1.2)
    c.line(36, top - 46, W - 36, top - 46)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, top - 30, "W-9")
    c.setFont("Helvetica", 7)
    c.drawString(40, top - 8, "Form")
    c.drawString(40, top - 42, "(Rev. March 2024)")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, top - 14, "Request for Taxpayer")
    c.drawCentredString(W / 2, top - 28, "Identification Number and Certification")
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, top - 40, "Go to www.irs.gov/FormW9 for instructions and the latest information.")
    c.setFont("Helvetica-Bold", 8)
    c.drawRightString(W - 40, top - 14, "Give form to the")
    c.drawRightString(W - 40, top - 24, "requester. Do not")
    c.drawRightString(W - 40, top - 34, "send to the IRS.")
    y = top - 52
    c.setFont("Helvetica-Bold", 7)
    c.drawString(40, y - 8, "Before you begin. For guidance related to the purpose of Form W-9, see Purpose of Form, below.")
    y -= 40
    box(c, 36, y, W - 72, 26, "1  Name of entity/individual. An entry is required.", d["name"])
    y -= 28
    box(c, 36, y, W - 72, 26, "2  Business name/disregarded entity name, if different from above.", d.get("dba", ""))
    y -= 62
    c.rect(36, y, W - 200, 60)
    c.setFont("Helvetica", 6.5)
    c.drawString(39, y + 52, "3a  Check the appropriate box for federal tax classification of the entity/individual whose name is entered on line 1.")
    cl = d["classification"]
    check(c, 42, y + 38, "Individual/sole proprietor", cl == "individual")
    check(c, 150, y + 38, "C corporation", cl == "c")
    check(c, 230, y + 38, "S corporation", cl == "s")
    check(c, 310, y + 38, "Partnership", cl == "partnership")
    check(c, 380, y + 38, "Trust/estate", cl == "trust")
    check(c, 42, y + 24, "LLC. Enter the tax classification (C = C corporation, S = S corporation, P = Partnership) . . .  " + d.get("llc_code", ""), cl == "llc")
    check(c, 42, y + 10, "Other (see instructions)", False)
    c.setFont("Helvetica", 6.5)
    c.drawString(39, y + 1, "3b  If on line 3a you checked Partnership or Trust/estate, or checked LLC and entered P, check this box if you have any foreign partners . . .")
    c.rect(W - 164, y, 128, 60)
    c.drawString(W - 160, y + 52, "4  Exemptions (codes apply only to")
    c.drawString(W - 160, y + 44, "certain entities, not individuals):")
    c.drawString(W - 160, y + 30, "Exempt payee code (if any)  ____")
    c.drawString(W - 160, y + 16, "Exemption from FATCA reporting")
    c.drawString(W - 160, y + 8, "code (if any)  ____")
    y -= 28
    box(c, 36, y, W - 250, 26, "5  Address (number, street, and apt. or suite no.). See instructions.", d["street"])
    box(c, W - 214, y - 28, 178, 54, "Requester's name and address (optional)", "")
    c.setFont("Helvetica", 8)
    c.drawString(W - 210, y + 2, "Customer Onboarding")
    c.drawString(W - 210, y - 9, "onboarding@tlm.example")
    y -= 28
    box(c, 36, y, W - 250, 26, "6  City, state, and ZIP code", d["city_state_zip"])
    y -= 28
    box(c, 36, y, W - 72, 26, "7  List account number(s) here (optional)", "")
    # Part I
    y -= 22
    c.setFillColor(black)
    c.rect(36, y, 40, 14, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, y + 4, "Part I")
    c.setFillColor(black)
    c.drawString(84, y + 4, "Taxpayer Identification Number (TIN)")
    y -= 70
    c.setFont("Helvetica", 7)
    for i, line in enumerate(["Enter your TIN in the appropriate box. The TIN provided must match the name given on line 1 to avoid",
                              "backup withholding. For individuals, this is generally your social security number (SSN). For other",
                              "entities, it is your employer identification number (EIN). If you do not have a number, see How to get",
                              "a TIN, later.", "Note: If the account is in more than one name, see the instructions for line 1."]):
        c.drawString(40, y + 58 - i * 10, line)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(W - 200, y + 60, "Social security number")
    c.rect(W - 200, y + 38, 160, 18)
    c.drawString(W - 200, y + 26, "or")
    c.drawString(W - 200, y + 14, "Employer identification number")
    c.rect(W - 200, y - 8, 160, 18)
    c.setFont("Courier-Bold", 13)
    ein = d["ein"]
    c.drawString(W - 192, y - 3, f"{ein[:2]}  -  {ein[3:]}")
    # Part II
    y -= 30
    c.setFillColor(black)
    c.rect(36, y, 44, 14, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(41, y + 4, "Part II")
    c.setFillColor(black)
    c.drawString(88, y + 4, "Certification")
    c.setFont("Helvetica", 7)
    lines = ["Under penalties of perjury, I certify that:",
             "1. The number shown on this form is my correct taxpayer identification number (or I am waiting for a number to be issued to me); and",
             "2. I am not subject to backup withholding because (a) I am exempt from backup withholding, or (b) I have not been notified by the Internal",
             "    Revenue Service (IRS) that I am subject to backup withholding as a result of a failure to report all interest or dividends, or (c) the IRS",
             "    has notified me that I am no longer subject to backup withholding; and",
             "3. I am a U.S. citizen or other U.S. person (defined below); and",
             "4. The FATCA code(s) entered on this form (if any) indicating that I am exempt from FATCA reporting is correct."]
    for i, line in enumerate(lines):
        c.drawString(40, y - 12 - i * 10, line)
    y -= 110
    c.setLineWidth(1)
    c.line(36, y + 26, W - 36, y + 26)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y + 8, "Sign")
    c.drawString(40, y - 2, "Here")
    c.setFont("Helvetica", 7)
    c.drawString(80, y + 14, "Signature of")
    c.drawString(80, y + 6, "U.S. person")
    c.setFont("Helvetica-Oblique", 14)
    c.drawString(140, y + 6, d["signer"])
    c.setFont("Helvetica", 7)
    c.drawString(W - 200, y + 10, "Date")
    c.setFont("Helvetica", 10)
    c.drawString(W - 170, y + 8, d["date"])
    c.setFont("Helvetica", 7)
    c.drawString(40, y - 30, "Cat. No. 10231X")
    c.drawRightString(W - 40, y - 30, "Form W-9 (Rev. 3-2024)")
    footer(c)
    c.save()


# ------------------------------------------------------------------ Texas pharmacy license
def tx_license(path, d):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Texas pharmacy license " + d["number"])
    c.setLineWidth(3)
    c.rect(40, 300, W - 80, H - 360)
    c.setLineWidth(0.8)
    c.rect(48, 308, W - 96, H - 376)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W / 2, H - 110, "TEXAS STATE BOARD OF PHARMACY")
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, H - 128, "333 Guadalupe Street, Suite 3-500, Austin, Texas 78701")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(W / 2, H - 175, "PHARMACY LICENSE")
    c.setFont("Helvetica", 11)
    c.drawCentredString(W / 2, H - 196, d["class"])
    rows = [("License Number", d["number"]), ("Pharmacy Name", d["name"]), ("Doing Business As", d.get("dba") or "—"),
            ("Address", d["street"]), ("", d["city_state_zip"]), ("Pharmacist-in-Charge", d["pic"]),
            ("Original Issue Date", d["issued"]), ("Expiration Date", d["expires"]), ("Status", "ACTIVE")]
    y = H - 250
    for k, v in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(110, y, k)
        c.setFont("Helvetica", 11)
        c.drawString(270, y, v)
        y -= 24
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, 360, "This license must be displayed in a conspicuous place in the pharmacy.")
    c.drawCentredString(W / 2, 346, "Verify license status at www.pharmacy.texas.gov.")
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(110, 320, "Executive Director")
    footer(c)
    c.save()


# ------------------------------------------------------------------ DEA registration certificate (Form DEA-223 layout)
def dea(path, d):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("DEA registration " + d["number"])
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W / 2, H - 60, "CONTROLLED SUBSTANCE REGISTRATION CERTIFICATE")
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, H - 76, "UNITED STATES DEPARTMENT OF JUSTICE · DRUG ENFORCEMENT ADMINISTRATION")
    c.drawCentredString(W / 2, H - 90, "WASHINGTON, D.C. 20537")
    y = H - 130
    cols = [("DEA REGISTRATION NUMBER", d["number"], 60, 170), ("THIS REGISTRATION EXPIRES", d["expires"], 240, 150), ("FEE PAID", "$888", 400, 150)]
    for label, val, x, w in cols:
        c.setFillColor(LIGHT); c.rect(x, y - 30, w, 46, fill=1, stroke=1); c.setFillColor(black)
        c.setFont("Helvetica-Bold", 7); c.drawString(x + 5, y + 6, label)
        c.setFont("Helvetica-Bold", 13); c.drawString(x + 5, y - 20, val)
    y -= 70
    for label, val, x, w in [("SCHEDULES", d["schedules"], 60, 250), ("BUSINESS ACTIVITY", "RETAIL PHARMACY", 320, 230)]:
        c.rect(x, y - 30, w, 46)
        c.setFont("Helvetica-Bold", 7); c.drawString(x + 5, y + 6, label)
        c.setFont("Helvetica-Bold", 12); c.drawString(x + 5, y - 20, val)
    c.rect(60, y - 70, 250, 30)
    c.setFont("Helvetica-Bold", 7); c.drawString(65, y - 48, "ISSUE DATE")
    c.setFont("Helvetica-Bold", 12); c.drawString(65, y - 64, d["issued"])
    y -= 120
    c.rect(60, y - 70, 490, 90)
    c.setFont("Helvetica-Bold", 7); c.drawString(65, y + 10, "REGISTRANT NAME AND ADDRESS")
    c.setFont("Helvetica-Bold", 12)
    for i, line in enumerate([d["name"].upper(), (d.get("dba") or "").upper(), d["street"].upper(), d["city_state_zip"].upper()]):
        c.drawString(70, y - 8 - i * 16, line)
    y -= 110
    c.setFont("Helvetica", 8)
    for i, line in enumerate(["Sections 304 and 1008 (21 USC 824 and 958) of the Controlled Substances Act of 1970, as amended, provide that the",
                              "Attorney General may revoke or suspend a registration to manufacture, distribute, dispense, import or export a",
                              "controlled substance.", "THIS CERTIFICATE IS NOT TRANSFERABLE ON CHANGE OF OWNERSHIP, CONTROL, LOCATION, OR BUSINESS ACTIVITY,",
                              "AND IT IS NOT VALID AFTER THE EXPIRATION DATE."]):
        c.drawString(60, y - i * 11, line)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(60, y - 70, "FORM DEA-223 (9/2016)")
    footer(c)
    c.save()


# ------------------------------------------------------------------ Texas Sales and Use Tax Resale Certificate (Form 01-339 front)
def resale(path, d):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle("Texas resale certificate " + d["purchaser"])
    c.setFont("Helvetica", 8)
    c.drawString(40, H - 40, "01-339")
    c.drawString(40, H - 50, "(Back) (Rev.10-21/9)")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W / 2, H - 50, "Texas Sales and Use Tax Resale Certificate")
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, H - 66, "Texas Comptroller of Public Accounts")
    y = H - 120
    box(c, 40, y, W - 80, 28, "Name of purchaser, firm or agency as shown on permit", d["purchaser"], 11, 7)
    y -= 30
    box(c, 40, y, 300, 28, "Address (Street & number, P.O. Box or Route number)", d["street"], 11, 7)
    box(c, 342, y, W - 382, 28, "Phone (Area code and number)", d["phone"], 11, 7)
    y -= 30
    box(c, 40, y, W - 80, 28, "City, State, ZIP code", d["city_state_zip"], 11, 7)
    y -= 30
    box(c, 40, y, W - 80, 28, "Texas Sales and Use Tax Permit Number (must contain 11 digits)", d["permit"], 12, 7)
    y -= 30
    box(c, 40, y, W - 80, 28, "Out-of-state retailer's registration number or Federal Taxpayers Registry (RFC) number for retailers in Mexico", "", 11, 7)
    y -= 34
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "I, the purchaser named above, claim the right to make a non-taxable purchase (for resale of the taxable items described")
    c.drawString(40, y - 12, "below or on the attached order or invoice) from:")
    y -= 44
    box(c, 40, y, W - 80, 28, "Seller", "McKesson Corporation and its affiliates", 11, 7)
    y -= 30
    box(c, 40, y, W - 80, 28, "Street address", "6555 State Hwy 161", 11, 7)
    y -= 30
    box(c, 40, y, W - 80, 28, "City, State, ZIP code", "Irving, TX 75039", 11, 7)
    y -= 36
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "Description of items to be purchased on the attached order or invoice:")
    y -= 30
    box(c, 40, y, W - 80, 26, "", d["items"], 11, 7)
    y -= 36
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "Description of the type of business activity generally engaged in or type of items normally sold by the purchaser:")
    y -= 30
    box(c, 40, y, W - 80, 26, "", d["activity"], 11, 7)
    y -= 40
    c.setFont("Helvetica", 7.5)
    for i, line in enumerate(["The taxable items described above, or on the attached order or invoice, will be resold, rented or leased by me within the geographical",
                              "limits of the United States of America, its territories and possessions or within the geographical limits of the United Mexican States,",
                              "in their present form or attached to other taxable items to be sold.",
                              "I understand that it is a criminal offense to give a resale certificate to the seller for taxable items that I know, at the time of purchase,",
                              "are purchased for use rather than for the purpose of resale, lease or rental, and depending on the amount of tax evaded, the offense",
                              "may range from a Class C misdemeanor to a felony of the second degree."]):
        c.drawString(40, y - i * 10, line)
    y -= 90
    box(c, 40, y, 220, 30, "Purchaser", d["signer"], 13, 7)
    box(c, 262, y, 170, 30, "Title", d["title"], 11, 7)
    box(c, 434, y, W - 474, 30, "Date", d["date"], 11, 7)
    footer(c)
    c.save()


# ------------------------------------------------------------------ letters
def letter_doc(path, title, head, lines, sign):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle(title)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, H - 70, head[0])
    c.setFont("Helvetica", 9)
    for i, l in enumerate(head[1:]):
        c.drawString(60, H - 86 - i * 12, l)
    c.line(60, H - 86 - len(head) * 12, W - 60, H - 86 - len(head) * 12)
    y = H - 130 - len(head) * 12
    c.setFont("Helvetica", 11)
    for l in lines:
        if l.startswith("|"):
            k, v = l[1:].split("|")
            c.setFont("Helvetica-Bold", 10); c.drawString(80, y, k); c.setFont("Helvetica", 11); c.drawString(250, y, v)
        else:
            c.drawString(60, y, l)
        y -= 18
    y -= 20
    c.setFont("Helvetica-Oblique", 13)
    c.drawString(60, y, sign[0])
    c.setFont("Helvetica", 10)
    for i, l in enumerate(sign[1:]):
        c.drawString(60, y - 16 - i * 13, l)
    footer(c)
    c.save()


# ------------------------------------------------------------------ packages
PACKAGES = [
 {
  "dir": "1-new-customer-lakeside",
  "title": "New customer: Lakeside Community Pharmacy",
  "expect": [
    "Search before create finds no customer at 0.80 or above (Lakeside Pharmacy #2 is related: same owner, different tax ID and address).",
    "A new Business ready record is created.",
    "Legal, Procurement and Tax decide on their own: license and DEA active, standard terms, Texas resale certificate in the customer's name.",
    "Credit stops for a person: about $80,000 a month needs a limit above the agent's $50,000 authority (BR-CR-001); Net 45 is declined for credit tier B and Net 30 applies (BR-PT-001).",
  ],
  "subject": "New account request - Lakeside Community Pharmacy",
  "from": ("Dana Whitfield", "purchasing@lakesiderx.com"),
  "thread": [
    ("Dana Whitfield <purchasing@lakesiderx.com>", "Wed, 11 Nov 2026 16:02:00 -0600",
     "Hello,\n\nWe'd like to open a wholesale account for Lakeside Community Pharmacy in Tyler. We're an independent retail pharmacy.\nOur W-9, Texas pharmacy license and DEA registration are attached.\n\nThank you,\nDana Whitfield\nOwner, Lakeside Community Pharmacy\n(903) 555-0148"),
    ("Customer Onboarding <onboarding@tlm.example>", "Wed, 11 Nov 2026 16:40:00 -0600",
     "Thanks, Dana. To finish setting up the account, please send your Texas resale certificate and a bank letter or voided check for ACH payments.\nAlso let us know your expected monthly volume and the payment terms you'd like.\n\nCustomer Onboarding"),
    ("Dana Whitfield <purchasing@lakesiderx.com>", "Thu, 12 Nov 2026 09:10:00 -0600",
     "Hi,\n\nAttached are our resale certificate and a letter from our bank.\nWe expect $60,000 to $80,000 a month in brand and generic Rx, including Schedule II-V controlled substances.\nWe'd prefer Net 45 terms if possible. We trade as Lakeside Pharmacy.\n\nThanks,\nDana"),
  ],
  "docs": [
    ("W-9_Lakeside_Community_Pharmacy.pdf", w9, dict(name="Lakeside Community Pharmacy, LLC", dba="Lakeside Pharmacy", classification="llc", llc_code="P",
                                                    street="1420 S Broadway Ave, Ste 200", city_state_zip="Tyler, TX 75701", ein="15-3939212", signer="Dana Whitfield", date="11/10/2026")),
    ("TX_Pharmacy_License_TX-PH-481220.pdf", tx_license, dict(number="TX-PH-481220", name="Lakeside Community Pharmacy, LLC", dba="Lakeside Pharmacy",
                                                             class_="", street="1420 S Broadway Ave, Ste 200", city_state_zip="Tyler, TX 75701-3318",
                                                             pic="Dana Whitfield, PharmD", issued="05/28/2019", expires="06/30/2027")),
    ("DEA_Registration_FL4827311.pdf", dea, dict(number="FL4827311", expires="06/30/2027", issued="06/12/2024", schedules="2, 2N, 3, 3N, 4, 5",
                                                 name="Lakeside Community Pharmacy, LLC", dba="Lakeside Pharmacy", street="1420 S Broadway Ave, Ste 200", city_state_zip="Tyler, TX 75701")),
    ("TX_Resale_Certificate_Lakeside.pdf", resale, dict(purchaser="Lakeside Community Pharmacy, LLC", street="1420 S Broadway Ave, Ste 200", phone="(903) 555-0148",
                                                       city_state_zip="Tyler, TX 75701", permit="3 2071 8441 0", items="Prescription and over-the-counter drugs and health products",
                                                       activity="Retail pharmacy", signer="Dana Whitfield", title="Owner", date="10/02/2026")),
    ("Bank_Letter_Lakeside.pdf", letter_doc, dict(title="Bank letter", head=["East Texas Community Bank", "2100 W Front St, Tyler, TX 75702 · (903) 555-0100"],
                                                 lines=["November 11, 2026", "", "To whom it may concern:", "",
                                                        "This letter confirms the following business checking account is open and in good standing.", "",
                                                        "|Account holder|Lakeside Community Pharmacy, LLC", "|Routing number (ABA)|111000025", "|Account number|ending 7302",
                                                        "|Account type|Business checking", "|Opened|June 3, 2019"],
                                                 sign=["Laura Mendez", "Branch Manager", "East Texas Community Bank"])),
  ],
 },
 {
  "dir": "2-existing-customer-cedar-park",
  "title": "Customer already exists: Cedar Park Family Pharmacy",
  "expect": [
    "Search before create finds the existing customer BRR-0004417 at about 0.99; the other hits are its SAP, Oracle EBS and AS/400 cross-references.",
    "No new customer is created. The request is linked to BRR-0004417 and the Specialty sales area is added.",
    "Every stage is decided by an agent: the request is touchless.",
    "Open BRR-0004417 in Business ready records to see the 5 cross-references, the winning values and the new sales area.",
  ],
  "subject": "Add Specialty account - Cedar Park Family Pharmacy",
  "from": ("Accounts Payable", "ap@cedarparkfamilyrx.com"),
  "thread": [
    ("Accounts Payable <ap@cedarparkfamilyrx.com>", "Tue, 10 Nov 2026 11:22:00 -0600",
     "Hello,\n\nPlease add a specialty account for Cedar Park Family Pharmacy, 1200 E Whitestone Blvd, Cedar Park TX 78613.\nWe're starting to dispense specialty oncology drugs and will buy them through our GPO, Keystone Purchasing Alliance.\n\nThanks,\nMegan Cho, Accounts Payable"),
    ("Customer Onboarding <onboarding@tlm.example>", "Tue, 10 Nov 2026 15:05:00 -0600",
     "Hi Megan, happy to help. Can you confirm your legal name and send your current pharmacy license and W-9? We'll also need your GPO membership confirmation."),
    ("Accounts Payable <ap@cedarparkfamilyrx.com>", "Thu, 12 Nov 2026 14:07:00 -0600",
     "Legal name is Cedar Park Family Pharmacy LLC. W-9, license and our Keystone membership letter are attached.\n\nMegan"),
  ],
  "docs": [
    ("W-9_Cedar_Park_Family_Pharmacy.pdf", w9, dict(name="Cedar Park Family Pharmacy LLC", dba="", classification="llc", llc_code="S",
                                                   street="1200 E Whitestone Blvd, Ste 4", city_state_zip="Cedar Park, TX 78613", ein="62-1415846", signer="Megan Cho", date="11/11/2026")),
    ("TX_Pharmacy_License_TX-PH-337905.pdf", tx_license, dict(number="TX-PH-337905", name="Cedar Park Family Pharmacy LLC", dba="",
                                                             street="1200 E Whitestone Blvd, Ste 4", city_state_zip="Cedar Park, TX 78613-3047",
                                                             pic="Raymond Ortiz, RPh", issued="08/15/2011", expires="03/31/2027")),
    ("GPO_Membership_Keystone.pdf", letter_doc, dict(title="GPO membership", head=["Keystone Purchasing Alliance", "Member Services · 400 Commerce St, Dallas, TX 75202"],
                                                    lines=["November 9, 2026", "", "Re: Membership confirmation", "",
                                                           "This confirms the member below participates in our specialty pharmacy program.", "",
                                                           "|Member|Cedar Park Family Pharmacy LLC", "|Member ID|KPA-SP-20418", "|Program|Specialty oncology",
                                                           "|Effective|December 1, 2026", "|Status|Active"],
                                                    sign=["Alan Brooks", "Director, Member Services"])),
  ],
 },
 {
  "dir": "3-existing-site-new-owner-westbrook",
  "title": "Existing site, new owner: Westbrook Infusion Partners",
  "expect": [
    "Search before create finds Westbrook Infusion Center LLC at the same address with a different tax ID (about 0.87).",
    "D&B reports an ownership change on Sep 2, 2026, so Match & merge creates a new customer linked as successor of BRR-0003388 (MM-007a). It does not merge.",
    "Validation stops for a person: account validation is AMBER because the bank account still shows the prior owner's name (BR-PM-001).",
    "Credit stops for a person: the limit resets after an ownership change and about $120,000 is above agent authority (BR-CR-001, MM-007a).",
    "Tax stops for a person: the resale certificate is in the prior owner's name (BR-TX-001).",
    "Approve the three stages in Request journey; the new record becomes Active.",
  ],
  "subject": "New customer setup - Westbrook Infusion Partners LP",
  "from": ("Priya Raman", "finance@westbrookinfusion.com"),
  "thread": [
    ("Priya Raman <finance@westbrookinfusion.com>", "Mon, 09 Nov 2026 10:15:00 -0600",
     "Hello,\n\nWestbrook Infusion Partners LP completed the purchase of the Westbrook Infusion Center in Plano on September 2.\nWe need a customer account in the new entity's name. Same location: 4500 W Park Blvd, Suite 120, Plano, TX 75093.\n\nPriya Raman, Finance"),
    ("Customer Onboarding <onboarding@tlm.example>", "Mon, 09 Nov 2026 13:30:00 -0600",
     "Thanks, Priya. Please send a W-9 for the new entity, the closing letter, your pharmacy license, a bank letter and your resale certificate.\nAlso confirm the ship-to and delivery instructions and your expected monthly volume."),
    ("Priya Raman <finance@westbrookinfusion.com>", "Thu, 12 Nov 2026 15:30:00 -0600",
     "Hi,\n\nAll documents are attached. Please keep the same ship-to and delivery instructions (Dock 2, 7am-3pm).\nWe expect about $120,000 a month, including Schedule II-V. The resale certificate is the one we have on file today; the new one is in progress.\n\nPriya"),
  ],
  "docs": [
    ("W-9_Westbrook_Infusion_Partners.pdf", w9, dict(name="Westbrook Infusion Partners LP", dba="", classification="partnership",
                                                    street="4500 W Park Blvd, Ste 120", city_state_zip="Plano, TX 75093", ein="44-3670896", signer="Priya Raman", date="11/10/2026")),
    ("Ownership_Change_Letter_Westbrook.pdf", letter_doc, dict(title="Ownership change", head=["Northstar Infusion Holdings", "1700 Pacific Ave, Suite 2400, Dallas, TX 75201"],
                                                              lines=["September 3, 2026", "", "Re: Completion of acquisition", "",
                                                                     "We confirm that the acquisition of the assets of Westbrook Infusion Center LLC",
                                                                     "by Westbrook Infusion Partners LP closed on September 2, 2026.", "",
                                                                     "|Seller|Westbrook Infusion Center LLC", "|Buyer|Westbrook Infusion Partners LP", "|Parent of buyer|Northstar Infusion Holdings",
                                                                     "|Site|4500 W Park Blvd, Ste 120, Plano, TX 75093", "|Closing date|September 2, 2026"],
                                                              sign=["Martin Kaye", "General Counsel, Northstar Infusion Holdings"])),
    ("TX_Pharmacy_License_TX-PH-552018.pdf", tx_license, dict(number="TX-PH-552018", name="Westbrook Infusion Partners LP", dba="Westbrook Infusion Center",
                                                             street="4500 W Park Blvd, Ste 120", city_state_zip="Plano, TX 75093-2210",
                                                             pic="Elena Ruiz, PharmD", issued="09/02/2026", expires="08/31/2027")),
    ("Bank_Letter_Westbrook.pdf", letter_doc, dict(title="Bank letter", head=["Collin County Business Bank", "5800 Legacy Dr, Plano, TX 75024"],
                                                  lines=["November 10, 2026", "", "To whom it may concern:", "",
                                                         "The account below is open. A change of account holder name is in process.", "",
                                                         "|Account holder (current)|Westbrook Infusion Center LLC", "|Routing number (ABA)|111000614", "|Account number|ending 9051",
                                                         "|Account type|Business checking"],
                                                  sign=["Kevin Tran", "Relationship Manager"])),
    ("TX_Resale_Certificate_Westbrook.pdf", resale, dict(purchaser="Westbrook Infusion Center LLC", street="4500 W Park Blvd, Ste 120", phone="(972) 555-0172",
                                                        city_state_zip="Plano, TX 75093", permit="1 7552 9071 3", items="Prescription drugs, infusion supplies",
                                                        activity="Outpatient infusion center", signer="Thomas Reed", title="Administrator", date="04/15/2024")),
  ],
 },
]

PACKAGES += [
 {
  "dir": "4-missing-w9-mesquite-creek",
  "title": "Missing W-9: Mesquite Creek Pharmacy",
  "expect": [
    "Intake reads the thread and attachments, but there is no W-9.",
    "DQ-INT-001 (required fields) blocks the request at intake; no other agent runs. The journey shows the rule and what is missing.",
    "Option A: Edit request → set W-9 form to 'Yes, provided' → Resubmit. Every agent runs again and the request completes touchless (limit $45,000, Net 30, ACH, exempt for resale).",
    "Option B: Reject → Email the requester → the drafted email asks for the signed W-9.",
  ],
  "subject": "Wholesale account - Mesquite Creek Pharmacy",
  "from": ("Luis Ortega", "luis@mesquitecreekrx.com"),
  "thread": [
    ("Luis Ortega <luis@mesquitecreekrx.com>", "Mon, 09 Nov 2026 09:40:00 -0600",
     "Hello,\n\nI own Mesquite Creek Pharmacy, LLC, an independent retail pharmacy at 2215 S 14th St, Abilene, TX 79605. EIN 73-4418205.\nWe'd like to open a wholesale account. Our pharmacy license, DEA registration, resale certificate and bank letter are attached.\n\nLuis Ortega, PharmD\n(325) 555-0191"),
    ("Customer Onboarding <onboarding@tlm.example>", "Mon, 09 Nov 2026 14:05:00 -0600",
     "Thanks, Luis. We also need a signed IRS Form W-9 before we can set up the account. What monthly volume do you expect?"),
    ("Luis Ortega <luis@mesquitecreekrx.com>", "Thu, 12 Nov 2026 16:10:00 -0600",
     "About $45,000 a month, including Schedule II-V. Our accountant is preparing the W-9 and will send it separately.\n\nLuis"),
  ],
  "docs": [
    ("TX_Pharmacy_License_TX-PH-512877.pdf", tx_license, dict(number="TX-PH-512877", name="Mesquite Creek Pharmacy, LLC", dba="", street="2215 S 14th St",
                                                             city_state_zip="Abilene, TX 79605", pic="Luis Ortega, PharmD", issued="03/02/2015", expires="06/30/2027")),
    ("DEA_Registration_FM3817542.pdf", dea, dict(number="FM3817542", expires="06/30/2027", issued="07/01/2024", schedules="2, 2N, 3, 3N, 4, 5",
                                                 name="Mesquite Creek Pharmacy, LLC", dba="", street="2215 S 14th St", city_state_zip="Abilene, TX 79605")),
    ("TX_Resale_Certificate_Mesquite_Creek.pdf", resale, dict(purchaser="Mesquite Creek Pharmacy, LLC", street="2215 S 14th St", phone="(325) 555-0191",
                                                             city_state_zip="Abilene, TX 79605", permit="3 2104 7719 5", items="Prescription and over-the-counter drugs",
                                                             activity="Retail pharmacy", signer="Luis Ortega", title="Owner", date="10/20/2026")),
    ("Bank_Letter_Mesquite_Creek.pdf", letter_doc, dict(title="Bank letter", head=["West Texas National Bank", "1300 Pine St, Abilene, TX 79601"],
                                                       lines=["November 6, 2026", "", "To whom it may concern:", "", "The business checking account below is open and in good standing.", "",
                                                              "|Account holder|Mesquite Creek Pharmacy, LLC", "|Routing number (ABA)|111000025", "|Account number|ending 4419"],
                                                       sign=["Dana Price", "Branch Manager"])),
  ],
 },
 {
  "dir": "5-expired-license-pinecrest",
  "title": "Expired pharmacy license: Pinecrest Apothecary",
  "expect": [
    "No existing customer; a new record is created.",
    "Validation stops for a person: the Texas State Board of Pharmacy shows the license expired on Sep 30, 2026 (LexisNexis test data).",
    "Legal stops for a person: RG-CS-001 holds the customer with no ordering until the license is renewed (Regulatory compliance).",
    "Credit, Procurement and Tax decide on their own (limit $30,000, Net 30, ACH, exempt for resale).",
  ],
  "subject": "New customer application - Pinecrest Apothecary",
  "from": ("Grace Holloway", "grace@pinecrestapothecary.com"),
  "thread": [
    ("Grace Holloway <grace@pinecrestapothecary.com>", "Tue, 10 Nov 2026 08:55:00 -0600",
     "Good morning,\n\nPinecrest Apothecary, Inc. would like to become a customer. We are a retail pharmacy at 708 Judson Rd, Longview, TX 75601.\nAttached: W-9, pharmacy license, DEA certificate and resale certificate. We expect around $30,000 a month.\n\nGrace Holloway, Pharmacist-in-Charge"),
    ("Customer Onboarding <onboarding@tlm.example>", "Tue, 10 Nov 2026 11:20:00 -0600", "Thank you, Grace. Do you plan to order controlled substances, and how should we pay refunds?"),
    ("Grace Holloway <grace@pinecrestapothecary.com>", "Thu, 12 Nov 2026 10:02:00 -0600",
     "Yes, Schedules II-V. ACH is fine: routing 111000614, account ending 6630. Our license renewal is in process with the board.\n\nGrace"),
  ],
  "docs": [
    ("W-9_Pinecrest_Apothecary.pdf", w9, dict(name="Pinecrest Apothecary, Inc.", dba="", classification="s", street="708 Judson Rd", city_state_zip="Longview, TX 75601",
                                             ein="27-5530916", signer="Grace Holloway", date="11/09/2026")),
    ("TX_Pharmacy_License_TX-PH-298140.pdf", tx_license, dict(number="TX-PH-298140", name="Pinecrest Apothecary, Inc.", dba="", street="708 Judson Rd",
                                                             city_state_zip="Longview, TX 75601", pic="Grace Holloway, RPh", issued="04/14/2009", expires="09/30/2026")),
    ("DEA_Registration_FP5528193.pdf", dea, dict(number="FP5528193", expires="06/30/2027", issued="06/20/2024", schedules="2, 2N, 3, 3N, 4, 5",
                                                 name="Pinecrest Apothecary, Inc.", dba="", street="708 Judson Rd", city_state_zip="Longview, TX 75601")),
    ("TX_Resale_Certificate_Pinecrest.pdf", resale, dict(purchaser="Pinecrest Apothecary, Inc.", street="708 Judson Rd", phone="(903) 555-0137", city_state_zip="Longview, TX 75601",
                                                        permit="1 7520 4418 9", items="Prescription drugs", activity="Retail pharmacy", signer="Grace Holloway", title="Pharmacist-in-Charge", date="09/02/2026")),
  ],
 },
 {
  "dir": "6-health-system-clinic-brazos-cancer-center",
  "title": "New clinic in an existing health system: Brazos Cancer Center – Frisco",
  "expect": [
    "Search finds Brazos entities but none at this address, so a new customer is created. D&B places it under Brazos Health System – North Texas.",
    "Procurement: hospital pricing from the IDN contract (BR-PR-001); bill-to and payer at the parent, which confirmed it pays (BR-PF-001).",
    "Credit stops for two people: about $300,000 a month is above the $250,000 manager limit, so the credit manager and the BU finance director approve (BR-CR-001).",
    "Open the new record and press Hierarchy to see the Brazos family.",
  ],
  "subject": "New ship-to and customer setup - Brazos Cancer Center Frisco",
  "from": ("Nina Patel", "ap.northtexas@brazoshealth.example"),
  "thread": [
    ("Nina Patel <ap.northtexas@brazoshealth.example>", "Wed, 11 Nov 2026 13:30:00 -0600",
     "Hello,\n\nBrazos Health System – North Texas is opening Brazos Cancer Center – Frisco at 5601 Warren Pkwy, Frisco, TX 75034 (EIN 81-2290457).\nIt will be a hospital outpatient oncology clinic ordering under our IDN contract. Brazos Health System – North Texas will be the bill-to and payer.\n\nNina Patel, Accounts Payable"),
    ("Customer Onboarding <onboarding@tlm.example>", "Wed, 11 Nov 2026 15:45:00 -0600", "Thanks, Nina. Please send the W-9, pharmacy license, DEA certificate and resale certificate for the new site, and the expected volume."),
    ("Nina Patel <ap.northtexas@brazoshealth.example>", "Thu, 12 Nov 2026 09:20:00 -0600",
     "Attached. Expected volume is about $300,000 a month, mostly oncology infusions, Schedules II-V.\n\nNina"),
  ],
  "docs": [
    ("W-9_Brazos_Cancer_Center_Frisco.pdf", w9, dict(name="Brazos Cancer Center – Frisco", dba="", classification="c", street="5601 Warren Pkwy", city_state_zip="Frisco, TX 75034",
                                                    ein="81-2290457", signer="Nina Patel", date="11/11/2026")),
    ("TX_Pharmacy_License_TX-PH-604412.pdf", tx_license, dict(number="TX-PH-604412", name="Brazos Cancer Center – Frisco", dba="", street="5601 Warren Pkwy",
                                                             city_state_zip="Frisco, TX 75034", pic="Omar Haddad, PharmD", issued="10/30/2026", expires="10/31/2028")),
    ("DEA_Registration_BB4417706.pdf", dea, dict(number="BB4417706", expires="06/30/2027", issued="11/02/2026", schedules="2, 2N, 3, 3N, 4, 5",
                                                 name="Brazos Cancer Center – Frisco", dba="", street="5601 Warren Pkwy", city_state_zip="Frisco, TX 75034")),
    ("TX_Resale_Certificate_Brazos_Cancer_Center.pdf", resale, dict(purchaser="Brazos Cancer Center – Frisco", street="5601 Warren Pkwy", phone="(972) 555-0150",
                                                                   city_state_zip="Frisco, TX 75034", permit="3 2290 4570 1", items="Prescription drugs and infusion supplies",
                                                                   activity="Hospital outpatient clinic", signer="Nina Patel", title="AP Manager", date="11/05/2026")),
  ],
 },
 {
  "dir": "7-near-duplicate-palo-duro",
  "title": "Near-duplicate needs a steward: Palo Duro Drugs",
  "expect": [
    "Search finds PALO DURO DRUG CO (SAP 0001205514) at the same address with a different tax ID; the score falls in the review band (0.80 to 0.95).",
    "D&B reports no ownership change, so MM-007a does not apply. Match & merge stops for a data steward to decide (MM-002).",
    "In Business ready record you can open the record, compare sources in the cross-reference table, and merge or unmerge.",
  ],
  "subject": "Account request - Palo Duro Drugs",
  "from": ("Ray Whitaker", "ray@paloduro-drugs.com"),
  "thread": [
    ("Ray Whitaker <ray@paloduro-drugs.com>", "Mon, 09 Nov 2026 12:00:00 -0600",
     "Hi,\n\nPlease open an account for Palo Duro Drugs LLC, 880 Canyon Rd, Amarillo, TX 79101. EIN 46-1187302. We're an independent retail pharmacy.\n\nRay Whitaker, Owner"),
    ("Customer Onboarding <onboarding@tlm.example>", "Mon, 09 Nov 2026 15:10:00 -0600", "Thanks, Ray. Please send your W-9, license, DEA certificate and resale certificate."),
    ("Ray Whitaker <ray@paloduro-drugs.com>", "Thu, 12 Nov 2026 11:45:00 -0600", "All attached. Around $35,000 a month. ACH: routing 111900659, account ending 2271.\n\nRay"),
  ],
  "docs": [
    ("W-9_Palo_Duro_Drugs.pdf", w9, dict(name="Palo Duro Drugs LLC", dba="", classification="llc", llc_code="S", street="880 Canyon Rd", city_state_zip="Amarillo, TX 79101",
                                        ein="46-1187302", signer="Ray Whitaker", date="11/10/2026")),
    ("TX_Pharmacy_License_TX-PH-177450.pdf", tx_license, dict(number="TX-PH-177450", name="Palo Duro Drugs LLC", dba="", street="880 Canyon Rd",
                                                             city_state_zip="Amarillo, TX 79101", pic="Ray Whitaker, RPh", issued="02/11/2004", expires="05/31/2027")),
    ("DEA_Registration_FP7712384.pdf", dea, dict(number="FP7712384", expires="05/31/2027", issued="05/15/2024", schedules="2, 2N, 3, 3N, 4, 5",
                                                 name="Palo Duro Drugs LLC", dba="", street="880 Canyon Rd", city_state_zip="Amarillo, TX 79101")),
    ("TX_Resale_Certificate_Palo_Duro.pdf", resale, dict(purchaser="Palo Duro Drugs LLC", street="880 Canyon Rd", phone="(806) 555-0174", city_state_zip="Amarillo, TX 79101",
                                                        permit="3 1187 3020 6", items="Prescription and over-the-counter drugs", activity="Retail pharmacy", signer="Ray Whitaker", title="Owner", date="08/14/2026")),
  ],
 },
 {
  "dir": "8-new-business-sunbelt-compounding",
  "title": "Brand-new business, no certificate, failed bank check: Sunbelt Compounding",
  "expect": [
    "No existing customer; a new record is created.",
    "Validation stops for a person: account validation is RED (account closed, name does not match).",
    "Credit stops for a person: the business started in 2026, so BR-PT-001 sets prepay or Net 15 for a credit manager; payment method falls back to check (BR-PM-001).",
    "Tax stops for a person: no resale certificate was sent, so the customer is taxable until one arrives (BR-TX-001).",
  ],
  "subject": "Open an account - Sunbelt Compounding Pharmacy",
  "from": ("Marco Reyes", "marco@sunbeltcompounding.com"),
  "thread": [
    ("Marco Reyes <marco@sunbeltcompounding.com>", "Tue, 10 Nov 2026 10:30:00 -0600",
     "Hello,\n\nWe just opened Sunbelt Compounding Pharmacy LLC at 1902 Saunders St, Laredo, TX 78041 (EIN 92-3305871) and would like an account.\nW-9, pharmacy license and DEA certificate attached.\n\nMarco Reyes, Owner"),
    ("Customer Onboarding <onboarding@tlm.example>", "Tue, 10 Nov 2026 13:00:00 -0600", "Welcome, Marco. Please send your resale certificate and bank details, and your expected volume."),
    ("Marco Reyes <marco@sunbeltcompounding.com>", "Thu, 12 Nov 2026 14:15:00 -0600",
     "About $20,000 a month to start. Bank: routing 114000093, account ending 0517. We'll send the resale certificate once the state issues it.\n\nMarco"),
  ],
  "docs": [
    ("W-9_Sunbelt_Compounding.pdf", w9, dict(name="Sunbelt Compounding Pharmacy LLC", dba="", classification="llc", llc_code="P", street="1902 Saunders St", city_state_zip="Laredo, TX 78041",
                                            ein="92-3305871", signer="Marco Reyes", date="11/09/2026")),
    ("TX_Pharmacy_License_TX-PH-655019.pdf", tx_license, dict(number="TX-PH-655019", name="Sunbelt Compounding Pharmacy LLC", dba="", street="1902 Saunders St",
                                                             city_state_zip="Laredo, TX 78041", pic="Marco Reyes, PharmD", issued="09/15/2026", expires="09/30/2028")),
    ("DEA_Registration_FS2209463.pdf", dea, dict(number="FS2209463", expires="06/30/2027", issued="10/01/2026", schedules="2, 2N, 3, 3N, 4, 5",
                                                 name="Sunbelt Compounding Pharmacy LLC", dba="", street="1902 Saunders St", city_state_zip="Laredo, TX 78041")),
  ],
 },
]


def build():
    for p in PACKAGES:
        d = os.path.join(OUT, p["dir"])
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(os.path.join(d, "attachments"))
        for name, fn, args in p["docs"]:
            if fn is tx_license:
                args = dict(args, **{"class": "Class A (Community) Pharmacy" if "Infusion" not in args["name"] else "Class A-S (Community, Sterile Compounding) Pharmacy"})
                args.pop("class_", None)
            target = os.path.join(d, "attachments", name)
            fn(target, **args) if fn is letter_doc else fn(target, args)
        # thread: newest message on top, earlier ones quoted below
        body = []
        for i, (frm, date, text) in enumerate(reversed(p["thread"])):
            if i == 0:
                body.append(text)
            else:
                body += ["", "-----Original Message-----", f"From: {frm}", f"Sent: {date}", f"Subject: {'RE: ' if i < len(p['thread']) - 1 else ''}{p['subject']}", "", text]
        body_text = "\n".join(body)
        last = p["thread"][-1]
        m = EmailMessage()
        m["Subject"] = "RE: " + p["subject"]
        m["From"] = last[0]
        m["To"] = "Customer Onboarding <onboarding@tlm.example>"
        m["Date"] = last[1]
        m["Message-ID"] = make_msgid(domain=last[0].split("@")[1].rstrip(">"))
        m.set_content(body_text)
        for name, _, _ in p["docs"]:
            with open(os.path.join(d, "attachments", name), "rb") as f:
                m.add_attachment(f.read(), maintype="application", subtype="pdf", filename=name)
        with open(os.path.join(d, "email.eml"), "wb") as f:
            f.write(bytes(m))
        with open(os.path.join(d, "email.txt"), "w") as f:
            f.write(f"Subject: RE: {p['subject']}\nFrom: {last[0]}\nTo: Customer Onboarding <onboarding@tlm.example>\nDate: {last[1]}\n\n{body_text}\n")
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write(f"# {p['title']}\n\n## How to test\n\n1. Start the app and add ANTHROPIC_API_KEY to backend/.env.\n"
                    "2. Go to Intake and either:\n   - upload `email.eml` alone (the PDFs are inside it), or\n"
                    "   - upload `email.txt` together with every file in `attachments/`.\n"
                    "3. Press Submit to agents. The Request journey opens.\n\n## What should happen\n\n" +
                    "\n".join(f"- {e}" for e in p["expect"]) +
                    "\n\n## Files\n\n- `email.eml`: the whole email thread with the PDFs attached\n- `email.txt`: the same thread as plain text\n" +
                    "\n".join(f"- `attachments/{n}`" for n, _, _ in p["docs"]) + "\n")
        z = os.path.join(OUT, p["dir"] + ".zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(d):
                for fn_ in files:
                    full = os.path.join(root, fn_)
                    zf.write(full, os.path.relpath(full, OUT))
        print("built", p["dir"])


if __name__ == "__main__":
    build()
