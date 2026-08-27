# Sequence

Six shots cut from `assets/footage/byakuya_tybw_edit.mp4`, 409 frames / 17.04s
at 24fps, 1920x1080. The fan edit's burned-in titles are removed.

| # | Shot | Source | Crop y | Frames | Content |
|---|------|--------|--------|--------|---------|
| 1 | shot01_release     | 0.000-1.033  | 480 | 25  | black, then the hand opens and the sword drops |
| 2 | shot02_sink        | 1.033-3.533  | 580 | 60  | blade enters the floor, sinks, ripples settle |
| 3 | shot03_swords      | 3.533-9.533  | 592 | 144 | BANKAI title; the two wings of blades rise into the V |
| 4 | shot04_declaration | 9.533-12.633 | 350 | 30  | face close-up (title frames dropped) |
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

The cut list lives in `shots/cuts.json`. Rebuild everything from it:

    tools/recut.py                    # or --source <newclip> --dry-run

## Resolution ceiling

The current source cannot reach HD, let alone 4K, and this is a property of
the footage rather than of the scaling.

A round-trip test (shrink, re-enlarge, measure the error) shows the fan edit
loses almost nothing when reduced to 812x1082 (RMS 2.95). So it is itself an
upscale: an ~810x1080 vertical slice taken out of a 16:9 original and blown up
1.33x. After the 608-tall crop band, each delivered frame rests on roughly
**810x456 of real detail**.

| Output | Upscale over real detail |
|--------|--------------------------|
| 1920x1080 | 2.37x |
| 3840x2160 | 4.74x |

The fix is a better source, not a better scaler. A 1080p broadcast source of
the same scene carries about 5.6x more real detail and removes three separate
compromises at once: the watermark that forced shot 3's crop, the burned-in
titles that cost shot 4 its middle 43 frames, and the vertical reframing.

When that source lands, re-derive the cut points with:

    tools/probe_cuts.py assets/footage/<clip> --start <t> --end <t>

then update `shots/cuts.json` and run `tools/recut.py`. Timings and crops from
the fan edit do not transfer: a different release has its own cut points, and
a 16:9 source needs no crop at all.

## Titles

The fan edit burned two titles into the picture. They are removed by
`tools/detext.py`, which keeps the untouched original in `plate_raw/` so every
pass is re-runnable.

**BANKAI** (shot 3, frames 9-32) sat on flat, unmoving night sky. Measuring
that region across the title-free frames gave a temporal standard deviation of
2.4, so the background is effectively static and can simply be replaced with a
median clean plate. Result is exact — zero residual glyph pixels.

    tools/detext.py shot03_swords --plate --rect 440,160,1490,390 \
        --clean 1-8,34-60 --frames 9-32

**SENBONZAKURA KAGEYOSHI** (shot 4, frames 24-66) sat on Byakuya's face. Three
methods were tried and rejected: ffmpeg `delogo` streaks wherever the box
crosses his hair; masked inpainting works on the flat skin but turns to mush
where it spans the hair edge; and a warped clean plate fails because the cel is
animated, not a held zoom (best-fit correlation only 0.40). The glyphs also
carry a dark neutral outline no colour test detects, which is what leaves grey
ghosts behind.

So the titled frames are dropped instead. The join was chosen by searching all
head/tail pairs for the smallest difference:

    tools/detext.py shot04_declaration --keep 1-23,68-74

That join measures 26.8 against this shot's own natural frame-to-frame motion
of 4.5-25.1, so it sits inside the movement the shot already has. The shot
goes from 74 frames to 30.

## Not yet done

No VFX. Every shot is the plate as-cut.
