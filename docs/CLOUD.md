# FleetMesh cloud deployment (v1.9)

The frontend is static HTML/CSS/JavaScript on Vercel. `/api/*` is rewritten to a
single Render Python service. Each visitor receives an HttpOnly, signed cookie
and a separate simulation session. Render connects to Neon using backend secrets.
The robot subprocesses communicate by authenticated UDP inside that service.

## Deploy

Current resources and measured checks are listed in [CLOUD_VALIDATION.md](CLOUD_VALIDATION.md).
Reuse those existing projects. The steps below also explain a manual setup.

1. Deploy this branch to Render using `render.yaml`, or a Python web service with
   build `pip install -r requirements-cloud.txt` and start
   `python migrate.py && python cloud.py`. Choose Singapore and the free plan.
2. Supply `DATABASE_URL` (Neon pooled), `DATABASE_URL_UNPOOLED` (direct), a stable
   random `SESSION_SECRET` of at least 32 characters, and `ALLOWED_ORIGINS` containing
   the exact frontend origin. Never put database credentials in Vercel or Git.
3. Update the `/api/:path*` destination in `vercel.json` to the actual Render URL.
4. Import this repository/branch into Vercel. Root: repository root; framework: Other;
   build: `npm run build`; output: `public`. No frontend environment secrets are needed.
5. Add the actual preview/production origin to Render `ALLOWED_ORIGINS`, comma-separated
   if necessary, and redeploy. Do not allow all `*.vercel.app` projects.
6. Verify health, session creation, demo, History, and exports on the Vercel URL.
   Confirm another browser cannot access the first browser's run URL.

Keep exactly one Render instance. The simulator is deliberately not horizontally
distributed across cloud workers. A deployment/restart interrupts active robots;
history stays in Neon and is marked interrupted. Keep the signing secret stable
so browser cookies continue to identify saved runs after a restart.

## Local compatibility and verification

`python start.py --open` retains the original local-only SQLite app with no extra
dependencies. Cloud support has separate requirements.

For a local split-frontend check, install cloud dependencies, set
`FLEETMESH_LOCAL_CLOUD=1`, `SESSION_SECRET` to a development-only random value,
`ALLOWED_ORIGINS=http://127.0.0.1:4173`, and `PORT=9293`, then run `python cloud.py`.
This explicit development mode uses SQLite if DATABASE_URL is absent. Run
`npm run build` and `node scripts/preview.mjs` in another terminal; open port 4173.
If DATABASE_URL is set, PostgreSQL failure never switches storage to SQLite.

Tests: `python -m unittest discover -s tests -v`, `npm run check`, and `npm run build`.
The Python suite includes real HTTP requests, independent processes, cookie/CSRF
checks, visitor isolation, retry receipts, resource caps, and restart persistence.

## Public demo limits

- At most two concurrent fleets (three to six processes each), 24 resident visitor
  sessions, bounded HTTP threads, 40 control requests and 180 private reads/minute
  per visitor. These bounds reduce resource abuse; they are not a DDoS guarantee.
- Fleets stop after ten wall-clock minutes or two minutes without visitor API
  activity. History access after clearing cookies requires a new identity; there
  is no account login or cross-device recovery in this release.
- Keep at most the latest 80 runs across the demo, up to seven days. Each run keeps
  up to 900 recent sampled frames, compressed. High-speed replay is sampled,
  not every physics tick; exact final state and retained events are also saved.
- Saved control receipts are capped at 10,000 globally and expire after seven days.
  Once full, new control commands stop with an explicit capacity message.
- A coalescing writer keeps SQL latency outside robot tick decisions. On a database
  outage, latest snapshots queue in memory and the console warns that history is
  temporarily unsaved. If the process crashes before reconnecting, those unsaved
  frames are lost. Control requests require a durable retry receipt before acting.
- An interrupted pending command is never blindly replayed after restart. Its
  outcome is reported unconfirmed; inspect history and issue a new command deliberately.
- Free Render services can sleep or restart; free quotas are shared with the
  account's other services. Open the demo before presenting, and keep the local
  launcher and included recording available. No paid service is required here.

## What the engineering establishes

Agent processes own task auctions, versioned unpicked-job handoffs, route planning,
and peer resource permissions. INFO packets now include position, short route intent,
stage, and job identity. The inspector exposes peer observations and their age.
Position/intent broadcasts are telemetry; safety decisions still rely on permission
ownership and the simulated local proximity stop. Stale observations never grant
permission. A dead robot's held zones do not expire automatically.

The supervisor supplies ideal own-position observations, a common simulation clock,
local proximity observations, physics, and new-job announcements. It aggregates
results for the dashboard. This is a hosted simulator, not physical AMR deployment.
Real localization, braking, independent clocks, Wi-Fi behavior, ROS integration,
and hardware safety remain unvalidated. Battery values are illustrative.

The original 160-run development benchmark remains historical evidence. The fixed
rule meets the 20% target in only 2 of 5 cohort means. Added cloud/session features
and peer telemetry do not by themselves establish faster routing or general safety.

## Three-minute judge demo

1. Open the cinematic introduction; identify the footage as illustrative.
2. Open Console, launch the live disruption demo, and inspect robot process IDs.
3. Show the urgent mission, aisle closure, peer-message interruption/restoration,
   and route/ownership decisions. Manual fault controls also work in New experiment.
4. Observe completion or explain the exact safe waiting condition if incomplete.
5. Open History, review the result, replay it, and download JSON/CSV/HTML evidence.
6. Refresh the page and reopen the same saved record. Explain that a backend restart
   preserves evidence but does not resume the previous robot processes.
