#!/usr/bin/env python3
"""Grows the reference data to about five times its original size and adds the parties used by test packages 4-8.

Runs after generate.py (which it calls if needed) with its own random seed, so every ID in the original data stays the same.
Run: python3 data/expand.py
"""
import json
import os
import random

ROOT = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(2026)


def load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


def out(rel, obj):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def duns():
    s = f"{rng.randint(10_000_000, 99_999_999)}{rng.randint(0, 9)}"
    return f"{s[:2]}-{s[2:5]}-{s[5:]}"


def ein():
    return f"{rng.randint(10, 99)}-{rng.randint(1000000, 9999999)}"


def dea(first, name):
    d = [rng.randint(0, 9) for _ in range(6)]
    chk = (d[0] + d[2] + d[4] + 2 * (d[1] + d[3] + d[5])) % 10
    return f"{first}{name[0].upper()}{''.join(map(str, d))}{chk}"


STREETS = ["Legacy Dr", "Main St", "Medical Pkwy", "Bluebonnet Ln", "Oak Hollow Blvd", "Cedar Springs Rd", "Heritage Pkwy", "Lakeview Dr",
           "Mockingbird Ln", "Trinity Mills Rd", "Pecan St", "Ranch Rd 620", "University Blvd", "Westheimer Rd", "Alamo Pkwy", "Red River St"]
CITIES = [("Dallas", "75201"), ("Fort Worth", "76102"), ("Arlington", "76010"), ("Austin", "78701"), ("San Antonio", "78205"), ("Houston", "77002"),
          ("El Paso", "79901"), ("Lubbock", "79401"), ("Amarillo", "79101"), ("Corpus Christi", "78401"), ("McKinney", "75069"), ("Denton", "76201"),
          ("Waco", "76701"), ("Tyler", "75701"), ("Beaumont", "77701"), ("Midland", "79701")]

FAMILIES = [
    {"key": "lonestar", "prefix": "LSP", "name": "Lone Star Pharmacy Group", "kinds": [("Pharmacy", "Pharmacy"), ("Compounding Pharmacy", "Pharmacy"), ("Clinic Pharmacy", "Pharmacy"), ("Specialty Pharmacy", "Pharmacy")],
     "regions": ["North", "Central", "South", "West"], "naics": "456110 · Pharmacies and drug retailers"},
    {"key": "gulfcoast", "prefix": "GCS", "name": "Gulf Coast Senior Care", "kinds": [("Senior Living", "Long-term care"), ("Skilled Nursing", "Long-term care"), ("Memory Care", "Long-term care"), ("Rehab Center", "Long-term care")],
     "regions": ["Houston", "Galveston", "Corpus Christi", "Beaumont"], "naics": "623110 · Nursing care facilities"},
    {"key": "bluebonnet", "prefix": "BHP", "name": "Bluebonnet Health Partners", "kinds": [("Medical Center", "Hospital"), ("Surgical Center", "Surgery center"), ("Infusion Center", "Infusion"), ("Outpatient Pharmacy", "Pharmacy")],
     "regions": ["Austin", "San Antonio", "Waco", "Temple"], "naics": "622110 · General medical and surgical hospitals"},
    {"key": "pecos", "prefix": "PVM", "name": "Pecos Valley Medical", "kinds": [("Regional Hospital", "Hospital"), ("Infusion Center", "Infusion"), ("Specialty Clinic", "Hospital"), ("Outpatient Pharmacy", "Pharmacy")],
     "regions": ["El Paso", "Midland", "Odessa", "Lubbock"], "naics": "622110 · General medical and surgical hospitals"},
]
SHIPTO = ["Central pharmacy", "Receiving dock", "Oncology suite", "Infusion suite", "Satellite pharmacy", "Nursing station 2", "Lab", "OR"]


def family(f):
    nodes = []
    n = 0
    def nid():
        nonlocal n
        n += 1
        return f"{f['prefix']}-{n:04d}"
    root = {"id": nid(), "level": 0, "kind": "Ultimate parent", "name": f["name"] + " Holdings, LLC", "duns": duns(), "parent": None,
            "city": "Dallas", "state": "TX", "status": "Active", "tax_id": ein()}
    nodes.append(root)
    for region in f["regions"]:
        city, zp = rng.choice(CITIES)
        r = {"id": nid(), "level": 1, "kind": "Regional system", "name": f"{f['name']} – {region}", "duns": duns(), "parent": root["id"],
             "city": city, "state": "TX", "status": "Active", "tax_id": ein()}
        nodes.append(r)
        city_of = dict(CITIES) | {"Galveston": "77550", "Temple": "76501", "Odessa": "79761"}
        for stype, kind in rng.sample(f["kinds"], 4):
            city, zp = (region, city_of[region]) if region in city_of else rng.choice(CITIES)
            street = f"{rng.randint(100, 9900)} {rng.choice(STREETS)}"
            s = {"id": nid(), "level": 2, "kind": kind, "name": f"{f['name'].split()[0]} {stype} {region}", "duns": duns(), "parent": r["id"],
                 "city": city, "state": "TX", "address": f"{street}, {city}, TX {zp}", "status": "Active", "dea": dea("B", f["name"]),
                 "tax_id": ein(), "npi": str(rng.randint(1000000000, 1999999999)), "license": f"TX-PH-{rng.randint(100000, 999999)}"}
            nodes.append(s)
            for j in range(rng.randint(2, 3)):
                nodes.append({"id": nid(), "level": 3, "kind": "Ship-to", "name": f"{rng.choice(SHIPTO)} – {stype} {region}", "duns": None,
                              "parent": s["id"], "city": city, "state": "TX", "address": f"{street}, Ste {100 + j * 10}", "status": "Active"})
    # one entity in each family is proposed by D&B but not yet in the hub
    [x for x in nodes if x["level"] == 2][-1]["status"] = "Proposed"
    le = sum(1 for x in nodes if x["level"] < 3)
    return {"key": f["key"], "name": f["name"], "ultimateParentDuns": root["duns"], "naics": f["naics"],
            "summary": {"legalEntities": le, "shipToAccounts": len(nodes) - le, "nodes": len(nodes), "source": "D&B family tree + hub"}, "nodes": nodes}


def org(node, root, fam, le_count, naics):
    return {"organization": {"duns": node["duns"].replace("-", ""), "primaryName": node["name"], "countryISOAlpha2Code": "US",
                             "primaryAddress": {"addressLocality": {"name": node["city"]}, "addressRegion": {"abbreviatedName": "TX"},
                                                "streetAddress": {"line1": (node.get("address") or "").split(",")[0] or None}},
                             "startDate": str(rng.randint(1975, 2018)), "numberOfEmployees": [{"value": rng.randint(15, 3800), "informationScopeDescription": "Consolidated"}],
                             "industryCodes": [{"code": naics.split(" ")[0], "description": naics.split("· ")[-1], "typeDescription": "NAICS"}],
                             "corporateLinkage": {"parent": {"duns": None}, "globalUltimate": {"duns": root["duns"].replace("-", ""), "primaryName": root["name"]},
                                                  "familyTreeMembersCount": le_count},
                             "dnbAssessment": {"failureScore": {"classScore": rng.randint(1, 4)}}},
            "inquiryDetail": {"duns": node["duns"].replace("-", ""), "productID": "cmpelk", "productVersion": "v1"},
            "matchQualityInformation": {"confidenceCode": rng.choice([8, 9, 9, 10])}, "family": fam}


# ------------------------------------------------------------------ the parties behind test packages 4-8
SCENARIO_PARTIES = [
    {"key": "mesquite", "name": "Mesquite Creek Pharmacy, LLC", "street": "2215 S 14th St", "city": "Abilene", "zip": "79605", "ein": "73-4418205",
     "duns": "05-772-1940", "start": "2015", "employees": 14, "fsc": 2, "cc": 9, "dea": "FM3817542", "license": "TX-PH-512877", "lic_status": "Active",
     "bank": ("111000025", "4419", "GREEN", "match"), "naics": "456110 · Pharmacies and drug retailers"},
    {"key": "pinecrest", "name": "Pinecrest Apothecary, Inc.", "street": "708 Judson Rd", "city": "Longview", "zip": "75601", "ein": "27-5530916",
     "duns": "02-486-3317", "start": "2009", "employees": 11, "fsc": 3, "cc": 9, "dea": "FP5528193", "license": "TX-PH-298140", "lic_status": "Expired",
     "lic_expired": "2026-09-30", "bank": ("111000614", "6630", "GREEN", "match"), "naics": "456110 · Pharmacies and drug retailers"},
    {"key": "brazos-cancer", "name": "Brazos Cancer Center – Frisco", "street": "5601 Warren Pkwy", "city": "Frisco", "zip": "75034", "ein": "81-2290457",
     "duns": "08-930-5521", "start": "2018", "employees": 210, "fsc": 1, "cc": 10, "dea": "BB4417706", "license": "TX-PH-604412", "lic_status": "Active",
     "parent": "Brazos Health System – North Texas", "bank": ("111000025", "8810", "GREEN", "match"), "naics": "622310 · Specialty hospitals"},
    {"key": "paloduro", "name": "Palo Duro Drugs LLC", "street": "880 Canyon Rd", "city": "Amarillo", "zip": "79101", "ein": "46-1187302",
     "duns": "04-318-7765", "start": "2004", "employees": 9, "fsc": 2, "cc": 8, "dea": "FP7712384", "license": "TX-PH-177450", "lic_status": "Active",
     "bank": ("111900659", "2271", "GREEN", "match"), "naics": "456110 · Pharmacies and drug retailers",
     "sap": {"KUNNR": "0001205514", "NAME1": "PALO DURO DRUG CO", "tin": "75-6610428"}},
    {"key": "sunbelt", "name": "Sunbelt Compounding Pharmacy LLC", "street": "1902 Saunders St", "city": "Laredo", "zip": "78041", "ein": "92-3305871",
     "duns": "09-114-2208", "start": "2026", "employees": 4, "fsc": 4, "cc": 8, "dea": "FS2209463", "license": "TX-PH-655019", "lic_status": "Active",
     "bank": ("114000093", "0517", "RED", "no match"), "naics": "456110 · Pharmacies and drug retailers"},
]


def main():
    if not os.path.exists(os.path.join(ROOT, "hierarchy", "brazos-health-system.json")):
        import subprocess, sys
        subprocess.run([sys.executable, os.path.join(ROOT, "generate.py")], check=True)

    sap = load("sources/sap/customers.json")
    leg = load("sources/legacy/customers.json")
    dnb = load("dnb/organizations.json")
    lex = load("lexisnexis/business-checks.json")
    acct = load("avs/account-validation.json")
    addr = load("avs/address-validation.json")
    brazos = load("hierarchy/brazos-health-system.json")
    for d in (sap, leg, dnb, lex, acct, addr):          # make the script safe to run twice
        k = "records" if "records" in d else "organizations"
        d[k] = [x for x in d[k] if x.get("batch") != 2]

    fams = [family(f) for f in FAMILIES]
    tin = [{"ein": "15-3939212", "name": "Lakeside Community Pharmacy, LLC"}, {"ein": "62-1415846", "name": "Cedar Park Family Pharmacy LLC"},
           {"ein": "44-3670896", "name": "Westbrook Infusion Partners LP"}]
    for r in sap["records"]:
        if r["NAME1"].startswith("WESTBROOK"):
            tin.append({"ein": r["STCD1"], "name": "Westbrook Infusion Center LLC"})
        if r["NAME1"].startswith("LAKESIDE PHARMACY #2"):
            tin.append({"ein": r["STCD1"], "name": "Lakeside Pharmacy #2 LLC"})
    for n in brazos["nodes"]:
        if n.get("tax_id"):
            tin.append({"ein": n["tax_id"], "name": n["name"]})

    for fdef, fam in zip(FAMILIES, fams):
        out(f"hierarchy/{fam['key']}.json", fam)
        root = fam["nodes"][0]
        le = fam["summary"]["legalEntities"]
        for n in fam["nodes"]:
            if n.get("duns"):
                dnb["organizations"].append(dict(org(n, root, fam["key"], le, fdef["naics"]), batch=2))
            if n.get("tax_id"):
                tin.append({"ein": n["tax_id"], "name": n["name"]})
            if n["level"] == 2:
                lex["records"].append({"entity": n["name"], "duns": n["duns"], "batch": 2, "checks": {
                    "ofac": {"result": "clear", "listsChecked": ["SDN", "Consolidated"]}, "oig_leie": {"result": "clear"}, "sam_gov": {"result": "clear"},
                    "businessRegistration": {"state": "TX", "status": "Active"},
                    "stateLicense": {"number": n["license"], "status": "Active", "expires": "2027-05-31"},
                    "dea": {"number": n["dea"], "status": "Active", "expires": "2027-05-31", "schedules": ["II", "III", "IV", "V"]}}})
                if rng.random() < 0.25:
                    acct["records"].append({"entity": n["name"], "routing": rng.choice(["111000025", "111000614", "111900659", "113000023"]),
                                            "accountLast4": f"{rng.randint(0, 9999):04d}", "batch": 2,
                                            "result": {"code": "GREEN", "accountStatus": "open", "nameMatch": "match", "ownerType": "business"}})
                    addr["records"].append({"input": n["address"], "standardized": n["address"].upper().replace(",", "").replace(" TX ", " TX ") , "batch": 2,
                                            "dpvConfirmation": "Y", "deliverable": True, "poBox": False, "rdi": "Commercial"})
            # every site and region also exists in SAP, about a third also in a legacy system
            if n["level"] in (1, 2):
                city = n["city"].upper()
                street = (n.get("address") or f"{rng.randint(100, 9900)} {rng.choice(STREETS)}").split(",")[0].upper()
                sap["records"].append({"KUNNR": f"{1300000 + len(sap['records']):010d}", "NAME1": n["name"].upper().replace("–", "-"), "STRAS": street, "ORT01": city,
                                       "REGIO": "TX", "LAND1": "US", "PSTLZ": (n.get("address") or "00000")[-5:], "STCD1": n.get("tax_id"), "ZTERM": rng.choice(["NT30", "NT45"]),
                                       "KLIMK": rng.choice([100000, 250000, 500000]), "ZWELS": "C", "KTOKD": "Z001", "VKORG": "US01", "batch": 2})
                if rng.random() < 0.35:
                    leg["records"].append({"system": rng.choice(["Oracle EBS", "AS/400 Order Entry"]), "legacyId": f"LEG-{80000 + len(leg['records'])}",
                                           "customerName": n["name"].replace("–", "-"), "addressLine": f"{street.title()}, {n['city']} TX", "taxRef": (n.get("tax_id") or "").replace("-", ""),
                                           "paymentTerms": rng.choice(["N30", "NET 30", "N45"]), "notes": None, "batch": 2})

    # background independents so search has realistic neighbours
    bits = ["Bluebonnet", "Mesa", "Caprock", "Brazos Valley", "Live Oak", "Rio Grande", "Hill Country", "Piney Woods", "Gulf Breeze", "Red River",
            "Llano", "Caddo", "Frontier", "Big Thicket", "Trinity", "Sabine"]
    kinds = ["Pharmacy", "Family Pharmacy", "Drug", "Apothecary", "Compounding", "Health Mart", "Discount Drug", "Medical Pharmacy"]
    for i in range(100):
        city, zp = rng.choice(CITIES)
        nm = f"{rng.choice(bits)} {rng.choice(kinds)} {'LLC' if rng.random() < .6 else 'Inc'}"
        tid = ein()
        sap["records"].append({"KUNNR": f"{1400000 + i:010d}", "NAME1": nm.upper(), "STRAS": f"{rng.randint(100, 9900)} {rng.choice(STREETS)}".upper(),
                               "ORT01": city.upper(), "REGIO": "TX", "LAND1": "US", "PSTLZ": zp, "STCD1": tid, "ZTERM": rng.choice(["NT30", "NT30", "NT45"]),
                               "KLIMK": rng.choice([25000, 50000, 75000]), "ZWELS": "C", "KTOKD": "Z001", "VKORG": "US01", "batch": 2})
        tin.append({"ein": tid, "name": nm})
        if i % 3 == 0:
            leg["records"].append({"system": rng.choice(["Oracle EBS", "AS/400 Order Entry"]), "legacyId": f"LEG-{90000 + i}", "customerName": nm.title(),
                                   "addressLine": f"{rng.randint(100, 9900)} {rng.choice(STREETS)}, {city} TX {zp}", "taxRef": tid.replace("-", ""),
                                   "paymentTerms": rng.choice(["N30", "NET 30"]), "notes": None, "batch": 2})

    # the parties behind test packages 4-8
    parties = []
    for p in SCENARIO_PARTIES:
        full = f"{p['street']}, {p['city']}, TX {p['zip']}"
        parties.append({"key": p["key"], "duns": p["duns"], "primaryName": p["name"], "parent": p.get("parent"), "globalUltimate": "Brazos Health System Holdings, Inc." if p.get("parent") else p.get("parent"),
                        "naics": p["naics"], "startDate": p["start"], "employees": p["employees"], "failureScoreClass": p["fsc"], "confidenceCode": p["cc"],
                        "ownershipChangeDate": None})
        lic = {"number": p["license"], "status": p["lic_status"], "expires": p.get("lic_expired", "2027-06-30")}
        lex["records"].append({"entity": p["name"], "duns": p["duns"], "batch": 2, "checks": {
            "ofac": {"result": "clear"}, "oig_leie": {"result": "clear"}, "sam_gov": {"result": "clear"},
            "businessRegistration": {"state": "TX", "status": "Active", "formed": f"{p['start']}-03-01"}, "stateLicense": lic,
            "dea": {"number": p["dea"], "status": "Active", "expires": "2027-06-30", "schedules": ["II", "III", "IV", "V"]}}})
        routing, last4, code, nm = p["bank"]
        acct["records"].append({"entity": p["name"], "routing": routing, "accountLast4": last4, "batch": 2,
                                "result": {"code": code, "accountStatus": "open" if code != "RED" else "closed", "nameMatch": nm, "ownerType": "business"}})
        addr["records"].append({"input": full, "standardized": f"{p['street'].upper()}, {p['city'].upper()} TX {p['zip']}-{rng.randint(1000, 9999)}", "batch": 2,
                                "dpvConfirmation": "Y", "deliverable": True, "poBox": False, "rdi": "Commercial"})
        tin.append({"ein": p["ein"], "name": p["name"]})
        if p.get("sap"):
            s = p["sap"]
            sap["records"].append({"KUNNR": s["KUNNR"], "NAME1": s["NAME1"], "STRAS": p["street"].upper(), "ORT01": p["city"].upper(), "REGIO": "TX", "LAND1": "US",
                                   "PSTLZ": p["zip"], "STCD1": s["tin"], "ZTERM": "NT30", "KLIMK": 40000, "ZWELS": "C", "KTOKD": "Z001", "VKORG": "US01", "batch": 2})
            tin.append({"ein": s["tin"], "name": "Palo Duro Drug Co"})
    out("dnb/scenario-companies.json", {"source": "D&B Direct+ identity resolution (test data)", "companies": parties})

    out("sources/sap/customers.json", sap)
    out("sources/legacy/customers.json", leg)
    out("dnb/organizations.json", dnb)
    out("lexisnexis/business-checks.json", lex)
    out("avs/account-validation.json", acct)
    out("avs/address-validation.json", addr)
    out("irs/tin-match.json", {"source": "IRS TIN matching (test data)", "records": tin})
    total_nodes = len(brazos["nodes"]) + sum(len(f["nodes"]) for f in fams)
    print(f"SAP {len(sap['records'])} · legacy {len(leg['records'])} · D&B {len(dnb['organizations'])} + {len(parties)} · LexisNexis {len(lex['records'])} · "
          f"AVS account {len(acct['records'])} · address {len(addr['records'])} · TIN {len(tin)} · hierarchy nodes {total_nodes} in {1 + len(fams)} families")


if __name__ == "__main__":
    main()
