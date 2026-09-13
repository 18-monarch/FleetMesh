# FleetMesh 1.8 frontend

The screenshot supplied by the team showed an abrupt edge between a full-screen film and a full-screen concept still, annotation text behind the heading, and a loading state. The exact cause of MP4 loading in the user's browser was not established from the screenshot. This release removes the homepage's dependency on video decoding/seeking and fixes the conflicting layout.

## Running the correct copy

Stop the previous terminal with Ctrl+C. Extract the complete update into a new writable folder. Run Start_FleetMesh.bat on Windows, or sh start_fleetmesh.sh on macOS/Linux. Open the exact URL printed by that terminal; the footer must show v1.8.0. The launcher can select a new port if the old port is occupied. Do not keep testing an older instance in an existing tab.

| Path | Purpose |
| --- | --- |
| / | Continuous warehouse scene and four story chapters |
| /app | Working operations console |
| /app#sample | Included recorded run, read-only |
| /app#evidence | Four-policy benchmark comparison |
| /app#review | Included recording's calculated review |
| /guide | Operating and presentation guide |

## Scene and layout

The same fixed canvas supplies the warehouse background across the story. It draws the supplied film's 141 extracted WebP frames. The overhead concept is a normal-flow framed figure in a separate grid cell from the heading. Its caption sits below the image. No SVG annotations or absolute image labels can cross into the text. At 800 CSS pixels and below, the text and illustration stack vertically. A complete source frame is fitted on narrow screens.

The video-shaped camera move remains illustrative, as labelled on the page. The animation completes by the coordination chapter. The original MP4 is retained for provenance and reuse, but the homepage never creates an HTML video element or requests the MP4. The operations console and benchmark evidence remain independent.

## Loading and lifecycle

web/sequence-player.js contains the active player. It has at most four in-flight image requests and sixteen cached decoded images. Requests around the current target are prioritized; obsolete downloads are cancelled after a large scroll jump. Frame changes are coalesced through requestAnimationFrame. There is no always-running animation loop when idle.

Pause motion remains enabled while loading and cancels requests. Resume catches up to the current scroll position. Reduced motion starts on the poster with optional Enable motion. Hidden pages stop requests; back-forward cache restoration resumes the state. Leaving clears image references, callbacks and timers.

A requested image that fails or exceeds five seconds freezes the last good scene, or keeps the poster if nothing loaded. Retry motion performs an explicit retry. Failed neighbour prefetch does not hide a good frame. There is no automatic retry loop. If canvas is unavailable, copy and console links remain readable.

The server only serves frame-000.webp through frame-140.webp under the exact media prefix. Frames are same-origin, privately cacheable and support HEAD. Existing local host validation, command tokens and media range handling are retained.

## Verification and remaining check

- 38 Python system/HTTP tests cover backend behavior, static/media delivery, exact frame bytes, cache headers, HEAD and frame path boundaries.
- 34 console checks use actual application JS and a real HTTP/UDP backend with minimal DOM/canvas stubs.
- 35 sequence/page checks exercise actual JS with deterministic image/canvas/DOM stubs, including all 141 frames, reverse/rapid scroll, cancellation, bounded memory, pause during loading, retry, failure and visibility.
- All 141 packaged WebP images fully decode at 1376 x 768. ZIP hashes and extracted launcher routes are verified separately.

The remote browser could not access localhost. These checks are not browser screenshots or proof of smoothness on the team's Brave browser, phone or projector. Windows/macOS launchers are included but were not executed here.

For visual acceptance, check the hero, challenge-to-coordination boundary, complete concept card and evidence footer at normal zoom. Repeat in a narrow window. Try scrolling in both directions and pausing immediately after reload. The picture and caption must stay within their card; bottom controls must remain separate. Then open the console, inspect the recorded run and complete a live demonstration.

Developer commands:

```text
python -m unittest discover -s tests -v
node tests/ui_smoke.cjs
node --experimental-vm-modules tests/cinematic_checks.mjs
```

Node is needed only for developer checks. Python 3.10+ is enough to run the application; all assets are bundled locally. The earlier film-player.js and Three.js scene remain reference source and are not imported by the current homepage.
