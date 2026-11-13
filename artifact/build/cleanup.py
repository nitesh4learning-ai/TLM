"""Terminology and wording clean-up for screens not generated from build scripts."""
import re, os, sys
from common import ART, replace_nav
R=[
 ('Golden record store: CSV on Blob (POC), SimpleMDG next','Business ready record store'),
 ('Saves to the golden record store: CSV on Blob storage in the POC, SimpleMDG as the target.','Saves to the business ready record store.'),
 ('CSV on Blob storage for the POC, SimpleMDG as the target. D&amp;B, LexisNexis and validation services are mocked. Snowflake syncs nightly.','Fed by D&amp;B, LexisNexis and the validation services. Snowflake syncs nightly.'),
 ('POC run 14 · Nov 12, 2026 · 260 synthetic requests (182 customers, 78 suppliers)','Nov 12, 2026 · 260 requests (182 customers, 78 suppliers)'),
 ('DEA registry check, mocked','DEA registry check'),
 ('Golden record','Business ready record'),('golden records','business ready records'),('golden record','business ready record'),
]
for name in ["Main.dc.html", "Steward.dc.html", "Lifecycle.dc.html"]:
    p = os.path.join(ART, name)
    s = open(p).read()
    s = re.sub(r'<span style="[^"]*">POC · synthetic data</span>\s*', '', s)
    for a, b in R: s = s.replace(a, b)
    s = s.replace('color: #5F6B7A">Business rules</span>', 'color: #5F6B7A">Function agents</span>')
    s = replace_nav(s, name)
    with open(p, "w") as f: f.write(s)
print("cleanup ok")
