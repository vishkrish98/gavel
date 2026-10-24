import type { AuditEvent } from "../types";

interface BlockedDetail {
  defense?: string;
  request_id?: string;
  field?: string;
  reason?: string;
  tag?: string;
  pattern?: string;
  text?: string;
}

export function InjectionBanner({ events }: { events: AuditEvent[] }) {
  const blocked = events.filter((e) => e.event === "blocked_injection");
  if (blocked.length === 0) return null;

  return (
    <div className="injection-banner" role="alert">
      <div className="title">⚠ Prompt injection blocked ({blocked.length})</div>
      {blocked.slice(0, 5).map((event) => {
        let detail: BlockedDetail = {};
        try {
          detail = JSON.parse(event.detail_json);
        } catch {
          // leave detail empty if it doesn't parse
        }
        return (
          <div key={event.id}>
            In request <code>{detail.request_id ?? "?"}</code>, field{" "}
            <code>{detail.field ?? "?"}</code> ({detail.defense === "hidden_text_stripped" ? `hidden text, ${detail.reason}` : "instruction pattern"}
            ): <em>&ldquo;{detail.text}&rdquo;</em>
          </div>
        );
      })}
      {blocked.length > 5 && <div className="hint">+{blocked.length - 5} more — see the Run screen's event feed.</div>}
    </div>
  );
}
