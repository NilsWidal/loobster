import * as vscode from 'vscode';
import { ClaudeCli } from '../claude/cli';
import { ClaudeEvent, Phase } from '../claude/types';
import { WorkflowState, GateResponse, INITIAL_STATE } from './types';
import { playGateSound, playCompletionSound } from '../notifications/sound';
import type { SidebarProvider } from '../sidebar/SidebarProvider';

const PHASE_ORDER: Phase[] = [
  'research',
  'propose',
  'plan',
  'implement',
  'review',
  'compliance',
  'done',
];

export class WorkflowEngine {
  private state: WorkflowState = { ...INITIAL_STATE };
  private gateResolver: ((response: GateResponse) => void) | null = null;

  constructor(
    private cli: ClaudeCli,
    private sidebar: SidebarProvider,
    private config: vscode.WorkspaceConfiguration
  ) {
    this.cli.on('event', (event: ClaudeEvent) => this.handleEvent(event));
  }

  async start(input: string): Promise<void> {
    this.state = { ...INITIAL_STATE, isRunning: true };
    this.updateSidebar();

    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    this.cli.start(`/reppit ${input}`, workspaceFolder);
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
    switch (event.type) {
      case 'phase':
        this.state.phase = event.phase;
        this.state.refinementCount = 0;
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
            `RePPITHealth: ${event.prompt}`,
            'Open Sidebar'
          );
        }
        break;

      case 'compliance':
        this.state.compliance[event.framework] = { items: event.items };
        break;

      case 'log':
        this.state.log.push(event.text);
        break;

      case 'error':
        this.state.log.push(`[ERROR] ${event.message}`);
        break;

      case 'done':
        this.state.phase = 'done';
        this.state.isRunning = false;
        if (this.config.get<boolean>('notifications.sound', true)) {
          playCompletionSound();
        }
        vscode.window.showInformationMessage(
          'RePPITHealth: Workflow complete!'
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
