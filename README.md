# FleetMesh 1.9

Cloud integration adds a static Vercel frontend, bounded visitor sessions on a Render
Python backend, and scoped Neon PostgreSQL history. The local SQLite launcher remains
available. See [cloud deployment and judge demo](docs/CLOUD.md) for setup, architecture,
resource limits, persistence behavior, and verification. The sections below document
the original local v1.8 release and its historical benchmark evidence.

**A complete local simulation application for warehouse robot coordination.** This release has a runnable backend, independent robot processes, an operations dashboard, live task submission, controlled task handoff, map disturbances, robot inspection, presentation mode, playable history, run review and exports.

It is **not a physical AMR controller or a certified warehouse deployment**. The general SIH 20% performance target is not claimed. Read the measured results in the Benchmarks tab.

## Quick start

1. Extract the complete ZIP to a writable folder.
2. Install **Python 3.10 or newer** if it is not already installed. No paid service, API key, Node.js or third-party Python dependency is needed.
3. **Windows:** double-click `Start_FleetMesh.bat`. **macOS/Linux:** run `sh start_fleetmesh.sh` in the extracted folder.
4. The browser opens the cinematic warehouse introduction. Select **Open console** for operations. If it does not, open the URL printed in the terminal, normally `http://127.0.0.1:9292`.
5. Keep that terminal open. Select **Launch live demo** for a repeatable disruption scenario, or **New experiment** for your own workload.

Manual launch: `python start.py --open` (use `python3` or `py -3` as appropriate). Stop with Ctrl+C.

The launcher tries the requested port and the next ten ports if occupied. You can choose `python start.py --port 9400 --open`. The local database is in `data/fleetmesh.sqlite3`; choose `--data-dir PATH` to use another writable location. One instance can use a data folder at a time.

The application has been executed on Linux. Windows and macOS launchers are provided but have not been executed on those systems in this environment.

## Product features

- Three warehouse sizes: 9, 12 and 16 road zones.
- Three to six separate robot processes with direct authenticated loopback UDP.
- Up to 30 startup jobs and 100 jobs per experiment, with priority and live submission.
- Per-job peer auctions and acknowledged ownership transfer before pickup.
- Maintenance mode: finish active work, donate queued unpicked jobs and stay docked.
- Four policies: sequential baseline, atomic route reservation, fixed-rule congestion routing and learned-delay routing.
- Dynamic aisle closures, local sensing and map sharing, with safe return/replanning when an owned path back to the dock exists.
- Network interruption/restoration, packet loss/delay scenarios and explicit process-failure injection.
- Live map, resource ownership, decisions, process IDs, local controller timings and job ledger.
- SQLite history, recorded-frame replay, JSON experiment exports and CSV job exports.
- Cross-platform launchers, input validation, local-only HTTP access and an operating guide at `/guide`.

## What changed in v1.8

- Fixed the abrupt scene split by retaining one warehouse background throughout the story. The overhead illustration now sits in a contained panel beside the explanation, with its caption below the image. Removed the floating route labels that overlapped the heading.
- Scroll animation now draws 141 WebP frames extracted from the supplied Leonardo/Hailuo film. It no longer depends on MP4 decoding or video seek events. The original MP4 remains in the package as a source asset.
- At most four frame requests and sixteen decoded images are retained. Rapid scroll changes cancel obsolete requests. Missing images time out after five seconds and expose Retry motion; the last good scene stays visible.
- Pause works during loading. Reduced motion starts static without frame downloads. Hidden pages stop requesting images. The complete camera move finishes by the coordination chapter.
- Consolidated the responsive stylesheet, kept image and text in separate grid cells, and separated bottom controls from the evidence footer.
- 38 system/HTTP tests, 34 console checks and 35 sequence/page checks pass. Every WebP image decodes successfully. Browser layout and device smoothness remain unverified in this environment; the remote browser could not access localhost.

**Use the updated release:** stop the old FleetMesh terminal with Ctrl+C. Extract this ZIP into a new folder, launch that folder's Start_FleetMesh.bat (or sh start_fleetmesh.sh), and use the exact new URL printed in its terminal. The footer shows v1.8.0. An old tab on port 9292 may belong to an older running copy.

## What was new in v1.7

- The team's new Leonardo/Hailuo warehouse film is now the scroll-controlled introduction: 1376 x 768, 24 fps, 141 frames, 5.875 seconds. Scroll down to advance and up to reverse; copy and buttons remain native HTML.
- The opening fallback now comes from this exact film. Its dark warehouse lighting is preserved without the previous extra brightness/contrast filter.
- The local 5.29 MB MP4 has keyframes every three frames and fast-start metadata. No video service subscription is needed to run FleetMesh.
- Pause/resume, reduced motion, retry, chapter navigation and direct console access are retained. The overhead coordination panel remains a separately labelled concept still.
- 36 system/HTTP tests, 34 console integration checks and 30 cinematic checks pass. Seek checks use the new clip duration. All 141 frames decode successfully with FFmpeg; this does not establish browser seek smoothness.

The supplied film illustrates the setting and a gentle rising camera move. It does not show the proposed blocked-junction maneuver or prove physical robot coordination. Browser playback, responsive visual acceptance and projector appearance still need a check on the team's laptop.

## What was new in v1.6

- Refined header, outlined controls, larger typography, emerald accents and horizontal chapter progress, following the supplied visual references.
- Approved opening image as a local fallback and a full-width overhead coordination illustration with separate vector routes and labels. The illustration is visibly labelled **still image**; it does not pretend to be newly generated video or live telemetry.
- Existing supplied MP4 retained for scroll-controlled motion. A subtle CSS treatment gives the film a darker presentation; its source content and camera movement are unchanged.
- All assets ship locally. No Gemini or Runway subscription is needed to run this release.
- 36 system/HTTP tests, 34 console integration checks and 30 film/page checks pass. The core coordination engine, benchmark and included recording remain unchanged.

**Historical v1.6 limitation:** a new film was unavailable then. Version 1.7 now includes the team's subsequent Leonardo/Hailuo upload, described above.

## What is new in v1.5

- **Realistic scroll-controlled film:** the team's supplied AI-generated warehouse footage replaces the procedural homepage scene. Scroll down to advance and up to reverse; all headings and controls remain native HTML.
- **Local media:** a muted 10-second H.264 film, 1280 x 720 at 24 fps, with frequent keyframes, fast-start metadata and byte-range HTTP delivery. No external player or API key is needed.
- **Motion controls:** pause/resume, reduced-motion still image, media-failure fallback and explicit retry. Hidden tabs stop requesting seeks. The operations console stays directly available at `/app`.
- **Consistent interface:** the v1.4 navy/green operations theme, robot inspector, presentation view, replay and run review are retained.
- **Clear provenance:** the film is labelled AI-generated and illustrative. Evidence cards read saved benchmark data; actual process behavior is inspected in the console.
- **Verified here:** 36 system/HTTP tests, 34 console integration checks and 30 film/page checks pass on Linux. Video asset decoding and packaged startup are also checked. Player tests use media/DOM stubs; actual browser seeking smoothness and responsive appearance need the presentation laptop.

Read **docs/FRONTEND.md** for the brief laptop check and **docs/MEDIA.md** for provenance and encoding. The film uses browser H.264 decoding; no WebGL renderer is loaded by the current homepage. Legacy Three.js scene source and its MIT license remain bundled for reference.

## Retained features from v1.3

- **Presentation view:** select Present or press P to focus on the floor and decisions; Escape exits.
- **Robot inspector:** click a robot on the map, its card name or the Inspect robot selector. Read its actual mission, decision reason, planned route, permissions and held zones.
- **Playable replay:** play/pause, scrub and choose playback speed. Recorded frames are read-only; the live experiment continues independently.
- **Ready-to-watch sample:** Watch recorded demo opens the included 201-frame v1.1 capture without starting or replacing a live fleet. It is clearly labelled as a recording.
- **Run review:** observed checks, waiting-time bars, urgent job completion and per-job lead times. The backend calculates these from saved observations. A single run is not a speed comparison or a physical safety proof.
- **Updated six-slide pitch and product guide:** current UI, implementation, evidence, business fit, next milestones and presenter notes.
- **At v1.3, 26 system tests and 34 UI/API harness checks passed.** The UI harness uses minimal DOM/canvas stubs against a real HTTP/UDP backend. Full browser visual review remains required on your presentation laptop.

The v1.2 persistence, retry protection, lifecycle handling, search, form feedback and explicit process-stop confirmation remain in place. Six retained v1.2 process audit cases completed 81 jobs without detected collisions. The original 160-run benchmark and controller algorithms are unchanged. Do not add these counts together.

Read **docs/FleetMesh_Product_Guide.pdf** for the updated v1.8 workflow. The same operating guide is available inside the app. The updated pitch describes v1.3. FleetMesh_Product_Audit.pdf is the historical v1.2 assessment; the winner research is background reading from the preceding milestone.

## Repeatable disruption demo

Select **Launch live demo** on Overview. This saves the current experiment and launches three independent robot processes on the warehouse map with seed 200 and the fixed routing policy. At 5 simulated seconds an urgent seventh mission arrives; an empty road segment closes at 12 s; peer messages stop at 20 s and resume at 28 s; the aisle reopens at 45 s. Outcomes come from the running agents. The script does not issue route permissions.

Use **Download run report** or **Run history > Report** for a portable HTML record with the configuration, observed outcome, disturbance log and mission ledger. The report captures the current snapshot for a live run. Run review computes lead times from mission submission and checks ownership only in saved frames. Open it in a browser and print to PDF if desired. Replay and Review remain available in Run history. The recorded sample can also be opened directly from Overview.

The included recorded demonstration completed seven missions in 198.4 simulated seconds, with two route recoveries, one ownership transfer and zero detected collisions. This is one known process-based scenario, separate from the unchanged 160-run benchmark. It is not a speed comparison or physical safety proof. Run `python tools/verify_demonstration.py` to regenerate its JSON/HTML evidence; timings and process IDs may differ.

The default new experiment now uses the fixed rule because it is faster in four of five current benchmark averages. The learned model is still available for comparison. See `docs/SIH_Winner_Research.md` for research lessons, sources, remaining gaps and the submission plan.

## A manual demonstration

1. Run three robots and six jobs on the warehouse map. Watch actual process IDs and peer-owned road zones.
2. Add a high-priority mission in the Missions tab.
3. Request maintenance on one robot. It finishes its active job and hands off queued unpicked work. It does not transfer a picked package.
4. Close an aisle. An occupied segment closes only after it clears. The agents learn changes from local observations and peer map messages. If a route cannot safely retreat within owned zones, it waits for reopening.
5. Interrupt the peer network, then restore it. Missing grants cause waiting; retransmission resumes coordination after communication returns.
6. Open Run history. Replay a saved experiment, open Review and export its report or JSON/CSV.

For an unrecoverable process fault, stop an agent while it holds zones. Those zones do not expire automatically. Start a new experiment for a clean simulation recovery. Never describe this as automatic physical robot recovery.

## Reproduce the release evidence

From this folder:

```text
python -m unittest discover -s tests -v
python evaluate.py
python tools/audit_runtime.py
```

`evaluate.py` trains on 12 compact-map seeds and evaluates seeds 200-207 across five cohorts and four policies (160 runs). It overwrites `model.json` and `evidence/benchmark.csv`, `training.json` and `summary.json`. The dashboard reads the saved results on page reload.

The policy comparison uses identical jobs, speeds, initial positions and maps. The baseline acquires required road zones sequentially and holds them to the dock. The atomic policy requests the route as one bundle and releases zones after their final use. The fixed-rule and predictive policies add congestion-aware route costs. Thus baseline-to-predictive improvement measures the **combined system**, not AI alone. Atomic/fixed-rule comparisons expose those contributions.

The metric is **mission makespan from simulation start through the final delivery and return to dock**. It includes auctions, resource negotiation, travel and waiting. This stricter dock-return metric must be distinguished from a delivery-only interpretation of the SIH statement. The benchmark is not directly comparable to the old single-crossing prototype's percentages.

Finite collision-free experiments do not constitute a universal safety proof. Map families share grid structure. A holdout of larger maps is not proof of arbitrary-topology generalization. Confidence intervals, physical robot motion and real wireless-network experiments remain future work.

## Architecture and trust boundaries

`warehouse.py` owns the map definitions. `agent.py` owns each robot's ledger, auction, path choice and peer-resource protocol. `simulation.py` provides local simulated sensors, motion integration and swept-body collision measurement. `transport.py` launches one OS process per robot and carries direct UDP peer messages. `server.py` supplies the observer console and deliberate experiment controls. `storage.py` persists run records. `insights.py` derives run reviews from those records. `web/workspace.js` handles inspection, presentation view and replay; these functions do not issue robot grants.

The supervisor does **not** issue movement grants, plan routes or correct velocities to avoid collisions. It does supply the common simulated world and initial/live job announcements. Task ownership decisions and path permissions happen in robot processes. Simulated sensor/velocity pipes and the common clock are not evidence of an independently deployed real robot fleet.

### Resource protocol

Baseline: acquire all required road nodes in a global order before leaving the private dock. Enhanced policies: request the complete route-zone set using one immutable Lamport timestamp and robot ID. A peer defers an overlapping later request while it has an earlier conflicting request or owns relevant zones. Disjoint route sets can receive grants concurrently. Entry requires all peer grants. After departure, a robot releases a zone only when its remaining route no longer visits it and it has reached another node. Physical clearance, not a timeout, releases ownership.

An agent can reroute only within already held zones while on the road. If an aisle closes, it may retreat within owned zones to its private dock and replan there. A carried package remains assigned to the same robot. If no safe owned retreat exists, the robot waits. It does not acquire a new unordered zone while stranded on the road.

### Task protocol

Each submitted job has a deterministic initial steward. The steward asks every peer for a cost bid. A self-assignment becomes ready locally. A transfer freezes pickup, broadcasts a proposed owner/version, gathers acknowledgments from every peer, then commits. The old owner ceases ownership before the new owner can act on the commit. Messages carry versions and immutable transfer tokens. Commit and ledger messages repeat to tolerate individual losses. This is a per-job coordinator, not a single fleet-wide assignment server.

Membership is fixed for a run. Every peer is required for grants and handoff commits. A failed peer can therefore stop progress. Individual process restart, Byzantine peers and live membership replacement are unsupported. Starting a new run creates a fresh epoch; it does not prove that a real robot has physically cleared a road.

### Local security

HTTP and UDP bind only to loopback. HTTP validates the host and a per-session control token, accepts bounded JSON requests and sets a content security policy. Direct UDP messages use an ephemeral shared HMAC key and a run epoch. Peers are trusted participants, not mutually hostile devices. The key is not a substitute for a production device identity or a safety certification.

## Data and limits

- Runtime data stays in the selected data directory. Closing the browser does not stop the server. Pause stops simulation time and motion. Ctrl+C stops processes and saves the last run.
- An interrupted run is available for inspection/replay, not automatic live resumption. No user login or cloud tenancy is part of this local single-operator product.
- Replay is recorded state; the current live run can continue while you inspect it.
- Robot radius is 0.28 m, time step 0.1 s, constant-speed holonomic motion and perfect localization. There are no humans, wheel slip, braking dynamics or noisy sensors.
- The proximity stop is a simulation feature. A process kill stops its simulated motor immediately. Hardware needs an independent watchdog, emergency stop and validated stopping distance.
- Battery is an illustrative distance-based estimate. There is no measured energy consumption or charging planner.
- The current process backend runs on one computer. Deployment on Raspberry Pi/Jetson, ROS 2/Nav2 integration and real LAN behavior remain engineering work.
- Full browser visual review remains unverified: the available cloud browser blocked local addresses; the earlier local build environment also lacked a browser binary. The release contains server/process tests and a JavaScript/DOM control harness; these do not replace testing in your presentation browser.

## Files worth reading first

- `docs/guide.html`: operator guide, limitations and demonstration sequence.
- `docs/FleetMesh_SIH_Winner_Research.pdf`: winner case studies, business area, present/future roadmap, submission plan and judge Q&A.
- `evidence/demonstration_report.html`: portable report from the recorded seven-job demonstration.
- `docs/ENGINEERING.md`: requirements and failure/benchmark interpretation.
- `docs/API.md`: local API reference.
- `evidence/`: reproducible numbers and validation results.
- `tests/test_product.py`: behavior and distributed-process tests.

The six-slide pitch now uses the supplied official SIH 2026 template. Both the editable PPT and its matching PDF are in docs/, alongside the operating guide and winner research report. Enter your registered team name and team ID before submission, replace the team-name placeholders on slides 2-6, and export the edited PPT to PDF again. The official template specifies a maximum of six slides including the title and PDF upload on the SIH portal. The instruction slide is omitted from the filled deck.

The visual pitch includes a native schematic of an actual three-process run at 20.0 simulated seconds. Its recorded state is `evidence/pitch_snapshot.json`. To capture a new demonstration frame, run `python tools/capture_pitch_snapshot.py`; this replaces that JSON file. Process IDs and asynchronous delivery timing can differ between executions. This capture is separate from the 160-run benchmark. The pitch also contains editable communication diagrams and a chart of all five scenario means.

## Prior work

The protocol uses established ideas rather than claiming a new mutual exclusion invention: [Ricart-Agrawala](https://doi.org/10.1145/358527.358537), [PIBT](https://kei18.github.io/pibt2/), [ORCA](https://gamma.cs.unc.edu/ORCA/) and [Open-RMF traffic work](https://discourse.openrobotics.org/t/next-gen-open-rmf-traffic-management/57646). Local collision-monitoring context: [Nav2 Collision Monitor](https://docs.ros.org/en/ros2_packages/jazzy/api/nav2_collision_monitor/__README.html).

The exact SIH 26123 title and requirements come from the team's supplied screenshots of `sih.gov.in/sih2026PS`. This is a student project release, with no claimed BEL/SIH endorsement, selection guarantee or industrial certification.
