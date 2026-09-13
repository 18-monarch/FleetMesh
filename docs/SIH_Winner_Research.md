# SIH winner research and FleetMesh upgrade

**Recommendation: enter FleetMesh as a demonstrable, measurable coordination prototype.** Its strongest story is three robot processes negotiating shared warehouse space, reacting to disruption and leaving evidence a judge can inspect. Keep the learned routing option, but use the better-performing fixed rule as the current default.

In simple words: each robot asks nearby peers before using a shared road. Robots agree who owns a job. When a road closes or messages disappear, the system records what happened, waits when permission is missing, and can resume after communication returns. The laptop supplies a simulated warehouse; it is not a deployed robot fleet.

### What the research changed

FleetMesh 1.1 adds a one-click seven-job disruption demonstration, a visible event timeline, saved replay and a portable run report. The demo injects an urgent job, an aisle closure and a message outage. The robots calculate the outcome; the script does not grant road access. The official six-slide pitch now points to this evidence and distinguishes completed work from the hardware pilot.

### What we can honestly present

| Evidence | Observed result | Meaning |
| --- | --- | --- |
| Existing benchmark | 160 completed runs; zero detected collisions | Five synthetic cohorts, eight paired seeds, four policies. |
| New disruption run | 7/7 missions; 198.4 simulated seconds | Three separate processes; two route recoveries; one job transfer. |
| Release checks | 17 system tests passed; HTTP/UI harness passed | Backend/process behavior and UI logic checked; no full browser visual test. |

Only two of five predictive-policy cohort averages exceed the requested 20% reduction against the included baseline. The fixed rule is faster than predictive routing in four of five. These are development experiments, not independent validation or physical safety certification.

### Scope and decision

The research covers accessible SIH winner accounts, original team-linked artifacts, public repositories and selected presentation mirrors through 12 September 2026. It is not an exhaustive inventory of every winner. No private judging scores were available, and public success stories cannot prove why judges selected a team.

For the 16 September internal round, improving the demonstration, evidence and explanation is a stronger choice than attempting an unvalidated RL, LLM or physical-robot rewrite. No solution can be called perfect or guaranteed to win. The next credible milestone is a supervised three-AMR pilot tied to the statement’s requirements.[1][2]

## Which winner materials were actually verified

Three different questions were checked: did the team win, is the artifact associated with that team, and does the artifact substantiate a working implementation? A winning label alone answers none of the technical validation questions.

| Case | Winner evidence | Material inspected / limit |
| --- | --- | --- |
| TwinX, 2025 | MathWorks sponsor archive and team account.[3][4] | Detailed workflow account. Original PPT, runnable code and repeatable benchmark not retrieved. |
| Solar Masters, 2024 | MathWorks sponsor archive and team account.[3][5] | Team-linked nine-page technical PDF; system diagrams, physical prototype photo and monitoring figures. No hardware reproduced.[6] |
| Vizion / KnitKraft, 2023 | Official SIH result, PS 1309, team 3411.[7] | Team repository, selected API code and four-slide team-linked PDF. Not executed; final judging-file identity unproven.[8][9] |
| Vision / VoCo, 2022 | Team claim plus result-mirror corroboration.[10][11] | README, implemented feature list and artifact links. APK not executed; original official result not retrieved. |
| Canon Crew, 2024 | Secondary result archive lists the team as winner.[12] | Reposted six-slide text. Conflicting problem IDs across mirrors; original file not authenticated.[13][14] |
| Dynamo / Pravah, 2025 | University announcement reports consecutive wins.[15] | Public announcement and product description. Original deck, code and benchmark not retrieved. |

### What was excluded from winner conclusions

A generic SIH reference collection supplied a three-page Team Amateurs deck, but its winner status was not established. A separate “winners” vault provides no reliable file-by-file provenance. A radar repository’s PS number matches a competition problem, but that does not make its authors a verified winning team.[20][21][22]

Videos and Canva links were discovered in team materials. Their content was not fully viewed or transcribed here. Two original team-linked PDFs and one generic reference PDF were inspected directly; public PPT reposts were assessed from accessible text. The research therefore distinguishes observed artifacts from reported product claims.

## Useful patterns from winning projects

### TwinX: one complete workflow

TwinX’s sponsor-hosted account describes importing road data, adding locally relevant road features, editing traffic scenarios and producing artifacts for simulation tools. The useful pattern is a connected workflow addressing a specific bottleneck, supported by iteration and feedback.[4]

**FleetMesh application:** begin with an operator’s actual question: “Can these jobs finish when this aisle closes?” Launch the scenario, show peer decisions, then inspect the saved outcome. Avoid presenting a collection of unrelated AI features.

### Solar Masters: connect model, prototype and evidence

The nine-page report links system modeling to a physical tracker and monitoring output. Page 3 contains system blocks; page 4 shows the design and prototype photograph; page 8 shows monitoring and tracking figures. These are tangible artifacts, though they do not independently validate every performance claim.[5][6]

**FleetMesh application:** connect the architecture diagram to live robot process IDs, the mission ledger and the downloadable report. Use the six-slide deck to tell the story and a separate technical report for depth. Present edge-board and physical motion tests as the next stage.

### KnitKraft: show who does what

KnitKraft’s four-slide submission organizes a wool-sector workflow around farmers, service providers, warehouses and transport. The public repository contains booking, status and related workflow endpoints. The proposal mentions Flutter while the inspected application uses EJS, which illustrates that pitch and implementation can evolve.[8][9]

**FleetMesh application:** make job ownership, pickup state and transfer state visible. Explain that a carried package remains with its robot. Show the path from job creation to final return, rather than treating a moving animation as sufficient proof.

### Other cases: learn selectively

VoCo distinguishes its user purpose and implemented app functions from broader proposals. Dynamo’s university account describes an AI traffic-management project, but does not provide enough evaluation detail to justify adopting its method for FleetMesh.[10][15]

**Our inference:** specificity, a demonstrable workflow, visible evidence and a coherent team explanation recur in the accessible material. These are useful design principles, not a statistically proven formula for winning. FleetMesh retains its tested core; it does not copy another team’s code, visual assets or award claims.

## How the research improves the official pitch

The supplied 2026 format controls the submission: six slides including the title, with the required topic pointers retained, then PDF export. Generic online advice recommending ten slides does not override it.[1][21]

| Slide | Judge’s question | FleetMesh answer |
| --- | --- | --- |
| 1 · Identity | What problem did you choose? | PS 26123, exact title, BEL context, FleetMesh proposition. Enter registered team name and ID. |
| 2 · Solution | What is different and useful? | Peer route permissions, explicit mission ownership and replayable disruption. Native schematic from a recorded run. |
| 3 · Approach | How does it actually work? | Robot processes, direct messages, local route costs and observer dashboard; separate simulation from deployment. |
| 4 · Feasibility | What fails and what have you tested? | Missing grants cause waiting; picked cargo stays owned; failed peers can halt progress. 17 tests and hardware next steps. |
| 5 · Impact | What improved, and for whom? | All five benchmark cohort means, stated baseline and limitations. Proposed pilot for AMR integrators. |
| 6 · References | Can we inspect the evidence? | Prior work, 160-run package, seven-job demo and run report; additional winner sources in speaker notes. |

### What to borrow from accessible decks

KnitKraft places user roles and a process diagram near the center of its idea. Canon Crew’s reposted deck follows a problem-to-mechanism-to-risk narrative and includes a concrete user scenario. Borrow that clarity, not the domain-specific technology or unverified claims.[9][13]

### What to improve on

The three-page generic reference deck uses dense text and a large technology-logo collage; part of a paragraph is cropped. FleetMesh uses readable text, editable diagrams and one meaningful results chart. These are our visual judgments from the inspected pages, not evidence that their design affected selection.[20]

Canon Crew mirrors show the same team ID with different PS numbers. A deck labelled “winning” may be a modified repost. Use original team links when available, preserve provenance and never import an award, statistic or affiliation from another project.[13][14]

Speaker notes support a short delivery. The deck remains editable; fill the team fields on every relevant slide, then export a fresh six-page PDF. Do not submit the reference instruction slide or a PDF containing placeholders.

## Business area, existing solutions and real impact

**Business area:** warehouse intralogistics and factory material movement. **First customer hypothesis:** an AMR integrator or robotics lab evaluating local coordination for a small fleet. **Daily user:** an operator who needs to see which robot owns a job, why it is waiting and what happened after a disruption.

| Existing option | What it already offers | Implication for our proposal |
| --- | --- | --- |
| MiR Fleet | Centralized fleet control, automatic mission assignment, operator UI and enterprise APIs.[16] | Scheduling and dashboards are established features. Do not claim competitors lack them or require a public cloud. |
| OTTO Autonomy | Onboard sensing, localization, obstacle handling and dynamic replanning.[17] | Local robot intelligence already exists. A laptop simulator does not match this physical capability. |
| Open-RMF traffic work | Modular planning/execution, parking reservations, obstacle handling and demonstrated traffic coordination.[18] | A serious technical reference and future comparator; not an obsolete straw-man baseline. |

### The gap we can investigate

Our proposed niche is an inspectable peer-coordination layer and experimentation tool: run local decisions, reproduce communication faults, trace road permissions and compare policies before an edge deployment. This is a testable integration hypothesis. Customer demand, reliability advantage, hardware portability and commercial differentiation remain unvalidated.

### A practical pilot offer

Start with one partner map and recorded job traces. Agree on a delivery-time metric, workload, disruption cases and acceptance criteria before testing. Next, place the controllers on three edge computers, then integrate three AMRs in a supervised test area. A pilot should produce raw logs, a failure report and an operator walkthrough.

| Value hypothesis | Measure with the partner |
| --- | --- |
| Less idle time | Delivery makespan, waiting time and throughput on the same job trace. |
| Faster incident diagnosis | Time to identify the blocked zone or failed peer from the event record. |
| Lower integration effort | Engineering hours to connect a new map, task interface and robot adapter. |

Proposed revenue is paid integration followed by maintenance/support. Do not invent prices, market size, paying customers or ROI. Interview integrators and warehouse operators first; estimate value from their actual downtime, deployment effort and task volumes. Safety and human interaction require separate physical validation.

## What is implemented in FleetMesh 1.1

| Research lesson | Delivered change | Where to inspect it |
| --- | --- | --- |
| Make the workflow demonstrable | One-click warehouse disruption scenario: urgent job, clear-segment closure, message outage and restoration. | demonstration.py; POST /api/demo; Overview panel |
| Let judges inspect the evidence | Action timeline, outcome from live state, saved replay and portable HTML report with configuration and ledger. | server.py; web/app.js; GET /api/runs/{id}/report |
| State exactly what works | Fixed rule becomes the default; predictive policy remains available for comparison. | New experiment selector; README; Benchmarks tab |
| Reproduce the demo independently | Tool launches real robot processes and validates ownership, completion and disturbance actions. | tools/verify_demonstration.py; evidence/demonstration.json |
| Keep presentation and product aligned | Six-slide pitch, updated notes, operating guide and this cited research report. | docs/ and evidence/ in the release package |

### What was already working and is retained

Three to six independent robot processes communicate over authenticated loopback UDP. Per-job auctions and an acknowledged transfer protocol establish ownership before pickup. Enhanced policies request a route’s road-zone set from peers and release zones after their final use. Operators can submit jobs, request maintenance, inject faults and review SQLite history.

### Architecture boundary

The server supplies the simulated world, clock, sensor observations and deliberate fault controls. It does not grant road access. Route choice and permission exchange happen in robot processes. Each job has a steward; there is no single fleet-wide assignment server. All processes still run on one laptop with a shared simulation supervisor.

### Important limits

Fleet membership is fixed. Missing acknowledgments can block progress, and a killed peer does not automatically release a road it may still occupy. The system is not a partition-tolerant service with guaranteed availability. Edge-board deployment, real Wi-Fi, ROS 2/Nav2 adapters, noisy localization, braking and independent motor stops remain future engineering work.

The learned component predicts route delay using a small ridge model. It does not grant safety permissions. A stronger future predictor must beat the fixed rule on unseen, predeclared scenarios before becoming the default.

## Measured evidence and what it does not prove

The existing benchmark contains 160 runs: five cohorts × eight paired seeds (200–207) × four policies, using three robots and six jobs. Values below are mean simulated seconds through final delivery **and return to dock**. Source: bundled evidence/benchmark.csv and summary.json.

| Cohort | Baseline | Atomic | Fixed | Predictive | Gain* |
| --- | --- | --- | --- | --- | --- |
| Compact / normal | 148.04 | 131.14 | 130.46 | 131.35 | 11.3% |
| Warehouse / normal | 170.55 | 145.94 | 138.64 | 140.31 | 17.7% |
| Extended / congestion | 190.14 | 161.54 | 142.25 | 144.00 | 24.3% |
| Warehouse / network | 183.85 | 143.09 | 136.10 | 135.94 | 26.1% |
| Warehouse / blocked | 176.08 | 149.18 | 141.38 | 142.86 | 18.9% |

*Gain = 100 × (baseline mean − predictive mean) / baseline mean. All runs completed with zero detected inter-robot collisions. Rounding is to two decimals for times and one for percentages.

### Interpretation the team must understand

The baseline acquires required zones sequentially and retains them to the dock. Atomic reservation changes the coordination protocol; fixed and predictive modes additionally change route costs. Baseline-to-predictive gains therefore measure the combined system, not the AI contribution. Fixed routing is faster in four of five cohort means; the 20% target is not generally achieved.

The model uses 315 training samples from compact-map seeds 0–11. Evaluation seeds differ, but the scenarios and results were inspected during development. The maps share a grid structure. No confidence intervals, independent final holdout, industrial competitor comparison or physical robot experiment are included. The network case injects 10% independent packet loss and up to 0.3 simulated seconds of delay; it is not a real Wi-Fi measurement.

### New demonstration: separate evidence

A known warehouse scenario completed all seven jobs in 198.4 simulated seconds using three distinct robot processes. It logged two route recoveries, one ownership transfer and zero detected collisions. The five scheduled actions completed and the urgent job returned to dock. Its 201 recorded frames and HTML report are included. This is a functional demonstration, not a new speed benchmark; repeated asynchronous runs can differ.

### Release verification

All 17 system tests passed. A JavaScript harness exercised the application with DOM/canvas stubs and a real HTTP/UDP backend, including demo launch, completion, history and report download. It is not a full browser visual review. Linux execution is verified; Windows/macOS launchers are supplied but must be tried on the presentation laptop.

## Present implementation and the next engineering gates

The strongest next solution is an incremental, testable edge deployment of the current architecture. Established approaches such as PIBT and Open-RMF should inform stronger comparisons; their existence also rules out claiming that distributed planning itself is new.[18][19]

| Stage | Deliverable | Gate before claiming success |
| --- | --- | --- |
| Now · laptops | FleetMesh 1.1 simulation, peer processes, fault demo, replay, reports and benchmark. | Run on the presentation laptop; inspect the ledger and logs; explain current gaps. |
| Next · independent evaluation | Unseen maps and job traces; stronger stop-and-wait baseline; fixed vs predictive ablation. | Freeze policy and test protocol first. Report all seeds, failures, timeouts, paired differences and uncertainty. |
| Next · edge computers | Three controllers on separate Raspberry Pi/Jetson-class boards; real network transport. | Measure CPU, memory, control timing, bandwidth and packet faults on actual hardware. No board benchmark is claimed yet. |
| Next · physical AMRs | Robot adapters, localization, motion constraints, independent stop/watchdog and supervised test area. | Validate stopping distance, occupancy clearance, obstacle interaction and loss of controller/network before throughput trials. |
| Later · deployment | Partner maps, WMS adapter, device identity, incident procedures, maintainable software. | Customer validation, support ownership and a controlled pilot with agreed acceptance criteria. |

### Performance protocol to agree before the pilot

Use identical missions, initial positions, speed limits, robot counts and disturbance timing for each policy. Report delivery-only makespan and delivery-plus-docking separately. Count timeouts and incomplete runs, not just successful traces. Predefine normal traffic, bottlenecks, blocked aisles, loss/delay and process failures. Evaluate AI against the fixed rule as well as the baseline.

### Recovery requires evidence of physical clearance

Do not solve a failed-peer stall by expiring its road ownership on a timer. A disconnected physical robot may still occupy that space. Membership replacement and permission recovery need a verified occupancy model, independent sensing and a procedure for stopping/rejoining robots. This is a concrete remaining design problem, not a hidden completed feature.

### Features to defer until they earn their place

Defer a new RL planner, LLM assistant, cloud tenancy, elaborate digital twin and charging optimization. None resolves the immediate need for a reproducible submission or physical validation. A partner requirement and measured benefit should justify each addition.

## Submission plan and judge demonstration

| Date | Work | Completion check |
| --- | --- | --- |
| 12 September | Freeze the v1.1 package; assign integration, testing, presentation and evidence owners. | Every teammate can explain jobs, grants, waiting and the limits. |
| 13 September | Run the app on the actual laptop and browser; inspect all demo actions; record a short backup video. | No clipped controls; replay and report open; Python and launchers work without internet. |
| 14 September | Rehearse the fault sequence and judge questions; check every slide against the source evidence. | Figures match the package; fixed-vs-AI result is explained honestly. |
| 15 September | Enter team name/ID, verify college rules, export PDF and check all six pages. | Keep the final PDF, PPT, ZIP and backup recording on the laptop and a spare drive. |
| 16 September | Open the final PDF and app before the allotted slot; submit in the college’s requested channel. | Confirm submission receipt and required naming/size rules with the college. |

### A five-minute demonstration

**0:00–0:40:** “FleetMesh lets robots negotiate shared warehouse roads and records why they wait.” Show PS 26123 and three process IDs.
**0:40–2:00:** Select Launch demo. Explain the urgent mission, closed aisle and message outage as the event timeline updates. Simulation time runs faster than wall time.
**2:00–3:00:** Inspect the ledger, report and replay. Show the actual outcome, including any incomplete jobs.
**3:00–4:15:** Show all five benchmark cohorts. Say the fixed rule wins four of five and AI needs further validation.
**4:15–5:00:** Explain the three-AMR pilot and the physical tests needed next.

### Short answers to likely questions

**Where is the decentralization?** Robot processes decide ownership and road permissions through peer messages. The laptop server supplies simulation and observation.
**Where is the AI?** A local ridge model estimates route delay. It is optional because it is not yet consistently better than the fixed rule.
**Do robots keep working through every outage?** No. Missing grants cause waiting. Communication restoration can resume progress; a failed peer can halt it.
**Have you met 20%?** Two of five predictive cohort means exceed it against our baseline. We do not claim a universal result.
**What is the impact?** The pilot measures task time, waiting, diagnosis and integration effort; value remains unvalidated.

**Final request to judges:** “We have a working, inspectable software prototype. We seek the next round to validate it on three edge-controlled AMRs and a partner warehouse workload.”

## Sources

Public sources accessed during the research through 12 September 2026. Bracketed references in the report link to the original page where available. The first two sources are the team’s supplied files. Winner status and artifact completeness are qualified in the evidence catalog.

[1] **Official SIH 2026 idea presentation template**. Team-supplied SIH2026-IDEA-Presentation-Format.pptx. Six slides including title; PDF submission. Inspected locally.

[2] **PS 26123: Edge-AI fleet coordination**. Team-supplied screenshots of sih.gov.in/sih2026PS. BEL; Software; Smart Automation. Requirements transcribed from the screenshots.

[3] **MathWorks: Hackathon winners**. Sponsor archive; confirms TwinX (2025) and Solar Masters (2024). [Open source](https://www.mathworks.com/academia/students/competitions/hackathons/winners.html)

[4] **TwinX: From real roads to real simulations**. MathWorks Student Lounge, 6 April 2026. Sponsor-hosted team account. [Open source](https://blogs.mathworks.com/student-lounge/2026/04/06/from-real-roads-to-real-simulations-how-team-twinx-won-smart-india-hackathon-2025/)

[5] **Solar Masters: Innovation meets excellence**. MathWorks Student Lounge, 13 June 2025. Sponsor-hosted team account with report and video links. [Open source](https://blogs.mathworks.com/student-lounge/2025/06/13/innovation-meets-excellence-solar-masters-winning-journey-at-smart-india-hackathon-2024/)

[6] **Solar Masters technical report**. Team report linked by MathWorks. Nine pages downloaded and read; pages 3, 4 and 8 visually inspected. [Open source](https://drive.google.com/file/d/1j2UZkoPTj_1MH4cUCnO_BDQAO8DpbKCn/view?pli=1)

[7] **SIH 2023 grand finale results**. Official result: PS 1309; Team Vizion; team ID 3411; Bakhtiyarpur College of Engineering. [Open source](https://www.sih.gov.in/sih2023-grand-finale-result)

[8] **KnitKraft repository**. Team-linked source, README and routes/api.js inspected; not executed or security audited. [Open source](https://github.com/uzibytes/KnitKraft)

[9] **KnitKraft submission PDF**. Team-linked four-slide document. All four pages visually inspected. Not established as the final judging version. [Open source](https://drive.google.com/file/d/1BhjldMFYz4rB5Iu3gg36Oxn4-SusAxQG/view?usp=drive_link)

[10] **VoCo repository**. Team Vision account; README and implementation list inspected. APK and proposal links found, not executed. [Open source](https://github.com/uzibytes/Voco_App)

[11] **SIH 2022 results mirror**. Secondary mirror corroborates RK774 / Team Vision / team 23641. Original result page not retrieved. [Open source](https://www.scribd.com/document/770047911/Results-for-SIH-2022-Software-Edition)

## Sources, continued

[12] **SIH PS archive: SIH1686**. Secondary archive lists Canon Crew, team 27113, KMIT as winner. Not an original SIH record. [Open source](https://github.com/Vigneshrdy/sih-ps-archive/blob/main/2024/SIH1686.md)

[13] **Reposted Canon Crew presentation**. Scribd six-slide text, cover PS 1686. Original final-file provenance unverified. [Open source](https://www.scribd.com/document/906186982/SIH-2024-Winning-PPT)

[14] **Altered-ID presentation mirror**. SlideShare version displays PS 25129 for the same team ID; illustrates provenance risk. [Open source](https://www.slideshare.net/slideshow/906186982-sih-2024-winning-ppt-pptx-sih-winning/283925301)

[15] **Bennett University: Team Dynamo**. Institution announcement, 26 December 2025, describing Pravah and consecutive SIH wins. [Open source](https://www.linkedin.com/posts/bennett-university_bennettuniversity-teamdynamo-aiinnovation-activity-7410306542887006209-l6m7)

[16] **MiR Fleet product page**. Manufacturer description of centralized fleet control, mission assignment and enterprise integration. [Open source](https://mobile-industrial-robots.com/products/software/mir-fleet)

[17] **OTTO Autonomy product page**. Manufacturer description of onboard sensing, localization, obstacle handling and replanning. [Open source](https://ottomotors.com/autonomy/)

[18] **Next-gen Open-RMF traffic management**. Open Robotics engineering discussion, 25 August 2026. Architecture, demonstrations and limitations. [Open source](https://discourse.openrobotics.org/t/next-gen-open-rmf-traffic-management/57646)

[19] **PIBT implementation and research**. Author-maintained project with multi-agent planning implementation and robot demonstrations. [Open source](https://kei18.github.io/pibt2/)

[20] **SIH PPT reference collection**. Generic collection. The three-page sih-2022-ppt.pdf was downloaded and visually inspected; winner status unverified. [Open source](https://github.com/mohitjoping/SIH-ppt-references)

[21] **SIH Winners PPT and Sources collection**. Repository metadata/README inspected. Individual PDFs not downloaded or authenticated. [Open source](https://github.com/Aadiii00/SIH-Winners-PPt-and-Sources)

[22] **Doppler radar repository**. WhiskeyTangoFoxtrot, PS 1606. Winner status unverified; a matching PS ID does not prove team identity. [Open source](https://github.com/Keerthi2134/doppler-radar)

### Project evidence included with this release

evidence/benchmark.csv; summary.json; training.json; demonstration.json; demonstration_report.html; tests.txt; ui_http_checks.json; pitch_snapshot.json. These are FleetMesh’s own results, not SIH or BEL certification. Reproduction commands and runtime limits are in README.md.

### Video links discovered, not reviewed

Solar Masters: https://www.youtube.com/watch?v=gZriKmawXq8
KnitKraft: https://youtube.com/watch?v=d0B1yQ7u524
