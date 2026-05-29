# Evaluation Checklist

_Architecture-neutral should-haves._

## 1. Backend installs cleanly: `pip install -r backend/requirements.txt` succeeds without resolution conflicts

**Scale:** yes/no  
**Review angles:**
- pip output
- version pinning sanity

_Source: baseline_

## 2. Frontend installs cleanly: `cd frontend && npm install` succeeds without unmet peer-dep errors

**Scale:** yes/no  
**Review angles:**
- npm output
- lockfile presence
- Node version compatibility

_Source: baseline_

## 3. Frontend builds without type or compile errors (`npm run build` or equivalent)

**Scale:** yes/no  
**Review angles:**
- build output
- tsc errors
- next/vite warnings

_Source: baseline_

## 4. Backend starts and the documented health/root endpoint returns 2xx

**Scale:** yes/no  
**Review angles:**
- startup logs
- curl response
- CORS headers

_Source: baseline_

## 5. Frontend dev server starts and the entry route renders without an error overlay

**Scale:** yes/no  
**Review angles:**
- dev-server console
- browser network tab
- no Next/Vite error overlay

_Source: baseline_

## 6. Frontend uses a modern React framework (Next.js 14+ or Vite + React 18) with TypeScript

**Scale:** yes/no  
**Review angles:**
- package.json deps
- tsconfig.json present
- app/ or src/ layout

_Source: baseline_

## 7. UI uses a real styling/component system (Tailwind + shadcn/ui or comparable) rather than ad-hoc inline styles

**Scale:** yes/no  
**Review angles:**
- tailwind.config presence
- components/ folder with reusable parts
- no large inline <style> blocks

_Source: baseline_

## 8. No uncaught JavaScript page errors on first render of the entry route

**Scale:** yes/no  
**Review angles:**
- browser pageerror events
- console.error from app code (ignore favicon)

_Source: baseline_

## 9. Visible UI quality is at v0/shadcn level: consistent spacing scale, deliberate typography hierarchy, accessible contrast, no default-browser look

**Scale:** 1-5  
**Review angles:**
- heading vs body type scale
- padding/margin rhythm
- color palette discipline
- interactive states (hover/focus)

_Source: baseline_

## 10. Primary user flow has loading, empty, and error states (not just the happy path)

**Scale:** yes/no  
**Review angles:**
- loading indicators / skeletons
- empty-state copy + illustration
- error message UI

_Source: baseline_

## 11. Responsive layout: usable without horizontal scroll at 1280×800 and 768×1024

**Scale:** yes/no  
**Review angles:**
- flex/grid breakpoints
- no fixed-pixel desktop-only layout

_Source: baseline_

## 12. Frontend ↔ backend wiring works end-to-end: at least one primary user action hits the backend and renders the response

**Scale:** yes/no  
**Review angles:**
- fetch/axios call in code
- 2xx on the main API path
- rendered result reflects backend response

_Source: baseline_

## 13. README contains the exact backend and frontend run commands and they match the actual ports/scripts

**Scale:** yes/no  
**Review angles:**
- README contents
- ports match code
- no missing setup steps

_Source: baseline_

## 14. Interactive elements respond visibly: clicking buttons, links, and content nodes produces a state change or clear feedback (no dead-click controls)

**Scale:** yes/no  
**Review angles:**
- interactive_probe no_change_interactions list
- console errors triggered by interaction
- implied next actions the UI actually exposes

_Source: baseline_

## 15. Page geometry is clean: no overlapping sibling elements, no content clipped behind overflow:hidden containers

**Scale:** yes/no  
**Review angles:**
- eval_layout.json sibling-overlap issues
- content-clipped warnings
- screenshot corroboration

_Source: baseline_

## 16. Disc trajectory is computed from lift and drag coefficients that vary with angle of attack (not treated as a ballistic projectile), with forces scaling with v² and air density.

**Scale:** yes/no  
**Review angles:**
- presence of α-dependent lift
- drag scales with v² and air density

## 17. Flight model represents spin-induced gyroscopic stability so release roll/pitch persist and influence curvature instead of the disc tumbling.

**Scale:** yes/no  
**Review angles:**
- spin rate is a throw input
- disc stays stable rather than tumbling

## 18. Angle of attack evolves over the flight from the disc's pitching moment (center of pressure offset from CG), producing realistic late-flight fade or hold.

**Scale:** yes/no  
**Review angles:**
- AoA evolves over time
- end-of-flight fade/curl visible

## 19. A flat release with no lateral velocity still curves predictably left or right depending on spin direction, modeling the Robins-Magnus lateral force.

**Scale:** yes/no  
**Review angles:**
- spin direction flips curve
- backhand vs flick curvature differs

## 20. Release speeds, spin rates, and angles of attack used by the simulator are grounded in measured human throw data rather than invented constants, and reproduce published range/hang-time.

**Scale:** yes/no  
**Review angles:**
- cites empirical coefficients
- reproduces published range/hang-time

## 21. Engine supports at least backhand, forehand/flick, and hammer releases, including inside-out and outside-in curvature variants.

**Scale:** yes/no  
**Review angles:**
- distinct release attitudes per throw
- IO vs OI curvature distinguishable

## 22. Player movement uses empirically grounded sprint, acceleration, and cutting parameters with distinct acceleration and top-speed phases, not constant velocity.

**Scale:** yes/no  
**Review angles:**
- separate accel vs top-speed phases
- direction-change cost modeled

## 23. Receivers and defenders pursue the disc's predicted future arrival point rather than its current position, and catch resolution depends on who arrives first while the disc is still catchable.

**Scale:** yes/no  
**Review angles:**
- anticipates disc landing point
- accounts for reaction time

## 24. When multiple players converge, the catch is resolved using vertical reach and timing (jump height, catch window), so a player can sky an opponent rather than winning purely by ground proximity.

**Scale:** yes/no  
**Review angles:**
- jump/reach modeled
- timing window for catch

## 25. The thrower's throw choices are constrained by marker force (open vs break side) and an advancing stall count, so defensive pressure shapes throw selection.

**Scale:** yes/no  
**Review angles:**
- force direction limits throw set
- stall pressure affects decision

## 26. Given a vertical, horizontal, or side stack placement, cutters produce lane-respecting cuts with clear lanes for the active cutter and a dump option behind the disc.

**Scale:** yes/no  
**Review angles:**
- recognizes stack type from placement
- lanes kept clear

## 27. Defenders can be configured for person, zone (cup/wall), or poach coverage, and their positioning and switching during disc flight follow the selected scheme.

**Scale:** yes/no  
**Review angles:**
- scheme is selectable
- switches/poaches on deep threat

## 28. Each point resolves to one of completion, drop, block/D, interception, out-of-bounds, or Callahan based on catch location and team, matching ultimate's turnover rules.

**Scale:** yes/no  
**Review angles:**
- OB detected at first ground contact
- defender catch in own endzone flagged

## 29. A user-controllable wind vector influences the disc through the aerodynamic model (altering effective AoA), not as a post-hoc positional offset, producing different upwind vs downwind hang times.

**Scale:** yes/no  
**Review angles:**
- wind alters effective AoA
- upwind vs downwind hang time differs

## 30. A flat (zero-bank) release with non-zero spin produces measurable lateral curvature via a spin-magnitude term in lateral acceleration, not solely from a bank/roll projection of lift.

**Scale:** yes/no  
**Review angles:**
- presence of spin-only lateral acceleration term
- trajectory curves at bank=0 with nonzero spin

## 31. Pitching moment drives heading/roll change proportional to 1/spin (gyroscopic precession), so higher spin yields straighter flight rather than directly tilting pitch.

**Scale:** yes/no  
**Review angles:**
- curvature decreases as spin rate increases
- pitching-moment-to-roll-rate conversion in integrator

## 32. Lift and drag use angle-of-attack polynomials (e.g., CL = CL0 + CLα·α, CD = CD0 + CDα·α²) with α recomputed each step from velocity vs. disc plane, not constants.

**Scale:** yes/no  
**Review angles:**
- α recomputed per step from disc orientation
- nonzero CL0 at α=0 reflecting camber

## 33. Dynamic pressure and all aero forces/moments use (v_disc − v_wind) with a configurable 3-component wind vector, not ground-frame velocity.

**Scale:** yes/no  
**Review angles:**
- wind subtracted before computing q
- headwind/tailwind/crosswind each alter range and curve distinctly

## 34. Aerodynamic center is placed forward of CG so an unspun disc is roll-unstable and stability emerges only via gyroscopic spin.

**Scale:** yes/no  
**Review angles:**
- CP/CG offset present in pitching moment
- zero-spin throws diverge/tumble as expected

## 35. Increasing spin yields a small lift enhancement (more pronounced at low α) and increases drag via trailing-vortex strength at higher α (~>5°).

**Scale:** yes/no  
**Review angles:**
- lift rises with spin at fixed α
- drag rises with spin only above moderate AoA

## 36. Catch/contest compares disc altitude at arrival to each player's max reach (standing reach + jump + extension), not just 2D ground distance.

**Scale:** yes/no  
**Review angles:**
- per-player reach height parameter
- tall/jumping player wins over closer short player

## 37. Contest checks whether each player can reach the disc's (x,y,z) within its flight time given sprint speed, acceleration, and jump takeoff timing window.

**Scale:** yes/no  
**Review angles:**
- per-player kinematic reachability check
- jump apex aligned with disc arrival time

## 38. Predicted trajectories are compared against measured release-state → landing-point data for at least one throw type (hyzer/anhyzer/flat), with documented error.

**Scale:** yes/no  
**Review angles:**
- range error vs. measured throws
- S-curve/fade profile matches observations

## 39. Nonzero crosswind produces altered AoA-driven lift and lateral drift consistent with relative-wind aerodynamics (upwind gains lift, downwind loses it; crosswind shifts landing laterally).

**Scale:** yes/no  
**Review angles:**
- headwind shortens range and boosts lift
- crosswind shifts landing point laterally

## 40. Banked releases still produce lateral force from the tilted lift vector; the spin-Magnus term is additive, so hyzer/anhyzer behavior is retained alongside spin curvature.

**Scale:** yes/no  
**Review angles:**
- bank-only throw still curves
- bank+spin behavior matches expected superposition

## 41. Disc roll/pitch precession rate is inversely proportional to spin angular velocity (ωp = τ/(Is·ωs)), so higher spin yields straighter, more stable flight rather than greater precession.

**Scale:** yes/no  
**Review angles:**
- physical correctness of torque-induced precession formula
- observable effect that fast-spin throws fly straighter than slow-spin throws at equal release angle

## 42. Simulated disc trajectories qualitatively match published frisbee aerodynamic models (Hummel/Potts) where pitch/roll response to aerodynamic torque decreases with increasing spin rate.

**Scale:** yes/no  
**Review angles:**
- agreement with experimental disc flight literature
- absence of unphysical "more spin = more curve" artifacts

## 43. Receivers accelerate from rest toward a top speed (e.g., v(t)=min(a·t, vmax) or v(t)=vmax(1−e^(−t/τ))) rather than translating at constant velocity from t=0.

**Scale:** yes/no  
**Review angles:**
- time-to-top-speed consistent with elite sprinters (~4–6 s to ~10 m/s)
- piecewise distance integral used for lead-pass interception

## 44. Player top-speed parameter is bounded by elite human sprint data (≈9–12 m/s) and acceleration by realistic peak values (≈3–4 m/s² average over 0–30 m).

**Scale:** yes/no  
**Review angles:**
- parameter values within published elite ranges
- no superhuman interception envelopes

## 45. When a receiver's cut vector changes direction, the simulator imposes a deceleration/reacceleration cost (time penalty proportional to angle change) instead of instantaneous velocity reversal.

**Scale:** yes/no  
**Review angles:**
- penalty magnitude scales with turn angle
- receiver loses ground on sharp cuts vs. straight cuts of equal distance

## 46. Simulator accepts a `force` input (flick/backhand/none) and biases the thrower's available/selected throws away from the forced side, reflecting standard ultimate marking strategy.

**Scale:** yes/no  
**Review angles:**
- forced-side throws penalized in probability or removed from option set
- force=none recovers unbiased throw distribution

## 47. The simulate API accepts an incoming `stall_count` (0–10), advances it during possession, returns the updated value, and forces a turnover/dump decision as the count approaches 10.

**Scale:** yes/no  
**Review angles:**
- stall increments at ~1/sec of possession
- thrower decision-making shifts toward safe/dump throws at high stall

## 48. Frontend exposes both `force` (flick/backhand/none) and `stall_count` controls alongside scheme/mode, posted values reach the backend, and returned stall_count is displayed.

**Scale:** yes/no  
**Review angles:**
- controls visible and editable pre-simulation
- round-trip displays updated stall after simulation

## 49. The catch-feasibility solver replaces `lead = pos + v*t` with reachability under the acceleration model (max distance achievable by time-of-flight given current velocity and heading).

**Scale:** yes/no  
**Review angles:**
- deep cuts with runway favored over standing receivers
- short reaction-window throws limited by acceleration, not top speed

## 50. When force is set, throw release points/angles available to the simulated thrower are geometrically constrained on the forced side (open-side hucks favored, break-side throws downweighted) rather than uniformly available.

**Scale:** yes/no  
**Review angles:**
- open-side completion rate higher than break-side under force
- force=none yields symmetric throw availability

