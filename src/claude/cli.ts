import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as vscode from 'vscode';
import { OutputParser } from './parser';
import { ClaudeEvent } from './types';

export class ClaudeCli extends EventEmitter {
  private process: ChildProcess | null = null;
  private parser = new OutputParser();

  constructor(
    private claudePath: string,
    private autoApprove: boolean,
    private trace: boolean,
    private log: vscode.LogOutputChannel
  ) {
    super();
  }

  start(prompt: string, cwd?: string): void {
    const args: string[] = [];
    if (this.autoApprove) args.push('--dangerously-skip-permissions');
    args.push('-p', prompt, '--output-format', 'stream-json');
    if (this.trace) {
      args.push('--verbose', '--debug');
    }

    this.log.info(`Spawning: ${this.claudePath} ${args.map(a => a.length > 60 ? a.substring(0, 60) + '...' : a).join(' ')}`);
    this.log.info(`CWD: ${cwd ?? '(none)'}`);

    this.process = spawn(this.claudePath, args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    this.log.info(`Process spawned, pid=${this.process.pid}`);

    let buffer = '';

    this.process.stdout?.on('data', (chunk: Buffer) => {
      const text = chunk.toString();
      this.log.trace(`stdout chunk (${text.length} chars)`);
      buffer += text;
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        const event = this.parser.parseLine(line);
        if (event) {
          this.emit('event', event);
        }
      }
    });

    this.process.stderr?.on('data', (chunk: Buffer) => {
      const text = chunk.toString().trim();
      if (!text) return;
      if (this.trace) {
        // In trace mode, stderr is debug output, not errors
        this.log.debug(`stderr: ${text.substring(0, 500)}`);
        this.emit('event', { type: 'log', text: `[trace] ${text}` } as ClaudeEvent);
      } else {
        this.log.warn(`stderr: ${text.substring(0, 200)}`);
        this.emit('event', { type: 'error', message: text } as ClaudeEvent);
      }
    });

    this.process.on('exit', (code, signal) => {
      this.log.info(`Process exited: code=${code}, signal=${signal}`);

      // Flush remaining buffer
      if (buffer.trim()) {
        const event = this.parser.parseLine(buffer);
        if (event) {
          this.emit('event', event);
        }
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
    if (this.process) {
      this.process.kill('SIGTERM');
      this.process = null;
    }
  }

  get isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }
}
