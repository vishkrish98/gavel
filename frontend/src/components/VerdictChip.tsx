const LABELS: Record<string, string> = {
  allowed: "Allowed",
  reduced: "Reduced",
  denied: "Denied",
  needs_docs: "Needs documents",
};

export function VerdictChip({ verdict }: { verdict: string }) {
  return <span className={`chip ${verdict}`}>{LABELS[verdict] ?? verdict}</span>;
}
