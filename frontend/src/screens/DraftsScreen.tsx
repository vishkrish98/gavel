import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { Draft } from "../types";
import { Empty, ErrorState, Loading } from "../components/StateBox";

const APPROVER_NAME = "committee-member";

export function DraftsScreen({ runId }: { runId: string | null }) {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function load() {
    if (!runId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .getRunDrafts(runId)
      .then(setDrafts)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load drafts."))
      .finally(() => setLoading(false));
  }

  useEffect(load, [runId]);

  async function handleApprove(id: string) {
    setBusyId(id);
    try {
      await api.approveDraft(id, APPROVER_NAME);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve that draft.");
    } finally {
      setBusyId(null);
    }
  }

  if (!runId) {
    return <Empty label="No run yet." hint="Drafted committee questions and the decision memo appear here once a run finishes." />;
  }
  if (loading) return <Loading label="Loading drafts…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (drafts.length === 0) {
    return <Empty label="No drafts for this run." hint="Drafts are only written for requests with a needs-documents line, a Skeptic flag, or a large reduction." />;
  }

  const memo = drafts.find((d) => d.kind === "memo");
  const questionDrafts = drafts.filter((d) => d.kind === "questions");

  return (
    <div className="stack">
      <div className="panel row-between">
        <div>
          <h2>Drafts</h2>
          <p className="hint" style={{ marginTop: 4 }}>
            Everything here is a DRAFT until the committee approves it. Nothing is final, and nothing is
            exported on its own.
          </p>
        </div>
        <a className="btn" href={api.exportCsvUrl(runId)} download={`gavel_verdicts_${runId}.csv`}>
          Download verdicts CSV
        </a>
      </div>

      {memo && (
        <div className="panel draft-card">
          <div className="row-between">
            <span className={`draft-label ${memo.status === "approved" ? "approved" : ""}`}>
              {memo.status === "approved" ? "Approved" : "DRAFT"} — Decision memo
            </span>
            {memo.status !== "approved" && (
              <button className="btn btn-sm btn-primary" onClick={() => handleApprove(memo.id)} disabled={busyId === memo.id}>
                {busyId === memo.id ? "Approving…" : "Approve"}
              </button>
            )}
          </div>
          <div className="draft-memo">{memo.content.memo}</div>
        </div>
      )}

      {questionDrafts.map((draft) => (
        <div key={draft.id} className="panel draft-card">
          <div className="row-between">
            <span className={`draft-label ${draft.status === "approved" ? "approved" : ""}`}>
              {draft.status === "approved" ? "Approved" : "DRAFT"} — Questions for {draft.request_id}
            </span>
            {draft.status !== "approved" && (
              <button className="btn btn-sm btn-primary" onClick={() => handleApprove(draft.id)} disabled={busyId === draft.id}>
                {busyId === draft.id ? "Approving…" : "Approve"}
              </button>
            )}
          </div>
          {(draft.content.questions ?? []).map((q, i) => (
            <div key={i} className="draft-question">
              {q.line_id && <p className="hint" style={{ marginBottom: 4 }}>Line {q.line_id}</p>}
              <p style={{ margin: 0 }}>{q.question}</p>
              {q.quote && <div className="quote-block" style={{ marginTop: 8 }}>&ldquo;{q.quote}&rdquo;</div>}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
