import * as vscode from 'vscode';
import { SidebarProvider } from './sidebar/SidebarProvider';
import { WorkflowEngine } from './engine/workflow';
import { ClaudeCli } from './claude/cli';
import { scaffoldTemplates } from './templates/scaffold';

let engine: WorkflowEngine | undefined;

export function activate(context: vscode.ExtensionContext) {
  const sidebarProvider = new SidebarProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      'reppithealth-sidebar',
      sidebarProvider
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('reppithealth.start', async () => {
      const input = await vscode.window.showInputBox({
        prompt: 'Enter a feature description or Linear issue ID (e.g., CAR-123)',
        placeHolder: 'Build patient intake form...',
      });

      if (!input) return;

      const config = vscode.workspace.getConfiguration('reppithealth');
      const claudePath = config.get<string>('claudePath', 'claude');
      const autoApprove = config.get<boolean>('autoApprove', false);

      const cli = new ClaudeCli(claudePath, autoApprove);
      engine = new WorkflowEngine(cli, sidebarProvider, config);

      try {
        await engine.start(input);
      } catch (err) {
        vscode.window.showErrorMessage(
          `RePPITHealth workflow failed: ${err instanceof Error ? err.message : String(err)}`
        );
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('reppithealth.stop', () => {
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
}

export function deactivate() {
  if (engine) {
    engine.stop();
    engine = undefined;
  }
}
