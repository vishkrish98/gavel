import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import type { AuditEvent, DemoLoadResult, RunStatus } from "./types";
import { InjectionBanner } from "./components/InjectionBanner";
import { StartScreen } from "./screens/StartScreen";
import { RulesScreen } from "./screens/RulesScreen";
import { RunScreen } from "./screens/RunScreen";
import { ReviewScreen } from "./screens/ReviewScreen";
import { ScenariosScreen } from "./screens/ScenariosScreen";
import { ConsistencyScreen } from "./screens/ConsistencyScreen";
import { DraftsScreen } from "./screens/DraftsScreen";
import { CostScreen } from "./screens/CostScreen";
import { ClubsScreen } from "./screens/ClubsScreen";

type Tab = "start" | "clubs" | "rules" | "run" | "review" | "scenarios" | "consistency" | "drafts" | "cost";

const TABS: { key: Tab; label: string }[] = [
  { key: "start", label: "Start" },
  { key: "clubs", label: "Clubs" },
  { key: "rules", label: "Rules" },
  { key: "run", label: "Run" },
  { key: "review", label: "Review" },
  { key: "scenarios", label: "Scenarios" },
  { key: "consistency", label: "Consistency" },
  { key: "drafts", label: "Drafts" },
  { key: "cost", label: "Cost" },
];

function App() {
  const [tab, setTab] = useState<Tab>("start");
  const [hasData, setHasData] = useState(false);

  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunStatus | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const poll = useCallback(async (id: string) => {
    try {
      const [statusResult, eventsResult] = await Promise.all([api.getRun(id), api.getRunEvents(id)]);
      setRun(statusResult);
      setEvents(eventsResult);
      if (statusResult.status !== "running" && pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {
      // transient network hiccup while polling -- keep the last known state, try again next tick
    }
  }, []);

  useEffect(() => {
    if (!runId) return;
    poll(runId);
    pollRef.current = window.setInterval(() => poll(runId), 1500);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [runId, poll]);

  function handleDemoLoaded(_result: DemoLoadResult) {
    setHasData(true);
    setTab("rules");
  }

  async function handleStartRun(requestIds: string[] | null) {
    setStarting(true);
    setStartError(null);
    try {
      const result = await api.startRun(requestIds);
      setRunId(result.run_id);
      setRun(null);
      setEvents([]);
    } catch (err) {
      setStartError(err instanceof ApiError ? err.message : "Could not start the run.");
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark">⚖ Gavel</span>
          <span className="tagline">Funding committee decision support</span>
        </div>
        <nav className="nav-tabs" aria-label="Screens">
          {TABS.map((t) => (
            <button
              key={t.key}
              id={`nav-${t.key}`}
              className={`nav-tab ${tab === t.key ? "active" : ""}`}
              onClick={() => setTab(t.key)}
              disabled={t.key !== "start" && t.key !== "clubs" && !hasData}
              aria-current={tab === t.key ? "page" : undefined}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="main stack">
        {events.length > 0 && <InjectionBanner events={events} />}

        {tab === "start" && (
          <StartScreen
            onDemoLoaded={handleDemoLoaded}
            onPolicyUploaded={() => {
              setHasData(true);
              setTab("rules");
            }}
            onRequestUploaded={() => setHasData(true)}
          />
        )}
        {tab === "clubs" && <ClubsScreen runId={runId} onRequestsImported={() => setHasData(true)} />}
        {tab === "rules" && <RulesScreen onReadyToRun={() => setTab("run")} />}
        {tab === "run" && <RunScreen run={run} events={events} onStart={handleStartRun} starting={starting} startError={startError} />}
        {tab === "review" && <ReviewScreen runId={runId} />}
        {tab === "scenarios" && <ScenariosScreen />}
        {tab === "consistency" && <ConsistencyScreen />}
        {tab === "drafts" && <DraftsScreen runId={runId} />}
        {tab === "cost" && <CostScreen runId={runId} />}
      </main>
    </div>
  );
}

export default App;
