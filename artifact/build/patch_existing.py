# One-time migration of the original Intake screen (adds the email upload panel). Do not re-run.
from common import *
import re

# Intake: add an email upload panel and logic
f = os.path.join(ART, "Intake.dc.html")
s = open(f).read()
s = replace_nav(s, "Intake.dc.html")
UP = f'''<section aria-label="Upload email" style="display: flex; flex-direction: column; gap: 12px; padding: 18px 20px; {CARD}">
<div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px">
<div style="display: flex; flex-direction: column; gap: 4px"><h2 style="margin: 0; font-size: 16px; font-weight: 600">Upload an email</h2>
<p style="margin: 0; font-size: 13px; color: #4B5563">Drop a saved email (.eml or .msg) with its whole thread and attachments. The Intake agent reads every message and document and extracts the key values.</p></div>
<label style="{BTN}; position: relative">Choose email file<input type="file" multiple accept=".eml,.msg,.pdf,.docx,.xlsx,.png,.jpg" onChange="{{{{onUpload}}}}" style="position: absolute; width: 1px; height: 1px; opacity: 0"></label>
</div>
<sc-if value="{{{{hasUpload}}}}" hint-placeholder-val="{{{{false}}}}">
<div style="display: flex; flex-direction: column; gap: 8px; padding: 12px 14px; border-radius: 12px; background: #F5F8FF; border: 1px solid #9DB3EE">
<span style="font-size: 13px; font-weight: 600; color: #1D47B8">{{{{fileName}}}} · thread of 3 messages · 4 attachments</span>
<ul style="margin: 0; padding-left: 18px; font-size: 13px; line-height: 20px; color: #2B323C">
<li>Dana Whitfield, Nov 11 4:02 PM: request to open an account; W-9, license and DEA certificate attached</li>
<li>Onboarding, Nov 11 4:40 PM: asked for the resale certificate</li>
<li>Dana Whitfield, Nov 12 9:10 AM: resale certificate attached; trades as Lakeside Pharmacy</li>
</ul>
<span style="font-size: 12px; color: #4B5563">Extracted 34 fields. Review them below, then submit to the agents.</span>
</div>
</sc-if>
</section>
'''
i = s.find("<main")
j = s.find(">", i) + 1
k = s.find("</div>\n</div>", j)  # end of page header block
k = s.find("\n", s.find("</div>\n\n", j) + 1)
s = s[:k] + "\n" + UP + s[k:]
s = re.sub(r'class Component extends DCLogic \{.*?\n\}\n', '''class Component extends DCLogic {
  renderVals() {
    return { hasUpload: !!(this.state && this.state.file), fileName: (this.state && this.state.file) || '',
      onUpload: (e) => { const f = e.target.files && e.target.files[0]; if (f) this.setState({ file: f.name }); } };
  }
}
''', s, count=1, flags=re.S)
open(f, "w").write(s)

for name in ["Main.dc.html", "Steward.dc.html", "Lifecycle.dc.html"]:
    p = os.path.join(ART, name)
    open(p, "w").write(replace_nav(open(p).read(), name))

c = json.load(open(os.path.join(ART, "canvas.json")))
c["boards"]["Records.dc.html"] = {"expand": "fill", "h": 1700, "is_interactive": True, "title": "9 · Business ready records", "w": 1440, "x": 6080, "y": 2360}
c["boards"]["Policy.dc.html"]["h"] = 2100
if "Records.dc.html" not in c["order"]:
    c["order"].append("Records.dc.html")
c["notes"]["row1"]["text"] = "Onboarding: from request to Business ready record"
json.dump(c, open(os.path.join(ART, "canvas.json"), "w"), indent=2)
print("patched")
