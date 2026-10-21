"""`GET /docs`: an offline page to try the API in a browser (ADR-0008; contracts/C3-api.md).

FastAPI's Swagger UI and ReDoc pages load assets from a CDN (guardrail G3), so this page is one
self-contained document: it reads the OpenAPI document from this server, shows every operation
with a small form, and sends the request to this server. Its Content-Security-Policy allows no
other origin. The page is not part of the OpenAPI document.
"""

import base64
import hashlib
from typing import Final

from neonradar_contracts.api import API_PREFIX

STYLE: Final = """
body{font:15px/1.45 system-ui,sans-serif;margin:0;padding-block:1rem;padding-inline:1rem;
color:#1b1b1f;background:#fafafa}
main{max-inline-size:60rem;margin-inline:auto}
section{border:1px solid #d0d0d7;border-radius:6px;padding:.75rem;margin-block:.75rem;
background:#fff}
h2{font-size:1rem;margin:0;font-family:ui-monospace,monospace}
label{display:inline-block;margin-inline-end:.75rem;margin-block:.25rem}
input,textarea{font:inherit;margin-inline-start:.25rem}
pre{background:#f1f1f4;padding:.5rem;overflow:auto;max-block-size:30rem}
"""
SCRIPT: Final = """
const main = document.querySelector('main');
const add = (parent, tag, text) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  parent.append(el);
  return el;
};
async function send(form, method, path, pre) {
  let url = path;
  const query = new URLSearchParams();
  for (const input of form.querySelectorAll('input')) {
    if (!input.value) continue;
    if (input.dataset.in === 'path') {
      url = url.replace('{' + input.name + '}', encodeURIComponent(input.value));
    } else if (input.dataset.many === 'true') {
      for (const value of input.value.split(',')) query.append(input.name, value.trim());
    } else query.append(input.name, input.value);
  }
  const init = {method: method.toUpperCase()};
  const body = form.querySelector('textarea');
  if (body) {
    init.headers = {'content-type': 'application/json'};
    init.body = body.value;
  }
  const response = await fetch(url + (query.size ? '?' + query : ''), init);
  const text = await response.text();
  let shown = text;
  try { shown = JSON.stringify(JSON.parse(text), null, 2); } catch {}
  pre.textContent = response.status + ' ' + response.statusText + '\\n' + shown;
}
fetch('OPENAPI').then((r) => r.json()).then((doc) => {
  add(main, 'p', doc.info.description);
  for (const [path, item] of Object.entries(doc.paths)) {
    for (const [method, op] of Object.entries(item)) {
      const section = add(main, 'section');
      add(section, 'h2', method.toUpperCase() + ' ' + path);
      add(section, 'p', op.description || op.summary || '');
      const form = add(section, 'form');
      for (const param of op.parameters || []) {
        const label = add(form, 'label', param.name + (param.required ? ' (required)' : ''));
        const input = add(label, 'input');
        input.name = param.name;
        input.dataset.in = param.in;
        input.dataset.many = String(JSON.stringify(param.schema).includes('"array"'));
        const fallback = param.schema && param.schema.default;
        if (fallback !== undefined && fallback !== null) input.placeholder = String(fallback);
      }
      if (op.requestBody) add(form, 'textarea').value = '{"question": ""}';
      add(form, 'button', 'Send');
      const pre = add(section, 'pre');
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        send(form, method, path, pre).catch((error) => { pre.textContent = String(error); });
      });
    }
  }
});
""".replace("OPENAPI", f"{API_PREFIX}/openapi.json")


def _sha256(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


PAGE: Final = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NeonRadar API</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>NeonRadar API v1</h1>
<p>Read-only, served from this machine. Repeatable parameters take comma-separated values.
The <a href="{API_PREFIX}/openapi.json">OpenAPI document</a> describes every response.</p>
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""
# Only this page's own style and script, and requests to this server.
CONTENT_SECURITY_POLICY: Final = "; ".join(
    [
        "default-src 'none'",
        f"style-src {_sha256(STYLE)}",
        f"script-src {_sha256(SCRIPT)}",
        "connect-src 'self'",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
    ]
)
