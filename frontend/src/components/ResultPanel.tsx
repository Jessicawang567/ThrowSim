import type { SimulateResponse } from "../types";
import { CheckCircle2, XCircle, AlertTriangle, MinusCircle } from "lucide-react";

interface Props {
  loading: boolean;
  error: string | null;
  result: SimulateResponse | null;
  highlightId: string | null;
  onHighlight: (id: string | null) => void;
}

const icon = (o: SimulateResponse["outcome"]) => {
  switch (o) {
    case "catch":
      return <CheckCircle2 className="text-emerald-400" size={20} />;
    case "block":
      return <XCircle className="text-rose-400" size={20} />;
    case "incomplete":
      return <AlertTriangle className="text-amber-400" size={20} />;
    default:
      return <MinusCircle className="text-slate-400" size={20} />;
  }
};

export function ResultPanel({ loading, error, result, highlightId, onHighlight }: Props) {
  if (loading)
    return (
      <div className="rounded-lg ring-1 ring-slate-700 bg-slate-900 p-4 text-sm text-slate-300">
        Simulating world-class motion...
      </div>
    );
  if (error)
    return (
      <div className="rounded-lg ring-1 ring-rose-700 bg-rose-950/50 p-4 text-sm text-rose-200">
        {error}
      </div>
    );
  if (!result)
    return (
      <div className="rounded-lg ring-1 ring-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
        Set the stack and press <span className="text-slate-200">Simulate</span> to see
        the predicted outcome.
      </div>
    );

  return (
    <div className="rounded-lg ring-1 ring-slate-700 bg-slate-900 p-4 space-y-3">
      <div className="flex items-center gap-2">
        {icon(result.outcome)}
        <div className="text-base font-semibold text-white capitalize">
          {result.outcome}
        </div>
      </div>
      <p className="text-sm text-slate-300 leading-relaxed">{result.outcome_detail}</p>

      <div>
        <div className="text-xs uppercase tracking-wider text-slate-400 mb-1">
          All evaluated options
        </div>
        <div className="space-y-1 max-h-72 overflow-y-auto pr-1">
          {result.options
            .slice()
            .sort((a, b) => b.expected_value - a.expected_value)
            .map((o) => {
              const isChosen = result.chosen?.receiver_id === o.receiver_id;
              const isHi = highlightId === o.receiver_id;
              return (
                <div
                  key={o.receiver_id}
                  onMouseEnter={() => onHighlight(o.receiver_id)}
                  onMouseLeave={() => onHighlight(null)}
                  className={`text-xs rounded px-2 py-1.5 ring-1 cursor-default ${
                    isChosen
                      ? "ring-cyan-500 bg-cyan-500/10"
                      : isHi
                      ? "ring-slate-500 bg-slate-800"
                      : "ring-slate-800 bg-slate-950/40"
                  }`}
                >
                  <div className="flex justify-between text-slate-200">
                    <span className="font-semibold">{o.receiver_id}</span>
                    <span>
                      P(catch)=
                      <span
                        className={
                          o.catch_probability > 0.6
                            ? "text-emerald-300"
                            : o.catch_probability > 0.35
                            ? "text-amber-300"
                            : "text-rose-300"
                        }
                      >
                        {(o.catch_probability * 100).toFixed(0)}%
                      </span>
                    </span>
                  </div>
                  <div className="text-slate-400 flex justify-between mt-0.5">
                    <span>
                      gain {o.yards_gained >= 0 ? "+" : ""}
                      {o.yards_gained.toFixed(1)}m
                    </span>
                    <span>EV {o.expected_value.toFixed(3)}</span>
                    <span>flight {o.flight_time.toFixed(2)}s</span>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}
