import { useState } from "react";
import { api, ApiError } from "../api";
import type { DemoLoadResult } from "../types";
import { ErrorState, Loading } from "../components/StateBox";

interface Props {
  onDemoLoaded: (result: DemoLoadResult) => void;
  onPolicyUploaded: () => void;
  onRequestUploaded: () => void;
}

export function StartScreen({ onDemoLoaded, onPolicyUploaded, onRequestUploaded }: Props) {
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  const [policyText, setPolicyText] = useState("");
  const [policyBusy, setPolicyBusy] = useState(false);
  const [policyMessage, setPolicyMessage] = useState<string | null>(null);
  const [policyErr, setPolicyErr] = useState<string | null>(null);

  const [requestText, setRequestText] = useState("");
  const [requestBusy, setRequestBusy] = useState(false);
  const [requestMessage, setRequestMessage] = useState<string | null>(null);
  const [requestErr, setRequestErr] = useState<string | null>(null);

  async function handleTrySample() {
    setDemoLoading(true);
    setDemoError(null);
    try {
      const result = await api.demoLoad();
      onDemoLoaded(result);
    } catch (err) {
      setDemoError(err instanceof ApiError ? err.message : "Could not load the sample.");
    } finally {
      setDemoLoading(false);
    }
  }

  async function handlePolicyFile(file: File) {
    setPolicyBusy(true);
    setPolicyErr(null);
    setPolicyMessage(null);
    try {
      const result = await api.uploadPolicyFile(file);
      setPolicyMessage(`Loaded ${result.paragraphs_loaded} paragraphs. Go to the Rules tab to compile and approve them.`);
      onPolicyUploaded();
    } catch (err) {
      setPolicyErr(err instanceof ApiError ? err.message : "Could not upload that file.");
    } finally {
      setPolicyBusy(false);
    }
  }

  async function handlePolicyPaste() {
    if (!policyText.trim()) return;
    setPolicyBusy(true);
    setPolicyErr(null);
    setPolicyMessage(null);
    try {
      const result = await api.uploadPolicyText(policyText);
      setPolicyMessage(`Loaded ${result.paragraphs_loaded} paragraphs. Go to the Rules tab to compile and approve them.`);
      onPolicyUploaded();
    } catch (err) {
      setPolicyErr(err instanceof ApiError ? err.message : "Could not parse that text.");
    } finally {
      setPolicyBusy(false);
    }
  }

  async function handleRequestFile(file: File) {
    setRequestBusy(true);
    setRequestErr(null);
    setRequestMessage(null);
    try {
      const result = await api.uploadRequestFile(file);
      setRequestMessage(`Loaded request ${result.request_id} with ${result.lines_loaded} line item(s).`);
      onRequestUploaded();
    } catch (err) {
      setRequestErr(err instanceof ApiError ? err.message : "Could not upload that file.");
    } finally {
      setRequestBusy(false);
    }
  }

  async function handleRequestPaste() {
    if (!requestText.trim()) return;
    setRequestBusy(true);
    setRequestErr(null);
    setRequestMessage(null);
    try {
      const payload = JSON.parse(requestText);
      const result = await api.createRequestJson(payload);
      setRequestMessage(`Loaded request ${result.request_id} with ${result.lines_loaded} line item(s).`);
      onRequestUploaded();
    } catch (err) {
      if (err instanceof SyntaxError) setRequestErr("That isn't valid JSON. Paste a request object with club, event_date, submitted_date, justification, and lines.");
      else setRequestErr(err instanceof ApiError ? err.message : "Could not load that request.");
    } finally {
      setRequestBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="panel hero-panel">
        <h1>Gavel</h1>
        <p className="lede">
          Decision support for a student-government funding committee. Gavel turns your policy into
          machine-checkable rules you approve, checks every budget line against them with a citation,
          and drafts committee questions — it recommends and explains; your committee always decides.
        </p>
        <button id="try-sample-btn" className="btn btn-primary btn-lg" onClick={handleTrySample} disabled={demoLoading}>
          {demoLoading ? "Loading sample…" : "Try the sample"}
        </button>
        <p className="hint">
          Loads a synthetic policy and 24 sample club requests, then compiles rules for you to review and
          approve — no uploads needed.
        </p>
        {demoLoading && <Loading label="Loading sample data and compiling the policy…" />}
        {demoError && <ErrorState message={demoError} onRetry={handleTrySample} />}
      </div>

      <div className="grid grid-2">
        <div className="panel upload-card">
          <h3>Use your own policy</h3>
          <p className="hint">
            Paste your policy text below, or upload a .txt file. Each rule paragraph should be on its own
            line, starting with a number like &ldquo;3.1&nbsp; Funds may not be used to purchase
            alcohol.&rdquo;
          </p>
          <textarea
            placeholder="3.1  Funds may not be used to purchase alcohol.&#10;3.2  Club apparel is funded up to $20 per item."
            value={policyText}
            onChange={(e) => setPolicyText(e.target.value)}
          />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn btn-sm" onClick={handlePolicyPaste} disabled={policyBusy || !policyText.trim()}>
              Load pasted text
            </button>
            <label className="btn btn-sm">
              Upload .txt
              <input
                type="file"
                accept=".txt"
                style={{ display: "none" }}
                onChange={(e) => e.target.files?.[0] && handlePolicyFile(e.target.files[0])}
              />
            </label>
          </div>
          {policyMessage && <p className="hint" style={{ color: "var(--allowed)" }}>{policyMessage}</p>}
          {policyErr && <p className="hint" style={{ color: "var(--error)" }}>{policyErr}</p>}
        </div>

        <div className="panel upload-card">
          <h3>Use your own request</h3>
          <p className="hint">
            Paste a request as JSON below, or upload a .txt, .html, or .json file. JSON needs club,
            event_date, submitted_date, justification, and a lines array (description + amount each).
          </p>
          <textarea
            placeholder='{"club": "Chess Club", "event_date": "2026-12-01", "submitted_date": "2026-11-01", "justification": "...", "lines": [{"description": "Venue rental", "amount": 300}]}'
            value={requestText}
            onChange={(e) => setRequestText(e.target.value)}
          />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn btn-sm" onClick={handleRequestPaste} disabled={requestBusy || !requestText.trim()}>
              Load pasted JSON
            </button>
            <label className="btn btn-sm">
              Upload file
              <input
                type="file"
                accept=".txt,.html,.json"
                style={{ display: "none" }}
                onChange={(e) => e.target.files?.[0] && handleRequestFile(e.target.files[0])}
              />
            </label>
          </div>
          {requestMessage && <p className="hint" style={{ color: "var(--allowed)" }}>{requestMessage}</p>}
          {requestErr && <p className="hint" style={{ color: "var(--error)" }}>{requestErr}</p>}
        </div>
      </div>
    </div>
  );
}
