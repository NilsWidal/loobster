import * as vscode from 'vscode';
import { WorkflowState } from '../engine/types';

export class SidebarProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly log: vscode.LogOutputChannel
  ) {}

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.log.info('resolveWebviewView called');
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtml(webviewView.webview);

    // Handle messages from webview
    webviewView.webview.onDidReceiveMessage(async (message) => {
      this.log.info(`Webview message received: ${JSON.stringify(message)}`);
      try {
        switch (message.type) {
          case 'gate-response':
            await vscode.commands.executeCommand(
              'reppithealth.gateResponse',
              message.payload
            );
            break;
          case 'start': {
            const input = message.payload?.input;
            this.log.info(`Start command: input="${input}"`);
            if (!input) {
              this.log.warn('Start command received with empty input, ignoring');
              // Send a state reset so the button doesn't stay stuck
              webviewView.webview.postMessage({
                type: 'debug',
                text: 'No input received by extension',
              });
              break;
            }
            await vscode.commands.executeCommand('reppithealth.start', input);
            break;
          }
          case 'stop':
            await vscode.commands.executeCommand('reppithealth.stop');
            break;
          case 'toggle-trace': {
            const config = vscode.workspace.getConfiguration('reppithealth');
            const current = config.get<boolean>('claudeTrace', false);
            await config.update('claudeTrace', !current, vscode.ConfigurationTarget.Global);
            this.log.info(`Claude trace toggled to ${!current}`);
            // Send current value back to webview
            webviewView.webview.postMessage({
              type: 'trace-updated',
              enabled: !current,
            });
            break;
          }
        }
      } catch (err) {
        this.log.error(`Error handling webview message: ${err}`);
        // CRITICAL: Send error back to webview so button doesn't get stuck
        webviewView.webview.postMessage({
          type: 'debug',
          text: `Extension error: ${err}`,
        });
      }
    });

    webviewView.onDidDispose(() => {
      this.log.info('Webview view disposed — clearing view reference');
      this.view = undefined;
    });

    this.log.info('resolveWebviewView complete');
  }

  updateState(state: WorkflowState): void {
    if (!this.view) {
      this.log.warn('updateState called but view is undefined');
      return;
    }
    this.view.webview.postMessage({ type: 'state-update', state });
  }

  private getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
      text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
  }

  private getHtml(webview: vscode.Webview): string {
    const nonce = this.getNonce();

    return /* html */ `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';" />
        <title>RePPIT Health</title>
        <style>
          * { box-sizing: border-box; }
          body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            padding: 0;
            margin: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
          }

          /* --- Phase stepper (compact horizontal) --- */
          .stepper {
            display: flex;
            align-items: center;
            padding: 10px 12px;
            gap: 2px;
            border-bottom: 1px solid var(--vscode-panel-border);
            flex-shrink: 0;
          }
          .step {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 10px;
            opacity: 0.4;
            white-space: nowrap;
          }
          .step.active { opacity: 1; font-weight: bold; }
          .step.completed { opacity: 0.7; }
          .step-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            border: 1.5px solid var(--vscode-foreground);
            flex-shrink: 0;
          }
          .step.active .step-dot {
            background: var(--vscode-charts-blue);
            border-color: var(--vscode-charts-blue);
            box-shadow: 0 0 6px var(--vscode-charts-blue);
          }
          .step.completed .step-dot {
            background: var(--vscode-charts-green);
            border-color: var(--vscode-charts-green);
          }
          .step-arrow {
            color: var(--vscode-descriptionForeground);
            font-size: 9px;
            margin: 0 1px;
            opacity: 0.4;
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
          .step.active .step-dot { animation: pulse 1.5s ease-in-out infinite; }

          /* --- Status bar --- */
          .status-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
            font-size: 10px;
            flex-shrink: 0;
          }
          .badges { display: flex; gap: 4px; flex-wrap: wrap; }
          .badge {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.3px;
          }
          .badge-pass { background: var(--vscode-charts-green); color: #fff; }
          .badge-warn { background: var(--vscode-charts-yellow); color: #000; }
          .badge-fail { background: var(--vscode-charts-red); color: #fff; }
          .badge-info { background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); }
          .badge-muted { background: var(--vscode-descriptionForeground); color: #fff; opacity: 0.6; }

          /* --- Output log --- */
          .output {
            flex: 1;
            overflow-y: auto;
            padding: 8px 12px;
            font-family: var(--vscode-editor-font-family, monospace);
            font-size: 12px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
          }
          .output .line { padding: 1px 0; }
          .output .line-error { color: var(--vscode-errorForeground); }
          .output .line-phase {
            color: var(--vscode-charts-blue);
            font-weight: bold;
            padding: 6px 0 2px;
          }
          .output .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            opacity: 0.5;
            text-align: center;
            font-family: var(--vscode-font-family);
          }
          .output .empty-state p { margin: 4px 0; font-size: 12px; }

          /* --- Gate prompt --- */
          .gate {
            padding: 10px 12px;
            border-top: 1px solid var(--vscode-charts-blue);
            background: var(--vscode-inputValidation-infoBackground);
            flex-shrink: 0;
          }
          .gate-text {
            font-size: 12px;
            margin: 0 0 8px;
            line-height: 1.4;
          }
          .gate-actions { display: flex; gap: 4px; flex-wrap: wrap; }

          /* --- Input bar --- */
          .input-bar {
            display: flex;
            gap: 4px;
            padding: 8px 12px;
            border-top: 1px solid var(--vscode-panel-border);
            flex-shrink: 0;
            background: var(--vscode-sideBar-background);
          }
          .input-bar input {
            flex: 1;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 3px;
            padding: 6px 8px;
            font-family: var(--vscode-font-family);
            font-size: 12px;
            outline: none;
          }
          .input-bar input:focus {
            border-color: var(--vscode-focusBorder);
          }
          .input-bar input::placeholder {
            color: var(--vscode-input-placeholderForeground);
          }

          /* --- Buttons --- */
          button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px;
            font-family: var(--vscode-font-family);
            white-space: nowrap;
          }
          button:hover { background: var(--vscode-button-hoverBackground); }
          button.secondary {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
          }
          button.secondary:hover { background: var(--vscode-button-secondaryHoverBackground); }
          button.stop {
            background: var(--vscode-errorForeground);
            color: #fff;
          }

          /* --- Trace toggle --- */
          .toolbar {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding: 4px 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
            flex-shrink: 0;
          }
          .trace-toggle {
            display: flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            font-size: 10px;
            opacity: 0.5;
            user-select: none;
          }
          .trace-toggle:hover { opacity: 0.8; }
          .trace-toggle.active { opacity: 1; color: var(--vscode-charts-yellow); }
          .trace-dot {
            width: 6px; height: 6px;
            border-radius: 50%;
            border: 1px solid currentColor;
          }
          .trace-toggle.active .trace-dot {
            background: var(--vscode-charts-yellow);
            border-color: var(--vscode-charts-yellow);
          }
          .output .line-trace {
            color: var(--vscode-descriptionForeground);
            font-size: 11px;
            opacity: 0.7;
          }

          /* --- Text vs tool line styling --- */
          .output .line-text {
            font-family: var(--vscode-font-family);
            font-size: 13px;
            line-height: 1.6;
            padding: 2px 0;
          }
          /* --- Markdown elements inside text lines --- */
          .output .line-text h2, .output .line-text h3, .output .line-text h4, .output .line-text h5 {
            margin: 10px 0 4px;
            line-height: 1.3;
          }
          .output .line-text h2 { font-size: 15px; }
          .output .line-text h3 { font-size: 14px; }
          .output .line-text h4 { font-size: 13px; }
          .output .line-text h5 { font-size: 12px; }
          .output .line-text table {
            border-collapse: collapse;
            margin: 6px 0;
            font-size: 11px;
            width: 100%;
          }
          .output .line-text th, .output .line-text td {
            border: 1px solid var(--vscode-panel-border);
            padding: 3px 8px;
            text-align: left;
          }
          .output .line-text th {
            background: var(--vscode-editor-background);
            font-weight: 600;
          }
          .output .line-text code {
            background: var(--vscode-editor-background);
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 11px;
            font-family: var(--vscode-editor-font-family, monospace);
          }
          .output .line-text pre {
            white-space: pre;
            word-break: normal;
          }
          .output .line-text pre code {
            padding: 0;
            background: none;
          }
          .output .line-text ul, .output .line-text ol {
            margin: 2px 0;
            padding-left: 20px;
          }
          .output .line-text li { margin: 1px 0; }
          .output .line-text hr {
            border: none;
            border-top: 1px solid var(--vscode-panel-border);
            margin: 8px 0;
          }
          .output .line-text p { margin: 2px 0; }
          .output .line-tool {
            color: var(--vscode-descriptionForeground);
            font-size: 11px;
            opacity: 0.55;
            padding-left: 8px;
            border-left: 2px solid var(--vscode-panel-border);
            margin: 1px 0;
          }
          .output .line-system {
            color: var(--vscode-descriptionForeground);
            font-size: 11px;
            opacity: 0.5;
          }

          /* --- Activity indicator --- */
          .activity-bar {
            height: 2px;
            background: var(--vscode-progressBar-background, var(--vscode-charts-blue));
            animation: activity-slide 1.5s ease-in-out infinite;
            flex-shrink: 0;
          }
          @keyframes activity-slide {
            0% { width: 0; margin-left: 0; }
            50% { width: 60%; margin-left: 20%; }
            100% { width: 0; margin-left: 100%; }
          }
        </style>
      </head>
      <body>
        <div id="stepper" class="stepper" style="display:none;"></div>
        <div class="toolbar">
          <label id="trace-toggle" class="trace-toggle" title="Enable Claude CLI verbose tracing">
            <span class="trace-dot"></span>
            <span>Trace</span>
          </label>
        </div>
        <div id="status-bar" class="status-bar" style="display:none;"></div>
        <div id="activity" class="activity-bar" style="display:none;"></div>
        <div id="output" class="output">
          <div class="empty-state">
            <p><strong>RePPIT Health</strong></p>
            <p>Enter a task below to start the workflow</p>
          </div>
        </div>
        <div id="gate" class="gate" style="display:none;"></div>
        <div id="input-bar" class="input-bar">
          <input id="user-input" type="text" placeholder="Describe a feature or paste an issue ID..." />
          <button id="send-btn">Start</button>
        </div>

        <script nonce="${nonce}">
          const vscode = acquireVsCodeApi();
          const phases = ['research', 'propose', 'plan', 'implement', 'test', 'secure', 'done'];
          const phaseLabels = {
            research: 'Research', propose: 'Propose', plan: 'Plan',
            implement: 'Implement', test: 'Test', secure: 'Secure', done: 'Done'
          };

          let state = null;
          let prevLogLength = 0;
          let startTimeout = null;

          const inputEl = document.getElementById('user-input');
          const sendBtn = document.getElementById('send-btn');
          const outputEl = document.getElementById('output');
          const stepperEl = document.getElementById('stepper');
          const statusBarEl = document.getElementById('status-bar');
          const activityEl = document.getElementById('activity');
          const gateEl = document.getElementById('gate');
          const traceToggleEl = document.getElementById('trace-toggle');
          let traceEnabled = false;

          inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          });

          traceToggleEl.addEventListener('click', () => {
            vscode.postMessage({ type: 'toggle-trace' });
          });

          sendBtn.addEventListener('click', () => {
            if (!state || !state.isRunning) {
              handleSend();
            } else {
              vscode.postMessage({ type: 'stop' });
            }
          });

          // Restore state if webview was hidden and re-created
          const savedState = vscode.getState();
          if (savedState && savedState.workflowState) {
            state = savedState.workflowState;
            render();
          }

          window.addEventListener('message', (event) => {
            const msg = event.data;
            if (msg.type === 'state-update') {
              state = msg.state;
              vscode.setState({ workflowState: state });
              if (startTimeout) { clearTimeout(startTimeout); startTimeout = null; }
              render();
            } else if (msg.type === 'trace-updated') {
              traceEnabled = msg.enabled;
              traceToggleEl.classList.toggle('active', traceEnabled);
            } else if (msg.type === 'debug') {
              console.log('Extension debug:', msg.text);
              sendBtn.disabled = false;
              sendBtn.textContent = 'Start';
            }
          });

          function handleSend() {
            const value = inputEl.value.trim();
            if (!value) {
              inputEl.style.borderColor = 'var(--vscode-inputValidation-errorBorder, red)';
              inputEl.placeholder = 'Please enter a description first...';
              setTimeout(() => {
                inputEl.style.borderColor = '';
                inputEl.placeholder = 'Describe a feature or paste an issue ID...';
              }, 2000);
              return;
            }

            // Gate active — send as refinement feedback
            if (state && state.gateActive) {
              vscode.postMessage({
                type: 'gate-response',
                payload: { action: 'refine', feedback: value }
              });
              inputEl.value = '';
              return;
            }

            // Workflow is running (no gate) — ignore input
            if (state && state.isRunning) {
              return;
            }

            // Not running — start a new workflow
            outputEl.innerHTML = '';
            prevLogLength = 0;
            sendBtn.textContent = 'Starting...';
            sendBtn.disabled = true;
            vscode.postMessage({ type: 'start', payload: { input: value } });
            inputEl.value = '';

            if (startTimeout) { clearTimeout(startTimeout); }
            startTimeout = setTimeout(() => {
              sendBtn.disabled = false;
              sendBtn.textContent = 'Start';
            }, 8000);
          }

          function sendGate(action, feedback, selection) {
            vscode.postMessage({ type: 'gate-response', payload: { action, feedback, selection } });
          }

          function classifyLine(line) {
            if (line.startsWith('[ERROR]')) return 'line line-error';
            if (line.startsWith('[trace]')) return 'line line-trace';
            if (line.startsWith('[warn]')) return 'line line-system';
            if (/^(\\u{1F527}|\\u{1F916}|🔧|🤖)/.test(line) || line.match(/^.\\uFE0F?\\u20E3? ?(Read|Edit|Write|Bash|Glob|Grep|Agent|WebFetch|WebSearch|ToolSearch|TodoWrite|Skill|NotebookEdit)/)) return 'line line-tool';
            if (line.startsWith('── Phase:')) return 'line line-phase';
            if (line === 'Connected') return 'line line-system';
            return 'line line-text';
          }

          // --- Lightweight Markdown renderer ---
          function escHtml(s) {
            return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
          }
          function inlineMd(s) {
            s = s.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
            s = s.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
            s = s.replace(/\`([^\`]+)\`/g, '<code>$1</code>');
            return s;
          }
          function renderMarkdown(raw) {
            const lines = raw.split('\\n');
            const out = [];
            let i = 0;
            while (i < lines.length) {
              const esc = escHtml(lines[i]);
              const t = esc.trim();
              if (!t) { i++; continue; }
              // Fenced code block (use hex \\x60 for backtick to avoid template literal issues)
              if (/^\\x60\\x60\\x60/.test(lines[i].trim())) {
                i++;
                const codeLines = [];
                while (i < lines.length && !/^\\x60\\x60\\x60/.test(lines[i].trim())) {
                  codeLines.push(escHtml(lines[i]));
                  i++;
                }
                if (i < lines.length) i++; // skip closing fence
                out.push('<pre style="background:var(--vscode-editor-background);padding:8px;border-radius:4px;overflow-x:auto;font-size:11px;margin:6px 0;"><code>' + codeLines.join('\\n') + '</code></pre>');
                continue;
              }
              // Horizontal rule
              if (/^-{3,}$/.test(t)) { out.push('<hr>'); i++; continue; }
              // Headers
              const hm = t.match(/^(#{1,4})\\s+(.+)$/);
              if (hm) {
                const lvl = Math.min(hm[1].length + 1, 6);
                out.push('<h'+lvl+'>'+inlineMd(hm[2])+'</h'+lvl+'>');
                i++; continue;
              }
              // Table block
              if (t.startsWith('|') && t.endsWith('|')) {
                let tbl = '<table>';
                let first = true;
                while (i < lines.length) {
                  const row = escHtml(lines[i]).trim();
                  if (!row.startsWith('|') || !row.endsWith('|')) break;
                  if (/^\\|[\\s\\-:|]+\\|$/.test(row)) { i++; continue; }
                  const cells = row.split('|').slice(1,-1);
                  const tag = first ? 'th' : 'td';
                  tbl += '<tr>'+cells.map(c=>'<'+tag+'>'+inlineMd(c.trim())+'</'+tag+'>').join('')+'</tr>';
                  first = false; i++;
                }
                tbl += '</table>';
                out.push(tbl); continue;
              }
              // Unordered list block
              if (/^[-*]\\s+/.test(t)) {
                let ul = '<ul>';
                while (i < lines.length) {
                  const ll = escHtml(lines[i]).trim();
                  const m = ll.match(/^[-*]\\s+(.+)$/);
                  if (!m) break;
                  ul += '<li>'+inlineMd(m[1])+'</li>'; i++;
                }
                ul += '</ul>'; out.push(ul); continue;
              }
              // Ordered list block
              if (/^\\d+\\.\\s+/.test(t)) {
                let ol = '<ol>';
                while (i < lines.length) {
                  const ll = escHtml(lines[i]).trim();
                  const m = ll.match(/^\\d+\\.\\s+(.+)$/);
                  if (!m) break;
                  ol += '<li>'+inlineMd(m[1])+'</li>'; i++;
                }
                ol += '</ol>'; out.push(ol); continue;
              }
              // Regular paragraph
              out.push('<p>'+inlineMd(t)+'</p>');
              i++;
            }
            return out.join('');
          }

          function render() {
            if (!state) return;

            if (state.claudeTrace !== undefined) {
              traceEnabled = state.claudeTrace;
              traceToggleEl.classList.toggle('active', traceEnabled);
            }

            // --- Activity indicator ---
            activityEl.style.display = state.isThinking ? 'block' : 'none';

            // --- Stepper ---
            if (state.isRunning || state.phase === 'done') {
              stepperEl.style.display = 'flex';
              const currentIdx = phases.indexOf(state.phase);
              stepperEl.innerHTML = phases.map((p, i) => {
                const cls = i < currentIdx ? 'completed' : i === currentIdx ? 'active' : '';
                const arrow = i < phases.length - 1 ? '<span class="step-arrow">&rsaquo;</span>' : '';
                return '<span class="step ' + cls + '"><span class="step-dot"></span>' + phaseLabels[p] + '</span>' + arrow;
              }).join('');
            } else {
              stepperEl.style.display = 'none';
            }

            // --- Status bar ---
            if (state.isRunning) {
              statusBarEl.style.display = 'flex';
              let left = '';
              let right = '';

              if (state.linearAvailable) {
                left += '<span class="badge badge-pass">Linear</span>';
              } else {
                left += '<span class="badge badge-muted">Local</span>';
              }

              const comp = state.security || {};
              Object.keys(comp).forEach(fw => {
                const items = comp[fw]?.items || [];
                const fails = items.filter(i => i.status === 'fail').length;
                const warns = items.filter(i => i.status === 'warn').length;
                const cls = fails > 0 ? 'badge-fail' : warns > 0 ? 'badge-warn' : 'badge-pass';
                const label = fails > 0 ? fails + ' fail' : warns > 0 ? warns + ' warn' : 'pass';
                left += '<span class="badge ' + cls + '">' + fw.toUpperCase() + ' ' + label + '</span>';
              });

              if (state.refinementCount > 0) {
                right += '<span class="badge badge-info">Refined ' + state.refinementCount + 'x</span>';
              }

              statusBarEl.innerHTML = '<div class="badges">' + left + '</div><div class="badges">' + right + '</div>';
            } else {
              statusBarEl.style.display = 'none';
            }

            // --- Output log ---
            if (state.log && state.log.length > 0) {
              // Detect log reset (new workflow started) — re-render from scratch
              if (state.log.length < prevLogLength) {
                prevLogLength = 0;
                outputEl.innerHTML = '';
              }
              if (state.log.length > prevLogLength) {
                if (prevLogLength === 0) {
                  outputEl.innerHTML = '';
                }
                const newLines = state.log.slice(prevLogLength);
                newLines.forEach(line => {
                  const cls = classifyLine(line);
                  const lastChild = outputEl.lastElementChild;

                  // Combine consecutive text lines and render as markdown (cap at 200 lines per block)
                  const rawLines = lastChild ? (lastChild.dataset.raw || '').split('\\n').length : 0;
                  if (cls === 'line line-text' && lastChild && lastChild.className === 'line line-text' && rawLines < 200) {
                    const raw = (lastChild.dataset.raw || '') + '\\n' + line;
                    lastChild.dataset.raw = raw;
                    lastChild.innerHTML = renderMarkdown(raw);
                  } else if (cls === 'line line-text') {
                    const div = document.createElement('div');
                    div.className = cls;
                    div.dataset.raw = line;
                    div.innerHTML = renderMarkdown(line);
                    outputEl.appendChild(div);
                  } else {
                    const div = document.createElement('div');
                    div.className = cls;
                    div.textContent = line;
                    outputEl.appendChild(div);
                  }
                });
                prevLogLength = state.log.length;
                outputEl.scrollTop = outputEl.scrollHeight;
              }
            } else if (!state.isRunning && state.phase !== 'done') {
              prevLogLength = 0;
              outputEl.innerHTML = '<div class="empty-state"><p><strong>RePPIT Health</strong></p><p>Enter a task below to start the workflow</p></div>';
            }

            // --- Gate ---
            if (state.gateActive && state.gatePrompt) {
              gateEl.style.display = 'block';
              gateEl.innerHTML = '';

              const gateText = document.createElement('div');
              gateText.className = 'gate-text';
              gateText.textContent = state.gatePrompt;
              gateEl.appendChild(gateText);

              const gateActions = document.createElement('div');
              gateActions.className = 'gate-actions';

              if (state.gateOptions && state.gateOptions.length > 0) {
                state.gateOptions.forEach(opt => {
                  const btn = document.createElement('button');
                  btn.textContent = 'Pick ' + opt;
                  btn.addEventListener('click', () => sendGate('ok', null, opt));
                  gateActions.appendChild(btn);
                });
              } else {
                const okBtn = document.createElement('button');
                okBtn.textContent = 'Approve & Implement';
                okBtn.addEventListener('click', () => sendGate('ok'));
                gateActions.appendChild(okBtn);
              }

              const ticketsBtn = document.createElement('button');
              ticketsBtn.className = 'secondary';
              ticketsBtn.textContent = 'Create Tickets';
              ticketsBtn.title = 'Create Linear issues or local .md files from the plan';
              ticketsBtn.addEventListener('click', () => sendGate('create-tickets'));
              gateActions.appendChild(ticketsBtn);

              gateEl.appendChild(gateActions);

              inputEl.placeholder = 'Type refinement feedback and press Enter...';
            } else {
              gateEl.style.display = 'none';
              if (state.isRunning) {
                inputEl.placeholder = 'Claude is working...';
              } else {
                inputEl.placeholder = 'Describe a feature or paste an issue ID...';
              }
            }

            // --- Button ---
            sendBtn.disabled = false;
            if (!state.isRunning) {
              sendBtn.textContent = 'Start';
              sendBtn.className = '';
            } else {
              sendBtn.textContent = 'Stop';
              sendBtn.className = 'stop';
            }

            // --- Done ---
            if (state.phase === 'done' && !state.isRunning) {
              const doneDiv = document.createElement('div');
              doneDiv.className = 'line line-phase';
              doneDiv.textContent = '--- Workflow complete ---';
              outputEl.appendChild(doneDiv);
              outputEl.scrollTop = outputEl.scrollHeight;
              sendBtn.textContent = 'Start';
              sendBtn.className = '';
              inputEl.placeholder = 'Start another workflow...';
              prevLogLength = 0;
            }
          }

        </script>
      </body>
      </html>
    `;
  }
}
