# Loobster docs site

A self-contained static docs site (`index.html`) — no build step, no dependencies. Open it locally or deploy it to Vercel for a shared team URL.

## Local
```
open docs/index.html
```

## Deploy to Vercel (gives a URL)
**Option A — CLI:**
```
npm i -g vercel    # if needed
cd site
vercel             # follow prompts → preview URL
vercel --prod      # production URL
```

**Option B — Git integration:** import `NilsWidal/loobster` in the Vercel dashboard and set:
- **Root Directory:** `docs`
- **Framework Preset:** Other
- **Build Command:** (none) · **Output Directory:** (leave default)

`vercel.json` here enables clean URLs. To use a custom domain (e.g. `loobster.dev`), add it in the Vercel project's Domains tab.

## Editing
It's one HTML file with inline CSS. Edit `index.html` and redeploy. If you outgrow a single page, this drops cleanly into Nextra or Docusaurus later — the content sections map 1:1 to docs pages.
