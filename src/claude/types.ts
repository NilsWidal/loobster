export type Phase =
  | 'research'
  | 'propose'
  | 'plan'
  | 'implement'
  | 'test'
  | 'secure'
  | 'done';

export interface PhaseChangeEvent {
  type: 'phase';
  phase: Phase;
}

export interface GateRequestEvent {
  type: 'gate';
  phase: Phase;
  prompt: string;
  options?: string[]; // e.g., ["1", "2"] for proposal selection
}

export interface ComplianceResultEvent {
  type: 'secure';
  framework: 'hipaa' | 'soc2' | 'hitrust';
  items: ComplianceItem[];
}

export interface ComplianceItem {
  name: string;
  status: 'pass' | 'warn' | 'fail';
  detail: string;
}

export interface LogLineEvent {
  type: 'log';
  text: string;
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export interface DoneEvent {
  type: 'done';
}

export interface TaskCreatedEvent {
  type: 'task-created';
  taskId: string;
  title: string;
  status: string;
}

export interface TaskUpdatedEvent {
  type: 'task-updated';
  taskId: string;
  status: string;
}

export type ClaudeEvent =
  | PhaseChangeEvent
  | GateRequestEvent
  | ComplianceResultEvent
  | LogLineEvent
  | ErrorEvent
  | DoneEvent
  | TaskCreatedEvent
  | TaskUpdatedEvent;

export type SecurityFramework = 'hipaa' | 'soc2' | 'hitrust';
