# Sequence

Six shots cut from `assets/footage/byakuya_tybw_edit.mp4`, 453 frames / 18.88s
at 24fps, 1920x1080.

| # | Shot | Source | Crop y | Frames | Content |
|---|------|--------|--------|--------|---------|
| 1 | shot01_release     | 0.000-1.033  | 480 | 25  | black, then the hand opens and the sword drops |
| 2 | shot02_sink        | 1.033-3.533  | 580 | 60  | blade enters the floor, sinks, ripples settle |
| 3 | shot03_swords      | 3.533-9.533  | 592 | 144 | BANKAI title; the two wings of blades rise into the V |
| 4 | shot04_declaration | 9.533-12.633 | 350 | 74  | face close-up, SENBONZAKURA KAGEYOSHI titles |
| 5 | shot05_eruption    | 12.633-14.275| 500 | 39  | single light blade, petals erupt upward |
| 6 | shot06_storm       | 14.275-18.900| 500 | 111 | petal columns, storm fills frame |

## Reframing

The source is a 1080x1440 vertical edit, so every shot is cropped to a
1080x608 band and scaled up 1.78x. The band is chosen per shot: it has to hold
the composition *and* sit clear of the burned-in "ANIME GALAXYZ" watermark at
y 1200-1235.

Shot 3 is the one case where those two goals conflict — the watermark sits
directly on Byakuya's chest. Cropping above it keeps his head and shoulders and
the whole sword V, and loses his lower body. `delogo` was tried instead and
left a visible smear band across the stripes, so the crop won.

## Edges

Cut points come from ffmpeg scene detection, then checked frame by frame:

- The clip opens on **two black frames** and a one-frame ramp. Kept — it is the
  closest thing the footage has to "emerging from darkness", and it is real
  source rather than something invented.
- The 14.233s cut detection was one frame early; shot 6 began on the tail of
  the eruption. Moved to 14.275s.
- Shot 6 contains fast internal flashes that read as cuts to a detector. They
  are one continuous effect and are left whole.

## Rebuilding

    tools/ingest.py cut assets/footage/byakuya_tybw_edit.mp4 <shot> \
        --start <t> --duration <d> --crop 1080:608:0:<y>
    tools/assemble.py --slate

## Not yet done

No VFX. Every shot is the plate as-cut. The burned-in BANKAI and SENBONZAKURA
titles are still the fan edit's own; PLAN.md assigns titles to the grade, so
they are candidates for replacement.
