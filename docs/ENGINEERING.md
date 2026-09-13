# Engineering record — FleetMesh 1.0

## Requirement traceability

| SIH 26123 requirement | Release implementation | Evidence / boundary |
|---|---|---|
| At least three AMRs | Three to six independent controller processes | Integration test runs real UDP processes; physical robots are not included |
| Local peer communication | Loopback UDP, HMAC authentication, epoch/request IDs, retransmission | Packet integrity and network partition/restoration tests |
| Multi-agent conflict handling | Ordered sequential baseline; enhanced atomic route requests with release after final use | Every-step held-zone exclusion assertions on several maps/fleet sizes |
| Dynamic routing | Local map versions and peer propagation; cancel/replan at dock or retreat within held resources | Mid-mission closure test completes without duplicate deliveries |
| Task allocation and reassignment | Per-job auctions, frozen pickup during handoff, all-peer acknowledgment, committed owner/version | Maintenance transfer test and picked-cargo ownership test |
| Dashboard | Live map, mission ledger, process telemetry, experiment controls, persistent replay and exports | Real backend plus JavaScript/DOM interaction harness; browser visual QA remains unperformed |
| Edge AI | Small ridge model trained from observed simulated resource waiting | 315 labeled waits on compact-map seeds 0-11; compare against fixed rule and atomic-only policies |
| Zero collisions | Swept-disc monitoring, peer resource exclusion and a local stop | 0 detected collisions in 160 benchmark runs; no universal/physical safety proof |
| At least 20% reduction | Measured on five cohorts with transparent baselines | Cohort averages exceed 20% for extended congestion and loss/delay; not all cohorts or individual seeds |

## Why the protocol changed

The old single-crossing prototype did not support repeated tasks or multiple road zones. The first larger-map version reserved zones sequentially and could leave partially reserved space unused while waiting. The enhanced protocol requests the entire route as one resource set and progressively releases zones after their final use.

Requests use a common total order, independent of wall-clock synchronization. An overlapping lower-priority request waits. Different route sets can proceed concurrently. Every peer must grant the exact current request. A duplicated, stale or previous-epoch grant cannot create additional votes. The same route request remains in force during retransmission.

The controller never releases a zone it still plans to visit. At an obstacle it either waits or returns to its private dock using only already owned zones. There it releases resources and replans. This avoids acquiring unordered new resources while stopped on a road. It is deliberately conservative and can sacrifice progress if no owned retreat exists.

These arguments rely on trusted fixed members, complete matching messages eventually delivered, correct resource-to-geometry mapping, unique request IDs and no agent state loss. They are not a theorem for arbitrary robot motion, Byzantine faults or unrestricted warehouse maps.

## Task handoff boundaries

The steward is a per-job coordinator. Each job may have a different steward. All participants bid, but the current owner alone can initiate a versioned transfer. It cannot pick the job while its offer is pending. Every peer acknowledges the exact proposed version and target. The old owner commits and ceases ownership; the new owner starts only after receiving that commit.

A network interruption can postpone handoff indefinitely. A failed owner cannot be replaced by a timeout. Picked cargo never transfers automatically. If a loaded robot returns to its dock to replan, it retains the job and package. Live individual restarts are unsupported; replay does not recover physical state.

## Fair reading of the benchmark

Training: compact 3x3 grid, seeds 0-11. Test: seeds 200-207 on compact, warehouse and extended layouts. Five map/scenario cohorts x eight seeds x four policies = 160 runs. There are six jobs and three robots per benchmark run. Fleet-size tests cover additional counts, but their results are not silently mixed into this dataset.

The baseline uses shortest paths, sequential ordered zone acquisition, and holds mission zones through return to dock. Atomic-only changes negotiation and release; it keeps shortest paths. The fixed rule adds known peer delay and queue estimates. Predictive routing uses a learned delay estimate. All policies use the same job auctions and physical limits.

The combined-system percentages must not be described as AI-only improvement. The fixed rule is faster than predictive routing in four of the five cohort means. The predictor's value is not established as a general improvement. The baseline is a transparent conservative reference implemented in this package, not an industry-wide or competitor benchmark.

The performance metric ends when the final mission has delivered and returned to its dock. A delivery-only interpretation of the SIH criterion can produce different values. The package does not claim blanket satisfaction of the statement based on two favorable cohorts.

The design was developed while inspecting test results. These seeds are reproducibility fixtures, not a blind final validation set. A future release needs a preregistered unseen set of maps and workloads, statistical uncertainty estimates and an independent reviewer. The larger grids differ in size but share topology conventions with the training map.

## Test boundary

Fifteen Python system tests cover fleet sizes/maps, exclusion, maintenance transfers, loaded jobs, message outages, blocked routes, new jobs, grant identities, message authentication, collision detection, actual UDP processes, killed owners, SQLite persistence and parameter validation. The JavaScript harness uses minimal DOM/canvas stubs with a real HTTP/process backend. It exercises application logic and controls but cannot verify CSS layout, browser APIs or visual appearance in a real browser.

No physical edge board, external Wi-Fi, Windows/macOS execution, ROS 2 adapter, braking model, localization uncertainty, charging control or industrial safety certification is demonstrated.

## Product extension order

1. Confirm the console and launcher on the team's actual presentation laptops; record a full demo.
2. Benchmark a frozen release on independent maps and workloads, with a stronger reservation baseline and delivery-only as an additional metric.
3. Improve delay training only if the model adds value beyond a fixed estimator.
4. Separate physics/sensors from real robot adapters and run one controller per edge board.
5. Add differential-drive dynamics, calibrated local sensing, braking envelopes and independent hardware stops.
6. Define membership recovery with verified physical occupancy, then test partitions and robot restarts.
7. Validate integrator demand, deployment cost, device interoperability and pricing with a pilot.
