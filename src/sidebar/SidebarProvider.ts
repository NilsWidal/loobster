import * as vscode from 'vscode';
import { WorkflowState } from '../engine/types';

export class SidebarProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;

  constructor(private readonly extensionUri: vscode.Uri) {}

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtml(webviewView.webview);

    // Handle messages from webview
    webviewView.webview.onDidReceiveMessage((message) => {
      switch (message.type) {
        case 'gate-response':
          // Forwarded to WorkflowEngine via command
          vscode.commands.executeCommand(
            'reppithealth.gateResponse',
            message.payload
          );
          break;
        case 'start':
          vscode.commands.executeCommand('reppithealth.start');
          break;
        case 'stop':
          vscode.commands.executeCommand('reppithealth.stop');
          break;
      }
    });
  }

  updateState(state: WorkflowState): void {
    this.view?.webview.postMessage({ type: 'state-update', state });
  }

  private getHtml(webview: vscode.Webview): string {
    // In production, this loads the built React app from webview/dist
    // For now, inline a minimal UI
    return /* html */ `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>RePPIT Health</title>
        <style>
          body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            padding: 12px;
            margin: 0;
          }
          h2 { font-size: 14px; margin: 0 0 12px; }
          .phase {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 0;
            font-size: 12px;
            opacity: 0.5;
          }
          .phase.active { opacity: 1; font-weight: bold; }
          .phase.completed { opacity: 0.8; }
          .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            border: 1px solid var(--vscode-foreground);
            flex-shrink: 0;
          }
          .phase.active .dot {
            background: var(--vscode-charts-blue);
            border-color: var(--vscode-charts-blue);
          }
          .phase.completed .dot {
            background: var(--vscode-charts-green);
            border-color: var(--vscode-charts-green);
          }
          .gate-prompt {
            margin: 16px 0;
            padding: 12px;
            background: var(--vscode-inputValidation-infoBackground);
            border: 1px solid var(--vscode-inputValidation-infoBorder);
            border-radius: 4px;
            font-size: 12px;
          }
          button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 6px 12px;
            border-radius: 2px;
            cursor: pointer;
            font-size: 12px;
            margin: 4px 4px 4px 0;
          }
          button:hover { background: var(--vscode-button-hoverBackground); }
          button.secondary {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
          }
          textarea {
            width: 100%;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 2px;
            padding: 6px;
            font-family: var(--vscode-font-family);
            font-size: 12px;
            resize: vertical;
            margin: 8px 0;
            box-sizing: border-box;
          }
          .log {
            margin-top: 16px;
            font-size: 11px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            opacity: 0.7;
          }
          .compliance-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 2px;
            font-size: 10px;
            font-weight: bold;
            margin: 2px;
          }
          .badge-pass { background: var(--vscode-charts-green); color: #fff; }
          .badge-warn { background: var(--vscode-charts-yellow); color: #000; }
          .badge-fail { background: var(--vscode-charts-red); color: #fff; }
          .start-section { text-align: center; margin-top: 24px; }
        </style>
      </head>
      <body>
        <h2>RePPIT Health</h2>
        <div id="app">
          <div class="start-section">
            <p style="font-size: 12px; opacity: 0.7;">No workflow running</p>
            <button onclick="startWorkflow()">Start Workflow</button>
          </div>
        </div>

        <script>
          const vscode = acquireVsCodeApi();
          const phases = ['research', 'propose', 'plan', 'implement', 'test', 'secure', 'done'];
          const phaseLabels = {
            research: 'Research',
            propose: 'Propose',
            plan: 'Plan',
            implement: 'Implement',
            test: 'Test',
            secure: 'Secure',
            done: 'Done'
          };

          let currentState = null;

          window.addEventListener('message', (event) => {
            const msg = event.data;
            if (msg.type === 'state-update') {
              currentState = msg.state;
              render();
            }
          });

          function render() {
            if (!currentState || !currentState.isRunning) {
              document.getElementById('app').innerHTML = \`
                <div class="start-section">
                  <p style="font-size: 12px; opacity: 0.7;">No workflow running</p>
                  <button onclick="startWorkflow()">Start Workflow</button>
                </div>
              \`;
              return;
            }

            const currentIdx = phases.indexOf(currentState.phase);

            let html = phases.map((p, i) => {
              const cls = i < currentIdx ? 'completed' : i === currentIdx ? 'active' : '';
              return \`<div class="phase \${cls}"><div class="dot"></div>\${phaseLabels[p]}</div>\`;
            }).join('');

            if (currentState.gateActive && currentState.gatePrompt) {
              html += \`<div class="gate-prompt">\${currentState.gatePrompt}</div>\`;

              if (currentState.gateOptions && currentState.gateOptions.length > 0) {
                currentState.gateOptions.forEach(opt => {
                  html += \`<button onclick="sendGate('ok', null, '\${opt}')">Pick \${opt}</button>\`;
                });
              } else {
                html += \`<button onclick="sendGate('ok')">OK, proceed</button>\`;
              }
              html += \`<button class="secondary" onclick="showRefine()">Refine</button>\`;
              html += \`<button class="secondary" onclick="sendGate('skip')">Skip</button>\`;
              html += \`<div id="refine-area" style="display:none;">
                <textarea id="refine-input" rows="3" placeholder="Feedback..."></textarea>
                <button onclick="sendRefine()">Send</button>
              </div>\`;
            }

            // Compliance badges
            const comp = currentState.security || {};
            Object.keys(comp).forEach(fw => {
              const items = comp[fw]?.items || [];
              const fails = items.filter(i => i.status === 'fail').length;
              const warns = items.filter(i => i.status === 'warn').length;
              const cls = fails > 0 ? 'badge-fail' : warns > 0 ? 'badge-warn' : 'badge-pass';
              const label = fails > 0 ? \`\${fails} fail\` : warns > 0 ? \`\${warns} warn\` : 'pass';
              html += \`<span class="compliance-badge \${cls}">\${fw.toUpperCase()}: \${label}</span>\`;
            });

            // Log
            if (currentState.log && currentState.log.length > 0) {
              const recent = currentState.log.slice(-50).join('\\n');
              html += \`<div class="log">\${escapeHtml(recent)}</div>\`;
            }

            html += \`<div style="margin-top:12px;"><button class="secondary" onclick="stopWorkflow()">Stop</button></div>\`;

            document.getElementById('app').innerHTML = html;
          }

          function sendGate(action, feedback, selection) {
            vscode.postMessage({ type: 'gate-response', payload: { action, feedback, selection } });
          }

          function showRefine() {
            document.getElementById('refine-area').style.display = 'block';
          }

          function sendRefine() {
            const input = document.getElementById('refine-input').value;
            sendGate('refine', input);
          }

          function startWorkflow() {
            vscode.postMessage({ type: 'start' });
          }

          function stopWorkflow() {
            vscode.postMessage({ type: 'stop' });
          }

          function escapeHtml(str) {
            return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
          }
        </script>
      </body>
      </html>
    `;
  }
}
