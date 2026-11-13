const fs = require('fs');
class DCLogic { constructor(p){ this.props = p || {}; this.state = {}; } setState(s){ this.state = Object.assign({}, this.state, s); } }
for (const f of process.argv.slice(2)) {
  const html = fs.readFileSync(f, 'utf8');
  const m = html.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/);
  try {
    const C = new Function('DCLogic', m[1] + '\nreturn Component;')(DCLogic);
    const c = new C({}); if (!c.state) c.state = {};
    let v = c.renderVals();
    // exercise handlers
    for (const k of Object.keys(v)) if (typeof v[k] === 'function' && /^(more|pick|expandAll|collapse|startEdit|less)$/.test(k)) { try { v[k]({target:{value:'x', files:[{name:'a.eml'}]}}); } catch(e){} }
    ['tabs','stages','rows','items','folders','list'].forEach(k => { if (Array.isArray(v[k]) && v[k][1]) { const it = v[k][1]; (it.pick||it.open||it.toggle) && (it.pick||it.open||it.toggle)(); } });
    if (v.groups && v.groups[2]) v.groups[2].agents[0].pick();
    v = c.renderVals();
    // holes used in template must exist
    const tpl = html.slice(html.indexOf('<x-dc>'), html.indexOf('</x-dc>'));
    const holes = [...tpl.matchAll(/\{\{\s*([A-Za-z_$][\w$]*)/g)].map(x => x[1]);
    const loopVars = new Set([...tpl.matchAll(/as="(\w+)"/g)].map(x => x[1]).concat(['true','false','$index']));
    const missing = [...new Set(holes.filter(h => !loopVars.has(h) && !(h in v)))];
    console.log(f, 'ok', missing.length ? 'MISSING: ' + missing.join(',') : '');
  } catch (e) { console.log(f, 'ERROR', e.message); }
}
