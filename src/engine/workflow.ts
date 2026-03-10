import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { ClaudeCli } from '../claude/cli';
import { ClaudeEvent, Phase } from '../claude/types';
import { WorkflowState, GateResponse, createFreshState } from './types';
import { playGateSound, playCompletionSound } from '../notifications/sound';
import { detectLinearMcp } from '../linear/detector';
import type { SidebarProvider } from '../sidebar/SidebarProvider';

export class WorkflowEngine {
  private state: WorkflowState = createFreshState();
  private workspaceFolder: string | undefined;

  constructor(
    private cli: ClaudeCli,
    private sidebar: SidebarProvider,
    private config: vscode.WorkspaceConfiguration,
    private log: vscode.LogOutputChannel,
    private extensionRoot: string
  ) {
    this.cli.on('event', (event: ClaudeEvent) => this.handleEvent(event));
    this.log.info('WorkflowEngine created');
  }

  async start(input: string): Promise<void> {
    // Immediately show "starting" state so the UI responds right away
    this.state = createFreshState();
    this.state.isRunning = true;
    this.state.claudeTrace = this.config.get<boolean>('claudeTrace', false);
    this.updateSidebar();

    const claudePath = this.config.get<string>('claudePath', 'claude');
    this.log.info(`Detecting Linear MCP (claudePath="${claudePath}")...`);

    const linearAvailable = await detectLinearMcp(claudePath);
    this.log.info(`Linear MCP available: ${linearAvailable}`);

    this.state.linearAvailable = linearAvailable;
    this.updateSidebar();

    const linearContext = linearAvailable
      ? 'Linear MCP tools are available. Use them for documents, issues, and comments.'
      : 'Linear is NOT available. Save all outputs as local .md files in research/ and plans/ directories.';

    // Build system prompt from the reppit template
    const templatePath = path.join(this.extensionRoot, 'templates', 'commands', 'reppit.md');
    let reppitTemplate = '';
    try {
      reppitTemplate = fs.readFileSync(templatePath, 'utf-8');
      this.log.info(`Loaded reppit template (${reppitTemplate.length} chars)`);
    } catch (err) {
      this.log.error(`Failed to read reppit template: ${err}`);
      this.state.log.push('[ERROR] Could not load workflow template');
      this.updateSidebar();
      return;
    }

    const systemPrompt = `${linearContext}\n\n${reppitTemplate}`;

    this.workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

    this.log.info(`Starting CLI in cwd="${this.workspaceFolder}"`);
    this.updateSidebar();

    this.cli.start(input, this.workspaceFolder, systemPrompt);
    this.log.info('CLI process spawned');
  }

  stop(): void {
    this.cli.stop();
    this.state.isRunning = false;
    this.state.isPaused = false;
    this.updateSidebar();
  }

  async handleGateResponse(response: GateResponse): Promise<void> {
    this.state.gateActive = false;

    if (response.action === 'pause') {
      this.state.isPaused = true;
      this.state.isRunning = false;
      this.updateSidebar();
      return;
    }

    // The CLI process has already exited (one-shot -p mode).
    // Start a NEW CLI call with --continue to resume the conversation.
    let prompt: string;
    if (response.action === 'refine') {
      this.state.refinementCount++;
      prompt = response.feedback ?? 'Please refine the plan.';
    } else if (response.action === 'ok') {
      this.state.refinementCount = 0;
      const selection = response.selection;
      prompt = selection
        ? `OK, go with ${selection}. Proceed with implementation.`
        : 'OK, proceed with the implementation.';
    } else {
      // skip
      this.state.refinementCount = 0;
      prompt = 'Skip the plan review and proceed directly to implementation.';
    }

    this.log.info(`Gate response: ${response.action} — continuing session with: "${prompt}"`);
    this.state.isRunning = true;
    this.updateSidebar();
    this.cli.start(prompt, this.workspaceFolder, undefined, true);
  }

  private handleEvent(event: ClaudeEvent): void {
    this.log.info(`CLI event: ${event.type}${'text' in event ? ` "${event.text.substring(0, 80)}"` : ''}`);

    switch (event.type) {
      case 'phase':
        this.state.phase = event.phase;
        this.state.refinementCount = 0;
        this.state.log.push(`── Phase: ${event.phase} ──`);
        break;

      case 'gate':
        this.state.gateActive = true;
        this.state.gatePrompt = event.prompt;
        this.state.gateOptions = event.options;

        if (this.config.get<boolean>('notifications.sound', true)) {
          playGateSound();
        }
        if (this.config.get<boolean>('notifications.system', true)) {
          vscode.window.showInformationMessage(
            `RePPIT Health: ${event.prompt}`,
            'Open Sidebar'
          );
        }
        break;

      case 'secure':
        this.state.security[event.framework] = { items: event.items };
        break;

      case 'log':
        this.state.log.push(event.text);
        break;

      case 'error':
        this.log.error(`CLI error: ${event.message}`);
        this.state.log.push(`[ERROR] ${event.message}`);
        break;

      case 'done':
        if (!this.state.isRunning) break; // guard against duplicate done events

        if (this.state.gateActive) {
          // CLI exited (one-shot -p mode) but gate is waiting for user input.
          // Don't complete the workflow — keep it paused at the gate.
          this.log.info('CLI exited at gate — waiting for user response');
          break;
        }

        this.log.info('Workflow done');
        this.state.phase = 'done';
        this.state.isRunning = false;
        if (this.config.get<boolean>('notifications.sound', true)) {
          playCompletionSound();
        }
        vscode.window.showInformationMessage(
          'RePPIT Health: Workflow complete!'
        );
        break;
    }

    this.updateSidebar();
  }

  private updateSidebar(): void {
    this.state.isThinking = this.state.isRunning && !this.state.gateActive;
    this.sidebar.updateState(this.state);
  }

  get currentPhase(): Phase {
    return this.state.phase;
  }

  get isRunning(): boolean {
    return this.state.isRunning;
  }
}
