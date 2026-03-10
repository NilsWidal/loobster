# Research: Transform RePPIT Health into a Lovable-like Healthcare App Builder

## High-Level Summary

RePPIT Health is currently a VS Code/Cursor sidebar extension that wraps the Claude CLI as a child process, communicating via structured HTML comment markers in stream-json output. It implements the RePPITS workflow (Research → Propose → Plan → Implement → Test → Secure) with gate-based approvals, compliance checklists (HIPAA/SOC2/HITRUST), and optional Linear integration. The UI is a simple webview sidebar with a phase stepper, monospace text log, gate buttons, and an input bar.

Lovable is a web-based AI app builder that uses Claude to generate complete React applications from natural language, featuring real-time streaming code generation, live preview via Vite HMR, a split-pane chat+preview UI, and one-click deployment. It uses React + TypeScript + Tailwind + shadcn/ui + Supabase.

The shift from "VS Code extension wrapping CLI" to "web-based AI healthcare app builder" requires a fundamental platform change: new web architecture, direct Claude SDK integration (replacing CLI spawning), in-browser code rendering, and a healthcare-specific component library.

## Detailed Findings

### A. Current Architecture (RePPIT Health)

**10 source files in `src/`:**

| File | Purpose | Lines |
|------|---------|-------|
| `extension.ts` | VS Code extension entry point, registers commands/sidebar | 139 |
| `claude/cli.ts` | Spawns Claude CLI as child process, parses stdout stream-json | 144 |
| `claude/parser.ts` | Parses HTML comment markers + stream-json events from CLI output | 165 |
| `claude/types.ts` | Event types: phase, gate, secure, log, error, done | 57 |
| `engine/workflow.ts` | State machine orchestrating phases, gates, CLI interaction | 175 |
| `engine/types.ts` | WorkflowState, GateResponse, GateAction types | 47 |
| `sidebar/SidebarProvider.ts` | VS Code webview with inline HTML/CSS/JS (~530 lines of inline UI) | 638 |
| `linear/detector.ts` | Detects Linear MCP availability via `claude mcp list` | 25 |
| `templates/scaffold.ts` | Copies `.claude/commands/` + compliance templates to target project | 51 |
| `notifications/sound.ts` | Plays system sounds at gates (macOS/Windows/Linux) | 27 |

**Key architectural patterns:**
- `ClaudeCli` (`src/claude/cli.ts:7-144`) — spawns Claude CLI with `--output-format stream-json`, strips nested session env vars, buffers stdout line-by-line
- `OutputParser` (`src/claude/parser.ts:11-165`) — dual parser: JSON stream events (`assistant`, `result`, `system`) + legacy HTML comment markers (`<!-- PHASE:research -->`, `<!-- GATE:... -->`, `<!-- SECURE_ITEM:... -->`)
- `WorkflowEngine` (`src/engine/workflow.ts:11-175`) — orchestrates phases via event handling, resolves gate promises, manages compliance state
- `SidebarProvider` (`src/sidebar/SidebarProvider.ts:4-638`) — monolithic inline webview with ~300 lines of CSS + ~280 lines of JS, no framework

**Templates (scaffolded into target projects):**
- `templates/commands/reppit.md` — Master workflow template with HTML comment markers
- `templates/commands/{research-codebase,make-proposals,make-plan,implement,review-code,secure}.md` — Phase-specific prompts
- `templates/compliance/{hipaa,soc2,hitrust}-checklist.md` — Security checklists
- `templates/design_doc_template.md` — Design document template

**Dependencies:** VS Code extension APIs, esbuild, eslint, vitest. No web framework, no React, no Anthropic SDK.

### B. Lovable Platform (Reference Implementation)

**Core Experience:**
- Conversational: describe in plain English → see app built in real-time
- Split-pane UI: chat on left, live preview on right, code editor accessible
- Multiple modes: Agent (autonomous), Edit (targeted), Chat (planning only)
- Streaming code generation with Vite hot-reload for instant preview updates

**Tech Stack:**
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui + Radix UI
- Supabase (auth, DB, real-time, file storage)
- GitHub integration (bidirectional sync)
- One-click publish to CDN

**Key UX Patterns:**
- Code streams in real-time as AI generates it
- Preview updates incrementally via Vite HMR
- Design system integration ensures consistent output
- Full code ownership — export and deploy anywhere

### C. Claude SDK Options — AWS Bedrock Constraint

**CRITICAL FINDING: The Claude Agent SDK cannot run in containerized environments (EKS/K8s).**

A peer investigation revealed that `@anthropic-ai/claude-agent-sdk`'s `query()` function spawns a Claude CLI subprocess (bundles `cli.js`). This subprocess:
1. Needs `ANTHROPIC_API_KEY` in env vars — doesn't work with AWS Bedrock/IAM roles
2. Needs a writable filesystem (`~/.claude/`, temp dirs) — fails on read-only Alpine containers
3. Doesn't reliably support Bedrock — reported hangs after initial messages

**This rules out the Agent SDK for our deployment target (AWS EKS on Kubernetes).**

**Recommended: `@anthropic-ai/bedrock-sdk` + Custom Tool Loop**

The Bedrock SDK is the official TypeScript package for Claude via AWS Bedrock:
- Full streaming support via async iterables
- Complete tool use / function calling support
- Uses AWS default credential chain (IRSA in EKS — no API keys)
- Runs in any container environment (no filesystem requirements)
- Identical Messages API to the standard Anthropic SDK

**Authentication in EKS:**
- IRSA (IAM Roles for Service Accounts) — EKS webhook auto-injects credentials
- No API keys needed — uses IAM roles
- Required IAM actions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`

**Custom Tool Loop Pattern (replaces Agent SDK):**
```typescript
import AnthropicBedrock from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({ awsRegion: "us-east-1" });

let response = await client.messages.create({
  model: "us.anthropic.claude-sonnet-4-6",
  max_tokens: 4096,
  tools: healthcareTools,
  messages: [{ role: "user", content: prompt }],
});

while (response.stop_reason === "tool_use") {
  const toolResults = await executeTools(response.content);
  response = await client.messages.create({
    messages: [...prev, { role: "assistant", content: response.content },
      { role: "user", content: toolResults }],
  });
}
```

**Why NOT other options:**
- `@anthropic-ai/sdk` — Requires `ANTHROPIC_API_KEY`, no Bedrock/IAM support
- `@anthropic-ai/claude-agent-sdk` — Spawns CLI subprocess, needs writable FS, unreliable on Bedrock
- LiteLLM / LangGraph — Viable alternatives but add dependency complexity

### D. Gap Analysis: Current vs Target

| Dimension | Current (VS Code Extension) | Target (Lovable-like Web App) |
|-----------|---------------------------|-------------------------------|
| Platform | VS Code/Cursor only | Web browser (any device) |
| AI integration | Claude CLI child process | Claude SDK (streaming API) |
| UI framework | Inline HTML/CSS/JS webview | React + Tailwind + shadcn/ui |
| Preview | None (text log only) | Live rendered preview (Vite/Sandpack) |
| Code editor | None (delegates to VS Code) | Monaco/CodeMirror in-browser |
| Code execution | Local filesystem via CLI | Sandboxed (WebContainers/Sandpack) |
| Components | None | Healthcare-specific library |
| Auth | None | Supabase/Auth.js |
| Deployment | Manual | One-click publish |
| Compliance | Template checklists | Automated HIPAA/SOC2 scanning |
| Project mgmt | Optional Linear MCP | Built-in + Linear integration |
| Collaboration | Single user | Multi-user workspaces |

### E. Healthcare-Specific Requirements

**Domain components needed:**
- Patient intake forms (demographics, insurance, consent)
- Vital signs displays and charting
- Medication lists with interaction checking
- Appointment scheduling widgets
- Clinical notes / SOAP note editors
- Lab results tables and trending
- FHIR resource viewers
- Role-based dashboards (clinician vs admin vs patient)

**Compliance built-in:**
- HIPAA: PHI handling, encryption, audit trails, access control, minimum necessary
- SOC2: Input validation, error handling, dependency security
- HITRUST: Session management, credential handling
- 21 CFR Part 11: Electronic signatures, audit trails (FDA-regulated)
- WCAG 2.1 AA/AAA: Clinical accessibility requirements

**Integration standards:**
- HL7 FHIR R4 APIs
- SMART on FHIR launch framework
- CDS Hooks (clinical decision support)
- ICD-10, SNOMED CT, LOINC terminologies

### F. Technology Stack for the Shift

**Frontend:**
- Next.js 15 (App Router) — SSR, API routes, middleware
- React 19 — Component-based UI
- Tailwind CSS v4 — Utility-first styling
- shadcn/ui — Base component library (customized for healthcare)
- Monaco Editor — In-browser code editing
- Sandpack (CodeSandbox) or WebContainers (StackBlitz) — In-browser preview
- Framer Motion — Smooth transitions and streaming animations

**Backend:**
- Next.js API Routes — Streaming SSE to frontend
- `@anthropic-ai/bedrock-sdk` — Claude via AWS Bedrock (IAM auth, no API keys)
- Custom tool loop — Agentic code generation with file/code tools
- Supabase or AWS RDS — Auth, PostgreSQL, real-time subscriptions, file storage

**Infrastructure:**
- AWS EKS (Kubernetes) — Container orchestration
- AWS Bedrock — Claude model access via IAM/IRSA
- ECR — Container registry
- Supabase or AWS managed services — Postgres, auth, storage
- GitHub API — Project sync + version control
- Linear API — Project management integration

### G. Code Storage Architecture (Best Practices)

**How the leaders do it:**

| Platform | Primary Storage | Persistence | Production Ready |
|----------|----------------|-------------|-----------------|
| **Lovable** | GitHub + Supabase | Persistent | Yes |
| **Bolt.new** | Browser IndexedDB | Ephemeral | No |
| **v0** | Vercel cloud | Persistent | UI only |
| **Replit** | Container disk + Git | Persistent | Yes |

**Recommended: Git + PostgreSQL + S3 (Hybrid)**

1. **Git (GitHub)** — All generated application code
   - One repo per project (or monorepo per tenant)
   - Version history, branching, rollback, audit trail
   - Bidirectional sync (like Lovable)
   - HIPAA: never store PHI in Git — code only

2. **PostgreSQL (RDS)** — Metadata, state, generation history
   - `projects` table: id, tenant_id, name, github_repo_url, status
   - `generations` table: id, project_id, prompt, model, status, timestamp
   - `deployments` table: id, project_id, image_uri (ECR), endpoint, status
   - JSONB for semi-structured config (don't store full source as JSONB)

3. **S3** — Artifacts, assets, large files
   - Uploaded images, fonts, media files
   - Build logs, deployment bundles
   - Server-side encryption (SSE-S3 or SSE-KMS)
   - Bucket-per-tenant with IAM policies

**Multi-tenant isolation:**
- PostgreSQL: `tenant_id` column (shared schema)
- GitHub: Separate org/team per tenant
- S3: Bucket-per-tenant with IAM policies
- EKS: Namespace-per-tenant with network policies

### H. Lovable UX Patterns (Complete Inventory)

**1. Onboarding:** 5-second signup → personalization survey → straight into chat builder. No "create project" modal — implicit in workflow.

**2. Chat Interface:** Split-screen (chat left, preview right). Message history with context awareness. Can edit past prompts to branch. Cross-project @ mentions. Shows which files are being edited.

**3. Code Editor (Visual Edits):** WYSIWYG Figma-like overlay on live preview. Click-to-edit UI elements. Custom Vite plugin assigns persistent IDs to JSX for DOM-to-code mapping. Client-side AST processing via Babel/SWC. Monaco Editor available for power users. Visual edits are FREE (no credit deduction).

**4. Live Preview:** Sandboxed iframe with Vite HMR. Interactive — users click through like end-users. Browser Testing agent can fill forms, click buttons, test responsive sizes. Captures screenshots + detects runtime errors. Instant updates (no manual refresh).

**5. File Explorer:** Implicit — no persistent file tree panel. Access via Design view. `.lovable/` directory for design system rules.

**6. Version History / Undo:** Bookmarks for stable versions. History grouped by date. Revert creates new edit cards (like git revert). Can preview older versions. Non-destructive — reverted changes stay in chat. Can revert + edit past message to branch.

**7. Component Library:** shadcn/ui as default design system. Tailwind CSS for styling. No manual installation — AI handles imports. Design system projects with rules in `.lovable/` directory.

**8. Deployment:** One-click publish to Lovable CDN. Custom domains on paid plans. Changes NOT auto-published (explicit Update action). Secrets management via Supabase Edge Functions. Progressive: public on free → workspace isolation on business.

**9. Collaboration:** 4 permission tiers: Viewer, Editor, Admin, Owner. Credit-pooling — owner's workspace covers all collaborators. Unlimited collaborators on all plans. Real-time co-editing.

**10. Error Handling:** "Try to Fix" button — AI scans logs + code diffs. Chat Mode (read-only analysis, no edits). Structured debugging: codebase audits → plan mode → targeted fixes. Known AI limitation: generates "happy path" code, misses edge cases.

**11. Asset Management:** Drag-and-drop image uploads. AI-powered image generation. Google Fonts (no custom font uploads). Supabase Storage for file uploads (50MB free tier). Video/audio embedding support.

**12. Database/Backend:** Supabase Integration 2.0. Full PostgreSQL + Auth + Storage + Real-time + Edge Functions. Chat-driven schema creation. Auto-wires UI to database tables. Row Level Security (RLS) required before launch.

### I. Preview Technology: Sandpack vs WebContainers

| Aspect | Sandpack | WebContainers |
|--------|----------|---------------|
| Architecture | Bundler/transpiler | Full Node.js in browser |
| Browser support | Broad (Safari, iOS, mobile) | Limited (no Safari) |
| Memory | Higher per thread | Lower, more efficient |
| Use case | Components, maximum compat | Full Node ecosystem |
| Licensing | Open source (Apache 2.0) | Proprietary |
| Setup | Minimal | Requires COOP/COEP headers |

**Recommendation: Sandpack** — broader compatibility, open source, sufficient for React preview.

### J. Reusable Assets from Current Codebase

**Can be adapted:**
- `templates/commands/*.md` — Workflow phase prompts (repurpose as system prompts)
- `templates/compliance/*.md` — Security checklists (integrate into automated scanning)
- `engine/types.ts` — WorkflowState, Phase, GateResponse types (adapt for web)
- `claude/types.ts` — Event type definitions (adapt for SDK events)
- RePPITS workflow logic — phase ordering, gate resolution, compliance loop

**Must be replaced:**
- `claude/cli.ts` — CLI spawning → SDK streaming
- `claude/parser.ts` — CLI output parsing → SDK event handling
- `sidebar/SidebarProvider.ts` — VS Code webview → React components
- `extension.ts` — VS Code extension entry → Next.js app
- `linear/detector.ts` — CLI-based detection → Direct API integration
- `notifications/sound.ts` — OS-level sounds → Web Audio API / browser notifications
