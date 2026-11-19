export type SessionStatus = "idle" | "running" | "error" | string;

export interface Session {
  id: string;
  title: string;
  status: SessionStatus;
  model_name: string;
  workspace_path: string;
  goal?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  streaming?: boolean;
}

export interface Span {
  id: string;
  session_id: string;
  run_id: string;
  parent_span_id?: string | null;
  kind: string;
  name: string;
  started_at: string;
  ended_at?: string | null;
  duration_ms: number;
  status: string;
  summary: string;
  input?: unknown;
  output?: unknown;
  error?: unknown;
  usage?: { total_tokens?: number } | null;
}

export interface ToolCall {
  id: string;
  span_id?: string | null;
  tool_name: string;
  args_json: string;
  args_digest: string;
  status: string;
  started_at: string;
  ended_at?: string | null;
  duration_ms?: number | null;
  result_summary?: string | null;
}

export interface TraceSummary {
  total_duration_ms: number;
  round_count: number;
  call_count: number;
  error_count: number;
  success_rate: number;
  total_tokens: number;
  tokens_per_second: number;
}

export interface Attachment {
  name: string;
  kind: string;
  text: string;
  size: number;
}

export interface TraceData {
  session: Session;
  summary: TraceSummary;
  messages: Message[];
  runs: Array<Record<string, unknown>>;
  spans: Span[];
  tool_calls: ToolCall[];
  goals: Goal[];
}

export interface GoalIteration {
  id: string;
  goal_id: string;
  iteration_no: number;
  run_id?: string | null;
  status: string;
  plan?: string | null;
  summary?: string | null;
  started_at: string;
  ended_at?: string | null;
}

export interface Goal {
  id: string;
  session_id: string;
  objective: string;
  criteria: string[];
  constraints: string[];
  status: string;
  current_iteration: number;
  max_iterations: number;
  progress_summary?: string | null;
  iterations?: GoalIteration[];
}

export interface Provider {
  id: string;
  name: string;
  protocol: string;
  base_url: string;
  model: string;
  api_key_set: boolean;
  api_key_hint?: string | null;
  enabled: boolean;
  is_default: boolean;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  version: string;
  path: string;
  base_dir: string;
  source: string;
  enabled: boolean;
  disable_model_invocation: boolean;
}

export interface Checkpoint {
  id: string;
  session_id: string;
  run_id?: string | null;
  goal_id?: string | null;
  kind: string;
  status: string;
  created_at: string;
}

