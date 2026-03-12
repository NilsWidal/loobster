import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { ClaudeCli } from '../claude/cli';
import { ClaudeEvent, Phase } from '../claude/types';
import { WorkflowState, GateResponse, createFreshState } from './types';
import { playGateSound, playCompletionSound } from '../notifications/sound';
import { detectLinearMcp } from '../linear/detector';
import { pollTasks } from '../claude/tasks';
import type { SidebarProvider } from '../sidebar/SidebarProvider';

export class WorkflowEngine {
  private state: WorkflowState = createFreshState();
  private workspaceFolder: string | undefined;
  /** Tracks which segment of the two-call workflow we're in.
   *  'planning' = first CLI call (Research → Propose → Plan)
   *  'implementing' = second CLI call (Implement → Test → Secure) */
  private segment: 'planning' | 'implementing' = 'planning';
  /** Session ID from the planning call, used for --resume in continuation. */
  private planningSessionId: string | null = null;

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

    // Build system prompt from the planning template
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
    this.segment = 'planning';
    this.planningSessionId = null;

    this.log.info(`Starting CLI in cwd="${this.workspaceFolder}"`);
    this.updateSidebar();

    this.cli.start(input, this.workspaceFolder, systemPrompt);
    this.log.info('CLI process spawned (planning segment)');
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
    // Start a NEW CLI call with --resume to continue the conversation.
    let prompt: string;
    let implementSystemPrompt: string | undefined;

    if (response.action === 'create-tickets') {
      this.segment = 'planning'; // stay in planning — gate will re-appear
      const linearHint = this.state.linearAvailable
        ? 'Create Linear issues for each task in the plan.'
        : 'Create a .md file in the plans/ directory for each task in the plan.';
      prompt = `${linearHint} After creating tickets, present the updated plan with references.`;
    } else if (response.action === 'refine') {
      this.state.refinementCount++;
      this.segment = 'planning'; // stay in planning for refinement
      prompt = response.feedback ?? 'Please refine the plan.';
    } else if (response.action === 'ok') {
      this.state.refinementCount = 0;
      this.segment = 'implementing';
      this.state.phase = 'implement';
      const selection = response.selection;
      prompt = selection
        ? `OK, go with ${selection}. Proceed with implementation.`
        : 'OK, the plan is approved. Proceed with implementation.';
      implementSystemPrompt = this.loadImplementTemplate();
    } else {
      this.log.warn(`Unexpected gate action: ${response.action}`);
      return;
    }

    if (!this.planningSessionId) {
      this.log.warn('No planning session ID available — resume will start a fresh conversation');
    }

    this.log.info(`Gate response: ${response.action}, sessionId=${this.planningSessionId}, prompt="${prompt}"`);
    this.state.isRunning = true;
    this.updateSidebar();

    // Use --resume with the planning session ID for reliable continuation
    this.cli.start(prompt, this.workspaceFolder, implementSystemPrompt, this.planningSessionId ?? undefined);
  }

  private loadImplementTemplate(): string | undefined {
    const templatePath = path.join(this.extensionRoot, 'templates', 'commands', 'reppit-implement.md');
    try {
      const template = fs.readFileSync(templatePath, 'utf-8');
      this.log.info(`Loaded implement template (${template.length} chars)`);
      return template;
    } catch (err) {
      this.log.warn(`Could not load implement template: ${err}`);
      return undefined;
    }
  }

  private handleEvent(event: ClaudeEvent): void {
    this.log.info(`CLI event: ${event.type}${'text' in event ? ` "${event.text.substring(0, 80)}"` : ''}`);

    // Capture session ID from the CLI for --resume
    const sessionId = this.cli.sessionId;
    if (sessionId && this.segment === 'planning') {
      this.planningSessionId = sessionId;
    }

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

      case 'task-created':
        this.state.tasks.push({
          id: event.taskId,
          title: event.title,
          status: event.status,
        });
        this.state.subIssues.total = this.state.tasks.length;
        this.log.info(`Task created: "${event.title}" (total: ${this.state.subIssues.total})`);
        break;

      case 'task-updated': {
        const task = this.state.tasks.find(t => t.id === event.taskId);
        if (task) {
          task.status = event.status;
        }
        this.state.subIssues.current = this.state.tasks.filter(
          t => t.status === 'completed'
        ).length;
        this.log.info(`Task updated: "${event.taskId}" → ${event.status} (${this.state.subIssues.current}/${this.state.subIssues.total})`);
        break;
      }

      case 'error':
        this.log.error(`CLI error: ${event.message}`);
        this.state.log.push(`[ERROR] ${event.message}`);
        break;

      case 'done':
        if (!this.state.isRunning) break; // guard against duplicate done events

        if (this.state.gateActive) {
          // Gate marker was detected and CLI exited — keep waiting at gate
          this.log.info('CLI exited at gate — waiting for user response');
          break;
        }

        if (this.segment === 'planning') {
          // First CLI call finished (Research → Propose → Plan).
          // Always show the plan gate so the user can review before implementation.
          this.log.info(`Planning segment complete — showing plan gate (sessionId=${this.planningSessionId})`);
          this.state.phase = 'plan';
          this.state.gateActive = true;
          this.state.gatePrompt = 'Plan ready for review. OK to start implementing, or do you want changes?';
          this.state.gateOptions = undefined;
          if (this.config.get<boolean>('notifications.sound', true)) {
            playGateSound();
          }
          if (this.config.get<boolean>('notifications.system', true)) {
            vscode.window.showInformationMessage(
              'RePPIT Health: Plan ready for review',
              'Open Sidebar'
            );
          }
          break;
        }

        // Poll-mode: sync task state from disk after CLI completes
        if (this.config.get<string>('taskMode', 'stream') === 'poll') {
          const claudePath = this.config.get<string>('claudePath', 'claude');
          pollTasks(claudePath, this.workspaceFolder).then((result) => {
            if (result.total > 0) {
              this.state.tasks = result.tasks.map(t => ({
                id: t.id, title: t.title, status: t.status,
              }));
              this.state.subIssues.total = result.total;
              this.state.subIssues.current = result.completed;
              this.log.info(`Poll-mode sync: ${result.completed}/${result.total} tasks completed`);
              this.updateSidebar();
            }
          }).catch((err) => {
            this.log.warn(`Poll-mode task sync failed: ${err}`);
          });
        }

        // Implementation segment done — workflow complete
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
