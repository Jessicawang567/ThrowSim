# Ultimate Frisbee Stack Simulator

A top-down **7-on-7 ultimate frisbee** simulator that predicts the outcome of a
throw before it happens. Set up your stack, point your cutters, pick a handler,
and hit **Simulate** — the app computes who can catch the disc, accounting for
each defender chasing the predicted catch point during the disc's flight.

It's a coaching / tactics sandbox: experiment with formations, throwing forces,
defensive schemes, and wind, and see how the geometry changes who gets open.

---
<img width="1456" height="653" alt="image" src="https://github.com/user-attachments/assets/1d9b0d4b-61bf-4172-9fa1-2279b38f9307" />
---

## What it does

- **Static catch prediction with motion.** Every offensive player sprints along
  the direction you give them; their defender anticipates the catch point and
  races there at full speed. The simulator solves the "lead pass" geometry to
  decide whether the throw is caught or blocked.
- **Two play modes:**
  - **AI picks throw** — the engine evaluates every receiver and chooses the
    throw with the best expected value (an EPV-style trade-off between yards
    gained and the risk of a turnover).
  - **User picks target** — you click the receiver you want to throw to and see
    whether it works.
- **Tunable scenario:** defensive scheme (man / zone / cup), marking force
  (none / flick / backhand), stall count, and 3-axis wind (tailwind/headwind,
  crosswind, vertical).
- **Interactive field:** drag any player to reposition; shift-drag an offensive
  player to set their cutting direction; ghost markers show predicted positions
  at the moment the disc arrives.

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | 3.10 or newer | Runs the backend (FastAPI + uvicorn). |
| **Node.js** | 18 or newer | Runs the frontend (Vite + React). |
| **npm** | bundled with Node | Installs frontend dependencies. |

No API keys, accounts, databases, or internet connection are required at
runtime — the simulator is fully self-contained.

---

## Quick start

The project ships a one-command launcher that starts **both** servers:

```bash
./run.sh
```

Then open **http://localhost:5173** in your browser. Press `Ctrl+C` in the
terminal to stop everything.

> The launcher creates a Python virtual environment, installs backend
> dependencies, installs frontend dependencies (first run only), then starts the
> backend on port 8000 and the frontend on port 5173.

---

## Manual setup (step by step)

Use this if you want to run the two halves separately, or if `run.sh` doesn't
fit your environment.

### 1. Start the backend (API server)

```bash
cd backend

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API (serves on http://localhost:8000)
python main.py
```

Leave this terminal running. Verify it's up by opening
**http://localhost:8000/api/health** — you should see `{"status":"ok"}`.
Interactive API docs are at **http://localhost:8000/docs**.

### 2. Start the frontend (web UI)

Open a **second** terminal:

```bash
cd frontend

# Install dependencies (first run only)
npm install

# Start the dev server (serves on http://localhost:5173)
npm run dev
```

### 3. Open the app

Go to **http://localhost:5173**. The page talks to the backend automatically.

---

## Configuration

### Changing the backend URL / port

The frontend defaults to `http://localhost:8000`. If you run the backend on a
different host or port (for example because port 8000 is already in use), point
the frontend at it with the `VITE_API_BASE` environment variable:

```bash
# terminal 1 — backend on an alternate port
cd backend && source .venv/bin/activate
python -c "import uvicorn; uvicorn.run('main:app', host='127.0.0.1', port=8008)"

# terminal 2 — tell the frontend where the backend is
cd frontend
VITE_API_BASE=http://localhost:8008 npm run dev
```

CORS is enabled on the backend, so the browser can call it from the Vite dev
server without extra setup.

### Building for production

```bash
cd frontend
npm run build      # outputs static files to frontend/dist/
npm run preview    # optional: serve the built files locally
```

Serve `frontend/dist/` with any static host, and run the backend (
`python backend/main.py`) wherever it can be reached. Set `VITE_API_BASE` at
build time to the backend's public URL.

---

## Using the simulator

| Control | What it does |
|---------|--------------|
| **Drag a player** | Reposition any player on the field. |
| **Shift-drag an offensive player** | Set that player's cutting (running) direction. |
| **Click a non-handler offensive player** | In *User picks target* mode, choose them as the throw target. |
| **D scheme** (man / zone / cup) | Defensive coverage style. |
| **Force** (none / flick / backhand) | Which way the mark forces the handler to throw. |
| **Stall** | Stall count, which influences throw urgency. |
| **Wind sliders** | Tailwind/headwind, crosswind, and vertical wind (m/s). **Calm** resets them. |
| **AI picks throw** | Engine selects the highest-value throw. |
| **User picks target** | You choose the receiver. |
| **Simulate** | Run the prediction. |
| **Reset** | Restore the default stack. |

After simulating, the right-hand panel shows the chosen throw, the predicted
catch point, the margin over the nearest defender, and a ranked list of **all**
evaluated options with catch probability, yardage gained, expected value, and
disc flight time.

---

## How it works

The field is 100 m × 37 m, with end zones at `x ∈ [0, 18]` (defensive) and
`x ∈ [82, 100]` (offensive). The simulation:

1. Moves each offensive player along their assigned direction at a world-class
   sprint speed (~7.5 m/s).
2. Assumes each defender man-marks the nearest opponent and runs at full speed
   toward the receiver's **predicted** catch location from the moment of release.
3. Solves the lead-pass equation `t = distance(handler, lead_point(t)) / disc_speed`
   to find where and when the disc and receiver meet.
4. Gives the defender that same flight time `t`; if they reach the catch point
   first (within a small "play on the disc" radius), it's a block — otherwise the
   receiver catches.
5. In AI mode, scores every legal throw by expected gain toward the end zone with
   a risk penalty for low catch probability, and picks the best one.

---

## API reference

The backend exposes a small JSON API (base URL `http://localhost:8000`):

| Method & path | Description |
|---------------|-------------|
| `GET /api/health` | Liveness check → `{"status":"ok"}`. |
| `GET /api/field` | Field dimensions → `{"length":100.0,"width":37.0,"off_endzone_x":82.0,"def_endzone_x":18.0}`. |
| `POST /api/simulate` | Run a prediction. |

**`POST /api/simulate`** request body:

```jsonc
{
  "players":    [ /* 14 players: id, team, x, y, direction, is_handler */ ],
  "mode":       "ai",          // "ai" | "user"
  "target_id":  null,          // required in "user" mode
  "scheme":     "man",         // "man" | "zone" | "cup"
  "wind":       { "vx": 0, "vy": 0, "vz": 0 },
  "force":      "none",        // "none" | "flick" | "backhand"
  "stall_count": 0
}
```

The response contains the chosen throw, predicted catch point, defender margin,
and the per-receiver evaluation breakdown. See the live schema at
**http://localhost:8000/docs**.

---

## Project structure

```
frisbee-stack-sim/
├── run.sh                 # one-command launcher (backend + frontend)
├── backend/
│   ├── main.py            # FastAPI app + the entire simulation engine
│   └── requirements.txt   # fastapi, uvicorn, pydantic
└── frontend/
    ├── index.html
    ├── package.json       # Vite + React + TypeScript + Tailwind
    └── src/
        ├── App.tsx        # main UI
        ├── api.ts         # backend client (honors VITE_API_BASE)
        ├── components/    # field, controls, results panel
        ├── presets.ts     # default stack / formations
        └── types.ts       # shared TypeScript types
```

---

## Troubleshooting

- **"Port 8000 is already in use."** Another app is on 8000. Run the backend on a
  free port and set `VITE_API_BASE` (see [Configuration](#configuration)).
- **UI loads but Simulate fails / "Simulation failed".** The backend isn't
  reachable. Confirm `http://localhost:8000/api/health` returns `{"status":"ok"}`
  and that `VITE_API_BASE` matches the backend's actual address.
- **Blank page or build errors.** Make sure you're on Node 18+ (`node --version`)
  and re-run `npm install` in `frontend/`.
- **`python: command not found`.** Use `python3`, and confirm you're on Python
  3.10+ (`python3 --version`).

---

## Tech stack

- **Backend:** Python, FastAPI, Uvicorn, Pydantic — pure-Python geometry/physics,
  no external services.
- **Frontend:** React 18, TypeScript, Vite 5, Tailwind CSS, lucide-react icons.
