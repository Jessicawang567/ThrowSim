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
from enum import Enum
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
DISC_SPEED = 22.0      # m/s typical fast throw average (legacy / fallback)
DEFENDER_REACH = 1.2   # meters: how close a defender must be to D the disc
RECEIVER_REACH = 1.5
REACTION_DELAY = 0.15  # seconds defender reaction handicap (world-class but human)


# ---------------------------------------------------------------------------
# Throw aerodynamics — 3D flight model
# ---------------------------------------------------------------------------
# Minimal 3-DOF translational state (x, y, z) + (vx, vy, vz), with a scalar
# pitch state theta evolved from an aerodynamic pitching moment and a bank
# state phi that carries the inside-out vs outside-in release roll.
#
# Forces (Hummel 2003, Potts & Crowther 2002 ranges):
#   Lift:   L = 0.5 * rho * v^2 * S * CL(alpha)
#   Drag:   D = drag_k * v^2  (per-throw effective coefficient; CD(alpha)
#                              implicit via the CL-induced drag polar below)
#   Gravity: -g on z
# CL(alpha): linear ramp through zero-lift at alpha ~= -4 deg, slope ~0.04/deg,
# stall at alpha ~= 25 deg with linear post-stall decay (Hummel Fig. 4).
# CD(alpha): CD = (1 + k_i*CL^2) * (drag_k/CD0_ref) -- folded into drag_k so
# the per-throw drag_k still calibrates the cruise drag, and induced drag
# scales with CL(alpha).
# Pitching moment: CM(alpha) = CM_ALPHA * (alpha - alpha_trim) with a small
# CP-CG offset; pitch evolves as dtheta/dt = M(alpha)/Iyy (gyroscopic damping
# folded into the use of Iyy as a first-order rate coefficient).
# Bank precession: dphi/dt = spin_sign * GYRO_GAIN * (alpha - alpha_trim) --
# late fade falls out of the physics rather than a hardcoded t/1.2 ramp.

RHO          = 1.225      # kg/m^3, sea-level air
DISC_MASS    = 0.175      # kg, 175g Ultimate disc
DISC_AREA    = 0.0568     # m^2, planform area (d ~ 0.27 m)
DISC_CHORD   = 0.27       # m, used for pitching moment
GRAV         = 9.81
IYY          = 1.0e-3     # kg*m^2, representative pitch inertia
RELEASE_HEIGHT = 1.5      # m

ALPHA_ZERO_LIFT_DEG = -4.0   # CL=0 here
ALPHA_STALL_DEG     = 25.0
CL_SLOPE_PER_DEG    = 0.04
CL_POST_STALL_DECAY = 0.04   # 1/deg, linear drop past stall

ALPHA_TRIM_DEG      = 5.0    # trim AoA (zero pitching moment)
CM_ALPHA_PER_DEG    = -3.0e-6  # restoring (very small; gyro-stiffened disc)
GYRO_GAIN           = 0.0006   # rad/(s*deg) bank-precession coupling


def cl_of_alpha(alpha_deg: float) -> float:
    """Lift coefficient: linear from zero-lift to stall, linear decay after."""
    if alpha_deg <= ALPHA_STALL_DEG:
        return CL_SLOPE_PER_DEG * (alpha_deg - ALPHA_ZERO_LIFT_DEG)
    cl_peak = CL_SLOPE_PER_DEG * (ALPHA_STALL_DEG - ALPHA_ZERO_LIFT_DEG)
    return max(0.0, cl_peak * (1.0 - CL_POST_STALL_DECAY * (alpha_deg - ALPHA_STALL_DEG)))


class ThrowType(str, Enum):
    backhand = "backhand"
    flick = "flick"
    hammer = "hammer"
    scoober = "scoober"
    backhand_io = "backhand_io"  # inside-out release (negative bank for RHBH)
    backhand_oi = "backhand_oi"  # outside-in release (positive bank for RHBH)
    flick_io = "flick_io"
    flick_oi = "flick_oi"


# spin_sign: +1 = RHBH spin (clockwise viewed from above), -1 = flick spin.
# bank_deg: release roll angle phi about the velocity axis. Sign convention:
#   positive bank tilts lift toward the spin's natural fade direction
#   (OI: curve in same direction as fade -> exaggerated late fade)
#   negative bank tilts lift opposite spin's fade (IO: hyzer-flip / S-curve)
# aoa_deg: release pitch angle (initial theta).
THROW_PARAMS: dict = {
    ThrowType.backhand: {
        "release_speed": 24.0, "spin_sign": +1.0,
        "aoa_deg": 6.0, "bank_deg": 0.0, "drag_k": 0.0055,
    },
    ThrowType.flick: {
        "release_speed": 22.5, "spin_sign": -1.0,
        "aoa_deg": 7.0, "bank_deg": 0.0, "drag_k": 0.0065,
    },
    ThrowType.hammer: {
        "release_speed": 19.5, "spin_sign": +1.0,
        "aoa_deg": 12.0, "bank_deg": 15.0, "drag_k": 0.0090,
    },
    ThrowType.scoober: {
        "release_speed": 17.5, "spin_sign": -1.0,
        "aoa_deg": 10.0, "bank_deg": 15.0, "drag_k": 0.0085,
    },
    ThrowType.backhand_io: {
        "release_speed": 24.0, "spin_sign": +1.0,
        "aoa_deg": 6.0, "bank_deg": -8.0, "drag_k": 0.0055,
    },
    ThrowType.backhand_oi: {
        "release_speed": 24.0, "spin_sign": +1.0,
        "aoa_deg": 6.0, "bank_deg": +8.0, "drag_k": 0.0055,
    },
    ThrowType.flick_io: {
        "release_speed": 22.5, "spin_sign": -1.0,
        "aoa_deg": 7.0, "bank_deg": -8.0, "drag_k": 0.0065,
    },
    ThrowType.flick_oi: {
        "release_speed": 22.5, "spin_sign": -1.0,
        "aoa_deg": 7.0, "bank_deg": +8.0, "drag_k": 0.0065,
    },
}


def integrate_flight_3d(
    handler_x: float,
    handler_y: float,
    aim_x: float,
    aim_y: float,
    throw: ThrowType,
    dt: float = 0.02,
    max_t: float = 8.0,
) -> Tuple[float, float, float, List[Tuple[float, float]]]:
    """3-DOF translational integrator with pitch/bank evolution.

    Returns (end_x, end_y, flight_time, ground_samples). Samples are 2D
    ground-projected positions (x, y) so downstream OOB / intercept logic is
    unchanged. Termination: horizontal distance along the initial heading
    reaches dist0, OR the disc hits the ground (z <= 0), OR max_t expires.
    """
    params = THROW_PARAMS[throw]
    v0       = float(params["release_speed"])
    spin     = float(params["spin_sign"])
    drag_k   = float(params["drag_k"])
    theta    = math.radians(float(params["aoa_deg"]))   # pitch
    phi      = math.radians(float(params["bank_deg"]))  # bank (release roll)

    dx = aim_x - handler_x
    dy = aim_y - handler_y
    dist0 = math.hypot(dx, dy)
    if dist0 < 1e-6:
        return handler_x, handler_y, 0.0, [(handler_x, handler_y)]
    hx, hy = dx / dist0, dy / dist0  # initial horizontal heading

    # Initial velocity: aim flat in the horizontal plane with the release pitch
    # already absorbed in theta. (gamma0 = 0  => alpha0 = theta.)
    x, y, z = handler_x, handler_y, RELEASE_HEIGHT
    vx = v0 * hx
    vy = v0 * hy
    vz = 0.0

    samples: List[Tuple[float, float]] = [(x, y)]
    t = 0.0
    travelled = 0.0
    while t < max_t and travelled < dist0:
        v = math.sqrt(vx * vx + vy * vy + vz * vz)
        v_h = math.sqrt(vx * vx + vy * vy)
        if v < 1.0:
            break
        gamma = math.atan2(vz, v_h)  # flight-path angle
        alpha = theta - gamma         # angle of attack (rad)
        alpha_deg = math.degrees(alpha)
        CL = cl_of_alpha(alpha_deg)

        # Unit vectors
        vhx, vhy, vhz = vx / v, vy / v, vz / v
        if v_h > 1e-6:
            hxv, hyv = vx / v_h, vy / v_h
        else:
            hxv, hyv = hx, hy
        # Left-perpendicular horizontal (lateral lift axis at zero bank)
        plx, ply = -hyv, hxv
        # In-plane lift axis (perpendicular to v, in vertical plane of flight):
        sg, cg = math.sin(gamma), math.cos(gamma)
        Lvx, Lvy, Lvz = -hxv * sg, -hyv * sg, cg

        # Lift acceleration magnitude
        q = 0.5 * RHO * v * v
        lift_acc = q * DISC_AREA * CL / DISC_MASS
        # Drag: existing v^2 drag with CD(alpha) shape via induced-drag polar
        cd_shape = 1.0 + 1.2 * CL * CL
        drag_acc = drag_k * v * v * cd_shape

        # Apply bank phi: lift rotates about velocity axis. spin_sign sets the
        # chirality so that for RHBH (spin=+1) +bank pushes lift toward natural
        # fade direction (left for an RHBH = +plx direction).
        cphi, sphi = math.cos(phi), math.sin(phi)
        lat = spin * sphi
        Lx = lift_acc * (cphi * Lvx + lat * plx)
        Ly = lift_acc * (cphi * Lvy + lat * ply)
        Lz = lift_acc * (cphi * Lvz)

        ax = -drag_acc * vhx + Lx
        ay = -drag_acc * vhy + Ly
        az = -drag_acc * vhz + Lz - GRAV

        vx += ax * dt; vy += ay * dt; vz += az * dt
        x  += vx * dt; y  += vy * dt; z  += vz * dt

        # Pitching moment -> pitch evolution (instructions: dtheta/dt = M/Iyy)
        Cm = CM_ALPHA_PER_DEG * (alpha_deg - ALPHA_TRIM_DEG)
        M_pitch = q * DISC_AREA * DISC_CHORD * Cm
        theta += (M_pitch / IYY) * dt
        # Gyroscopic precession couples pitch moment into bank evolution;
        # this is what produces the late-flight lateral fade naturally.
        phi += spin * GYRO_GAIN * (alpha_deg - ALPHA_TRIM_DEG) * dt

        t += dt
        travelled = (x - handler_x) * hx + (y - handler_y) * hy
        samples.append((x, y))

        if z <= 0.0:
            break

    return x, y, t, samples


# Back-compat wrappers — both names route to the 3D integrator so that
# existing call sites (find_catch_point, evaluate_throw) work unchanged.
def integrate_flight(handler_x, handler_y, aim_x, aim_y, throw, dt=0.02, max_t=8.0):
    return integrate_flight_3d(handler_x, handler_y, aim_x, aim_y, throw, dt, max_t)


def integrate_with_lateral_velocity(handler_x, handler_y, aim_x, aim_y, throw, dt=0.02, max_t=8.0):
    return integrate_flight_3d(handler_x, handler_y, aim_x, aim_y, throw, dt, max_t)


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
    scheme: Literal["man", "zone", "cup"] = "man"


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
    throw_type: Literal[
        "backhand", "flick", "hammer", "scoober",
        "backhand_io", "backhand_oi", "flick_io", "flick_oi",
    ] = "backhand"
    outcome: Literal[
        "catch", "block", "incomplete", "out_of_bounds", "interception", "callahan"
    ] = "catch"
    flight_path: List[List[float]] = []


class SimulateResponse(BaseModel):
    handler_id: str
    chosen: Optional[ThrowOption]
    outcome: Literal[
        "catch",
        "block",
        "incomplete",
        "no_throw",
        "out_of_bounds",
        "interception",
        "callahan",
    ]
    outcome_detail: str
    options: List[ThrowOption]
    receiver_predicted_positions: dict  # id -> (x, y) at chosen flight time
    defender_predicted_positions: dict
    scheme: Literal["man", "zone", "cup"] = "man"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def clamp_to_field(x: float, y: float) -> Tuple[float, float]:
    return max(0.0, min(FIELD_LENGTH, x)), max(0.0, min(FIELD_WIDTH, y))


def assign_defenders(
    players: List[Player], scheme: str = "man", handler: Optional[Player] = None
) -> dict:
    """Defensive assignment by scheme.

    - "man":  greedy nearest-defender-to-offense pairing (returns off_id -> def_id).
    - "zone": partition the field into 4 regions; the closest defender to each
              region's centroid is anchored there. Remaining defenders fall back
              on nearest-offense pairing. Returns off_id -> def_id where the
              receiver's covering defender is the one whose anchor (zone
              centroid OR matched receiver) is closest to that receiver.
    - "cup":  3 defenders form a cup around the thrower at fixed offsets, the
              rest form a downfield wall; receivers are then matched to the
              nearest remaining defender (anchor positions used as virtual
              defenders for distance computation when answering "who guards
              receiver X").

    The returned mapping is consumed by evaluate_throw / predicted-position
    code; for zone/cup we additionally stash the defender anchor points on a
    module-level dict so the integrator can use them instead of the raw
    player coordinates (defenders move from their assigned anchor).
    """
    offense = [p for p in players if p.team == "offense"]
    defense = [p for p in players if p.team == "defense"]
    if not defense:
        return {}

    if scheme == "man" or handler is None:
        pairs = []
        for d in defense:
            for o in offense:
                pairs.append((dist(d.x, d.y, o.x, o.y), d.id, o.id))
        pairs.sort()
        assigned_def, assigned_off, mapping = set(), set(), {}
        for _, d_id, o_id in pairs:
            if d_id in assigned_def or o_id in assigned_off:
                continue
            assigned_def.add(d_id)
            assigned_off.add(o_id)
            mapping[o_id] = d_id
        return mapping

    if scheme == "zone":
        # 4 quadrant-ish regions of the downfield half: shallow-left,
        # shallow-right, deep-left, deep-right (relative to thrower).
        zones = [
            ((handler.x + OFF_ENDZONE_X) * 0.5, FIELD_WIDTH * 0.25),  # shallow L
            ((handler.x + OFF_ENDZONE_X) * 0.5, FIELD_WIDTH * 0.75),  # shallow R
            ((OFF_ENDZONE_X + FIELD_LENGTH) * 0.5, FIELD_WIDTH * 0.25),  # deep L
            ((OFF_ENDZONE_X + FIELD_LENGTH) * 0.5, FIELD_WIDTH * 0.75),  # deep R
        ]
        anchors: dict = {}  # def_id -> (x, y)
        pairs = sorted(
            ((dist(d.x, d.y, zx, zy), d.id, (zx, zy)) for d in defense for zx, zy in zones)
        )
        used_def = set()
        used_zone = set()
        for _, d_id, (zx, zy) in pairs:
            if d_id in used_def or (zx, zy) in used_zone:
                continue
            used_def.add(d_id)
            used_zone.add((zx, zy))
            anchors[d_id] = (zx, zy)
        # remaining defenders sit on their own positions
        for d in defense:
            if d.id not in anchors:
                anchors[d.id] = (d.x, d.y)
        # match each offensive receiver to the defender whose anchor is closest
        mapping = {}
        for o in offense:
            best_d = min(
                anchors.items(), key=lambda kv: dist(o.x, o.y, kv[1][0], kv[1][1])
            )[0]
            mapping[o.id] = best_d
        _ANCHORS[scheme] = anchors
        return mapping

    if scheme == "cup":
        # 3-person cup around the thrower: mark, strong-side, weak-side at
        # fixed offsets ~3m from handler.
        offsets = [(2.5, 0.0), (1.5, 2.5), (1.5, -2.5)]
        anchors: dict = {}
        sorted_def = sorted(defense, key=lambda d: dist(d.x, d.y, handler.x, handler.y))
        cup = sorted_def[:3]
        wall = sorted_def[3:]
        for d, (ox, oy) in zip(cup, offsets):
            ax, ay = clamp_to_field(handler.x + ox, handler.y + oy)
            anchors[d.id] = (ax, ay)
        # wall: spaced across the field ~15m downfield of the handler
        wall_x = min(handler.x + 15.0, FIELD_LENGTH - 2.0)
        if wall:
            for i, d in enumerate(wall):
                wy = FIELD_WIDTH * (i + 1) / (len(wall) + 1)
                anchors[d.id] = (wall_x, wy)
        mapping = {}
        for o in offense:
            best_d = min(
                anchors.items(), key=lambda kv: dist(o.x, o.y, kv[1][0], kv[1][1])
            )[0]
            mapping[o.id] = best_d
        _ANCHORS[scheme] = anchors
        return mapping

    return {}


# anchor cache keyed by scheme; populated by assign_defenders
_ANCHORS: dict = {"man": {}, "zone": {}, "cup": {}}


def best_throw_type(handler: Player, target_x: float, target_y: float) -> ThrowType:
    """Heuristic AI choice of throw type, including IO / OI release rolls.

    Long downfield = backhand/flick (IO for hyzer-flip when target is on the
    same side as natural fade so the curve straightens; OI when the target is
    on the break side so the curve doubles down). Short cross-field break =
    hammer/scoober.
    """
    dx = target_x - handler.x
    dy = target_y - handler.y
    d = math.hypot(dx, dy)
    if d > 30.0:
        # Long: pick handedness, then IO/OI depending on cross-field component.
        # RHBH (backhand, spin+1) naturally fades toward +y (left), flick (-1)
        # fades toward -y (right). IO ~ release-roll opposite spin's fade, OI
        # ~ release-roll with spin's fade.
        if dy < 0:  # break-side flick OR backhand-OI territory
            # strong cross to -y: flick straight, or OI for a curling backhand
            if abs(dy) > 12.0:
                return ThrowType.backhand_oi
            return ThrowType.flick
        else:
            if abs(dy) > 12.0:
                return ThrowType.flick_oi
            # gentle open-side: a hyzer-flip IO backhand carries flatter
            return ThrowType.backhand_io if d > 45.0 else ThrowType.backhand
    if abs(dy) > 8.0 and d < 25.0:
        return ThrowType.hammer if dy > 0 else ThrowType.scoober
    return ThrowType.backhand


def find_catch_point(
    handler: Player,
    receiver: Player,
    player_speed: float,
    throw: ThrowType,
) -> Tuple[float, float, float, List[Tuple[float, float]]]:
    """Iteratively solve the lead-pass equation with the time-stepped
    integrator. We pick an aim point, integrate the flight, then the catch
    point is the integrator's endpoint (which includes lateral curvature).
    The aim is shifted to cancel the predicted curvature so that the disc
    actually arrives at the lead point.
    Returns (catch_x, catch_y, flight_time, path_samples)."""
    if receiver.direction is None:
        vx, vy = 0.0, 0.0
    else:
        vx = math.cos(receiver.direction) * player_speed
        vy = math.sin(receiver.direction) * player_speed

    rx, ry = receiver.x, receiver.y
    # initial guess: aim at receiver, no lead
    aim_x, aim_y = rx, ry
    end_x, end_y, t, samples = integrate_with_lateral_velocity(
        handler.x, handler.y, aim_x, aim_y, throw
    )
    for _ in range(8):
        lead_x = rx + vx * t
        lead_y = ry + vy * t
        lead_x, lead_y = clamp_to_field(lead_x, lead_y)
        # correct aim by the curvature offset (lead - end)
        aim_x += lead_x - end_x
        aim_y += lead_y - end_y
        end_x, end_y, t, samples = integrate_with_lateral_velocity(
            handler.x, handler.y, aim_x, aim_y, throw
        )
        if abs(end_x - lead_x) < 0.1 and abs(end_y - lead_y) < 0.1:
            break
    return end_x, end_y, t, samples


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


def _path_crosses_oob(samples: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    """Return the (x, y) point at which the flight path first exits the
    sideline/endline rectangle, or None if it stays in bounds."""
    for (x, y) in samples:
        if x < 0.0 or x > FIELD_LENGTH or y < 0.0 or y > FIELD_WIDTH:
            return (max(0.0, min(FIELD_LENGTH, x)), max(0.0, min(FIELD_WIDTH, y)))
    return None


def _defender_intercept(
    defender: Player,
    samples: List[Tuple[float, float]],
    dt: float,
    player_speed: float,
) -> Optional[Tuple[int, float, Tuple[float, float]]]:
    """Walk the disc path and check whether the defender can physically reach
    any point on the path BEFORE the disc passes that point. Returns
    (sample_index, time_of_intercept, point) or None."""
    for i, (px, py) in enumerate(samples):
        t_disc = i * dt
        d_dist = dist(defender.x, defender.y, px, py)
        t_def = d_dist / player_speed + REACTION_DELAY
        if t_def <= t_disc and t_disc > 0.05:
            return (i, t_disc, (px, py))
    return None


def evaluate_throw(
    handler: Player,
    receiver: Player,
    defender: Optional[Player],
    all_defenders: List[Player],
    player_speed: float,
    throw: ThrowType,
) -> ThrowOption:
    cx, cy, flight_time, samples = find_catch_point(
        handler, receiver, player_speed, throw
    )
    dt_sample = 0.02

    receiver_run_dist = dist(receiver.x, receiver.y, cx, cy)
    receiver_reach_time = receiver_run_dist / player_speed
    receiver_arrival = max(flight_time, receiver_reach_time)

    if defender is not None:
        d_dist = dist(defender.x, defender.y, cx, cy)
        defender_arrival = d_dist / player_speed + REACTION_DELAY
    else:
        defender_arrival = float("inf")

    p = catch_probability(receiver_arrival, defender_arrival, receiver_reach_time)

    # --- Outcome classification --------------------------------------------
    outcome: str = "catch"

    # 1) Out of bounds: any point on flight path leaves the field
    oob_pt = _path_crosses_oob(samples)
    if oob_pt is not None:
        outcome = "out_of_bounds"
        cx, cy = oob_pt
        p = min(p, 0.05)

    # 2) Interception: any defender (not just the matched one) can reach a
    #    point on the path before the disc does, AND that point is within
    #    DEFENDER_REACH of the path point.
    if outcome == "catch":
        best_intercept = None
        for d in all_defenders:
            ic = _defender_intercept(d, samples, dt_sample, player_speed)
            if ic is not None:
                if best_intercept is None or ic[1] < best_intercept[1]:
                    best_intercept = ic + (d,)
        if best_intercept is not None:
            _, t_ic, (ix, iy), d_who = best_intercept
            # Also require the intercept is meaningful: defender beats receiver
            r_to_ic = dist(receiver.x, receiver.y, ix, iy) / player_speed
            if t_ic < r_to_ic:
                cx, cy = ix, iy
                flight_time = t_ic
                outcome = "interception"
                # Callahan: interception in attacking end zone (offense's
                # scoring end zone, which is the defense's defending end zone
                # from their perspective).
                if cx >= OFF_ENDZONE_X:
                    outcome = "callahan"
                p = 0.05

    # 3) Otherwise standard contested / block / catch by margin & P
    if outcome == "catch":
        if p < 0.35:
            outcome = "block"
        elif p < 0.6:
            outcome = "incomplete"

    yards_gained = cx - handler.x
    field_value_pre = handler.x / FIELD_LENGTH
    field_value_post_complete = min(cx, FIELD_LENGTH) / FIELD_LENGTH
    field_value_turnover = -(FIELD_LENGTH - cx) / FIELD_LENGTH
    # Callahan is the worst possible turnover (opponent score); OOB is just a
    # normal turnover at the OOB spot.
    turnover_bonus = 0.0
    if outcome == "callahan":
        turnover_bonus = -1.0
    ev = (
        p * (field_value_post_complete - field_value_pre)
        + (1 - p) * (field_value_turnover - field_value_pre)
        + turnover_bonus
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
        throw_type=throw.value,
        outcome=outcome,  # type: ignore[arg-type]
        flight_path=[[x, y] for (x, y) in samples[::3]],  # decimate
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

    matchups = assign_defenders(players, req.scheme, handler)  # offense_id -> defender_id
    def_lookup = {p.id: p for p in players if p.team == "defense"}
    all_defenders = list(def_lookup.values())
    off_lookup = {p.id: p for p in players if p.team == "offense"}

    options: List[ThrowOption] = []
    for o in players:
        if o.team != "offense" or o.id == handler.id:
            continue
        defender = def_lookup.get(matchups.get(o.id, ""), None)
        throw = best_throw_type(handler, o.x, o.y)
        opt = evaluate_throw(
            handler, o, defender, all_defenders, req.player_speed, throw
        )
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

    # Decide outcome: defer to the per-option outcome computed in evaluate_throw.
    margin = chosen.defender_arrival - chosen.receiver_arrival
    outcome = chosen.outcome
    if outcome == "catch":
        detail = (
            f"{chosen.receiver_id} catches at ({chosen.catch_x:.1f}, "
            f"{chosen.catch_y:.1f}) m on a {chosen.throw_type}. "
            f"Margin over defender: {margin:+.2f}s."
        )
        if chosen.catch_x >= OFF_ENDZONE_X:
            detail += " GOAL."
    elif outcome == "incomplete":
        detail = (
            f"Contested {chosen.throw_type} at ({chosen.catch_x:.1f}, "
            f"{chosen.catch_y:.1f}) m. Margin {margin:+.2f}s — likely 50-50."
        )
    elif outcome == "block":
        defender_label = chosen.defender_id or "defense"
        detail = (
            f"{defender_label} gets the D on the {chosen.throw_type} at "
            f"({chosen.catch_x:.1f}, {chosen.catch_y:.1f}) m "
            f"(arrives {-margin:.2f}s ahead)."
        )
    elif outcome == "out_of_bounds":
        detail = (
            f"{chosen.throw_type.capitalize()} sails out of bounds at "
            f"({chosen.catch_x:.1f}, {chosen.catch_y:.1f}) m — turnover."
        )
    elif outcome == "interception":
        defender_label = chosen.defender_id or "defense"
        detail = (
            f"Interception by the defense on the {chosen.throw_type} at "
            f"({chosen.catch_x:.1f}, {chosen.catch_y:.1f}) m "
            f"(disc reaches there in {chosen.flight_time:.2f}s)."
        )
    elif outcome == "callahan":
        detail = (
            f"CALLAHAN! Defender catches the {chosen.throw_type} in the "
            f"attacking end zone at ({chosen.catch_x:.1f}, {chosen.catch_y:.1f}) m."
        )
    else:
        detail = ""

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
    anchors = _ANCHORS.get(req.scheme, {}) if req.scheme != "man" else {}
    for d in def_lookup.values():
        if req.scheme != "man" and d.id in anchors:
            tx, ty = anchors[d.id]
        else:
            target_off_id = inv.get(d.id)
            if target_off_id and target_off_id in rec_pos:
                tx, ty = rec_pos[target_off_id]
            else:
                tx, ty = d.x, d.y
        # run toward predicted target, capped by speed*t
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
        outcome=outcome,  # type: ignore[arg-type]
        outcome_detail=detail,
        options=options,
        receiver_predicted_positions=rec_pos,
        defender_predicted_positions=def_pos,
        scheme=req.scheme,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
