import type { Player } from "./types";
import { FIELD_LENGTH, FIELD_WIDTH } from "./types";

// Classic vertical stack: handler near brick, 6 cutters stacked downfield.
export function defaultPlayers(): Player[] {
  const midY = FIELD_WIDTH / 2;
  const offense: Player[] = [
    { id: "O1", team: "offense", x: 20, y: midY, direction: 0, is_handler: true },
    { id: "O2", team: "offense", x: 23, y: midY - 6, direction: 0, is_handler: false },
    { id: "O3", team: "offense", x: 23, y: midY + 6, direction: 0, is_handler: false },
    { id: "O4", team: "offense", x: 40, y: midY, direction: 0, is_handler: false },
    { id: "O5", team: "offense", x: 48, y: midY, direction: 0, is_handler: false },
    { id: "O6", team: "offense", x: 56, y: midY, direction: 0, is_handler: false },
    { id: "O7", team: "offense", x: 64, y: midY, direction: 0, is_handler: false },
  ];
  const defense: Player[] = offense.map((o, i) => ({
    id: `D${i + 1}`,
    team: "defense",
    x: Math.min(FIELD_LENGTH - 1, o.x + 2),
    y: o.y + (i % 2 === 0 ? 1 : -1),
    direction: null,
    is_handler: false,
  }));
  return [...offense, ...defense];
}
