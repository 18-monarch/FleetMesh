# Supplied warehouse film and frame sequence - v1.8

The team supplied a new generated MP4 on 13 September 2026 after using the Leonardo setup. The upload filename identifies Hailuo 2.3; its provider generation job was not inspected here. The original upload remains separate and unmodified. The package contains an optimized derivative, not a duplicate of the original.

## Review and intended use

Twelve frames sampled at half-second intervals, plus full-size opening and near-final frames, show a dark warehouse, three carton-loaded graphite AMRs, green lamps and a gentle rising camera move. The robots' broad shapes and cargo remain visually coherent in the reviewed frames. Small generated markings should not be treated as reliable robot identifiers. The footage contains no website interface overlay.

This works as the cinematic setting for the landing page. It does not establish collision avoidance, a blocked-junction maneuver, network-loss recovery or physical FleetMesh control. The webpage labels it AI-generated and illustrative. Measured software behavior remains in the operations console and saved evidence.

## Packaged assets

| Asset | Description |
| --- | --- |
| web/media/warehouse-film.mp4 | H.264, 1376 x 768, 24 fps, 141 frames, 5.875 seconds, video only; 5,290,075 bytes. |
| web/media/warehouse-film-poster.webp | Frame near 0.04 seconds from this clip; used by the video and the page fallback. |
| web/media/warehouse-opening.png | Earlier clean opening reference, retained as an asset. |
| web/media/warehouse-coordination.png | Independent overhead concept, shown in a separate figure explicitly captioned as a still image. |

The MP4 has 47 keyframes, one every three frames. MP4 metadata precedes media data. This trades a larger file than the 1.69 MB upload for shorter decoding dependencies when seeking. The previous packaged film was 8.42 MB. The derivative retains the source dimensions, timing and visible content; no watermark removal, interpolation or invented test metrics were applied. There was no audio stream in the supplied clip.

Titles, buttons and evidence cards are separate webpage elements. The coordination still is in a contained figure; overlapping vector labels have been removed. The native film lighting is retained without the previous CSS darkening filter. Desktop cover fitting can crop edges on a different aspect ratio; the narrow layout fits the complete frame. Generated images are independent references, not calibrated views of a measured 3D warehouse.

## Rebuild

Supply the original upload as `source.mp4` and run:

```sh
ffmpeg -y -i source.mp4 -map 0:v:0 -an -c:v libx264 -threads 2 -preset fast -crf 20 -pix_fmt yuv420p -g 3 -keyint_min 3 -sc_threshold 0 -movflags +faststart warehouse-film.mp4
ffmpeg -y -ss 0.04 -i source.mp4 -frames:v 1 -c:v libwebp -quality 88 warehouse-film-poster.webp
```

`evidence/video_asset.json` records the exact original filename, source/output hashes, stream metadata, full software-decode status and keyframe spacing. All 141 frames decode successfully with FFmpeg. These checks establish a valid media asset; they do not measure browser scrubbing, mobile layout or projector quality. FFmpeg is needed only to rebuild the assets, not to run FleetMesh.

The server supports single byte ranges and HEAD. See `docs/API.md` for behavior. The active homepage uses the extracted frame sequence rather than HTML video seeking. Reduced motion can remain static without fetching the MP4. Playback failures retain the poster and direct console links.


## Frame sequence added in v1.8

The unchanged 5.875-second source derivative was extracted into web/media/warehouse-frames/frame-000.webp through frame-140.webp. All 141 frames retain 1376 x 768 dimensions and original order. No new camera motion was generated. The files total 9,007,770 bytes; the player loads only a small neighbourhood of the current scroll target and caches at most sixteen decoded images.

```sh
ffmpeg -y -i warehouse-film.mp4 -c:v libwebp -quality 78 -threads 2 -start_number 0 frame-%03d.webp
```

Every image was fully decoded with Pillow. evidence/sequence_asset.json records dimensions, counts, source hash and each image hash. This is an asset validity check, not browser visual acceptance. The old MP4 remains in the package for reuse; it is not fetched by the current homepage. Captions, reduced-motion fallback and read-only evidence distinctions remain explicit.
