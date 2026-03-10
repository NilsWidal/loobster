import { ClaudeEvent, Phase, ComplianceItem } from './types';

const PHASE_RE = /<!--\s*PHASE:(\w+)\s*-->/;
const GATE_RE = /<!--\s*GATE:(\w+):prompt:(.*?)\s*-->/;
const GATE_OPTIONS_RE = /<!--\s*GATE:(\w+):options:(.*?):prompt:(.*?)\s*-->/;
const SECURE_START_RE = /<!--\s*SECURE:(\w+):START\s*-->/;
const SECURE_ITEM_RE = /<!--\s*SECURE_ITEM:(pass|warn|fail):(.*?):(.*?)\s*-->/;
const SECURE_END_RE = /<!--\s*SECURE:(\w+):END\s*-->/;
const DONE_RE = /<!--\s*DONE\s*-->/;

export class OutputParser {
  private complianceBuffer: {
    framework: string;
    items: ComplianceItem[];
  } | null = null;

  /** Accumulates streaming text deltas into complete lines/paragraphs. */
  private textBuffer = '';

  /** Accumulates tool_use input JSON deltas. */
  private toolInputBuffer = '';
  private currentToolName = '';

  /**
   * Parse a JSONL line. Returns an array of events (may be empty if buffering text,
   * or multiple if flushing a buffer before a non-text event).
   */
  parseLine(line: string): ClaudeEvent[] {
    const trimmed = line.trim();
    if (!trimmed) return [];

    // Try to parse as stream-json JSONL
    if (trimmed.startsWith('{')) {
      try {
        const json = JSON.parse(trimmed);
        return this.parseJsonEvent(json);
      } catch {
        // Not valid JSON, fall through
      }
    }

    // Legacy text/HTML-comment format
    const evt = this.parseTextLine(trimmed);
    return evt ? [evt] : [];
  }

  /** Flush any remaining text buffer. Call when the stream ends. */
  flush(): ClaudeEvent[] {
    return this.flushTextBuffer(false);
  }

  /** Flush only complete lines (up to last newline). Keeps partial lines buffered.
   *  Use this from periodic timers to avoid splitting words mid-token. */
  flushCompletedLines(): ClaudeEvent[] {
    if (!this.textBuffer || !this.textBuffer.includes('\n')) return [];
    return this.flushTextBuffer(true);
  }

  // ---------------------------------------------------------------------------

  private parseJsonEvent(json: any): ClaudeEvent[] {
    if (!json || !json.type) return [];

    switch (json.type) {
      case 'stream_event':
        return this.handleStreamEvent(json.event);

      case 'assistant':
        return this.handleAssistantMessage(json.message);

      case 'result': {
        const events = this.flushTextBuffer();
        const isError = json.subtype && json.subtype.startsWith('error_');
        if (isError) {
          events.push({ type: 'error', message: json.result || `CLI error: ${json.subtype}` });
        } else {
          events.push({ type: 'done' });
        }
        return events;
      }

      case 'system': {
        if (json.subtype === 'init') {
          return [{ type: 'log', text: 'Connected' }];
        }
        return [];
      }

      default:
        return [];
    }
  }

  private handleStreamEvent(evt: any): ClaudeEvent[] {
    if (!evt) return [];

    // Streaming text delta — buffer it
    if (evt.type === 'content_block_delta' && evt.delta?.type === 'text_delta') {
      const text = evt.delta.text;
      if (text) {
        this.textBuffer += text;

        // Flush on newlines — only emit complete lines, keep partial remainder
        if (this.textBuffer.includes('\n')) {
          return this.flushTextBuffer(true);
        }
      }
      return [];
    }

    // Tool input JSON delta — accumulate for tool description
    if (evt.type === 'content_block_delta' && evt.delta?.type === 'input_json_delta') {
      this.toolInputBuffer += evt.delta.partial_json || '';
      return [];
    }

    // Tool use start — flush text, show tool name
    if (evt.type === 'content_block_start' && evt.content_block?.type === 'tool_use') {
      const events = this.flushTextBuffer();
      this.currentToolName = evt.content_block.name || 'unknown';
      this.toolInputBuffer = '';
      return events;
    }

    // Content block stop — if we have a tool, emit it with its input summary
    if (evt.type === 'content_block_stop') {
      if (this.currentToolName) {
        const events: ClaudeEvent[] = [];
        const summary = this.summarizeTool(this.currentToolName, this.toolInputBuffer);
        events.push({ type: 'log', text: summary });
        this.currentToolName = '';
        this.toolInputBuffer = '';
        return events;
      }
      // Text block stop — flush remaining text
      return this.flushTextBuffer();
    }

    // New assistant turn (message_start) — flush any pending text
    if (evt.type === 'message_start') {
      return this.flushTextBuffer();
    }

    return [];
  }

  private handleAssistantMessage(msg: any): ClaudeEvent[] {
    if (!msg) return [];

    // Scan complete message for embedded markers (PHASE, GATE, SECURE, DONE)
    const content = msg.content;
    if (Array.isArray(content)) {
      for (const block of content) {
        if (block.type === 'text' && block.text) {
          const markerEvent = this.parseTextLine(block.text);
          if (markerEvent && markerEvent.type !== 'log') {
            return [markerEvent];
          }
        }
      }
    }
    // Don't emit text — already streamed via stream_event
    return [];
  }

  /** Flush accumulated text as log events (one per line).
   *  @param keepPartial When true, only flush complete lines (up to last newline),
   *                     keeping any partial trailing text in the buffer to avoid
   *                     splitting words across lines. */
  private flushTextBuffer(keepPartial = false): ClaudeEvent[] {
    if (!this.textBuffer) return [];

    let toProcess: string;
    if (keepPartial) {
      const lastNewline = this.textBuffer.lastIndexOf('\n');
      if (lastNewline === -1) return []; // No complete lines yet
      toProcess = this.textBuffer.substring(0, lastNewline);
      this.textBuffer = this.textBuffer.substring(lastNewline + 1);
    } else {
      toProcess = this.textBuffer;
      this.textBuffer = '';
    }

    const events: ClaudeEvent[] = [];
    for (const line of toProcess.split('\n')) {
      const text = line.trim();
      if (!text) continue;

      // Check for embedded markers
      const markerEvent = this.parseTextLine(text);
      if (markerEvent && markerEvent.type !== 'log') {
        events.push(markerEvent);
      } else if (text) {
        events.push({ type: 'log', text });
      }
    }
    return events;
  }

  /** Produce a human-readable summary for a tool call. */
  private summarizeTool(name: string, inputJson: string): string {
    let detail = '';
    try {
      const input = JSON.parse(inputJson);
      switch (name) {
        case 'Agent':
          detail = input.prompt?.substring(0, 80) || input.description || '';
          break;
        case 'Read':
          detail = input.file_path || '';
          break;
        case 'Edit':
        case 'Write':
          detail = input.file_path || '';
          break;
        case 'Bash':
          detail = input.command?.substring(0, 80) || '';
          break;
        case 'Glob':
          detail = input.pattern || '';
          break;
        case 'Grep':
          detail = input.pattern || '';
          break;
        case 'WebFetch':
          detail = input.url?.substring(0, 60) || '';
          break;
        case 'WebSearch':
          detail = input.query?.substring(0, 60) || '';
          break;
        case 'TodoWrite':
          detail = `${(input.todos || []).length} items`;
          break;
        default:
          // MCP tools or others — try common field names
          detail = input.query || input.description || input.prompt || '';
          if (typeof detail === 'string') detail = detail.substring(0, 60);
          break;
      }
    } catch {
      // Invalid JSON — just show name
    }

    const icon = name === 'Agent' ? '🤖' : '🔧';
    return detail ? `${icon} ${name}: ${detail}` : `${icon} ${name}`;
  }

  /** Parse a line using text/HTML-comment markers. */
  private parseTextLine(line: string): ClaudeEvent | null {
    if (DONE_RE.test(line)) return { type: 'done' };

    const phaseMatch = line.match(PHASE_RE);
    if (phaseMatch) return { type: 'phase', phase: phaseMatch[1] as Phase };

    const gateOptionsMatch = line.match(GATE_OPTIONS_RE);
    if (gateOptionsMatch) {
      return {
        type: 'gate',
        phase: gateOptionsMatch[1] as Phase,
        options: gateOptionsMatch[2].split(',').map((s) => s.trim()),
        prompt: gateOptionsMatch[3],
      };
    }

    const gateMatch = line.match(GATE_RE);
    if (gateMatch) {
      return { type: 'gate', phase: gateMatch[1] as Phase, prompt: gateMatch[2] };
    }

    const compStartMatch = line.match(SECURE_START_RE);
    if (compStartMatch) {
      this.complianceBuffer = { framework: compStartMatch[1], items: [] };
      return null;
    }

    if (this.complianceBuffer) {
      const itemMatch = line.match(SECURE_ITEM_RE);
      if (itemMatch) {
        this.complianceBuffer.items.push({
          status: itemMatch[1] as 'pass' | 'warn' | 'fail',
          name: itemMatch[2],
          detail: itemMatch[3],
        });
        return null;
      }

      const compEndMatch = line.match(SECURE_END_RE);
      if (compEndMatch) {
        const result: ClaudeEvent = {
          type: 'secure',
          framework: this.complianceBuffer.framework as 'hipaa' | 'soc2' | 'hitrust',
          items: this.complianceBuffer.items,
        };
        this.complianceBuffer = null;
        return result;
      }
    }

    if (line.trim() && !line.includes('<!--')) {
      return { type: 'log', text: line };
    }

    return null;
  }
}
