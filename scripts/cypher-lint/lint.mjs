#!/usr/bin/env node
// Lint every .cypher file under the given folders with Neo4j's Cypher language support,
// applying Cypher 5 rules. Errors and warnings fail; "Parameter $x is not defined" is
// ignored because parameters are bound at run time. A template declares its placeholder
// values in a header comment, for example: // lint-values: max_hops=1,2,8 rel_type=OWNS
// and uses them as {{max_hops}}; every combination is linted.
import { lintCypherQuery } from '@neo4j-cypher/language-support';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const roots = process.argv.length > 2 ? process.argv.slice(2) : ['graph', 'detect', 'api'];
const IGNORED = [/^Parameter \$[A-Za-z_][A-Za-z0-9_]* is not defined\.?$/];

function* cypherFiles(dir) {
  let entries;
  try { entries = readdirSync(dir); } catch { return; }
  for (const name of entries) {
    if (name === 'node_modules' || name.startsWith('.')) continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* cypherFiles(path);
    else if (name.endsWith('.cypher')) yield path;
  }
}

function statements(text) {
  const out = [];
  let lines = [];
  let start = 0;
  text.split('\n').forEach((line, index) => {
    if (lines.length === 0) {
      if (/^\s*(\/\/.*)?$/.test(line)) return;
      start = index + 1;
    }
    lines.push(line);
    if (/;\s*$/.test(line)) {
      out.push({ start, text: lines.join('\n').replace(/;\s*$/, '') });
      lines = [];
    }
  });
  if (lines.join('').trim()) out.push({ start, text: lines.join('\n') });
  return out;
}

function variants(text) {
  const header = text.match(/^\s*\/\/\s*lint-values:\s*(.+)$/m);
  if (!header) return [text];
  let combos = [{}];
  for (const pair of header[1].trim().split(/\s+/)) {
    const [key, values] = pair.split('=');
    combos = combos.flatMap((c) => values.split(',').map((v) => ({ ...c, [key]: v })));
  }
  return combos.map((c) => text.replace(/\{\{(\w+)\}\}/g, (_, k) => (k in c ? c[k] : `{{${k}}}`)));
}

let failures = 0;
let checked = 0;
for (const root of roots) {
  for (const file of cypherFiles(root)) {
    for (const variant of variants(readFileSync(file, 'utf8'))) {
      for (const { start, text } of statements(variant)) {
        checked += 1;
        const { diagnostics } = lintCypherQuery(`CYPHER 5 ${text}`, {});
        for (const d of diagnostics) {
          if (d.severity > 2 || IGNORED.some((re) => re.test(d.message))) continue;
          failures += 1;
          console.log(`${file}:${start + d.range.start.line}: ${d.severity === 1 ? 'error' : 'warning'}: ${d.message}`);
        }
        if (/\{\{\w+\}\}/.test(text)) {
          failures += 1;
          console.log(`${file}:${start}: error: placeholder without a lint-values entry`);
        }
      }
    }
  }
}
console.log(`cypher-lint: ${checked} statements checked, ${failures} problems`);
process.exit(failures ? 1 : 0);
