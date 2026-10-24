import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { PolicyParagraph, Rule } from "../types";
import { Empty, ErrorState, Loading } from "../components/StateBox";

const APPROVER_NAME = "committee-member";

function decoyReason(text: string): string {
  if (/\bmay\b(?!\s+not)/i.test(text)) {
    return "Guidance, not a binding rule — “may” leaves it to the committee's discretion rather than requiring or prohibiting anything.";
  }
  return "Informational — describes the committee or policy itself, not a checkable rule about a purchase.";
}

export function RulesScreen({ onReadyToRun }: { onReadyToRun: () => void }) {
  const [paragraphs, setParagraphs] = useState<PolicyParagraph[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, r] = await Promise.all([api.listPolicy(), api.listRules()]);
      setParagraphs(p);
      setRules(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load the policy or rules.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCompile() {
    setCompiling(true);
    setError(null);
    try {
      await api.compilePolicy();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Compilation failed.");
    } finally {
      setCompiling(false);
    }
  }

  async function handleApprove(id: string) {
    setBusyId(id);
    try {
      await api.approveRule(id, APPROVER_NAME);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve that rule.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(id: string) {
    setBusyId(id);
    try {
      await api.rejectRule(id, APPROVER_NAME);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject that rule.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleApproveAll() {
    setBusyId("__all__");
    try {
      await api.approveAllVerified(APPROVER_NAME);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve the verified rules.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <Loading label="Loading policy and rules…" />;

  if (paragraphs.length === 0) {
    return <Empty label="No policy loaded yet." hint="Go to Start and try the sample, or paste/upload your own policy." />;
  }

  const rulesByPara = new Map<string, Rule[]>();
  for (const rule of rules) {
    rulesByPara.set(rule.para_id, [...(rulesByPara.get(rule.para_id) ?? []), rule]);
  }
  const compiled = rules.length > 0;
  const approvedCount = rules.filter((r) => r.status === "approved").length;
  const verifiedProposedCount = rules.filter((r) => r.status === "proposed" && r.quote_verified).length;

  return (
    <div className="stack">
      <div className="panel row-between">
        <div>
          <h2>Rules</h2>
          <p className="hint" style={{ marginTop: 4 }}>
            {compiled
              ? `${approvedCount} approved, ${verifiedProposedCount} awaiting your approval, of ${rules.length} proposed from ${paragraphs.length} policy paragraphs.`
              : `${paragraphs.length} policy paragraphs loaded. Compile to propose rules for you to approve.`}
          </p>
        </div>
        <div className="row">
          {!compiled && (
            <button className="btn btn-primary" onClick={handleCompile} disabled={compiling}>
              {compiling ? "Compiling…" : "Compile policy"}
            </button>
          )}
          {compiled && verifiedProposedCount > 0 && (
            <button id="approve-all-btn" className="btn btn-primary" onClick={handleApproveAll} disabled={busyId !== null}>
              {busyId === "__all__" ? "Approving…" : `Approve all verified (${verifiedProposedCount})`}
            </button>
          )}
          {compiled && approvedCount > 0 && (
            <button id="go-to-run-btn" className="btn" onClick={onReadyToRun}>
              Go to Run →
            </button>
          )}
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {compiled && (
        <div className="grid grid-2">
          {paragraphs.map((para) => {
            const paraRules = rulesByPara.get(para.para_id) ?? [];
            if (paraRules.length === 0) {
              return (
                <div key={para.para_id} className="decoy-card">
                  <div className="row-between">
                    <span className="rule-type">{para.para_id}</span>
                    <span className="badge status-rejected">Not a rule</span>
                  </div>
                  <p style={{ margin: "8px 0 0", fontSize: 13.5 }}>{para.text}</p>
                  <p className="why">{decoyReason(para.text)}</p>
                </div>
              );
            }
            return paraRules.map((rule) => (
              <div key={rule.id} className={`rule-card ${rule.status === "rejected" ? "rejected" : ""}`}>
                <div className="rule-head">
                  <span className="rule-type">{rule.type}</span>
                  <div className="row" style={{ gap: 6 }}>
                    <span className={`badge ${rule.quote_verified ? "verified" : "unverified"}`}>
                      {rule.quote_verified ? "Verified" : "Unverified"}
                    </span>
                    <span className={`badge status-${rule.status}`}>{rule.status}</span>
                  </div>
                </div>
                <div className="quote-block">&ldquo;{rule.quote}&rdquo;</div>
                <p className="hint">
                  Paragraph {rule.para_id} · params: {JSON.stringify(rule.params)}
                  {rule.approved_by ? ` · approved by ${rule.approved_by}` : ""}
                </p>
                {rule.status === "proposed" && (
                  <div className="row">
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => handleApprove(rule.id)}
                      disabled={busyId === rule.id || !rule.quote_verified}
                      title={!rule.quote_verified ? "Cannot approve: quote did not verify against the policy text" : undefined}
                    >
                      Approve
                    </button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleReject(rule.id)} disabled={busyId === rule.id}>
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ));
          })}
        </div>
      )}
    </div>
  );
}
