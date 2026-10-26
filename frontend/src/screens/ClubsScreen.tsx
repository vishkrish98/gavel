import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { BulkImportResult, Club } from "../types";
import { Empty, ErrorState, Loading } from "../components/StateBox";

export function ClubsScreen({ runId, onRequestsImported }: { runId: string | null; onRequestsImported?: () => void }) {
  const [clubs, setClubs] = useState<Club[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [clubsText, setClubsText] = useState("");
  const [clubsBusy, setClubsBusy] = useState(false);
  const [clubsMessage, setClubsMessage] = useState<string | null>(null);
  const [clubsErr, setClubsErr] = useState<string | null>(null);

  const [requestsText, setRequestsText] = useState("");
  const [requestsBusy, setRequestsBusy] = useState(false);
  const [requestsResult, setRequestsResult] = useState<BulkImportResult | null>(null);
  const [requestsErr, setRequestsErr] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    api
      .listClubs(runId ?? undefined)
      .then(setClubs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load clubs."))
      .finally(() => setLoading(false));
  }

  useEffect(load, [runId]);

  async function handleClubsPaste() {
    if (!clubsText.trim()) return;
    setClubsBusy(true);
    setClubsErr(null);
    setClubsMessage(null);
    try {
      const parsed = JSON.parse(clubsText);
      const result = await api.importClubsBulkJson(parsed);
      setClubsMessage(`Imported ${result.imported} club(s).`);
      setClubsText("");
      load();
    } catch (err) {
      setClubsErr(err instanceof ApiError ? err.message : err instanceof SyntaxError ? "That's not valid JSON." : "Could not import clubs.");
    } finally {
      setClubsBusy(false);
    }
  }

  async function handleClubsFile(file: File) {
    setClubsBusy(true);
    setClubsErr(null);
    setClubsMessage(null);
    try {
      const result = await api.importClubsBulkFile(file);
      setClubsMessage(`Imported ${result.imported} club(s).`);
      load();
    } catch (err) {
      setClubsErr(err instanceof ApiError ? err.message : "Could not import that file.");
    } finally {
      setClubsBusy(false);
    }
  }

  async function handleRequestsPaste() {
    if (!requestsText.trim()) return;
    setRequestsBusy(true);
    setRequestsErr(null);
    setRequestsResult(null);
    try {
      const parsed = JSON.parse(requestsText);
      const result = await api.createRequestsBulkJson(parsed);
      setRequestsResult(result);
      setRequestsText("");
      if (result.succeeded > 0) onRequestsImported?.();
    } catch (err) {
      setRequestsErr(err instanceof ApiError ? err.message : err instanceof SyntaxError ? "That's not valid JSON." : "Could not import requests.");
    } finally {
      setRequestsBusy(false);
    }
  }

  async function handleRequestsFile(file: File) {
    setRequestsBusy(true);
    setRequestsErr(null);
    setRequestsResult(null);
    try {
      const result = await api.uploadRequestsBulkFile(file);
      setRequestsResult(result);
      if (result.succeeded > 0) onRequestsImported?.();
    } catch (err) {
      setRequestsErr(err instanceof ApiError ? err.message : "Could not import that file.");
    } finally {
      setRequestsBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="panel">
        <h2>Clubs</h2>
        <p className="hint" style={{ marginTop: 4 }}>
          Each club's pre-approved budget and running balance. Balance = budget minus every allowed or
          reduced dollar from {runId ? "this run" : "its most recent run"}. A negative balance means the
          club is over its pre-approved budget.
        </p>
        {loading && <Loading label="Loading clubs…" />}
        {error && <ErrorState message={error} onRetry={load} />}
        {!loading && !error && (!clubs || clubs.length === 0) && (
          <Empty label="No clubs registered yet." hint="Import clubs below, or click Try the sample on the Start tab." />
        )}
        {!loading && !error && clubs && clubs.length > 0 && (
          <div className="table-wrap" style={{ marginTop: 14 }}>
            <table className="review-table">
              <thead>
                <tr>
                  <th>Club</th>
                  <th>Category</th>
                  <th>Pre-approved budget</th>
                  <th>Spent</th>
                  <th>Remaining</th>
                  <th>Lines reviewed</th>
                </tr>
              </thead>
              <tbody>
                {clubs.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.category ?? "—"}</td>
                    <td className="tabular">${c.pre_approved_budget.toLocaleString()}</td>
                    <td className="tabular">${c.spent.toLocaleString()}</td>
                    <td className="tabular" style={{ color: c.remaining_balance < 0 ? "var(--error)" : undefined }}>
                      ${c.remaining_balance.toLocaleString()}
                    </td>
                    <td className="tabular">{c.lines_reviewed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="grid grid-2">
        <div className="panel upload-card">
          <h3>Import clubs and budgets</h3>
          <p className="hint">
            Paste a JSON array of clubs, or upload a .json file. Each club needs a <code>name</code>; add{" "}
            <code>pre_approved_budget</code> and <code>category</code> if you have them. Re-importing a
            club by the same name updates its budget in place, so this is also how you'd roll the
            registry over to a new year's allocations.
          </p>
          <textarea
            placeholder='[{"name": "Robotics Club", "category": "academic", "pre_approved_budget": 6000}]'
            value={clubsText}
            onChange={(e) => setClubsText(e.target.value)}
          />
          <div className="row" style={{ marginTop: 10 }}>
            <button id="import-clubs-btn" className="btn btn-sm" onClick={handleClubsPaste} disabled={clubsBusy || !clubsText.trim()}>
              Import pasted clubs
            </button>
            <label className="btn btn-sm">
              Upload file
              <input
                type="file"
                accept=".json"
                style={{ display: "none" }}
                onChange={(e) => e.target.files?.[0] && handleClubsFile(e.target.files[0])}
              />
            </label>
          </div>
          {clubsMessage && <p className="hint" style={{ color: "var(--allowed)" }}>{clubsMessage}</p>}
          {clubsErr && <p className="hint" style={{ color: "var(--error)" }}>{clubsErr}</p>}
        </div>

        <div className="panel upload-card">
          <h3>Import many requests at once</h3>
          <p className="hint">
            Built for the once-a-year budgeting pass, where every club submits its full annual
            budget in one weekend. Paste a JSON array of requests (same shape as a single request
            on the Start tab), or upload a .json file. Each row is imported independently, so one
            bad row won't block the rest. Different clubs can use different structures: flat
            lines, or each line tagged with an optional <code>goal</code>/<code>program</code> for
            clubs that budget by goal → program (event) → line item. For a single additional
            request between annual cycles, like a weekly committee meeting handles, use the Start
            tab instead.
          </p>
          <textarea
            placeholder='[{"club": "Chess Club", "event_date": "2026-12-01", "submitted_date": "2026-11-01", "justification": "...", "lines": [{"description": "Venue rental", "amount": 300}]}]'
            value={requestsText}
            onChange={(e) => setRequestsText(e.target.value)}
          />
          <div className="row" style={{ marginTop: 10 }}>
            <button id="import-requests-bulk-btn" className="btn btn-sm" onClick={handleRequestsPaste} disabled={requestsBusy || !requestsText.trim()}>
              Import pasted requests
            </button>
            <label className="btn btn-sm">
              Upload file
              <input
                type="file"
                accept=".json"
                style={{ display: "none" }}
                onChange={(e) => e.target.files?.[0] && handleRequestsFile(e.target.files[0])}
              />
            </label>
          </div>
          {requestsErr && <p className="hint" style={{ color: "var(--error)" }}>{requestsErr}</p>}
          {requestsResult && (
            <div style={{ marginTop: 10 }}>
              <p className="hint" style={{ color: requestsResult.failed === 0 ? "var(--allowed)" : "var(--error)" }}>
                {requestsResult.succeeded}/{requestsResult.total} imported.
              </p>
              {requestsResult.results
                .filter((r) => r.status === "error")
                .map((r) => (
                  <p key={r.row} className="hint" style={{ color: "var(--error)" }}>
                    Row {r.row}: {r.error}
                  </p>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
