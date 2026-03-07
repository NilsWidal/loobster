import { ClaudeEvent, Phase, ComplianceItem } from './types';

const PHASE_RE = /<!--\s*PHASE:(\w+)\s*-->/;
const GATE_RE = /<!--\s*GATE:(\w+):prompt:(.*?)\s*-->/;
const GATE_OPTIONS_RE = /<!--\s*GATE:(\w+):options:(.*?):prompt:(.*?)\s*-->/;
const COMPLIANCE_START_RE = /<!--\s*COMPLIANCE:(\w+):START\s*-->/;
const COMPLIANCE_ITEM_RE = /<!--\s*COMPLIANCE_ITEM:(pass|warn|fail):(.*?):(.*?)\s*-->/;
const COMPLIANCE_END_RE = /<!--\s*COMPLIANCE:(\w+):END\s*-->/;
const DONE_RE = /<!--\s*DONE\s*-->/;

export class OutputParser {
  private complianceBuffer: {
    framework: string;
    items: ComplianceItem[];
  } | null = null;

  parseLine(line: string): ClaudeEvent | null {
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
    const compStartMatch = line.match(COMPLIANCE_START_RE);
    if (compStartMatch) {
      this.complianceBuffer = {
        framework: compStartMatch[1],
        items: [],
      };
      return null;
    }

    if (this.complianceBuffer) {
      const itemMatch = line.match(COMPLIANCE_ITEM_RE);
      if (itemMatch) {
        this.complianceBuffer.items.push({
          status: itemMatch[1] as 'pass' | 'warn' | 'fail',
          name: itemMatch[2],
          detail: itemMatch[3],
        });
        return null;
      }

      const compEndMatch = line.match(COMPLIANCE_END_RE);
      if (compEndMatch) {
        const result: ClaudeEvent = {
          type: 'compliance',
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
