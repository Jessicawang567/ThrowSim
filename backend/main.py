"""
Ultimate Frisbee top-down simulator backend.

Field coordinate system (meters):
  x: 0 .. 100  (length, attack toward x = 100; offense scores in x in [82, 100])
  y: 0 .. 37   (width)
  Defensive end zone:  x in [0, 18]
  Playing field:       x in [18, 82]
  Offensive end zone:  x in [82, 100]

Simulator pipeline
------------------
1. Each offensive player has an initial running direction (unit vector) and runs
   at world-class sprint speed (~7.5 m/s) along that direction.
2. The defender of each offensive player is assumed to be man-marking the
   nearest opposing player; defenders aim toward the receiver's predicted catch
   location at full speed from t=0 (smart, world-class anticipation).
3. For each candidate offensive target, the catch point is found by iterating
   the "lead pass" equation:
       t = distance(handler, lead_point(t)) / disc_speed
   where lead_point(t) = receiver_pos + receiver_vel * t.
4. The defender of the receiver is given the same flight time t to reach that
   point.  If the defender arrives within a small "play on the disc" radius
   before the receiver, it is a D/block; otherwise the receiver catches.
5. AI mode picks the throw maximizing expected gain toward the end zone, with
   a risk penalty for low catch probability (loosely inspired by EPV-style
   throw valuation literature for ultimate).
"""

from __future__ import annotations

import math
from typing import List, Literal, Optional, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FIELD_LENGTH = 100.0  # meters end-to-end
FIELD_WIDTH = 37.0
OFF_ENDZONE_X = 82.0  # x >= this is offensive end zone
DEF_ENDZONE_X = 18.0
PLAYER_SPEED = 7.5     # m/s, world-class
DISC_SPEED = 22.0      # m/s typical fast throw average
DEFENDER_REACH = 1.2   # meters: how close a defender must be to D the disc
RECEIVER_REACH = 1.5
REACTION_DELAY = 0.15  # seconds defender reaction handicap (world-class but human)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
class Player(BaseModel):
    id: str
    team: Literal["offense", "defense"]
    x: float
    y: float
    # Direction in radians (math convention); None for defense (AI controls them)
    direction: Optional[float] = None
    is_handler: bool = False


class SimulateRequest(BaseModel):
    players: List[Player]
    mode: Literal["user", "ai"] = "ai"
    target_id: Optional[str] = None  # required when mode == "user"
    disc_speed: float = Field(default=DISC_SPEED, ge=5.0, le=40.0)
    player_speed: float = Field(default=PLAYER_SPEED, ge=2.0, le=12.0)


class ThrowOption(BaseModel):
    receiver_id: str
    catch_x: float
    catch_y: float
    flight_time: float
    receiver_arrival: float
    defender_arrival: float
    defender_id: Optional[str]
    catch_probability: float
    yards_gained: float
    expected_value: float


class SimulateResponse(BaseModel):
    handler_id: str
    chosen: Optional[ThrowOption]
    outcome: Literal["catch", "block", "incomplete", "no_throw"]
    outcome_detail: str
    options: List[ThrowOption]
    receiver_predicted_positions: dict  # id -> (x, y) at chosen flight time
    defender_predicted_positions: dict


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def clamp_to_field(x: float, y: float) -> Tuple[float, float]:
    return max(0.0, min(FIELD_LENGTH, x)), max(0.0, min(FIELD_WIDTH, y))


def assign_defenders(players: List[Player]) -> dict:
    """Man-marking: each defender assigned to nearest offensive player not
    already taken (greedy). Returns receiver_id -> defender_id."""
    offense = [p for p in players if p.team == "offense"]
    defense = [p for p in players if p.team == "defense"]

    pairs = []
    for d in defense:
        for o in offense:
            pairs.append((dist(d.x, d.y, o.x, o.y), d.id, o.id))
    pairs.sort()

    assigned_def = set()
    assigned_off = set()
    mapping: dict = {}
    for _, d_id, o_id in pairs:
        if d_id in assigned_def or o_id in assigned_off:
            continue
        assigned_def.add(d_id)
        assigned_off.add(o_id)
        mapping[o_id] = d_id
    return mapping


def find_catch_point(
    handler: Player,
    receiver: Player,
    disc_speed: float,
    player_speed: float,
) -> Tuple[float, float, float]:
    """Iteratively solve for the lead-pass catch point.
    Returns (catch_x, catch_y, flight_time)."""
    if receiver.direction is None:
        vx, vy = 0.0, 0.0
    else:
        vx = math.cos(receiver.direction) * player_speed
        vy = math.sin(receiver.direction) * player_speed

    rx, ry = receiver.x, receiver.y
    # initial guess: catch where receiver is now
    cx, cy = rx, ry
    for _ in range(20):
        d = dist(handler.x, handler.y, cx, cy)
        t = d / disc_speed
        new_cx = rx + vx * t
        new_cy = ry + vy * t
        new_cx, new_cy = clamp_to_field(new_cx, new_cy)
        if abs(new_cx - cx) < 0.05 and abs(new_cy - cy) < 0.05:
            cx, cy = new_cx, new_cy
            break
        cx, cy = new_cx, new_cy
    t = dist(handler.x, handler.y, cx, cy) / disc_speed
    return cx, cy, t


def catch_probability(
    receiver_arrival: float,
    defender_arrival: float,
    receiver_reach_time: float,
) -> float:
    """Smooth logistic of the time-margin between defender and receiver
    arriving at the catch point. Positive margin => defender late => high P."""
    margin = defender_arrival - receiver_arrival
    # also penalize if receiver itself can't make it before disc lands
    if receiver_reach_time > receiver_arrival + 0.4:
        return 0.05
    # logistic centered at 0.0s margin, scale 0.35s
    return 1.0 / (1.0 + math.exp(-margin / 0.35))


def evaluate_throw(
    handler: Player,
    receiver: Player,
    defender: Optional[Player],
    disc_speed: float,
    player_speed: float,
) -> ThrowOption:
    cx, cy, flight_time = find_catch_point(handler, receiver, disc_speed, player_speed)

    receiver_run_dist = dist(receiver.x, receiver.y, cx, cy)
    receiver_reach_time = receiver_run_dist / player_speed
    # The receiver is on the disc at catch_point at flight_time by construction
    # (lead pass); we still use receiver_reach_time vs flight_time as sanity.
    receiver_arrival = max(flight_time, receiver_reach_time)

    if defender is not None:
        d_dist = dist(defender.x, defender.y, cx, cy)
        defender_arrival = d_dist / player_speed + REACTION_DELAY
    else:
        defender_arrival = float("inf")

    p = catch_probability(receiver_arrival, defender_arrival, receiver_reach_time)
    # Throws into own end zone (back) or out of bounds get penalized
    if cy <= 0.2 or cy >= FIELD_WIDTH - 0.2 or cx <= 0.5 or cx >= FIELD_LENGTH - 0.5:
        p *= 0.5

    yards_gained = cx - handler.x  # progress toward offensive end zone
    # Expected value: progress weighted by catch P, turnover penalty proportional
    # to field position lost (loosely an EPV-style throw value).
    field_value_pre = handler.x / FIELD_LENGTH
    field_value_post_complete = min(cx, FIELD_LENGTH) / FIELD_LENGTH
    # Turnover gives opponent value from (FIELD_LENGTH - cx)
    field_value_turnover = -(FIELD_LENGTH - cx) / FIELD_LENGTH
    ev = (
        p * (field_value_post_complete - field_value_pre)
        + (1 - p) * (field_value_turnover - field_value_pre)
    )

    return ThrowOption(
        receiver_id=receiver.id,
        catch_x=cx,
        catch_y=cy,
        flight_time=flight_time,
        receiver_arrival=receiver_arrival,
        defender_arrival=defender_arrival if defender is not None else 0.0,
        defender_id=defender.id if defender is not None else None,
        catch_probability=p,
        yards_gained=yards_gained,
        expected_value=ev,
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Ultimate Frisbee Simulator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/field")
def field():
    return {
        "length": FIELD_LENGTH,
        "width": FIELD_WIDTH,
        "off_endzone_x": OFF_ENDZONE_X,
        "def_endzone_x": DEF_ENDZONE_X,
    }


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    players = req.players
    handlers = [p for p in players if p.is_handler and p.team == "offense"]
    if not handlers:
        return SimulateResponse(
            handler_id="",
            chosen=None,
            outcome="no_throw",
            outcome_detail="No handler marked on offense.",
            options=[],
            receiver_predicted_positions={},
            defender_predicted_positions={},
        )
    handler = handlers[0]

    matchups = assign_defenders(players)  # offense_id -> defender_id
    def_lookup = {p.id: p for p in players if p.team == "defense"}
    off_lookup = {p.id: p for p in players if p.team == "offense"}

    options: List[ThrowOption] = []
    for o in players:
        if o.team != "offense" or o.id == handler.id:
            continue
        defender = def_lookup.get(matchups.get(o.id, ""), None)
        opt = evaluate_throw(handler, o, defender, req.disc_speed, req.player_speed)
        options.append(opt)

    if not options:
        return SimulateResponse(
            handler_id=handler.id,
            chosen=None,
            outcome="no_throw",
            outcome_detail="No eligible receivers.",
            options=[],
            receiver_predicted_positions={},
            defender_predicted_positions={},
        )

    if req.mode == "user":
        chosen = next((o for o in options if o.receiver_id == req.target_id), None)
        if chosen is None:
            return SimulateResponse(
                handler_id=handler.id,
                chosen=None,
                outcome="no_throw",
                outcome_detail="Selected target is not a valid receiver.",
                options=options,
                receiver_predicted_positions={},
                defender_predicted_positions={},
            )
    else:
        chosen = max(options, key=lambda o: o.expected_value)

    # Decide outcome deterministically by margin (this is a static prediction).
    margin = chosen.defender_arrival - chosen.receiver_arrival
    if chosen.catch_probability >= 0.6:
        outcome = "catch"
        detail = (
            f"{chosen.receiver_id} catches at ({chosen.catch_x:.1f}, "
            f"{chosen.catch_y:.1f}) m. Margin over defender: {margin:+.2f}s."
        )
        if chosen.catch_x >= OFF_ENDZONE_X:
            detail += " GOAL."
    elif chosen.catch_probability >= 0.35:
        outcome = "incomplete"
        detail = (
            f"Contested disc at ({chosen.catch_x:.1f}, {chosen.catch_y:.1f}) m. "
            f"Margin {margin:+.2f}s — likely incompletion / 50-50."
        )
    else:
        outcome = "block"
        defender_label = chosen.defender_id or "defense"
        detail = (
            f"{defender_label} gets the D at "
            f"({chosen.catch_x:.1f}, {chosen.catch_y:.1f}) m "
            f"(arrives {-margin:.2f}s ahead)."
        )

    # Predicted positions at flight_time
    t = chosen.flight_time
    rec_pos = {}
    for o in off_lookup.values():
        if o.direction is None or o.is_handler:
            rec_pos[o.id] = [o.x, o.y]
        else:
            nx = o.x + math.cos(o.direction) * req.player_speed * t
            ny = o.y + math.sin(o.direction) * req.player_speed * t
            nx, ny = clamp_to_field(nx, ny)
            rec_pos[o.id] = [nx, ny]

    def_pos = {}
    # invert mapping
    inv = {v: k for k, v in matchups.items()}
    for d in def_lookup.values():
        target_off_id = inv.get(d.id)
        if target_off_id and target_off_id in rec_pos:
            tx, ty = rec_pos[target_off_id]
        else:
            tx, ty = d.x, d.y
        # run toward predicted receiver location, capped by speed*t
        dx, dy = tx - d.x, ty - d.y
        dd = math.hypot(dx, dy)
        max_d = req.player_speed * t
        if dd > max_d and dd > 0:
            tx = d.x + dx / dd * max_d
            ty = d.y + dy / dd * max_d
        def_pos[d.id] = [tx, ty]

    return SimulateResponse(
        handler_id=handler.id,
        chosen=chosen,
        outcome=outcome,
        outcome_detail=detail,
        options=options,
        receiver_predicted_positions=rec_pos,
        defender_predicted_positions=def_pos,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
