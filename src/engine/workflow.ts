import * as vscode from 'vscode';
import { ClaudeCli } from '../claude/cli';
import { ClaudeEvent } from '../claude/types';
import { WorkflowState, GateResponse, createFreshState } from './types';
import { playGateSound, playCompletionSound } from '../notifications/sound';
import { detectLinearMcp } from '../linear/detector';
import type { SidebarProvider } from '../sidebar/SidebarProvider';

export class WorkflowEngine {
  private state: WorkflowState = createFreshState();
  private gateResolver: ((response: GateResponse) => void) | null = null;

  constructor(
    private cli: ClaudeCli,
    private sidebar: SidebarProvider,
    private config: vscode.WorkspaceConfiguration,
    private log: vscode.LogOutputChannel
  ) {
    this.cli.on('event', (event: ClaudeEvent) => this.handleEvent(event));
    this.log.info('WorkflowEngine created');
  }

  async start(input: string): Promise<void> {
    // Immediately show "starting" state so the UI responds right away
    this.state = createFreshState();
    this.state.isRunning = true;
    this.state.claudeTrace = this.config.get<boolean>('claudeTrace', false);
    this.state.log.push('Starting workflow...');
    this.updateSidebar();

    const claudePath = this.config.get<string>('claudePath', 'claude');
    this.log.info(`Detecting Linear MCP (claudePath="${claudePath}")...`);

    const linearAvailable = await detectLinearMcp(claudePath);
    this.log.info(`Linear MCP available: ${linearAvailable}`);

    this.state.linearAvailable = linearAvailable;
    this.state.log.push(linearAvailable ? 'Linear MCP detected' : 'Running in local mode (no Linear)');
    this.updateSidebar();

    const linearContext = linearAvailable
      ? 'Linear MCP tools are available. Use them for documents, issues, and comments.'
      : 'Linear is NOT available. Save all outputs as local .md files in research/ and plans/ directories.';

    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    this.log.info(`Starting CLI in cwd="${workspaceFolder}"`);
    this.state.log.push('Launching Claude CLI...');
    this.updateSidebar();

    this.cli.start(`${linearContext}\n\n/reppit ${input}`, workspaceFolder);
    this.log.info('CLI process spawned');
  }

  stop(): void {
    this.cli.stop();
    this.state.isRunning = false;
    this.state.isPaused = false;
    this.updateSidebar();
  }

  async handleGateResponse(response: GateResponse): Promise<void> {
    if (this.gateResolver) {
      this.gateResolver(response);
      this.gateResolver = null;
    }

    this.state.gateActive = false;

    if (response.action === 'refine') {
      this.state.refinementCount++;
      this.cli.send(response.feedback ?? 'Please refine.');
    } else if (response.action === 'ok') {
      this.state.refinementCount = 0;
      const selection = response.selection;
      this.cli.send(selection ? `OK, go with ${selection}` : 'OK, proceed.');
    } else if (response.action === 'skip') {
      this.state.refinementCount = 0;
      this.cli.send('Skip this phase.');
    } else if (response.action === 'pause') {
      this.state.isPaused = true;
      this.cli.send('Pause.');
    }

    this.updateSidebar();
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
    this.sidebar.updateState(this.state);
  }

  get currentPhase(): Phase {
    return this.state.phase;
  }

  get isRunning(): boolean {
    return this.state.isRunning;
  }
}
