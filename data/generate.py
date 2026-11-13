#!/usr/bin/env python3
"""Generates the reference data under data/. Run: python3 data/generate.py"""
import json, random, os, datetime

random.seed(42)
ROOT = os.path.dirname(os.path.abspath(__file__))


def out(path, obj):
    p = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def duns():
    n = random.randint(10_000_000, 99_999_999)
    s = f"{n}{random.randint(0, 9)}"
    return f"{s[:2]}-{s[2:5]}-{s[5:]}"


def ein():
    return f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}"


def dea(prefix_letter, last_name):
    d = [random.randint(0, 9) for _ in range(6)]
    chk = (d[0] + d[2] + d[4] + 2 * (d[1] + d[3] + d[5])) % 10
    return f"{prefix_letter}{last_name[0].upper()}{''.join(map(str, d))}{chk}"


def npi():
    return str(random.randint(1000000000, 1999999999))


# ---------------------------------------------------------------- hierarchy
SYSTEM = "Brazos Health System"
regions = [
    ("North Texas", "Plano", "TX", "75024"),
    ("East Texas", "Tyler", "TX", "75701"),
    ("Gulf Coast", "Houston", "TX", "77030"),
    ("Hill Country", "Austin", "TX", "78701"),
]
streets = ["Legacy Ridge Pkwy", "S Broadway Ave", "Medical Center Dr", "Bluebonnet Ln", "Oak Hollow Blvd",
           "Cedar Springs Rd", "Heritage Pkwy", "Lakeview Dr", "Mockingbird Ln", "Trinity Mills Rd"]
site_types = [
    ("Medical Center", "Hospital"), ("Specialty Hospital", "Hospital"),
    ("Outpatient Pharmacy", "Pharmacy"), ("Infusion Center", "Infusion"),
    ("Surgical Center", "Surgery center"), ("Senior Living", "Long-term care"),
]

nodes = []
orgs = {}   # DUNS -> D&B payload


def add_node(**kw):
    nodes.append(kw)
    return kw


root_duns = duns()
add_node(id="N-0001", level=0, kind="Ultimate parent", name=SYSTEM + " Holdings, Inc.", duns=root_duns,
         parent=None, city="Dallas", state="TX", status="Active")
ship_count = 0
legal_entities = 1
n = 1
for r, city, st, zp in regions:
    n += 1
    rid = f"N-{n:04d}"
    rd = duns()
    legal_entities += 1
    add_node(id=rid, level=1, kind="Regional system", name=f"{SYSTEM} – {r}", duns=rd, parent="N-0001",
             city=city, state=st, status="Active")
    for i, (stype, kind) in enumerate(random.sample(site_types, 4)):
        n += 1
        sid = f"N-{n:04d}"
        sd = duns()
        legal_entities += 1
        street = f"{random.randint(100, 9900)} {random.choice(streets)}"
        name = f"{SYSTEM.split()[0]} {stype} {city}" if i == 0 else f"{SYSTEM.split()[0]} {stype} – {r}"
        site = add_node(id=sid, level=2, kind=kind, name=name, duns=sd, parent=rid, city=city, state=st,
                        address=f"{street}, {city}, {st} {zp}", status="Active",
                        dea=dea("B", "Brazos"), tax_id=ein(), npi=npi(),
                        license=f"TX-PH-{random.randint(100000, 999999)}")
        for j in range(random.randint(2, 3)):
            n += 1
            ship_count += 1
            label = random.choice(["Central pharmacy", "Outpatient pharmacy", "ED", "OR", "Infusion suite",
                                   "Lab", "Oncology", "Dock B", "Satellite pharmacy"])
            add_node(id=f"N-{n:04d}", level=3, kind="Ship-to", name=f"{label} – {name.split(' ', 1)[1]}",
                     duns=None, parent=sid, city=city, state=st, address=f"{street}, Ste {100 + j * 10}",
                     status="Active")

# make exactly one proposed legal entity (new from D&B family tree)
for nd in reversed(nodes):
    if nd["level"] == 2:
        nd["status"] = "Proposed"
        break

out("hierarchy/brazos-health-system.json", {
    "ultimateParentDuns": root_duns,
    "summary": {"legalEntities": legal_entities, "shipToAccounts": ship_count,
                "nodes": len(nodes), "source": "D&B family tree + hub"},
    "nodes": nodes,
})

# D&B Direct+ style payloads for legal entities
for nd in nodes:
    if not nd["duns"]:
        continue
    orgs[nd["duns"]] = {
        "organization": {
            "duns": nd["duns"].replace("-", ""),
            "primaryName": nd["name"],
            "countryISOAlpha2Code": "US",
            "primaryAddress": {
                "addressLocality": {"name": nd["city"]},
                "addressRegion": {"abbreviatedName": nd["state"]},
                "streetAddress": {"line1": nd.get("address", "").split(",")[0] or None},
            },
            "startDate": str(random.randint(1978, 2016)),
            "numberOfEmployees": [{"value": random.randint(40, 4200), "informationScopeDescription": "Consolidated"}],
            "corporateLinkage": {
                "parent": {"duns": None if nd["parent"] is None else next(x["duns"] for x in nodes if x["id"] == nd["parent"]) or None},
                "globalUltimate": {"duns": root_duns.replace("-", ""), "primaryName": SYSTEM + " Holdings, Inc."},
                "familyTreeMembersCount": legal_entities,
            },
            "dnbAssessment": {"failureScore": {"classScore": random.randint(2, 5)}},
        },
        "inquiryDetail": {"duns": nd["duns"].replace("-", ""), "productID": "cmpelk", "productVersion": "v1"},
        "matchQualityInformation": {"confidenceCode": random.choice([9, 9, 10, 8])},
    }

# ---------------------------------------------------------------- source systems
SAP_FIELDS = "KUNNR NAME1 STRAS ORT01 REGIO PSTLZ STCD1 ZTERM KLIMK ZWELS KTOKD VKORG"
sap, legacy = [], []


def sap_row(k, name, street, city, zp, tin, zterm, klimk, vkorg, zwels="C", ktokd="Z001"):
    return {"KUNNR": k, "NAME1": name, "STRAS": street, "ORT01": city, "REGIO": "TX", "LAND1": "US",
            "PSTLZ": zp, "STCD1": tin, "ZTERM": zterm, "KLIMK": klimk, "ZWELS": zwels, "KTOKD": ktokd,
            "VKORG": vkorg}


def leg_row(system, k, name, addr, tin, terms, notes=None):
    return {"system": system, "legacyId": k, "customerName": name, "addressLine": addr, "taxRef": tin,
            "paymentTerms": terms, "notes": notes}


# Scenario 1: Cedar Park Family Pharmacy -> 5 sources already in the hub
cp_tin = ein()
cp_duns = duns()
sap += [
    sap_row("0001004417", "CEDAR PARK FAMILY PHARMACY LLC", "1200 E WHITESTONE BLVD", "CEDAR PARK", "78613-3047", cp_tin, "NT30", 50000, "US01"),
    sap_row("0001004418", "Cedar Park Family Pharmacy", "1200 E Whitestone Blvd Ste 4", "Cedar Park", "78613", cp_tin, "NT30", 25000, "US02", ktokd="Z002"),
    sap_row("0001009902", "CEDAR PARK FAMILY PHARM", "1200 E WHITESTONE", "CEDAR PARK", "78613", cp_tin, "NT45", 0, "US01", ktokd="Z003"),
]
legacy += [
    leg_row("Oracle EBS", "ORA-88213", "Cedar Pk Family Pharmacy Inc", "1200 Whitestone Blvd, Cedar Park TX 78613", cp_tin.replace("-", ""), "N30"),
    leg_row("AS/400 Order Entry", "AS4-30771", "CEDAR PARK FAM PHCY", "1200 E WHITESTONE BLVD STE 4 CEDAR PARK TX", None, "NET 30", "tax id missing"),
]

# Scenario 2: Westbrook Infusion Center - existing record, new owner at same site
wb_old_tin, wb_new_tin = ein(), ein()
sap += [sap_row("0001003388", "WESTBROOK INFUSION CENTER LLC", "4500 W PARK BLVD STE 120", "PLANO", "75093-2210", wb_old_tin, "NT30", 120000, "US02")]
legacy += [leg_row("Oracle EBS", "ORA-55102", "Westbrook Infusion Ctr", "4500 W Park Blvd Ste 120, Plano TX 75093", wb_old_tin.replace("-", ""), "N30")]

# Background population for search (so search has realistic neighbours)
name_bits = ["Lakeside", "Riverbend", "Prairie", "Summit", "Oakmont", "Harbor", "Magnolia", "Pioneer", "Sunrise", "Ironwood"]
kinds = ["Pharmacy", "Community Pharmacy", "Drug", "Health Mart", "Compounding Pharmacy", "Clinic Pharmacy"]
cities = [("Tyler", "75701"), ("Plano", "75024"), ("Frisco", "75034"), ("Waco", "76710"), ("Katy", "77494"), ("Round Rock", "78664")]
k = 1010000
for i in range(40):
    c, z = random.choice(cities)
    nm = f"{random.choice(name_bits)} {random.choice(kinds)} {'LLC' if random.random() < .6 else 'Inc'}"
    row = sap_row(f"{k + i:010d}", nm.upper(), f"{random.randint(100, 9900)} {random.choice(streets)}".upper(), c.upper(), z, ein(), random.choice(["NT30", "NT30", "NT45"]), random.choice([25000, 50000, 75000]), "US01")
    sap.append(row)
# Lakeside Pharmacy #2: the near-miss (same owner, different tax ID) referenced by the new request
lk_old = sap_row("0000042871", "LAKESIDE PHARMACY #2", "310 N BROADWAY AVE", "TYLER", "75702", ein(), "NT30", 50000, "US01")
sap.append(lk_old)
for i in range(12):
    c, z = random.choice(cities)
    legacy.append(leg_row(random.choice(["Oracle EBS", "AS/400 Order Entry"]), f"LEG-{70000 + i}",
                          f"{random.choice(name_bits)} {random.choice(kinds)}", f"{random.randint(100, 9900)} {random.choice(streets)}, {c} TX {z}",
                          ein().replace("-", ""), random.choice(["N30", "NET 30", "N45"])))

out("sources/sap/customers.json", {"system": "SAP S/4HANA", "table": "KNA1/KNVV", "fields": SAP_FIELDS.split(), "records": sap})
out("sources/legacy/customers.json", {"systems": ["Oracle EBS", "AS/400 Order Entry"], "records": legacy})
out("dnb/organizations.json", {"source": "D&B Direct+ (identity resolution + family tree)", "organizations": list(orgs.values())})

# ---------------------------------------------------------------- scenarios
lk_tin, lk_duns, lk_dea = ein(), duns(), dea("F", "Lakeside")
# Lakeside matches the Journey screen: DUNS 08-447-3921, DEA FL4827311
lk_duns, lk_dea = "08-447-3921", "FL4827311"
lk_tin_masked = "••-•••" + lk_tin[-4:]

ADV = ["legal", "procurement", "credit", "tax"]

scenarios = {
    "S1-existing-customer": {
        "title": "Request for a customer that already exists",
        "request": {
            "channel": "email", "from": "ap@cedarparkfamilyrx.com", "received": "2026-11-12T14:07:00Z",
            "subject": "Add Specialty account – Cedar Park Family Pharmacy",
            "thread": [
                {"from": "ap@cedarparkfamilyrx.com", "body": "Please add a specialty account for Cedar Park Family Pharmacy, 1200 E Whitestone Blvd, Cedar Park TX 78613. We will order specialty oncology drugs."},
                {"from": "onboarding@mckesson.example", "body": "Thanks. Can you confirm the legal name and attach your current pharmacy license and W-9?"},
                {"from": "ap@cedarparkfamilyrx.com", "body": "Legal name is Cedar Park Family Pharmacy LLC. W-9 and license attached."},
            ],
            "attachments": ["W-9.pdf", "TX_Pharmacy_License.pdf"],
        },
        "keyValues": {
            "legal_name": "Cedar Park Family Pharmacy LLC", "address": "1200 E Whitestone Blvd, Cedar Park, TX 78613",
            "tax_id": cp_tin, "request_type": "Add sales area", "sales_area": "Specialty · US02", "product_line": "Specialty oncology",
        },
        "search": {"query": "Cedar Park Family Pharmacy LLC / 1200 E Whitestone Blvd", "results": [
            {"rank": 1, "id": "BRR-0004417", "name": "Cedar Park Family Pharmacy, LLC", "confidence": 0.98, "decision": "Same customer"},
            {"rank": 2, "id": "SAP 0001004418", "name": "Cedar Park Family Pharmacy", "confidence": 0.96, "decision": "Merged into BRR-0004417"},
            {"rank": 3, "id": "SAP 0001009902", "name": "CEDAR PARK FAMILY PHARM", "confidence": 0.93, "decision": "Merged into BRR-0004417"},
            {"rank": 4, "id": "Oracle EBS ORA-88213", "name": "Cedar Pk Family Pharmacy Inc", "confidence": 0.91, "decision": "Merged into BRR-0004417"},
            {"rank": 5, "id": "AS/400 AS4-30771", "name": "CEDAR PARK FAM PHCY", "confidence": 0.84, "decision": "Merged; steward confirmed"}]},
        "outcome": "No new customer. Request linked to BRR-0004417; Specialty US02 sales area added.",
    },
    "S2-existing-customer-new-owner": {
        "title": "Request on an existing site with a different tax ID",
        "request": {"channel": "form", "legal_name": "Westbrook Infusion Partners LP", "address": "4500 W Park Blvd Ste 120, Plano, TX 75093",
                    "tax_id": wb_new_tin, "request_type": "New customer"},
        "search": {"results": [
            {"rank": 1, "id": "SAP 0001003388", "name": "WESTBROOK INFUSION CENTER LLC", "confidence": 0.89, "decision": "Same site, different tax ID"},
            {"rank": 2, "id": "Oracle EBS ORA-55102", "name": "Westbrook Infusion Ctr", "confidence": 0.86, "decision": "Same site"}]},
        "enrichment": {"dnb": "Ownership change reported 2026-09-02 (Westbrook Infusion Center LLC acquired by Westbrook Infusion Partners LP)"},
        "outcome": "Policy MM-007a: create a new customer, link as successor of 0001003388; carry over ship-to; Credit decides limit and terms afresh.",
    },
    "S3-new-customer": {
        "title": "New customer that does not exist",
        "request": {"channel": "email + attachments", "legal_name": "Lakeside Community Pharmacy, LLC", "dba": "Lakeside Pharmacy",
                    "address": "1420 S Broadway Ave, Ste 200, Tyler, TX 75701-3318", "tax_id": lk_tin, "dea": lk_dea,
                    "request_type": "New customer", "sales_area": "Pharma · US01", "product_line": "Independent retail pharmacy"},
        "search": {"results": [
            {"rank": 1, "id": "SAP 0000042871", "name": "LAKESIDE PHARMACY #2", "confidence": 0.71, "decision": "Related: same owner, different tax ID. Below 0.80, no merge."}]},
        "enrichment": {"dnb": {"duns": lk_duns, "parent": "Lakeside Rx Holdings, LLC", "confidenceCode": 9}},
        "outcome": "New customer BRR-0051207 created after Credit, Tax, Legal and Procurement decisions.",
    },
}
for key, sc in scenarios.items():
    out(f"scenarios/{key}.json", sc)

# ---------------------------------------------------------------- LexisNexis / AVS
lex = []
for nd in nodes:
    if nd["level"] == 2:
        lex.append({"entity": nd["name"], "duns": nd["duns"], "checks": {
            "ofac": {"result": "clear", "listsChecked": ["SDN", "Consolidated"]},
            "oig_leie": {"result": "clear"}, "sam_gov": {"result": "clear"},
            "businessRegistration": {"state": "TX", "status": "Active"},
            "stateLicense": {"number": nd["license"], "status": "Active", "expires": "2027-03-31"},
            "dea": {"number": nd["dea"], "status": "Active", "schedules": ["II", "III", "IV", "V"]}}})
lex.append({"entity": "Lakeside Community Pharmacy, LLC", "duns": lk_duns, "checks": {
    "ofac": {"result": "clear"}, "oig_leie": {"result": "clear"}, "sam_gov": {"result": "clear"},
    "businessRegistration": {"state": "TX", "status": "Active", "formed": "2019-05-14"},
    "stateLicense": {"number": "TX-PH-481220", "status": "Active", "expires": "2027-06-30"},
    "dea": {"number": lk_dea, "status": "Active", "expires": "2027-06-30", "schedules": ["II", "III", "IV", "V"]},
    "nameMatch": {"watchlistHits": [{"list": "OIG", "name": "Lakeside Pharmacy Services", "score": 0.41, "result": "below threshold, clear"}]}}})
out("lexisnexis/business-checks.json", {"source": "LexisNexis business and exclusion checks", "records": lex})

avs_acct = [
    {"entity": "Lakeside Community Pharmacy, LLC", "routing": "111000025", "accountLast4": "7302",
     "result": {"code": "GREEN", "accountStatus": "open", "nameMatch": "match", "ownerType": "business"}},
    {"entity": "Cedar Park Family Pharmacy LLC", "routing": "111900659", "accountLast4": "1184",
     "result": {"code": "GREEN", "accountStatus": "open", "nameMatch": "match", "ownerType": "business"}},
    {"entity": "Westbrook Infusion Partners LP", "routing": "111000614", "accountLast4": "9051",
     "result": {"code": "AMBER", "accountStatus": "open", "nameMatch": "partial", "ownerType": "business",
                "note": "Account holder shows prior owner name"}},
]
out("avs/account-validation.json", {"source": "Account validation service", "records": avs_acct})
out("avs/address-validation.json", {"source": "Address validation service (USPS CASS)", "records": [
    {"input": "1420 S Broadway Ave, Ste 200, Tyler, TX 75701", "standardized": "1420 S BROADWAY AVE STE 200, TYLER TX 75701-3318",
     "dpvConfirmation": "Y", "deliverable": True, "poBox": False, "rdi": "Commercial"},
    {"input": "1200 E Whitestone Blvd, Cedar Park, TX 78613", "standardized": "1200 E WHITESTONE BLVD, CEDAR PARK TX 78613-3047",
     "dpvConfirmation": "Y", "deliverable": True, "poBox": False, "rdi": "Commercial"},
    {"input": "4500 W Park Blvd Ste 120, Plano, TX 75093", "standardized": "4500 W PARK BLVD STE 120, PLANO TX 75093-2210",
     "dpvConfirmation": "Y", "deliverable": True, "poBox": False, "rdi": "Commercial"}]})

# ---------------------------------------------------------------- Business ready record for S1 (cross-reference)
brr = {
    "id": "BRR-0004417",
    "attributes": {
        "legal_name": {"value": "Cedar Park Family Pharmacy, LLC", "winner": "D&B", "policy": "SV-001"},
        "address": {"value": "1200 E Whitestone Blvd, Cedar Park, TX 78613-3047", "winner": "Address validation", "policy": "SV-001"},
        "tax_id": {"value": cp_tin, "winner": "SAP 0001004417", "policy": "SV-001"},
        "payment_terms": {"value": "Net 30", "winner": "SAP 0001004417", "policy": "BR-PT-001"},
        "credit_limit": {"value": 50000, "winner": "SAP 0001004417", "policy": "BR-CR-001"},
    },
    "crossReferences": [
        {"system": "SAP S/4HANA", "id": "0001004417", "record": sap[0]},
        {"system": "SAP S/4HANA", "id": "0001004418", "record": sap[1]},
        {"system": "SAP S/4HANA", "id": "0001009902", "record": sap[2]},
        {"system": "Oracle EBS", "id": "ORA-88213", "record": legacy[0]},
        {"system": "AS/400 Order Entry", "id": "AS4-30771", "record": legacy[1]},
    ],
}
out("business-ready-records/BRR-0004417.json", brr)
print("nodes", len(nodes), "ship-tos", ship_count, "legal entities", legal_entities)
