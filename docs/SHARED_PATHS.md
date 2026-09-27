# Shared paths: implementation and judge demo

This update makes robot conflicts visible and explainable. It retains Dijkstra,
the existing whole-route permission protocol, and independent Python/UDP agents.
It does not introduce shorter reservations or claim a throughput improvement.

## What is implemented

- **Explore shared paths** starts three independent robot processes, six missions,
  shared-pickup demand and the compact map at 2x speed. It is an experiment preset,
  not a scripted winner, predetermined route, or synthetic movement animation.
- Each agent emits its own structured decision: requested zones, immutable request
  key, missing peers, report ages, overlapping held zones and earlier conflicting
  requests when those are supported by a peer's last report.
- A missing/stale report is explicitly unconfirmed. A fresh report is still the
  last received report, not perfect current knowledge. Silence never supplies a
  grant, removes a failed robot or clears its reservations.
- The map shows requested zones for the selected robot, held-zone ownership and
  occupied road sections. The shared-space table has a textual equivalent.
- Occupancy comes from simulator positions and disc-to-segment distance. It includes
  endpoints and dead robots. This observer overlay is not fed to the permission
  protocol. It does not mean an entire highlighted road is filled by a robot.
- A requested closure waits until the simulated robot body clears the segment.
  This fixes the old centreline-only closure test. Reopening cancels a pending
  closure. A pending closure is still not a gate forbidding all new arrivals.
- Decision transitions enter the event log. Decisions and occupancy are stored with
  snapshots/frames and JSON exports. HTML reports include decisions at the saved
  snapshot. Replay shows recorded observations; older recordings show an explicit
  unavailable-detail message instead of invented explanations.
- The new start action uses the existing cloud authentication, visitor isolation,
  capacity check and command receipt/idempotency handling.

## Judge demonstration (about three minutes)

1. Open `/app` and choose **Explore shared paths**. This saves/replaces the current
   experiment. Watch the robots move out of their private docks.
2. Select a robot in the **reserving** stage. Read **Why this robot acts**. Point to
   the named peer and overlapping zones. A dashed intended route is not permission.
3. Pause once another robot is on a road. Select that road under **Aisle access**,
   choose **Close aisle**, and show the queued closure. Choose **Reopen** to cancel.
4. Interrupt peer messages and resume for over two simulated seconds. Pause and
   inspect a waiting robot. Peer information should become stale while permission
   remains required. An already granted robot may continue its reserved movement.
5. Restore messages and resume. Use 8x or 32x to finish. Read actual completion and
   detected-collision counts; do not promise an identical UDP execution time.
6. Refresh, then open Run history and replay the run. Inspect a saved waiting frame.
   Download the report to preserve the final decision and mission evidence.

The regular **Launch live demo** remains available for scheduled aisle closures,
map sharing and route recovery. The shared-path preset has no scheduled disturbances.

## Where the code lives

| File | Responsibility |
|---|---|
| `agent.py: Agent.decision` | Explanation from this agent's request and received peer data |
| `agent.py: Agent.step` | Peer request-key telemetry and decision-transition events |
| `simulation.py: World.edge_occupants` | Finite segment / robot disc occupancy |
| `simulation.py: World.traffic` | Read-only occupancy and reservation overlay |
| `server.py: Session.command` | Repeatable shared-path experiment preset |
| `cloud.py: Manager.execute` | Existing isolation, capacity and retry handling for the action |
| `web/workspace.js` | Decision panel, zone table and map overlay |
| `demonstration.py: run_report` | Saved decision evidence in HTML export |

## Validation

Verified locally on 27 September 2026: 58 Python tests passed. The Chromium
workflow completed 6/6 missions in 127.5 simulated seconds with zero detected
collisions, three distinct process IDs and 130 saved frames. This is one
disturbed run, not a paired performance benchmark. Desktop and 390px mobile
views were inspected; no browser console errors or page-width overflow were observed.


Run the Python suite and frontend build from the repository root:

```sh
python -m unittest discover -s tests -v
npm run check
npm run build
```

The optional browser test starts its own local HTTP server and real robot processes,
then closes the browser/server and deletes its temporary database. Install Playwright
locally for development; it is not a production runtime dependency:

```sh
npm install --no-save playwright
npx playwright install chromium
node tests/conflict_browser.cjs
```

`FLEETMESH_BROWSER_EXECUTABLE` can select an installed Chromium. Browser output and
screenshots go to `test-results/`. Committed captured evidence is in
`evidence/shared_path_browser.json` and `docs/screenshots/shared-path-*.png`.

## Deployment and boundaries

Merge the reviewed branch, then deploy the Python backend on Render and the static
frontend on Vercel. No new environment variables or database migrations are required.
The frontend disables the new scenario if the backend has not advertised support;
existing controls and recordings remain usable. A Vercel PR preview alone does not
upgrade the production Render backend.

This change has local verification, not a new production deployment or live Neon
verification. The cloud API is tested with its explicit SQLite test configuration.
Existing retained performance numbers are historical: the changed closure geometry
has not been subjected to a refreshed paired 160-run benchmark.

Simulator step: 0.1 simulated seconds. Live browser polling: 250 ms local / 1000 ms
cloud, plus network and scheduling delay. This is not an instant-response or hard
real-time guarantee. Perfect localization and constant-speed motion remain; realistic
braking, human sensing, automatic failed-peer replacement and deadlock-safe adaptive
short reservations still require separate engineering and validation.
