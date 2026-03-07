import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import { OutputParser } from './parser';
import { ClaudeEvent } from './types';

export class ClaudeCli extends EventEmitter {
  private process: ChildProcess | null = null;
  private parser = new OutputParser();

  constructor(
    private claudePath: string,
    private autoApprove: boolean
  ) {
    super();
  }

  start(prompt: string, cwd?: string): void {
    const args = this.autoApprove
      ? ['--dangerously-skip-permissions', '-p', prompt]
      : ['-p', prompt];

    this.process = spawn(this.claudePath, args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    let buffer = '';

    this.process.stdout?.on('data', (chunk: Buffer) => {
      buffer += chunk.toString();
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
      const event: ClaudeEvent = {
        type: 'error',
        message: chunk.toString(),
      };
      this.emit('event', event);
    });

    this.process.on('exit', (code) => {
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
