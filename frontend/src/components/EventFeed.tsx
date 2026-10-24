import type { AuditEvent } from "../types";

function summarize(event: AuditEvent): string {
  try {
    const detail = JSON.parse(event.detail_json);
    if (event.event === "agent_run") return `${detail.agent} — ${detail.usage?.total_tokens ?? "?"} tokens, $${Number(detail.usage?.cost_usd ?? 0).toFixed(6)}`;
    if (event.event === "blocked_injection") return `${detail.field} in ${detail.request_id}: "${String(detail.text ?? "").slice(0, 90)}"`;
    if (event.event === "auto_approved_for_benchmark") return `${detail.rule_id} (${detail.para_id}, ${detail.type})`;
    if (event.event === "rule_rejected") return `${detail.rule_id}: ${detail.reason}`;
    if (event.event === "run_start") return `${detail.request_ids?.length ?? "?"} request(s)`;
    if (event.event === "run_end" || event.event === "run_limit_hit") return JSON.stringify(detail);
    const text = JSON.stringify(detail);
    return text.length > 140 ? text.slice(0, 140) + "…" : text;
  } catch {
    return event.detail_json;
  }
}

export function EventFeed({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return <div className="state-box">No events yet.</div>;
  }
  return (
    <div className="feed" aria-live="polite" aria-label="Agent event trace">
      {events
        .slice()
        .reverse()
        .map((event) => (
          <div key={event.id} className="feed-row">
            <div>
              <div className="feed-event">{event.event}</div>
              <div className="feed-time">{new Date(event.ts).toLocaleTimeString()}</div>
            </div>
            <div className="feed-detail">{summarize(event)}</div>
          </div>
        ))}
    </div>
  );
}
