# Shot 01 — Release

Close on the gloved hand. The fingers open and Senbonzakura drops out of frame.
25 frames, 1.04s.

## Plate

    tools/ingest.py cut assets/footage/byakuya_tybw_edit.mp4 shot01_release \
        --start 0 --duration 1.033 --crop 1080:608:0:480

The source is a 1080x1440 vertical edit, so it has to be reframed before it can
be a 16:9 plate. `y=480` is the band that keeps the hand and the top of the hilt
wrap while excluding the "ANIME GALAXYZ" watermark, which sits at y 1200-1235.
Upscale to 1920x1080 is 1.78x; the source is flat-shaded and already soft, so it
holds.

## Beats

| Frame | Beat |
|-------|------|
| 1-6   | hand closed on the hilt, still |
| 7-16  | fingers open |
| 17-25 | hand fully open, sword already gone |

## Notes

There is no "Byakuya emerges from darkness" anywhere in this clip — it opens
cold on the hand. If that beat is wanted it has to be built, most cheaply as a
fade up from black over frames 1-8.
