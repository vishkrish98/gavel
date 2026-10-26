export type RuleStatus = "proposed" | "approved" | "rejected";

export interface PolicyParagraph {
  para_id: string;
  text: string;
  kind: string | null;
}

export interface Rule {
  id: string;
  para_id: string;
  type: string;
  params: Record<string, unknown>;
  quote: string;
  quote_verified: number;
  status: RuleStatus;
  approved_by: string | null;
}

export interface RequestLine {
  id: string;
  request_id: string;
  description: string;
  amount: number;
  docs: string[];
  already_purchased: boolean;
  category: string | null;
  headcount: number | null;
  qty: number | null;
  nights: number | null;
  unit_cost: number | null;
  quarantined: boolean;
}

export interface RequestDetail {
  id: string;
  club: string;
  event_date: string;
  submitted_date: string;
  justification: string;
  source: string;
  found: boolean;
  lines: RequestLine[];
}

export interface UsageTotals {
  input_tokens: number;
  cached_tokens: number;
  cache_write_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  seconds: number;
  cost_usd: number;
  calls: number;
}

export interface RunStatus {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: "running" | "completed" | "limit_hit" | "failed";
  mode: string;
  progress_by_agent: Record<string, { calls: number }>;
  usage_total: UsageTotals;
}

export interface AuditEvent {
  id: number;
  run_id: string | null;
  ts: string;
  event: string;
  detail_json: string;
}

export interface Verdict {
  run_id: string;
  line_id: string;
  verdict: "allowed" | "reduced" | "denied" | "needs_docs";
  allowed_amount: number;
  rules_json: string;
  explanation: string | null;
  flagged_for_review: number;
  description: string;
  amount: number;
  request_id: string;
  club: string;
  goal: string | null;
  program: string | null;
}

export interface Citation {
  rule_id: string;
  para_id: string;
  quote: string;
}

export interface ExplainResult {
  request_id: string;
  line_id: string;
  found: boolean;
  verdict: string;
  allowed_amount: number;
  rules: string[];
  citations: Citation[];
}

export interface CommitteeQuestion {
  line_id: string | null;
  question: string;
  rule_id: string | null;
  quote: string | null;
}

export interface Draft {
  id: string;
  run_id: string;
  request_id: string | null;
  kind: "questions" | "memo";
  status: "awaiting_approval" | "approved";
  created_at: string;
  content: { request_id?: string; questions?: CommitteeQuestion[]; memo?: string };
}

export interface ConsistencyDecision {
  decision_id: string;
  club: string;
  description: string;
  requested: number;
  approved: number;
  matched: boolean;
  engine_allowed: number | null;
  inconsistent: boolean | null;
}

export interface ConsistencyReport {
  decisions: ConsistencyDecision[];
  total: number;
  matched: number;
  inconsistent_count: number;
  inconsistency_rate: number;
}

export interface AllocateResult {
  pot: number;
  alpha: number;
  allowed_by_club: Record<string, number>;
  allocation: Record<string, number>;
}

export interface DemoLoadResult {
  loaded: { policy_paragraphs: number; requests: number; prior_decisions: number };
  policy_compiled: boolean;
  compiler_summary: Record<string, unknown>;
  proposed_rules: Rule[];
  next_step: string;
}

export interface UsageByRun {
  run_id: string;
  input_tokens: number;
  cached_tokens: number;
  cache_write_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  seconds: number;
  cost_usd: number;
  calls: number;
}

export interface Club {
  id: string;
  name: string;
  category: string | null;
  pre_approved_budget: number;
  notes: string | null;
  spent: number;
  remaining_balance: number;
  lines_reviewed: number;
}

export interface BulkImportRow {
  row: number;
  status: "ok" | "error";
  request_id?: string;
  lines_loaded?: number;
  error?: string;
}

export interface BulkImportResult {
  total: number;
  succeeded: number;
  failed: number;
  results: BulkImportRow[];
}
