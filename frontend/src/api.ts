import type { Player, Scheme, SimulateResponse } from "./types";

const BASE =
  ((import.meta as unknown as { env?: { VITE_API_BASE?: string } }).env
    ?.VITE_API_BASE) || "http://localhost:8000";

export async function simulate(
  players: Player[],
  mode: "user" | "ai",
  targetId: string | null,
  scheme: Scheme = "man",
): Promise<SimulateResponse> {
  const res = await fetch(`${BASE}/api/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ players, mode, target_id: targetId, scheme }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Simulation failed: ${res.status} ${text}`);
  }
  return res.json();
}
