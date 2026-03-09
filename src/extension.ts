import * as vscode from 'vscode';
import { SidebarProvider } from './sidebar/SidebarProvider';
import { WorkflowEngine } from './engine/workflow';
import { ClaudeCli } from './claude/cli';
import { scaffoldTemplates } from './templates/scaffold';

let engine: WorkflowEngine | undefined;
const log = vscode.window.createOutputChannel('RePPIT Health', { log: true });

export function activate(context: vscode.ExtensionContext) {
  log.info('Extension activating...');

  const sidebarProvider = new SidebarProvider(context.extensionUri, log);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      'reppithealth-sidebar',
      sidebarProvider
    )
  );

  log.info('Sidebar provider registered');

  context.subscriptions.push(
    vscode.commands.registerCommand('reppithealth.start', async (sidebarInput?: string) => {
      log.info(`reppithealth.start command fired, sidebarInput=${sidebarInput ? `"${sidebarInput}"` : 'undefined'}`);

      const input = sidebarInput || await vscode.window.showInputBox({
        prompt: 'Enter a feature description or Linear issue ID (e.g., CAR-123)',
        placeHolder: 'Build patient intake form...',
      });

      if (!input) {
        log.info('No input provided, aborting');
        return;
      }

      // Stop any existing engine before starting a new one
      if (engine) {
        log.info('Stopping previous engine');
        engine.stop();
      }

      const config = vscode.workspace.getConfiguration('reppithealth');
      const claudePath = config.get<string>('claudePath', 'claude');
      const autoApprove = config.get<boolean>('autoApprove', false);
      const claudeTrace = config.get<boolean>('claudeTrace', false);

      log.info(`Config: claudePath="${claudePath}", autoApprove=${autoApprove}, claudeTrace=${claudeTrace}`);

      const cli = new ClaudeCli(claudePath, autoApprove, claudeTrace, log);
      engine = new WorkflowEngine(cli, sidebarProvider, config, log);

      try {
        await engine.start(input);
        log.info('engine.start() resolved');
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        log.error(`engine.start() threw: ${msg}`);
        vscode.window.showErrorMessage(`RePPITHealth workflow failed: ${msg}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      'reppithealth.gateResponse',
      (response: { action: string; feedback?: string; selection?: string }) => {
        log.info(`gateResponse: ${JSON.stringify(response)}`);
        if (engine) {
          engine.handleGateResponse(response as any);
        } else {
          log.warn('gateResponse called but no engine exists');
        }
      }
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('reppithealth.stop', () => {
      log.info('reppithealth.stop command fired');
      if (engine) {
        engine.stop();
        engine = undefined;
        vscode.window.showInformationMessage('RePPITHealth workflow stopped.');
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('reppithealth.initTemplates', async () => {
      const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
      if (!workspaceFolder) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
      }

      const result = await scaffoldTemplates(
        workspaceFolder.uri.fsPath,
        context.extensionUri.fsPath
      );

      if (result.created.length > 0) {
        vscode.window.showInformationMessage(
          `Created ${result.created.length} template files. ${result.skipped.length} already existed.`
        );
      } else {
        vscode.window.showInformationMessage('All templates already exist.');
      }
    })
  );

  log.info('Extension activated successfully');
}

export function deactivate() {
  log.info('Extension deactivating');
  if (engine) {
    engine.stop();
    engine = undefined;
  }
}
