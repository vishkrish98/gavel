import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import type { AllocateResult } from "../types";
import { ErrorState, Loading } from "../components/StateBox";

const DEFAULT_POT = 40000;

function useAllocation(pot: number, alpha: number) {
  const [result, setResult] = useState<AllocateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      api
        .allocate(pot, alpha)
        .then((r) => {
          setResult(r);
          setError(null);
        })
        .catch((err) => setError(err instanceof ApiError ? err.message : "Could not compute the allocation."));
    }, 120);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [pot, alpha]);

  return { result, error };
}

function BarChart({ result }: { result: AllocateResult }) {
  const clubs = Object.keys(result.allowed_by_club).sort((a, b) => result.allowed_by_club[b] - result.allowed_by_club[a]);
  const max = Math.max(1, ...clubs.map((c) => result.allowed_by_club[c]));
  return (
    <div className="bar-chart">
      {clubs.map((club) => {
        const allowed = result.allowed_by_club[club];
        const allocated = result.allocation[club] ?? 0;
        return (
          <div key={club} className="bar-chart-row">
            <div className="bar-chart-label" title={club}>{club}</div>
            <div className="bar-track">
              <div className="bar-fill-allowed" style={{ width: `${(allowed / max) * 100}%` }} />
              <div className="bar-fill-allocated" style={{ width: `${(allocated / max) * 100}%` }} />
            </div>
            <div className="bar-chart-amount">${Math.round(allocated).toLocaleString()}</div>
          </div>
        );
      })}
    </div>
  );
}

function tradeoffSentence(alpha: number): string {
  if (alpha <= 0.05) return "At alpha = 0, funding follows policy-allowed amounts only — past spending habits play no role.";
  if (alpha >= 0.95) return "At alpha = 1, funding leans entirely on last year's utilization — clubs that spent well get weighted far more, even if their allowed amount is similar to others.";
  return `At alpha = ${alpha.toFixed(2)}, funding blends policy-allowed amounts with last year's utilization — clubs with both a larger allowed amount and a track record of spending what they received get weighted more heavily.`;
}

export function ScenariosScreen() {
  const [pot, setPot] = useState(DEFAULT_POT);
  const [alphaA, setAlphaA] = useState(0.5);
  const [alphaB, setAlphaB] = useState(1.0);

  const sceneA = useAllocation(pot, alphaA);
  const sceneB = useAllocation(pot, alphaB);

  return (
    <div className="stack">
      <div className="panel">
        <h2>Scenarios</h2>
        <p className="hint" style={{ marginTop: 4 }}>
          Instant, code-only — recomputed on every slider move. Policy 2.1 allows considering prior-year
          utilization; alpha is that weight.
        </p>
        <div className="grid grid-2" style={{ marginTop: 16 }}>
          <div className="slider-row">
            <label>
              <span>Pot size</span>
              <span className="tabular">${pot.toLocaleString()}</span>
            </label>
            <input type="range" min={0} max={80000} step={1000} value={pot} onChange={(e) => setPot(Number(e.target.value))} />
          </div>
          <div />
          <div className="slider-row">
            <label>
              <span>Scenario A — weight on utilization (alpha)</span>
              <span className="tabular">{alphaA.toFixed(2)}</span>
            </label>
            <input type="range" min={0} max={1} step={0.05} value={alphaA} onChange={(e) => setAlphaA(Number(e.target.value))} />
          </div>
          <div className="slider-row">
            <label>
              <span>Scenario B — weight on utilization (alpha)</span>
              <span className="tabular">{alphaB.toFixed(2)}</span>
            </label>
            <input type="range" min={0} max={1} step={0.05} value={alphaB} onChange={(e) => setAlphaB(Number(e.target.value))} />
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="panel">
          <div className="panel-title">Scenario A</div>
          <p className="hint">{tradeoffSentence(alphaA)}</p>
          {sceneA.error && <ErrorState message={sceneA.error} />}
          {!sceneA.result && !sceneA.error && <Loading label="Computing…" />}
          {sceneA.result && <BarChart result={sceneA.result} />}
        </div>
        <div className="panel">
          <div className="panel-title">Scenario B</div>
          <p className="hint">{tradeoffSentence(alphaB)}</p>
          {sceneB.error && <ErrorState message={sceneB.error} />}
          {!sceneB.result && !sceneB.error && <Loading label="Computing…" />}
          {sceneB.result && <BarChart result={sceneB.result} />}
        </div>
      </div>

      {sceneA.result && sceneB.result && (
        <div className="panel">
          <div className="panel-title">Who gains and loses, A → B</div>
          <div className="table-wrap">
            <table className="review-table">
              <thead>
                <tr>
                  <th>Club</th>
                  <th>Scenario A</th>
                  <th>Scenario B</th>
                  <th>Change</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(sceneA.result.allocation)
                  .map((club) => ({
                    club,
                    a: sceneA.result!.allocation[club] ?? 0,
                    b: sceneB.result!.allocation[club] ?? 0,
                  }))
                  .sort((x, y) => (y.b - y.a) - (x.b - x.a))
                  .map(({ club, a, b }) => (
                    <tr key={club}>
                      <td>{club}</td>
                      <td className="tabular">${Math.round(a).toLocaleString()}</td>
                      <td className="tabular">${Math.round(b).toLocaleString()}</td>
                      <td className="tabular" style={{ color: b - a > 0.5 ? "var(--allowed)" : b - a < -0.5 ? "var(--denied)" : "var(--muted)" }}>
                        {b - a > 0 ? "+" : ""}
                        {Math.round(b - a).toLocaleString()}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
