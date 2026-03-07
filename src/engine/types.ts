import { Phase, ComplianceItem } from '../claude/types';

export type GateAction = 'ok' | 'refine' | 'skip' | 'pause';

export interface GateResponse {
  action: GateAction;
  feedback?: string; // provided when action is 'refine'
  selection?: string; // provided when picking a proposal (e.g., "1" or "2")
}

export interface WorkflowState {
  phase: Phase;
  isRunning: boolean;
  isPaused: boolean;
  gateActive: boolean;
  gatePrompt?: string;
  gateOptions?: string[];
  refinementCount: number;
  log: string[];
  security: {
    hipaa?: { items: ComplianceItem[] };
    soc2?: { items: ComplianceItem[] };
    hitrust?: { items: ComplianceItem[] };
  };
  subIssues: {
    total: number;
    current: number;
  };
  linearAvailable: boolean;
}

export const INITIAL_STATE: WorkflowState = {
  phase: 'research',
  isRunning: false,
  isPaused: false,
  gateActive: false,
  refinementCount: 0,
  log: [],
  security: {},
  subIssues: { total: 0, current: 0 },
  linearAvailable: false,
};
