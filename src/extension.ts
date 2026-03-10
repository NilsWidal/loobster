import * as vscode from 'vscode';
import { spawn, execFile } from 'child_process';
import { SidebarProvider } from './sidebar/SidebarProvider';
import { WorkflowEngine } from './engine/workflow';
import { ClaudeCli } from './claude/cli';
import { scaffoldTemplates } from './templates/scaffold';
import { buildCleanEnv } from './claude/env';

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

      // Auto-scaffold .claude/commands/ and .claude/compliance/ into the workspace
      // so the /reppit slash command and sub-commands are available to Claude CLI
      const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
      if (workspaceFolder) {
        try {
          const result = await scaffoldTemplates(
            workspaceFolder.uri.fsPath,
            context.extensionUri.fsPath
          );
          if (result.created.length > 0) {
            log.info(`Scaffolded ${result.created.length} template files: ${result.created.join(', ')}`);
          }
        } catch (err) {
          log.warn(`Template scaffolding failed (non-fatal): ${err}`);
        }
      }

      const config = vscode.workspace.getConfiguration('reppithealth');
      const claudePath = config.get<string>('claudePath', 'claude');
      const autoApprove = config.get<boolean>('autoApprove', false);
      const claudeTrace = config.get<boolean>('claudeTrace', false);

      log.info(`Config: claudePath="${claudePath}", autoApprove=${autoApprove}, claudeTrace=${claudeTrace}`);

      const cli = new ClaudeCli(claudePath, autoApprove, claudeTrace, log);
      engine = new WorkflowEngine(cli, sidebarProvider, config, log, context.extensionUri.fsPath);

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

  // --- Test CLI command: diagnoses claude -p connectivity ---
  context.subscriptions.push(
    vscode.commands.registerCommand('reppithealth.testCli', async () => {
      const config = vscode.workspace.getConfiguration('reppithealth');
      const claudePath = config.get<string>('claudePath', 'claude');
      const cleanEnv = buildCleanEnv();
      const output = vscode.window.createOutputChannel('RePPIT CLI Test');
      output.show(true);

      output.appendLine('=== RePPIT CLI Diagnostic ===');
      output.appendLine(`Claude path: ${claudePath}`);
      output.appendLine(`Clean env keys: ${Object.keys(cleanEnv).join(', ')}`);
      output.appendLine(`PATH: ${cleanEnv.PATH?.substring(0, 200)}`);
      output.appendLine('');

      // 1) Version check
      output.appendLine('--- Version check ---');
      try {
        const version = await new Promise<string>((resolve, reject) => {
          execFile(claudePath, ['--version'], { env: cleanEnv, timeout: 5000 }, (err, stdout) => {
            if (err) reject(err); else resolve(stdout.trim());
          });
        });
        output.appendLine(`Version: ${version}`);
      } catch (e: any) {
        output.appendLine(`ERROR: ${e.message}`);
      }

      // 2) Auth check
      output.appendLine('');
      output.appendLine('--- Auth check ---');
      try {
        const auth = await new Promise<string>((resolve, reject) => {
          execFile(claudePath, ['auth', 'status'], { env: cleanEnv, timeout: 5000 }, (err, stdout, stderr) => {
            if (err) reject(new Error(`${err.message}\nstdout: ${stdout}\nstderr: ${stderr}`));
            else resolve(stdout.trim());
          });
        });
        output.appendLine(`Auth: ${auth}`);
      } catch (e: any) {
        output.appendLine(`Auth error: ${e.message}`);
      }

      // 3) Inherited env vars (for diagnostics)
      output.appendLine('');
      output.appendLine('--- Inherited env vars (before cleaning) ---');
      const claudeVars = Object.keys(process.env).filter(k => k.startsWith('CLAUDE'));
      const vscodeVars = Object.keys(process.env).filter(k => k.startsWith('VSCODE'));
      const electronVars = Object.keys(process.env).filter(k => k.startsWith('ELECTRON'));
      output.appendLine(`CLAUDE*: ${claudeVars.map(k => `${k}=${process.env[k]}`).join(', ') || '(none)'}`);
      output.appendLine(`VSCODE*: ${vscodeVars.join(', ') || '(none)'}`);
      output.appendLine(`ELECTRON*: ${electronVars.join(', ') || '(none)'}`);
      output.appendLine(`NODE_OPTIONS: ${process.env.NODE_OPTIONS || '(not set)'}`);

      // 4) Spawn test with multiple configs
      const tests = [
        {
          name: 'A: stream-json + no-chrome',
          args: ['--output-format', 'stream-json', '--no-chrome', '-p', 'Respond with just the word OK'],
        },
        {
          name: 'B: stream-json + no-chrome + acceptEdits',
          args: ['--output-format', 'stream-json', '--no-chrome', '--permission-mode', 'acceptEdits', '-p', 'Respond with just the word OK'],
        },
        {
          name: 'C: text output + no-chrome',
          args: ['--output-format', 'text', '--no-chrome', '-p', 'Respond with just the word OK'],
        },
        {
          name: 'D: json output + no-chrome',
          args: ['--output-format', 'json', '--no-chrome', '-p', 'Respond with just the word OK'],
        },
      ];

      for (const test of tests) {
        output.appendLine('');
        output.appendLine(`--- Test ${test.name} ---`);

        const result = await new Promise<string>((resolve) => {
          let stdout = '';
          let stderr = '';
          let gotOutput = false;
          const start = Date.now();

          const child = spawn(claudePath, test.args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            env: cleanEnv,
          });

          output.appendLine(`  PID: ${child.pid}`);

          child.stdout?.on('data', (chunk: Buffer) => {
            gotOutput = true;
            stdout += chunk.toString();
          });

          child.stderr?.on('data', (chunk: Buffer) => {
            gotOutput = true;
            stderr += chunk.toString();
          });

          const timeout = setTimeout(() => {
            // Check if process is still alive
            let alive = false;
            try { process.kill(child.pid!, 0); alive = true; } catch {}
            output.appendLine(`  TIMEOUT after 20s — process ${alive ? 'ALIVE (hanging)' : 'DEAD'}`);
            child.kill('SIGTERM');
          }, 20000);

          child.on('close', (code, signal) => {
            clearTimeout(timeout);
            const elapsed = ((Date.now() - start) / 1000).toFixed(1);
            let summary = `  Exit: code=${code} signal=${signal}, Time: ${elapsed}s`;
            if (stdout) summary += `\n  STDOUT (${stdout.length} chars): ${stdout.substring(0, 300)}`;
            if (stderr) summary += `\n  STDERR (${stderr.length} chars): ${stderr.substring(0, 300)}`;
            if (!stdout && !stderr) summary += '\n  *** NO OUTPUT AT ALL ***';
            resolve(summary);
          });

          child.on('error', (err) => {
            clearTimeout(timeout);
            resolve(`  SPAWN ERROR: ${err.message}`);
          });
        });

        output.appendLine(result);
      }

      output.appendLine('');
      output.appendLine('=== Diagnostic complete ===');
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
