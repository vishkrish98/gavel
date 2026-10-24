export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="state-box" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function Empty({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="state-box">
      <span>{label}</span>
      {hint && <span className="hint">{hint}</span>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-banner" role="alert">
      <div>{message}</div>
      {onRetry && (
        <button className="btn btn-sm" style={{ marginTop: 10 }} onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
