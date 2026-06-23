#!/usr/bin/env node
// Verifiable frontend layer — capture screenshots of changed UI with Playwright.
// Used by the RePPITS Test phase / goal-loop and by templates/playwright-verify.yml.
//
//   node bin/screenshot.mjs --base http://localhost:3000 --paths / /login /dashboard
//   node bin/screenshot.mjs --config .loobster/screens.json
//   node bin/screenshot.mjs --help
//
// Requires Playwright in the target repo:  npm i -D playwright  &&  npx playwright install chromium
// Writes PNGs to .loobster/screens/ (override with --out). Exits non-zero if a page errors,
// so the loop/PR check can BLOCK on a broken frontend.

import { mkdirSync, existsSync, readFileSync } from 'node:fs';

function usage() {
  console.log(`screenshot.mjs — capture UI screenshots with Playwright

Usage:
  node bin/screenshot.mjs --base <url> --paths <p1> [p2 ...]   capture the given routes
  node bin/screenshot.mjs --config <file.json>                 capture views from a config
  node bin/screenshot.mjs --help

Options:
  --base <url>     base URL (default: $BASE_URL or http://localhost:3000)
  --paths <p...>   one or more route paths to capture (default: /)
  --config <file>  JSON with { "views": [{ "name", "path" }] }
  --out <dir>      output directory (default: .loobster/screens)

Requires: npm i -D playwright && npx playwright install chromium`);
}

if (process.argv.includes('--help') || process.argv.includes('-h')) {
  usage();
  process.exit(0);
}

// Returns the value tokens following --name (an array; empty if the flag is present
// with no value), or undefined if the flag is absent. Never coerces to boolean.
function argTokens(name) {
  const i = process.argv.indexOf('--' + name);
  if (i === -1) return undefined;
  const vals = [];
  for (let j = i + 1; j < process.argv.length && !process.argv[j].startsWith('--'); j++) vals.push(process.argv[j]);
  return vals;
}

function strArg(name, def) {
  const v = argTokens(name);
  if (v === undefined) return def;
  if (v.length === 0) { console.error(`error: --${name} requires a value`); usage(); process.exit(2); }
  return v[0];
}

function listArg(name, def) {
  const v = argTokens(name);
  if (v === undefined) return def;
  if (v.length === 0) { console.error(`error: --${name} requires at least one value`); usage(); process.exit(2); }
  return v;
}

const out = strArg('out', '.loobster/screens');
const base = strArg('base', process.env.BASE_URL || 'http://localhost:3000');
const configPath = strArg('config', null);

let views;
if (configPath && existsSync(configPath)) {
  const cfg = JSON.parse(readFileSync(configPath, 'utf8'));
  views = cfg.views; // [{ name, path }]
} else {
  const paths = listArg('paths', ['/']);
  views = paths.map((p) => ({ name: (p.replace(/[^\w-]+/g, '_') || 'home').replace(/^_|_$/g, '') || 'home', path: p }));
}

// Import Playwright lazily so --help and arg errors work without it installed.
let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  console.error('error: Playwright is not installed. Run:\n  npm i -D playwright && npx playwright install chromium');
  process.exit(2);
}

const viewports = [
  { tag: 'desktop', width: 1280, height: 800 },
  { tag: 'mobile', width: 390, height: 844 },
];

mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
let failures = 0;
const written = [];

for (const vp of viewports) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));

  for (const v of views) {
    const url = base.replace(/\/$/, '') + v.path;
    const file = `${out}/${v.name}-${vp.tag}.png`;
    try {
      const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.screenshot({ path: file, fullPage: true });
      const status = resp ? resp.status() : 0;
      const bad = !resp || status >= 400 || errors.length;
      if (bad) failures++;
      written.push({ file, url, vp: vp.tag, status, errors: errors.slice() });
      console.log(`${bad ? 'FAIL' : 'ok  '} ${vp.tag} ${v.path} -> ${file} (HTTP ${status}${errors.length ? `, ${errors.length} console/page errors` : ''})`);
      errors.length = 0;
    } catch (e) {
      failures++;
      console.log(`FAIL ${vp.tag} ${v.path} -> ${url}: ${e.message}`);
    }
  }
  await ctx.close();
}
await browser.close();

console.log(`\n${written.length} screenshot(s) in ${out}/ · ${failures} failure(s)`);
process.exit(failures ? 1 : 0);
