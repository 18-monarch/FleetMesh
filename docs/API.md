# Local API

The console normally runs at `http://127.0.0.1:9292`. All endpoints are local-only. A valid Host header is required. State requests are read-only. POST requests require `Content-Type: application/json` and the `X-FleetMesh-Token` value from the operations page at `/app` and its meta element. Maximum request body: 4096 bytes.

| Method/path | Purpose | JSON fields |
|---|---|---|
| GET `/api/health` | Version and readiness | - |
| GET `/api/state` | Current world, jobs, robots, events and map | - |
| GET `/api/evidence` | Saved benchmark summary | - |
| GET `/api/runs` | Most recent 100 experiments | - |
| GET `/api/runs/{id}` | Configuration and latest snapshot | - |
| GET `/api/runs/{id}?frames=1` | Up to 2000 recorded frames | - |
| GET `/api/runs/{id}?download=1` | JSON download | - |
| GET `/api/runs/{id}/csv` | Job ledger CSV | - |
| POST `/api/start` | Save current run and create a fresh one | `map`, `scenario`, `mode`, `seed`, `robots`, `jobs` |
| POST `/api/pause` | Toggle simulated time and motion | `{}` |
| POST `/api/speed` | Playback speed | `rate`: 1, 2, 4, 8, 16 or 32 |
| POST `/api/maintenance` | Accept/donate new work; finish active cargo | `robot`: zero-based ID, `available`: boolean |
| POST `/api/network` | Interrupt or restore peer messages | `partitioned`: boolean |
| POST `/api/aisle` | Close/reopen a road edge | `edge`: sorted `Nxx:Nxx`, `blocked`: boolean |
| POST `/api/kill` | Stop one process without expiring its resources | `robot`: zero-based ID |
| POST `/api/job` | Announce a new job for peer allocation | `pickup`, `drop`, `priority`: 1-3 |

Maps: `compact`, `warehouse`, `extended`. Scenarios: `normal`, `congestion`, `network`, `blocked`. Policies: `baseline`, `atomic`, `heuristic`, `predictive`. Seed: 0-999999. Robot count: 3-6. Startup jobs: 1-30. Maximum jobs per run: 100.

Robot timing values are local controller-step milliseconds. Mission time is simulated seconds. Distances are simulated metres. Job owners and robot IDs are zero-based in JSON and one-based in the interface.

This observer API has no endpoint for injecting arbitrary robot velocities or forging peer grants. Read `README.md` before adapting any transport for a real machine.

## Demonstration and run reports (1.1)

`POST /api/demo` with an empty JSON object launches the documented fixed-policy disturbance scenario, saving the existing run first. It uses the same local session token as other controls. `GET /api/runs/{id}/report` downloads an escaped, standalone HTML summary of the last persisted snapshot. State, history and replay records include `demonstration` when attached, with observed action times and the urgent mission state. Older saved records remain readable.

## Release 1.2 command and persistence behavior

POST requests may send `X-FleetMesh-Request-ID` (8-80 alphanumeric, dash or underscore characters). Repeating the same successful command and JSON body with the same ID returns its original `run_id` with `replayed: true`. Reusing the ID for a different command is rejected. The last 256 successful IDs are retained for the current server process; this is not a durable exactly-once guarantee across restarts or eviction. The UI retries transport failures once with the same ID.

All accepted run mutations persist immediately, including paused mission submissions and network/aisle controls. Reading a live run export captures the current snapshot. Run snapshots are detached copies. Unknown export suffixes return 404.

Failed/timed-out runs reject mutation commands. Completed runs allow `job` to begin more work; fault controls require an active run. Starting a new experiment remains available. Speed is an operator playback setting, not a motion controller command.

A startup failure clears live run identity and retains earlier records. On opening a data folder, old `running` or `paused` records become `interrupted`, since their robot processes cannot be resumed. The instance lock prevents simultaneous application instances from owning a data folder.

`GET /api/health`, configuration metadata and the launcher use `version.py`. Predictive mode requires three finite model weights; an unavailable/invalid model is rejected explicitly. The fixed policy remains usable.


## Run review and the included recording (v1.3)

- `GET /api/runs/{id}/insights`: current saved run review. Includes mission counts, lead times since submission, per-robot waits, source version and finite observation checks. The live run is persisted before review. Road ownership and duplicate active-job checks inspect saved frames only; collisions come from the simulator counter. Empty/no-frame data are labelled not checked.
- `GET /api/sample`: the included v1.1 demonstration record and 201 frames, served read-only from evidence/demonstration.json. It does not create a database run or launch workers.
- `GET /api/sample/insights`: the same review schema for the included recording.
- `GET /api/sample/report`: portable HTML report for that recording.
- `/workspace.js`: companion interface logic for inspection, presentation mode, replay and review.

No review endpoint grants access, changes mission ownership or commands a robot. Sample process IDs are historical capture metadata, not currently running processes.

## Cinematic frontend (v1.6)

- `GET /` serves the token-free illustrative film page. It reads only `/api/evidence`; it never starts robot processes.
- `GET /app` and `/app/` serve the token-bearing operations console. `/app#sample`, `/app#evidence` and `/app#review` are read-only client entry points.
- `GET /media/warehouse-film.mp4` serves local H.264 media. A valid single byte Range returns 206 and Content-Range; an unsatisfiable range returns 416 and `bytes */SIZE`. Unsupported or malformed ranges are ignored with a full 200 response. If-Range also falls back to 200 because no matching validator is supplied.
- `HEAD /media/warehouse-film.mp4` returns full-file headers without a body. Streaming uses bounded chunks and does not read the whole asset into memory.
- `/media/warehouse-film-poster.webp` supplies the still image; `/film-player.js` handles seeking. The version query on the media URL busts caches when upgrading.
- The explicit static allowlist and local Host check apply to media as to other assets. CSP permits only same-origin media. No arbitrary filesystem path is served.

The film never sends routes, velocities, grants or task ownership to the backend. Text and navigation remain independent of media loading.

The explicit static allowlist also serves `/media/warehouse-opening.png` and `/media/warehouse-coordination.png` as `image/png`. These are illustrative still assets. Navigation to the coordination chapter does not start a run.


## Frame sequence assets (v1.8)

GET or HEAD /media/warehouse-frames/frame-NNN.webp accepts exactly three digits, 000 through 140, followed by .webp. Valid frames return image/webp, exact Content-Length and Cache-Control: private, max-age=3600. Invalid names or out-of-range indices return 404. The usual local Host validation applies. Query strings may carry a release version. GET /sequence-player.js serves the active player; it sends no robot commands.
