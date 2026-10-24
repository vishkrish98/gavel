import type {
  AllocateResult,
  AuditEvent,
  ConsistencyReport,
  DemoLoadResult,
  Draft,
  ExplainResult,
  PolicyParagraph,
  RequestDetail,
  Rule,
  RunStatus,
  UsageByRun,
  Verdict,
} from "./types";

// Same-origin in production (run.py serves both from one FastAPI app). In dev (`npm run dev`),
// Vite's proxy (vite.config.ts) forwards /api and /health to the backend on 8000.
const BASE = "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "Could not reach the server. Is it still running?");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // ignore: non-JSON error body, keep the generic message
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/csv")) return (await response.text()) as unknown as T;
  return (await response.json()) as T;
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  // Policy
  uploadPolicyText: (text: string) => {
    const form = new FormData();
    form.append("text", text);
    return request<{ paragraphs_loaded: number }>("/api/policy", { method: "POST", body: form });
  },
  uploadPolicyFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ paragraphs_loaded: number }>("/api/policy", { method: "POST", body: form });
  },
  compilePolicy: () => postJson<{ summary: Record<string, unknown>; rules: Rule[] }>("/api/policy/compile", {}),
  listPolicy: () => request<PolicyParagraph[]>("/api/policy/paragraphs"),
  listRules: (status?: string) => request<Rule[]>(status ? `/api/rules?status=${status}` : "/api/rules"),
  approveRule: (id: string, by: string) => postJson<{ rule_id: string; approved: boolean; reason?: string }>(`/api/rules/${id}/approve`, { by }),
  rejectRule: (id: string, by: string, reason?: string) => postJson<{ rule_id: string; rejected: boolean }>(`/api/rules/${id}/reject`, { by, reason }),
  approveAllVerified: (by: string) => postJson<{ approved_rule_ids: string[]; count: number }>("/api/rules/approve-all-verified", { by }),

  // Requests
  createRequestJson: (payload: Record<string, unknown>) => postJson<{ request_id: string; lines_loaded: number }>("/api/requests", payload),
  uploadRequestFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ request_id: string; lines_loaded: number }>("/api/requests", { method: "POST", body: form });
  },
  demoLoad: () => postJson<DemoLoadResult>("/api/demo/load", {}),
  listRequests: () => request<(RequestDetail & { line_count: number })[]>("/api/requests"),
  getRequest: (id: string) => request<RequestDetail>(`/api/requests/${id}`),

  // Runs
  startRun: (requestIds: string[] | null, benchmarkMode = false) =>
    postJson<{ run_id: string; status: string; request_count: number }>("/api/runs", {
      request_ids: requestIds,
      benchmark_mode: benchmarkMode,
    }),
  getRun: (id: string) => request<RunStatus>(`/api/runs/${id}`),
  getRunEvents: (id: string) => request<AuditEvent[]>(`/api/runs/${id}/events`),
  getRunVerdicts: (id: string) => request<Verdict[]>(`/api/runs/${id}/verdicts`),
  getRunDrafts: (id: string) => request<Draft[]>(`/api/runs/${id}/drafts`),
  approveDraft: (id: string, by: string) => postJson<{ draft_id: string; approved: boolean }>(`/api/drafts/${id}/approve`, { by }),
  listRuns: () => request<RunStatus[]>("/api/runs"),

  // Consistency / optimizer / explain / usage
  consistency: () => request<ConsistencyReport>("/api/consistency"),
  allocate: (pot: number, alpha: number) => postJson<AllocateResult>("/api/allocate", { pot, alpha }),
  explainLine: (lineId: string) => request<ExplainResult>(`/api/lines/${lineId}/explain`),
  usage: (runId?: string) => request<{ runs?: UsageByRun[]; run_id?: string; by_agent?: Record<string, UsageByRun>; total?: UsageByRun }>(
    runId ? `/api/usage?run_id=${encodeURIComponent(runId)}` : "/api/usage",
  ),
  exportCsvUrl: (runId: string) => `${BASE}/api/export.csv?run_id=${encodeURIComponent(runId)}`,
};
