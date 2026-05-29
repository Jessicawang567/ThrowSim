# Ultimate Frisbee Stack Simulator

Top-down 7v7 ultimate frisbee simulator. Drag players to their starting stack
positions, assign running directions to the offense, mark one offensive player
as the handler, then press **Simulate** to see a static prediction of who can
catch the disc — accounting for defender pursuit during the disc's flight.

Two modes:
- **AI picks throw** — chooses the throw maximizing an EPV-style value.
- **User picks target** — you click the intended receiver.

## Run

Backend (port **8000**):

```
pip install -r backend/requirements.txt && python backend/main.py
```

Frontend (port **5173**):

```
cd frontend && npm install && npm run dev
```

Then open http://localhost:5173.
