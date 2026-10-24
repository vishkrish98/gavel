import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { ConsistencyReport } from "../types";
import { Empty, ErrorState, Loading } from "../components/StateBox";

export function ConsistencyScreen() {
  const [report, setReport] = useState<ConsistencyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    api
      .consistency()
      .then(setReport)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load the consistency report."))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  if (loading) return <Loading label="Comparing last year's decisions against this year's rules…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!report || report.matched === 0) {
    return <Empty label="No prior decisions to compare yet." hint="This needs requests loaded and lines classified first." />;
  }

  const inconsistent = report.decisions.filter((d) => d.inconsistent);

  return (
    <div className="stack">
      <div className="panel">
        <h2>Consistency</h2>
        <p className="hint" style={{ marginTop: 4 }}>
          Compares last year's committee decisions against what this year's approved rules would allow for
          the same line, using the current line's actual facts.
        </p>
        <div className="grid grid-3" style={{ marginTop: 16 }}>
          <div>
            <div className="consistency-stat">{report.inconsistent_count}</div>
            <div className="consistency-stat-label">of {report.matched} matched decisions disagree</div>
          </div>
          <div>
            <div className="consistency-stat">{(report.inconsistency_rate * 100).toFixed(1)}%</div>
            <div className="consistency-stat-label">inconsistency rate</div>
          </div>
          <div>
            <div className="consistency-stat">{report.total - report.matched}</div>
            <div className="consistency-stat-label">could not be matched to a current line</div>
          </div>
        </div>
      </div>

      {inconsistent.length === 0 ? (
        <div className="panel">
          <Empty label="No inconsistencies found." hint="Every matched prior decision agrees with what this year's rules would allow." />
        </div>
      ) : (
        <div className="panel">
          <div className="panel-title">Decisions that disagree with the policy</div>
          <div className="table-wrap">
            <table className="review-table">
              <thead>
                <tr>
                  <th>Club</th>
                  <th>Description</th>
                  <th>Requested</th>
                  <th>Approved last year</th>
                  <th>Policy would allow</th>
                  <th>Dollar gap</th>
                </tr>
              </thead>
              <tbody>
                {inconsistent.map((d) => (
                  <tr key={d.decision_id}>
                    <td>{d.club}</td>
                    <td>{d.description}</td>
                    <td className="tabular">${d.requested.toLocaleString()}</td>
                    <td className="tabular">${d.approved.toLocaleString()}</td>
                    <td className="tabular">${(d.engine_allowed ?? 0).toLocaleString()}</td>
                    <td className="tabular" style={{ color: "var(--denied)" }}>
                      ${Math.abs(d.approved - (d.engine_allowed ?? 0)).toLocaleString()}
                    </td>
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
