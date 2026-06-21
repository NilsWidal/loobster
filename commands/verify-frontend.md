Verifiable frontend layer: when a change touches the UI, **prove it renders** with Playwright screenshots and attach them to the PR. This is the visual half of the Test phase — "tests pass" is not enough for frontend work.

## When this runs
During Phase 5 (Test) of `/reppit`, inside the goal-loop's verify step, or standalone. Trigger it when the diff touches frontend: files matching `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.html`, `*.css`, `*.scss`, or component/route directories. If the diff is backend-only, skip (note "no frontend changes").

## Steps
1. **Find the affected views.** From the changed files, infer the routes/pages to capture (e.g. an edited `app/dashboard/page.tsx` → `/dashboard`). Default to `/` if routes can't be inferred. Keep the list small and relevant (token-discipline).
2. **Run the app.** Start the dev server (use the project's `run`/`dev` command, or a project skill if one exists). Wait until it serves.
3. **Capture.** Run the bundled Playwright script against the affected routes at desktop + mobile viewports:
   ```bash
   node ${CLAUDE_PLUGIN_ROOT}/bin/screenshot.mjs --base http://localhost:3000 --paths / /dashboard /login
   ```
   It writes PNGs to `.reppit/screens/` and **exits non-zero if a page 4xx/5xx's or logs console/page errors** — so a broken frontend BLOCKS the verify step (a real gate, not just pretty pictures). Requires `npm i -D playwright && npx playwright install chromium` in the target repo.
4. **Attach to the PR — GitHub-native, no other accounts.** Two ways:
   - **CI artifacts (default, zero repo clutter):** the `templates/playwright-verify.yml` workflow runs this on the PR and `upload-artifact`s `.reppit/screens/` — downloadable from the PR's **Checks** tab. It also posts a sticky PR comment with the result table + artifact link.
   - **Inline images:** commit `.reppit/screens/*.png` to the PR branch and embed them in a PR comment via `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/.reppit/screens/<file>.png`. Same repo, no external host. (Clean the dir on merge, or keep it on the branch only.)
5. **Report.** Summarize: which views were captured, any failures (HTTP/console errors), and the attachment location. A failure is a **FAIL** for the Test/Secure gate.

## Independent verification
Per the "Never self-verify" rule in `reppit.md`, the agent that wrote the frontend does **not** judge its own screenshots. Either (a) the CI workflow runs this — CI is inherently independent — or (b) spawn a **separate verifier subagent**, hand it the captured PNGs + what the change was supposed to do, and let it report whether the UI is correct. The implementer captures; an independent judge assesses.

## Notes
- `.reppit/screens/` should be gitignored unless you intentionally commit images for the inline-attach path.
- This is a *verification* layer — it does not modify the app. It renders the real UI and proves the change works.
- For the goal-loop, a frontend signal/finding can be backed by a screenshot the whole team sees on the PR.
