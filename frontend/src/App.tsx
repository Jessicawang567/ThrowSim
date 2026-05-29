import { useState } from "react";
import { FieldCanvas } from "./components/FieldCanvas";
import { PlayerInspector } from "./components/PlayerInspector";
import { ResultPanel } from "./components/ResultPanel";
import { defaultPlayers } from "./presets";
import type { Player, SimulateResponse } from "./types";
import { simulate } from "./api";
import { Play, RotateCcw, Bot, MousePointerClick } from "lucide-react";

export default function App() {
  const [players, setPlayers] = useState<Player[]>(defaultPlayers());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mode, setMode] = useState<"user" | "ai">("ai");
  const [targetId, setTargetId] = useState<string | null>(null);
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = players.find((p) => p.id === selectedId) ?? null;

  const updatePlayer = (np: Player) =>
    setPlayers(players.map((p) => (p.id === np.id ? np : p)));

  const makeHandler = (id: string) =>
    setPlayers(
      players.map((p) =>
        p.team === "offense" ? { ...p, is_handler: p.id === id } : p,
      ),
    );

  const deletePlayer = (id: string) => {
    setPlayers(players.filter((p) => p.id !== id));
    if (selectedId === id) setSelectedId(null);
    if (targetId === id) setTargetId(null);
  };

  const reset = () => {
    setPlayers(defaultPlayers());
    setSelectedId(null);
    setTargetId(null);
    setResult(null);
    setError(null);
  };

  const onSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await simulate(players, mode, targetId);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const canSimulate =
    players.some((p) => p.is_handler && p.team === "offense") &&
    (mode === "ai" || targetId !== null);

  return (
    <div className="min-h-screen text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-[1400px] mx-auto px-4 py-3 flex flex-wrap items-center gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              Ultimate Frisbee Stack Simulator
            </h1>
            <p className="text-xs text-slate-400">
              Top-down 7v7 · world-class players · static catch prediction with motion
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className="flex rounded-md ring-1 ring-slate-700 overflow-hidden text-sm">
              <button
                onClick={() => setMode("ai")}
                className={`flex items-center gap-1.5 px-3 py-1.5 ${
                  mode === "ai" ? "bg-slate-700 text-white" : "text-slate-400"
                }`}
              >
                <Bot size={14} /> AI picks throw
              </button>
              <button
                onClick={() => setMode("user")}
                className={`flex items-center gap-1.5 px-3 py-1.5 ${
                  mode === "user" ? "bg-slate-700 text-white" : "text-slate-400"
                }`}
              >
                <MousePointerClick size={14} /> User picks target
              </button>
            </div>
            <button
              onClick={reset}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-700 hover:bg-slate-800"
            >
              <RotateCcw size={14} /> Reset
            </button>
            <button
              onClick={onSimulate}
              disabled={!canSimulate || loading}
              className="flex items-center gap-1.5 rounded-md bg-cyan-500 px-4 py-1.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Play size={14} /> Simulate
            </button>
          </div>
        </div>
        {mode === "user" && (
          <div className="bg-slate-900/70 border-t border-slate-800 px-4 py-1.5 text-xs text-slate-300 max-w-[1400px] mx-auto">
            Target: {targetId ? <span className="text-cyan-300">{targetId}</span> : (
              <span className="text-amber-300">
                click an offensive player (non-handler) on the field to pick a target
              </span>
            )}
          </div>
        )}
      </header>

      <main className="max-w-[1400px] mx-auto p-4 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
        <div className="space-y-3">
          <FieldCanvas
            players={players}
            setPlayers={setPlayers}
            selectedId={selectedId}
            setSelectedId={setSelectedId}
            result={result}
            targetId={targetId}
            setTargetId={setTargetId}
            mode={mode}
          />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <Legend swatch="#fde047" label="Handler (holds disc)" />
            <Legend swatch="#f8fafc" label="Offense" />
            <Legend swatch="#ef4444" label="Defense" />
            <Legend swatch="#22d3ee" label="Selected target / catch point" />
          </div>
          <p className="text-xs text-slate-400">
            <span className="text-slate-200">Drag</span> to move ·
            <span className="text-slate-200"> Shift-drag</span> an offensive player to
            set running direction · ghost markers show predicted positions at catch
            time, accounting for defender pursuit during disc flight.
          </p>
          {highlightId && result && (
            <div className="text-xs text-slate-300">
              Hover preview:{" "}
              <span className="text-cyan-300">{highlightId}</span>
            </div>
          )}
        </div>
        <aside className="space-y-3">
          <PlayerInspector
            player={selected}
            onChange={updatePlayer}
            onMakeHandler={makeHandler}
            onDelete={deletePlayer}
          />
          <ResultPanel
            loading={loading}
            error={error}
            result={result}
            highlightId={highlightId}
            onHighlight={setHighlightId}
          />
        </aside>
      </main>
    </div>
  );
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <div className="flex items-center gap-2 text-slate-300">
      <span
        className="inline-block h-3 w-3 rounded-full ring-1 ring-slate-700"
        style={{ background: swatch }}
      />
      {label}
    </div>
  );
}
