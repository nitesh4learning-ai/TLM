"""The agent roster. Thresholds and decisions come from the policy store; these are the agents' settings."""

def A(name, group, what, model, uses, stops, version="v1.0"):
    return {"name": name, "group": group, "what": what, "model": model, "uses": uses, "stops": stops, "version": version}


AGENTS = [
    A("Orchestrator", "Orchestration", "Routes each request through the agents and applies the autonomy matrix.", "Rules", "Request store, policy store", "A stage fails twice, or no policy applies", "v3.1"),
    A("Intake", "Core MDM", "Reads emails, threads, PDFs and forms and turns them into key values mapped to the data model.", "Claude", "Uploaded emails and documents", "Any field below 0.75 goes to a steward; 0.75–0.95 the requester confirms", "v2.4"),
    A("Search before create", "Core MDM", "Looks for the party in the hub and source systems before anything new is made.", "Fuzzy matching on name, address and tax ID", "Business ready records, SAP, Oracle EBS, AS/400", "Never. Near-matches go to match & merge.", "v2.4"),
    A("Match & merge", "Core MDM", "Decides link, successor or new, and applies survivorship.", "Rules from MM-002, MM-007a, SV-001", "Business ready record store, D&B", "Scores from 0.80 to 0.95 without an ownership change", "v2.4"),
    A("Enrichment", "Core MDM", "Adds D&B firmographics and family trees and LexisNexis business checks.", "Lookup", "D&B, LexisNexis", "D&B confidence code below 8", "v2.4"),
    A("Validation", "Core MDM", "Checks address, bank account, tax ID, licenses and exclusion lists.", "Rules", "Address and account validation, IRS TIN match, DEA, state boards, OFAC, OIG, SAM", "Any failed call, or account validation AMBER/RED", "v2.4"),
    A("Legal", "Function", "Decides on agreements, licensure and controlled-substance eligibility.", "Rules; Claude writes the explanation", "Policy store, LexisNexis", "Edited terms, lapsed license, or no matching policy", "v1.2"),
    A("Procurement", "Function", "Sets pricing group and partner functions; checks BPO supplier information.", "Rules; Claude writes the explanation", "Policy store, contracts, GPO rosters", "Contract without a pricing group", "v1.2"),
    A("Credit", "Function", "Decides credit limit, payment terms and payment method.", "Rules; Claude writes the explanation", "Policy store, D&B scores, account validation", "Limit above $50,000; terms above the credit tier; AMBER bank check", "v1.3"),
    A("Tax", "Function", "Decides tax status from resale and exemption certificates.", "Rules; Claude writes the explanation", "Policy store, certificates from intake", "Certificate missing, expired or in another name", "v1.1"),
    A("Steward copilot", "People support", "Explains each exception and recommends what to do.", "Claude", "Audit trail", "Always. It advises and never commits.", "v1.0"),
    A("Lifecycle monitor", "People support", "Watches expiries, dormancy and D&B changes.", "Rules, nightly", "License feeds, D&B", "Deactivations and re-parenting", "v1.0"),
    A("Contextual outreach", "People support", "Drafts messages that draw on past conversations.", "Claude", "Email history, read-only", "Any message that cites a past conversation", "v1.0"),
]
