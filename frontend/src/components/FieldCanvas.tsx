import { useRef, useState, useEffect } from "react";
import type { Player, SimulateResponse } from "../types";
import {
  FIELD_LENGTH,
  FIELD_WIDTH,
  OFF_ENDZONE_X,
  DEF_ENDZONE_X,
} from "../types";

interface Props {
  players: Player[];
  setPlayers: (p: Player[]) => void;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
  result: SimulateResponse | null;
  targetId: string | null;
  setTargetId: (id: string | null) => void;
  mode: "user" | "ai";
}

const PX_PER_M = 9; // 100m * 9 = 900px wide
const W = FIELD_LENGTH * PX_PER_M;
const H = FIELD_WIDTH * PX_PER_M;

const teamColor = (t: Player["team"], isHandler: boolean, isTarget: boolean) => {
  if (t === "offense") {
    if (isHandler) return "#fde047"; // yellow
    if (isTarget) return "#22d3ee";
    return "#f8fafc";
  }
  return "#ef4444";
};

export function FieldCanvas(props: Props) {
  const { players, setPlayers, selectedId, setSelectedId, result, targetId, setTargetId, mode } =
    props;
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [drag, setDrag] = useState<
    | { id: string; kind: "move" }
    | { id: string; kind: "direction" }
    | null
  >(null);

  const toFieldCoords = (clientX: number, clientY: number) => {
    const svg = svgRef.current!;
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const loc = pt.matrixTransform(ctm.inverse());
    return { x: loc.x / PX_PER_M, y: loc.y / PX_PER_M };
  };

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!drag) return;
      const { x, y } = toFieldCoords(e.clientX, e.clientY);
      setPlayers(
        players.map((p) => {
          if (p.id !== drag.id) return p;
          if (drag.kind === "move") {
            return {
              ...p,
              x: Math.max(0, Math.min(FIELD_LENGTH, x)),
              y: Math.max(0, Math.min(FIELD_WIDTH, y)),
            };
          } else {
            const dx = x - p.x;
            const dy = y - p.y;
            if (Math.hypot(dx, dy) < 0.4) return p;
            return { ...p, direction: Math.atan2(dy, dx) };
          }
        }),
      );
    };
    const onUp = () => setDrag(null);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [drag, players, setPlayers]);

  const handler = players.find((p) => p.is_handler && p.team === "offense");

  return (
    <div className="w-full overflow-x-auto rounded-lg ring-1 ring-slate-700 bg-slate-900">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto block"
        style={{ minWidth: 640 }}
      >
        {/* Field */}
        <rect x={0} y={0} width={W} height={H} fill="#1f6f3a" />
        {/* End zones */}
        <rect x={0} y={0} width={DEF_ENDZONE_X * PX_PER_M} height={H} fill="#174d29" />
        <rect
          x={OFF_ENDZONE_X * PX_PER_M}
          y={0}
          width={(FIELD_LENGTH - OFF_ENDZONE_X) * PX_PER_M}
          height={H}
          fill="#174d29"
        />
        {/* Lines */}
        <line
          x1={DEF_ENDZONE_X * PX_PER_M}
          x2={DEF_ENDZONE_X * PX_PER_M}
          y1={0}
          y2={H}
          stroke="white"
          strokeWidth={2}
        />
        <line
          x1={OFF_ENDZONE_X * PX_PER_M}
          x2={OFF_ENDZONE_X * PX_PER_M}
          y1={0}
          y2={H}
          stroke="white"
          strokeWidth={2}
        />
        {/* Brick marks */}
        {[(DEF_ENDZONE_X + 20) * PX_PER_M, (OFF_ENDZONE_X - 20) * PX_PER_M].map((x) => (
          <circle key={x} cx={x} cy={H / 2} r={4} fill="white" opacity={0.6} />
        ))}

        {/* Prediction overlays */}
        {result?.chosen && (
          <>
            <line
              x1={handler!.x * PX_PER_M}
              y1={handler!.y * PX_PER_M}
              x2={result.chosen.catch_x * PX_PER_M}
              y2={result.chosen.catch_y * PX_PER_M}
              stroke={result.outcome === "catch" ? "#22d3ee" : "#f87171"}
              strokeWidth={3}
              strokeDasharray="6 4"
            />
            <circle
              cx={result.chosen.catch_x * PX_PER_M}
              cy={result.chosen.catch_y * PX_PER_M}
              r={10}
              fill="none"
              stroke={result.outcome === "catch" ? "#22d3ee" : "#f87171"}
              strokeWidth={2}
            />
          </>
        )}

        {/* Predicted positions (ghosts) */}
        {result &&
          Object.entries(result.receiver_predicted_positions).map(([id, [x, y]]) => (
            <circle
              key={`gr-${id}`}
              cx={x * PX_PER_M}
              cy={y * PX_PER_M}
              r={7}
              fill="white"
              opacity={0.25}
            />
          ))}
        {result &&
          Object.entries(result.defender_predicted_positions).map(([id, [x, y]]) => (
            <circle
              key={`gd-${id}`}
              cx={x * PX_PER_M}
              cy={y * PX_PER_M}
              r={7}
              fill="#ef4444"
              opacity={0.25}
            />
          ))}

        {/* Players */}
        {players.map((p) => {
          const cx = p.x * PX_PER_M;
          const cy = p.y * PX_PER_M;
          const isTarget = mode === "user" && p.id === targetId;
          const sel = selectedId === p.id;
          return (
            <g key={p.id}>
              {/* Direction arrow for offense */}
              {p.team === "offense" && p.direction !== null && (
                <line
                  x1={cx}
                  y1={cy}
                  x2={cx + Math.cos(p.direction) * 30}
                  y2={cy + Math.sin(p.direction) * 30}
                  stroke="#fbbf24"
                  strokeWidth={3}
                  markerEnd="url(#arrow)"
                />
              )}
              <circle
                cx={cx}
                cy={cy}
                r={12}
                fill={teamColor(p.team, p.is_handler, isTarget)}
                stroke={sel ? "#0ea5e9" : "#0f172a"}
                strokeWidth={sel ? 3 : 1.5}
                style={{ cursor: "grab" }}
                onMouseDown={(e) => {
                  e.preventDefault();
                  setSelectedId(p.id);
                  if (e.shiftKey && p.team === "offense") {
                    setDrag({ id: p.id, kind: "direction" });
                  } else {
                    setDrag({ id: p.id, kind: "move" });
                  }
                }}
                onClick={() => {
                  if (mode === "user" && p.team === "offense" && !p.is_handler) {
                    setTargetId(p.id);
                  }
                }}
              />
              <text
                x={cx}
                y={cy + 4}
                textAnchor="middle"
                fontSize={11}
                fontWeight={700}
                fill={p.team === "offense" ? "#0f172a" : "white"}
                pointerEvents="none"
              >
                {p.id}
              </text>
            </g>
          );
        })}

        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#fbbf24" />
          </marker>
        </defs>
      </svg>
    </div>
  );
}
