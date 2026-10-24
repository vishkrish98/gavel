import { useEffect, useState } from "react";
import { api } from "../api";
import type { AuditEvent, RunStatus } from "../types";
import { AgentNameplates } from "../components/AgentNameplates";
import { EventFeed } from "../components/EventFeed";
import { Empty, ErrorState, Loading } from "../components/StateBox";

interface Props {
  run: RunStatus | null;
  events: AuditEvent[];
  onStart: (requestIds: string[] | null) => Promise<void>;
  starting: boolean;
  startError: string | null;
}

export function RunScreen({ run, events, onStart, starting, startError }: Props) {
  const [requests, setRequests] = useState<{ id: string; club: string; line_count: number }[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loadingRequests, setLoadingRequests] = useState(true);

  useEffect(() => {
    api
      .listRequests()
      .then((r) => {
        setRequests(r);
        setSelected(new Set(r.map((x) => x.id)));
      })
      .finally(() => setLoadingRequests(false));
  }, [run?.id]);

  if (loadingRequests) return <Loading label="Loading requests…" />;

  if (requests.length === 0) {
    return <Empty label="No requests loaded yet." hint="Go to Start and try the sample, or upload your own request." />;
  }

  const expectedCalls = selected.size * 2 + 2; // rough: reader + skeptic per request, compiler + memo
  const actualCalls = run ? Object.values(run.progress_by_agent).reduce((sum, p) => sum + p.calls, 0) : 0;
  const progressPct = run ? Math.min(100, Math.round((actualCalls / Math.max(expectedCalls, 1)) * 100)) : 0;

  return (
    <div className="stack">
      <div className="panel row-between">
        <div>
          <h2>Run</h2>
          <p className="hint" style={{ marginTop: 4 }}>
            {run ? `Run ${run.id} — ${run.status}` : `${selected.size} of ${requests.length} requests selected.`}
          </p>
        </div>
        {!run || run.status !== "running" ? (
          <button id="start-run-btn" className="btn btn-primary" onClick={() => onStart(Array.from(selected))} disabled={starting || selected.size === 0}>
            {starting ? "Starting…" : run ? "Run again" : "Start run"}
          </button>
        ) : (
          <span className="chip reduced">Running…</span>
        )}
      </div>

      {startError && <ErrorState message={startError} />}

      {!run && (
        <div className="panel">
          <div className="panel-title">Choose requests</div>
          <div className="row" style={{ marginBottom: 10 }}>
            <button className="btn btn-sm" onClick={() => setSelected(new Set(requests.map((r) => r.id)))}>
              Select all
            </button>
            <button className="btn btn-sm" onClick={() => setSelected(new Set())}>
              Select none
            </button>
          </div>
          <div className="table-wrap">
            <table className="review-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Request</th>
                  <th>Club</th>
                  <th>Lines</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(r.id)}
                        onChange={(e) => {
                          const next = new Set(selected);
                          if (e.target.checked) next.add(r.id);
                          else next.delete(r.id);
                          setSelected(next);
                        }}
                        aria-label={`Include ${r.id}`}
                      />
                    </td>
                    <td>{r.id}</td>
                    <td>{r.club}</td>
                    <td>{r.line_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {run && (
        <>
          <div className="panel">
            <div className="panel-title">Agents</div>
            <AgentNameplates run={run} />
            <div style={{ marginTop: 16 }}>
              <div className="row-between" style={{ marginBottom: 6 }}>
                <span className="hint">Progress ({actualCalls} model calls so far)</span>
                <span className="hint">{progressPct}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
              </div>
            </div>
            {run.status !== "running" && (
              <p className="hint" style={{ marginTop: 12 }}>
                Finished with status <strong>{run.status}</strong>
                {run.status === "limit_hit" && " — a safety limit (token cap, timeout, or request limit) ended the run cleanly."}
                . {run.usage_total.calls} model calls, {run.usage_total.total_tokens.toLocaleString()} tokens, $
                {run.usage_total.cost_usd.toFixed(6)}, {run.usage_total.seconds.toFixed(1)}s.
              </p>
            )}
          </div>

          <div className="panel">
            <div className="panel-title">Event trace (tool calls &amp; agent steps)</div>
            <EventFeed events={events} />
          </div>
        </>
      )}
    </div>
  );
}
