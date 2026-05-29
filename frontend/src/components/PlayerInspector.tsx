import type { Player } from "../types";

interface Props {
  player: Player | null;
  onChange: (p: Player) => void;
  onMakeHandler: (id: string) => void;
  onDelete: (id: string) => void;
}

const DIRS: { label: string; rad: number }[] = [
  { label: "↑ deep (toward end zone)", rad: 0 },
  { label: "↗ in-cut break side", rad: -Math.PI / 4 },
  { label: "→ across (break)", rad: -Math.PI / 2 },
  { label: "↘ under break", rad: -(3 * Math.PI) / 4 },
  { label: "↓ dump", rad: Math.PI },
  { label: "↙ under open", rad: (3 * Math.PI) / 4 },
  { label: "← across (open)", rad: Math.PI / 2 },
  { label: "↖ in-cut open", rad: Math.PI / 4 },
];
// Note: in our coord system +x is downfield, +y is right. We map labels intuitively.

export function PlayerInspector({ player, onChange, onMakeHandler, onDelete }: Props) {
  if (!player) {
    return (
      <div className="rounded-lg ring-1 ring-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
        Select a player on the field to inspect or assign a running direction.
        <div className="mt-2 text-xs text-slate-500">
          Tip: <span className="text-slate-300">drag</span> a player to reposition.
          <span className="text-slate-300"> Shift-drag</span> an offensive player to set
          its running direction. Click a non-handler offensive player to set it as the
          throw target in user mode.
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-lg ring-1 ring-slate-700 bg-slate-900 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-400">
            {player.team}
            {player.is_handler && " · handler"}
          </div>
          <div className="text-lg font-semibold text-white">{player.id}</div>
        </div>
        <button
          className="text-xs text-rose-400 hover:text-rose-300"
          onClick={() => onDelete(player.id)}
        >
          remove
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <label className="text-slate-400">
          x (m)
          <input
            type="number"
            value={player.x.toFixed(1)}
            step={0.5}
            onChange={(e) => onChange({ ...player, x: parseFloat(e.target.value) })}
            className="mt-1 w-full rounded bg-slate-800 px-2 py-1 text-white ring-1 ring-slate-700"
          />
        </label>
        <label className="text-slate-400">
          y (m)
          <input
            type="number"
            value={player.y.toFixed(1)}
            step={0.5}
            onChange={(e) => onChange({ ...player, y: parseFloat(e.target.value) })}
            className="mt-1 w-full rounded bg-slate-800 px-2 py-1 text-white ring-1 ring-slate-700"
          />
        </label>
      </div>

      {player.team === "offense" && (
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-400 mb-1">
            Running direction
          </div>
          <div className="grid grid-cols-2 gap-1">
            {DIRS.map((d) => (
              <button
                key={d.label}
                onClick={() => onChange({ ...player, direction: d.rad })}
                className={`text-left rounded px-2 py-1 text-xs ring-1 ring-slate-700 hover:bg-slate-800 ${
                  player.direction !== null &&
                  Math.abs(player.direction - d.rad) < 0.01
                    ? "bg-slate-700 text-white"
                    : "text-slate-300"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => onChange({ ...player, direction: null })}
            className="mt-2 text-xs text-slate-400 hover:text-slate-200"
          >
            stand still
          </button>
        </div>
      )}

      {player.team === "offense" && !player.is_handler && (
        <button
          onClick={() => onMakeHandler(player.id)}
          className="w-full rounded bg-yellow-400 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-yellow-300"
        >
          Mark as handler (holds disc)
        </button>
      )}
    </div>
  );
}
