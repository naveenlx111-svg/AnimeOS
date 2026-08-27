# Shot 02 — Sink

Cut to the ground. The blade falls into the tiled floor, which behaves like
water: it enters, sinks, and the ripples spread and settle. 60 frames, 2.50s.

## Plate

    tools/ingest.py cut assets/footage/byakuya_tybw_edit.mp4 shot02_sink \
        --start 1.033 --duration 2.50 --crop 1080:608:0:580

`y=580` frames the contact point and the ripple field, and clears the watermark.
Cut points came from ffmpeg scene detection on the source: 1.033s (hand ->
ground) and 3.533s (ground -> BANKAI title).

## Beats

| Frame | Beat |
|-------|------|
| 1-6   | empty floor |
| 7-8   | blade tip enters from frame top, still in air |
| 9     | **contact** — glow blooms at the base |
| 10-26 | blade sinks, ripples spread |
| 27-30 | tsuba reaches the surface |
| 31-40 | hilt sinks and disappears |
| 41-60 | ripples spread and settle |

## Anchor

Measured, not guessed. The impact point at contact, from the blade column and
the waterline across frames 9-12:

    contact_frame = 9
    contact_px    = (903, 632)
    contact_ndc   = (-0.060, -0.171)

**The camera drifts.** Tracking a static background patch over the clean early
frames gives roughly +2px/frame down-and-right, and the hilt's own column walks
from x 922 to x 984 between frames 27 and 40. So anything added to this shot has
to be tracked, not pinned to a fixed screen position. When VFX actually goes in,
track off the sword itself while it is still visible — it is the highest-contrast
feature in frame and it sits exactly where the effect belongs.

## Layers out

- `vfx/####.png` — Blender, RGBA, straight alpha. No Byakuya.
- `out/####.png` — plate + vfx composited, for review.
