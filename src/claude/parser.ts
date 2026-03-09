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

  parseLine(line: string): ClaudeEvent | null {
    const trimmed = line.trim();
    if (!trimmed) return null;

    // Try to parse as stream-json JSONL from Claude CLI
    if (trimmed.startsWith('{')) {
      try {
        const json = JSON.parse(trimmed);
        return this.parseJsonEvent(json);
      } catch {
        // Not valid JSON, fall through to text parsing
      }
    }

    // --- Text/HTML-comment format (legacy) ---
    return this.parseTextLine(trimmed);
  }

  /**
   * Parse a stream-json event from `claude -p --output-format stream-json`.
   * Event shapes: https://docs.anthropic.com/en/docs/claude-code/sdk
   *   { type: "assistant", message: { type: "text", text: "..." } }
   *   { type: "assistant", message: { type: "tool_use", name: "...", input: {...} } }
   *   { type: "result", result: "...", subtype: "success"|"error_max_turns"|... }
   *   { type: "system", message: "...", subtype: "init"|... }
   */
  private parseJsonEvent(json: any): ClaudeEvent | null {
    if (!json || !json.type) return null;

    switch (json.type) {
      case 'assistant': {
        const msg = json.message;
        if (!msg) return null;

        if (msg.type === 'text' && typeof msg.text === 'string') {
          const text = msg.text;
          // Check for embedded markers in the text
          const markerEvent = this.parseTextLine(text);
          if (markerEvent && markerEvent.type !== 'log') {
            return markerEvent;
          }
          // Show meaningful text as log (skip very short fragments)
          if (text.trim().length > 0) {
            return { type: 'log', text: text };
          }
        }

        if (msg.type === 'tool_use') {
          return { type: 'log', text: `🔧 ${msg.name}` };
        }
        return null;
      }

      case 'result': {
        // Final result from the CLI
        const isError = json.subtype && json.subtype.startsWith('error_');
        if (isError) {
          return { type: 'error', message: json.result || `CLI error: ${json.subtype}` };
        }
        return { type: 'done' };
      }

      case 'system': {
        if (json.subtype === 'init') {
          return { type: 'log', text: 'Claude CLI connected' };
        }
        return null;
      }

      default:
        return null;
    }
  }

  /** Parse a line using text/HTML-comment markers. */
  private parseTextLine(line: string): ClaudeEvent | null {
    // Check for done marker
    if (DONE_RE.test(line)) {
      return { type: 'done' };
    }

    // Check for phase change
    const phaseMatch = line.match(PHASE_RE);
    if (phaseMatch) {
      return { type: 'phase', phase: phaseMatch[1] as Phase };
    }

    // Check for gate with options (e.g., proposal selection)
    const gateOptionsMatch = line.match(GATE_OPTIONS_RE);
    if (gateOptionsMatch) {
      return {
        type: 'gate',
        phase: gateOptionsMatch[1] as Phase,
        options: gateOptionsMatch[2].split(',').map((s) => s.trim()),
        prompt: gateOptionsMatch[3],
      };
    }

    // Check for simple gate
    const gateMatch = line.match(GATE_RE);
    if (gateMatch) {
      return {
        type: 'gate',
        phase: gateMatch[1] as Phase,
        prompt: gateMatch[2],
      };
    }

    // Compliance tracking
    const compStartMatch = line.match(SECURE_START_RE);
    if (compStartMatch) {
      this.complianceBuffer = {
        framework: compStartMatch[1],
        items: [],
      };
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

    // Default: log line (skip empty marker lines)
    if (line.trim() && !line.includes('<!--')) {
      return { type: 'log', text: line };
    }

    return null;
  }
}
