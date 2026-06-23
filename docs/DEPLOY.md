# Loobster docs site

A self-contained static docs site (`index.html`) — no build step, no dependencies. Open it locally, or deploy it to **GitHub Pages** (default) or Vercel for a shared team URL.

## Local
```
open docs/index.html
```

## Deploy to GitHub Pages (default)
The repo ships `.github/workflows/pages.yml`, which publishes `docs/` to GitHub Pages on every push to `main`. Enable it once:

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. Push to `main` (or re-run the workflow from the Actions tab). The site goes live at `https://<owner>.github.io/loobster/`.

There's no build step — the workflow uploads `docs/` as-is.

## Deploy to Vercel (alternative)
**Option A — CLI:**
```
npm i -g vercel    # if needed
cd docs
vercel             # follow prompts → preview URL
vercel --prod      # production URL
```

**Option B — Git integration:** import `NilsWidal/loobster` in the Vercel dashboard and set:
- **Root Directory:** `docs`
- **Framework Preset:** Other
- **Build Command:** (none) · **Output Directory:** (leave default)

`docs/vercel.json` enables clean URLs for the Vercel path.

## Editing
It's one HTML file with inline CSS. Edit `index.html` and redeploy. If you outgrow a single page, this drops cleanly into Nextra or Docusaurus later — the content sections map 1:1 to docs pages.
