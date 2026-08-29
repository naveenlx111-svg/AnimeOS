# Sequence

Nine shots cut from `assets/footage/bleach_tybw_ep04.mp4` -- Bleach: Thousand-
Year Blood War ep.04, "Kill The Shadow" -- 517 frames / 21.54s at 24fps,
1920x1080. The Bankai runs 784.30-805.76s (13:04-13:26).

| # | Shot | Source (s) | Frames | Beat |
|---|------|-----------|--------|------|
| 1 | shot01_release  | 784.30-785.41 | 27  | the hand opens and lets the sword fall |
| 2 | shot02_sink     | 785.41-787.91 | 60  | the blade touches stone and rings out in circles |
| 3 | shot03_bankai   | 787.91-793.92 | 145 | black; a small figure; the blade rows rise into wings |
| 4 | shot04_declare  | 793.92-796.92 | 72  | Byakuya, close, naming it |
| 5 | shot05_firstjet | 796.92-798.63 | 41  | one jet of petals breaks upward |
| 6 | shot06_columns  | 798.63-800.01 | 34  | columns of petals erupt |
| 7 | shot07_wall     | 800.01-801.76 | 42  | the storm fills frame |
| 8 | shot08_arcs     | 801.76-803.26 | 36  | blades arc over the storm |
| 9 | shot09_stand    | 803.26-805.76 | 60  | he stands inside it; the hold the login lands on |

Cut points come from `tools/probe_cuts.py` scene detection, not by eye.

## No reframing

The earlier source was a fan edit: a 1.33x upscale of an ~810px vertical slice
of a 16:9 original, which after its 608-tall crop band left each delivered
frame resting on roughly 810x456 of real detail. That is where the softness
came from, and no scaler fixes it.

The broadcast source is a true 1920x1080 16:9, and the panel it plays on is
also 1920x1080, so the whole crop-and-scale stage is gone: every plate is the
original pixels 1:1. Only shot04 is reframed, and only to escape a subtitle.

23.976 is retimed to 24 by stretching timestamps, not by resampling -- `fps=24`
would duplicate one frame in every 42, which reads as a stutter on a slow push.

## The two overlays

**The AnimePahe logo** is alpha-composited, not baked, so it can be inverted
rather than inpainted -- the pixels underneath are still in the file, just
washed toward white. `tools/dewatermark.py` solves the blend against the
episode itself: the premultiplied colour comes off frames that fade to black,
and L off frames whose corner is bright and flat. That gives L=254 with a
per-pixel alpha peaking at 0.22, agreeing across 95 independent frames.

Measured as the logo's excess luma over its own immediate surroundings, the
523-frame window goes from +32.9 DN to under a quarter of a DN on most shots.
The first solve left a faint outline: at the glyphs' anti-aliased edges the
premultiplied value is 1-5 DN, the same size as the quantisation noise in a
27-frame median. Refining it over 83 dark frames -- subtracting what the
background contributes rather than requiring pure black -- settles those edges.

**The subtitles** needed two different answers.

*"Bankai..."* sits on a held near-black frame. Frames 13 and 37 differ by
0.53 DN across the whole picture, so the covered region is rebuilt exactly
from the frames either side. Nothing is invented.

*"Senbonzakura Kageyoshi..."* sits on a moving haori -- its band animates at
4-5 DN per frame -- so there is no clean plate to borrow from, and inpainting
would break the gold trim and the tassel it crosses. That shot is cropped
above the subtitle (rows 968-1048) and pushed in 1.125x instead. It invents no
pixels, and it tightens the close-up while it is at it.

Both verified by re-running the detector: worst score 3, against 6320 before.

## Grade

Sharpen, then deband, then dither -- in that order, on the clean plate.

Contrast Adaptive Sharpen rather than an unsharp mask: at matched strength
unsharp pushes twice as many pixels to clip, which on line art is a halo down
every contour. `cas=0.8` lifts high-frequency energy about 40% with clipping
essentially unchanged.

The deband is not cosmetic. The dark shots arrive from a 1.6 Mbit source with
about six distinct luma levels across the near-black background, measuring as
flat runs averaging 111 pixels -- visible contour rings, on a login screen that
is mostly dark. Dithering breaks those runs to under two pixels.

Delivered at CRF 14, not 18. The dither costs bitrate, and at 18 the encoder
spends it by smoothing exactly the detail the sharpen just added: measured
against the plate, CRF 18 keeps a laplacian of 3.02 where CRF 14 keeps 3.92.
End to end the delivered frame carries 78% more high-frequency energy than the
plate it came from.

## Resolution

The panel is 1920x1080 and its highest mode is 1920x1080, so it cannot display
4K. A 3840x2160 file would be downscaled by the compositor before it reached
the glass -- four times the decode work on a login screen for nothing visible.
The sharpness win came from the better source, the sharpen, and the bitrate,
not from more pixels.
