import { AGENTS } from "../agentTheme";
import type { RunStatus } from "../types";

type Status = "waiting" | "working" | "done";

function computeStatuses(run: RunStatus | null): Record<string, Status> {
  const families = run ? Object.keys(run.progress_by_agent) : [];
  const has = (name: string) => families.includes(name);
  const terminal = run ? run.status !== "running" : false;

  const compilerDone = has("policy_compiler");
  const readerStarted = has("request_reader");
  const skepticStarted = has("skeptic");
  const drafterStarted = has("drafter_questions") || has("drafter_memo");

  const statuses: Record<string, Status> = {
    chair: !run ? "waiting" : terminal ? "done" : "working",
    policy_compiler: !run ? "waiting" : compilerDone ? "done" : "working",
    request_reader: !readerStarted ? "waiting" : skepticStarted || terminal ? "done" : "working",
    skeptic: !skepticStarted ? "waiting" : drafterStarted || terminal ? "done" : "working",
    engine: !skepticStarted ? "waiting" : drafterStarted || terminal ? "done" : "working",
    optimizer: !skepticStarted ? "waiting" : drafterStarted || terminal ? "done" : "working",
    drafter: !drafterStarted ? "waiting" : terminal ? "done" : "working",
  };
  return statuses;
}

const STATUS_LABEL: Record<Status, string> = { waiting: "Waiting", working: "Working…", done: "Done" };

export function AgentNameplates({ run }: { run: RunStatus | null }) {
  const statuses = computeStatuses(run);
  return (
    <div className="nameplates">
      {AGENTS.map((agent) => {
        const status = statuses[agent.key];
        const calls = agent.usageFamilies.reduce((sum, family) => sum + (run?.progress_by_agent[family]?.calls ?? 0), 0);
        return (
          <div key={agent.key} className={`nameplate ${status}`}>
            <div className="row" style={{ gap: 8 }}>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: 7,
                  background: agent.color + "33",
                  color: agent.color,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10.5,
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {agent.monogram}
              </div>
              <div>
                <div className="nameplate-name">{agent.name}</div>
                <div className="nameplate-role">{agent.role}</div>
              </div>
            </div>
            <div className="nameplate-status">
              {status === "working" && <span className="pulse-dot" aria-hidden="true" />}
              {STATUS_LABEL[status]}
              {calls > 0 && ` · ${calls} call${calls === 1 ? "" : "s"}`}
            </div>
          </div>
        );
      })}
    </div>
  );
}
