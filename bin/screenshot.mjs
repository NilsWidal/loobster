#!/usr/bin/env node
// Verifiable frontend layer — capture screenshots of changed UI with Playwright.
// Used by the RePPITS Test phase / goal-loop and by templates/playwright-verify.yml.
//
//   node bin/screenshot.mjs --base http://localhost:3000 --paths / /login /dashboard
//   node bin/screenshot.mjs --config .reppit/screens.json
//
// Requires Playwright in the target repo:  npm i -D playwright  &&  npx playwright install chromium
// Writes PNGs to .reppit/screens/ (override with --out). Exits non-zero if a page errors,
// so the loop/PR check can BLOCK on a broken frontend.

import { mkdirSync, existsSync, readFileSync } from 'node:fs';
import { chromium } from 'playwright';

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i === -1) return def;
  // collect following tokens until the next --flag
  const vals = [];
  for (let j = i + 1; j < process.argv.length && !process.argv[j].startsWith('--'); j++) vals.push(process.argv[j]);
  return vals.length <= 1 ? (vals[0] ?? true) : vals;
}

const out = arg('out', '.reppit/screens');
const base = arg('base', process.env.BASE_URL || 'http://localhost:3000');
const configPath = arg('config', null);

let views;
if (configPath && existsSync(configPath)) {
  const cfg = JSON.parse(readFileSync(configPath, 'utf8'));
  views = cfg.views; // [{ name, path }]
} else {
  const paths = [].concat(arg('paths', ['/']));
  views = paths.map((p) => ({ name: (p.replace(/[^\w-]+/g, '_') || 'home').replace(/^_|_$/g, '') || 'home', path: p }));
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
