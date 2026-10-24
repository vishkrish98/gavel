import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { UsageByRun } from "../types";
import { Empty, ErrorState, Loading } from "../components/StateBox";

export function CostScreen({ runId }: { runId: string | null }) {
  const [byAgent, setByAgent] = useState<Record<string, UsageByRun> | null>(null);
  const [total, setTotal] = useState<UsageByRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!runId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .usage(runId)
      .then((r) => {
        setByAgent((r.by_agent as Record<string, UsageByRun>) ?? null);
        setTotal((r.total as UsageByRun) ?? null);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load usage."))
      .finally(() => setLoading(false));
  }

  useEffect(load, [runId]);

  if (!runId) {
    return <Empty label="No run yet." hint="Token and cost totals appear here once a run has started." />;
  }
  if (loading) return <Loading label="Loading usage…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!total || total.calls === 0) {
    return <Empty label="No model calls logged for this run yet." />;
  }

  return (
    <div className="stack">
      <div className="panel">
        <h2>Cost</h2>
        <p className="hint" style={{ marginTop: 4 }}>
          Real token counts and cost for run {runId}, from the provider's own response fields — never
          estimated.
        </p>
        <div className="grid grid-3" style={{ marginTop: 18 }}>
          <div>
            <div className="cost-figure">${total.cost_usd.toFixed(6)}</div>
            <div className="cost-label">Total cost</div>
          </div>
          <div>
            <div className="cost-figure">{total.total_tokens.toLocaleString()}</div>
            <div className="cost-label">Total tokens</div>
          </div>
          <div>
            <div className="cost-figure">{total.calls}</div>
            <div className="cost-label">Model calls</div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">Tokens by type</div>
        <div className="grid grid-3">
          <div>
            <div className="cost-figure" style={{ fontSize: 22 }}>{total.input_tokens.toLocaleString()}</div>
            <div className="cost-label">Input</div>
          </div>
          <div>
            <div className="cost-figure" style={{ fontSize: 22 }}>{total.cached_tokens.toLocaleString()}</div>
            <div className="cost-label">Cached</div>
          </div>
          <div>
            <div className="cost-figure" style={{ fontSize: 22 }}>{total.output_tokens.toLocaleString()}</div>
            <div className="cost-label">Output</div>
          </div>
        </div>
      </div>

      {byAgent && (
        <div className="panel">
          <div className="panel-title">By agent</div>
          <div className="table-wrap">
            <table className="review-table">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Calls</th>
                  <th>Input</th>
                  <th>Cached</th>
                  <th>Output</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(byAgent).map(([name, u]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td className="tabular">{u.calls}</td>
                    <td className="tabular">{u.input_tokens.toLocaleString()}</td>
                    <td className="tabular">{u.cached_tokens.toLocaleString()}</td>
                    <td className="tabular">{u.output_tokens.toLocaleString()}</td>
                    <td className="tabular">{u.total_tokens.toLocaleString()}</td>
                    <td className="tabular">${u.cost_usd.toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
