import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import type { ExplainResult, Verdict } from "../types";
import { VerdictChip } from "../components/VerdictChip";
import { Empty, ErrorState, Loading } from "../components/StateBox";

export function ReviewScreen({ runId }: { runId: string | null }) {
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verdictFilter, setVerdictFilter] = useState("all");
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Verdict | null>(null);
  const [explain, setExplain] = useState<ExplainResult | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  useEffect(() => {
    if (!runId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .getRunVerdicts(runId)
      .then(setVerdicts)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load verdicts."))
      .finally(() => setLoading(false));
  }, [runId]);

  const filtered = useMemo(() => {
    return verdicts.filter((v) => {
      if (verdictFilter !== "all" && v.verdict !== verdictFilter) return false;
      if (flaggedOnly && !v.flagged_for_review) return false;
      if (search && !(`${v.club} ${v.description} ${v.line_id}`.toLowerCase().includes(search.toLowerCase()))) return false;
      return true;
    });
  }, [verdicts, verdictFilter, flaggedOnly, search]);

  async function openLine(v: Verdict) {
    setSelected(v);
    setExplain(null);
    setExplainLoading(true);
    try {
      const result = await api.explainLine(v.line_id);
      setExplain(result);
    } catch {
      setExplain(null);
    } finally {
      setExplainLoading(false);
    }
  }

  if (!runId) {
    return <Empty label="No run yet." hint="Start a run from the Run tab, then come back here to review every line." />;
  }
  if (loading) return <Loading label="Loading verdicts…" />;
  if (error) return <ErrorState message={error} />;
  if (verdicts.length === 0) {
    return <Empty label="This run hasn't produced any verdicts yet." hint="Check the Run tab — it may still be in progress." />;
  }

  return (
    <div className="stack">
      <div className="panel">
        <div className="row-between">
          <h2>Review</h2>
          <span className="hint">{filtered.length} of {verdicts.length} lines</span>
        </div>
        <div className="filters" style={{ marginTop: 14 }}>
          <select value={verdictFilter} onChange={(e) => setVerdictFilter(e.target.value)} aria-label="Filter by verdict">
            <option value="all">All verdicts</option>
            <option value="allowed">Allowed</option>
            <option value="reduced">Reduced</option>
            <option value="denied">Denied</option>
            <option value="needs_docs">Needs documents</option>
          </select>
          <label className="row" style={{ fontSize: 13, gap: 6 }}>
            <input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} />
            Flagged by Skeptic only
          </label>
          <input
            type="search"
            placeholder="Search club, description, line id…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search"
          />
        </div>
        <div className="table-wrap">
          <table className="review-table">
            <thead>
              <tr>
                <th>Club</th>
                <th>Line</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Verdict</th>
                <th>Allowed</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => (
                <tr key={v.line_id} className="clickable" onClick={() => openLine(v)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && openLine(v)}>
                  <td>{v.club}</td>
                  <td className="tabular">{v.line_id}</td>
                  <td>{v.description}</td>
                  <td className="tabular">${v.amount.toLocaleString()}</td>
                  <td>
                    <VerdictChip verdict={v.verdict} />
                    {v.flagged_for_review ? <span className="chip flag">Review this</span> : null}
                  </td>
                  <td className="tabular">${v.allowed_amount.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="side-panel-overlay" onClick={() => setSelected(null)}>
          <div className="side-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={`Line ${selected.line_id} details`}>
            <button className="btn btn-sm side-panel-close" onClick={() => setSelected(null)} autoFocus>
              Close
            </button>
            <div>
              <h3>{selected.line_id}</h3>
              <p className="hint">
                {selected.club} · {selected.request_id}
              </p>
            </div>
            <p>{selected.description}</p>
            <div className="row">
              <VerdictChip verdict={selected.verdict} />
              {selected.flagged_for_review ? <span className="chip flag">Review this</span> : null}
            </div>
            <dl className="fact-grid">
              <dt>Requested</dt>
              <dd>${selected.amount.toLocaleString()}</dd>
              <dt>Allowed</dt>
              <dd>${selected.allowed_amount.toLocaleString()}</dd>
            </dl>
            {selected.explanation && (
              <div>
                <div className="panel-title">Skeptic's note</div>
                <p style={{ fontSize: 13.5 }}>{selected.explanation}</p>
              </div>
            )}
            <div>
              <div className="panel-title">Rule citation</div>
              {explainLoading && <Loading label="Loading citation…" />}
              {!explainLoading && explain && explain.citations.length === 0 && (
                <p className="hint">No rule applied to this line — it was allowed as requested.</p>
              )}
              {!explainLoading &&
                explain?.citations.map((c) => (
                  <div key={c.rule_id} style={{ marginBottom: 10 }}>
                    <p className="hint">
                      Rule {c.rule_id} · policy paragraph {c.para_id}
                    </p>
                    <div className="quote-block">&ldquo;{c.quote}&rdquo;</div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
