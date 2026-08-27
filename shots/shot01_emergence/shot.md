# Shot 01 — Emergence

Byakuya resolves out of darkness and drops Senbonzakura. This is the shot the
whole cinematic hangs off: it is the last moment before Bankai, and it has to
land the trigger cleanly or nothing after it reads.

## Source

The plate is real footage, cut with `tools/ingest.py cut`. It lands in
`plate/` as 1920x1080 / 24fps PNGs numbered from 0001.

## Beats

Frame numbers are deliberately unset. They get pinned against the actual plate
once it exists — the drop happens when the footage says it happens, and the VFX
is timed to that, not the other way round.

| # | Beat | Plate | Blender adds |
|---|------|-------|--------------|
| 1 | Darkness | near-black, figure not yet readable | ambient dust / faint drift |
| 2 | Resolve | figure separates from the ground | edge light lift, haze |
| 3 | Hold | Byakuya readable, still | minimal — let the plate carry it |
| 4 | Release | hand opens, blade begins to fall | first glow at the hilt |
| 5 | Fall | blade descends | motion trail, air displacement |
| 6 | Contact | blade meets the ground | impact flash, ground light |

Beat 6 is the handoff. Whatever the swords do in shot 02 has to originate from
exactly where and when this blade lands.

## Anchor

The one number every later shot depends on: **where the blade tip contacts, in
frame-normalised coordinates**, and **on which frame**. Both get measured off
the plate and recorded here. The old build guessed at an anchor and the sword
formation never lined up; this time it is measured.

    contact_ndc  = (unset)
    contact_frame = (unset)

## Layers out

- `vfx/####.png` — Blender, RGBA, straight alpha, VFX only. No Byakuya.
- `out/####.png` — plate + vfx composited, for review.
