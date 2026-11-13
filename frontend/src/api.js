async function call(method, path, body, isForm) {
  const opt = { method, headers: {} };
  if (body !== undefined) {
    if (isForm) opt.body = body;
    else { opt.body = JSON.stringify(body); opt.headers['Content-Type'] = 'application/json'; }
  }
  const r = await fetch('/api' + path, opt);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Request failed (${r.status})`);
  return data;
}

export const api = {
  get: (p) => call('GET', p),
  post: (p, b) => call('POST', p, b ?? {}),
  put: (p, b) => call('PUT', p, b),
  patch: (p, b) => call('PATCH', p, b),
  upload: (p, files, field = 'files') => {
    const fd = new FormData();
    for (const f of files) fd.append(field, f);
    return call('POST', p, fd, true);
  },
};

let policyCache = null;
export async function policyMap() {
  if (!policyCache) {
    const d = await api.get('/policies');
    policyCache = {};
    d.policies.forEach((p) => { policyCache[p.id] = p; });
  }
  return policyCache;
}
export function clearPolicyCache() { policyCache = null; }

export const go = (path) => { window.location.hash = '#/' + path; };
