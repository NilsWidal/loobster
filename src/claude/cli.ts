import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as vscode from 'vscode';
import { OutputParser } from './parser';
import { ClaudeEvent } from './types';
import { buildCleanEnv } from './env';

export class ClaudeCli extends EventEmitter {
  private process: ChildProcess | null = null;
  private parser = new OutputParser();
  private heartbeat: ReturnType<typeof setTimeout> | null = null;
  private flushTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private claudePath: string,
    private autoApprove: boolean,
    private trace: boolean,
    private log: vscode.LogOutputChannel
  ) {
    super();
  }

  start(prompt: string, cwd?: string, systemPrompt?: string, continueSession = false): void {
    // Clean up any previous process listeners to prevent stale events
    if (this.process) {
      this.process.stdout?.removeAllListeners();
      this.process.stderr?.removeAllListeners();
      this.process.removeAllListeners();
    }

    // Fresh parser for each CLI invocation
    this.parser = new OutputParser();

    const args: string[] = [];
    if (this.autoApprove) args.push('--dangerously-skip-permissions');
    // --verbose is REQUIRED for stream-json with -p (Claude CLI ≥2.1.72)
    // --include-partial-messages streams text/tool events as they arrive
    args.push('--output-format', 'stream-json', '--verbose', '--include-partial-messages');
    args.push('--no-chrome');
    if (continueSession) {
      args.push('--continue');
    }
    if (systemPrompt && !continueSession) {
      args.push('--append-system-prompt', systemPrompt);
    }
    args.push('-p', prompt);
    if (this.trace) {
      args.push('--debug');
    }

    this.log.info(`Spawning: ${this.claudePath} ${args.map(a => a.length > 60 ? a.substring(0, 60) + '...' : a).join(' ')}`);
    this.log.info(`CWD: ${cwd ?? '(none)'}`);

    const clean = buildCleanEnv();
    this.log.info(`Clean env keys: ${Object.keys(clean).join(', ')}`);

    this.process = spawn(this.claudePath, args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: clean,
    });

    // Close stdin immediately — in -p mode the prompt comes from args.
    // An open pipe on stdin causes the CLI to block waiting for input EOF.
    this.process.stdin?.end();

    // Periodically flush the parser's completed lines so text appears in real-time
    // without splitting words mid-token (flushCompletedLines only emits at newline boundaries)
    if (this.flushTimer) clearInterval(this.flushTimer);
    this.flushTimer = setInterval(() => {
      for (const event of this.parser.flushCompletedLines()) {
        this.emit('event', event);
      }
    }, 300);

    this.log.info(`Process spawned, pid=${this.process.pid}`);

    let buffer = '';
    let gotOutput = false;

    // Heartbeat: warn if no output arrives within 15s
    if (this.heartbeat) clearTimeout(this.heartbeat);
    this.heartbeat = setTimeout(() => {
      if (!gotOutput) {
        this.log.warn('No output from Claude CLI after 15s');
        this.emit('event', {
          type: 'log',
          text: '[warn] No output from Claude CLI after 15s — check if claude is authenticated and responding',
        } as ClaudeEvent);
      }
    }, 15_000);

    this.process.stdout?.on('data', (chunk: Buffer) => {
      gotOutput = true;
      if (this.heartbeat) { clearTimeout(this.heartbeat); this.heartbeat = null; }
      const text = chunk.toString();
      this.log.trace(`stdout chunk (${text.length} chars)`);
      buffer += text;
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        for (const event of this.parser.parseLine(line)) {
          this.emit('event', event);
        }
      }
    });

    this.process.stderr?.on('data', (chunk: Buffer) => {
      gotOutput = true;
      if (this.heartbeat) { clearTimeout(this.heartbeat); this.heartbeat = null; }
      const text = chunk.toString().trim();
      if (!text) return;
      // --verbose is always on (required for stream-json), so stderr is
      // debug output. Only surface it in the UI when trace mode is enabled.
      this.log.debug(`stderr: ${text.substring(0, 500)}`);
      if (this.trace) {
        this.emit('event', { type: 'log', text: `[trace] ${text}` } as ClaudeEvent);
      }
    });

    // Use 'close' instead of 'exit' to ensure all stdio streams are flushed
    this.process.on('close', (code, signal) => {
      if (this.heartbeat) { clearTimeout(this.heartbeat); this.heartbeat = null; }
      if (this.flushTimer) { clearInterval(this.flushTimer); this.flushTimer = null; }
      this.log.info(`Process closed: code=${code}, signal=${signal}`);

      // Flush remaining JSONL line buffer
      if (buffer.trim()) {
        for (const event of this.parser.parseLine(buffer)) {
          this.emit('event', event);
        }
      }
      // Flush any remaining text accumulated in the parser
      for (const event of this.parser.flush()) {
        this.emit('event', event);
      }

      if (code !== 0) {
        this.emit('event', {
          type: 'error',
          message: `Claude CLI exited with code ${code}`,
        } as ClaudeEvent);
      }
      this.emit('event', { type: 'done' } as ClaudeEvent);
    });

    this.process.on('error', (err) => {
      this.log.error(`Process error: ${err.message}`);
      this.emit('event', {
        type: 'error',
        message: `Failed to start Claude CLI: ${err.message}`,
      } as ClaudeEvent);
    });
  }

  send(input: string): void {
    if (this.process?.stdin?.writable) {
      this.process.stdin.write(input + '\n');
    }
  }

  stop(): void {
    if (this.heartbeat) { clearTimeout(this.heartbeat); this.heartbeat = null; }
    if (this.flushTimer) { clearInterval(this.flushTimer); this.flushTimer = null; }
    if (this.process) {
      this.process.kill('SIGTERM');
      this.process = null;
    }
  }

  get isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }
}
