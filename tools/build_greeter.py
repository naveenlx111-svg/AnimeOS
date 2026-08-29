#!/usr/bin/env python3
"""Build the two videos the SDDM theme plays.

    tools/build_greeter.py

`sequence.mp4` is the whole cut, played once when the greeter starts.
`idle_loop.mp4` loops underneath for as long as the user takes to type.

Both get a deband and a light temporal grain. That is not a stylistic choice:
the dark shots arrive from a 1.6 Mbit source with about six distinct luma
levels across the near-black background, which measures as flat runs averaging
111 pixels -- visible contour rings on a decent panel, and the login screen is
mostly dark. Dithering breaks those runs to under two pixels. The grain also
hides the 8-pixel blocking in the storm, where gradients across the DCT grid
sit 34% above their neighbours.

The idle loop is the dark hold, because it is the only stretch calm enough to
read a login panel against: measured luma 11 and local contrast 0.02 in the
region the panel occupies, where the storm the sequence ends on measures 175.
On its own that is very close to black, so the matted petals are composited
back over it at low opacity -- enough to keep the screen alive while the user
types without lifting the background into the panel's way.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'login' / 'senbonzakura' / 'assets' / 'video'
FPS = 24

# Deband, then dither. coupling=1 treats the planes together so the fix does
# not tint. The noise is temporal (allf=t) because a fixed pattern reads as
# dirt on the screen, while one that changes every frame reads as grain.
# Sharpen first, on the clean plate, then deband, then dither. Contrast
# Adaptive Sharpen rather than an unsharp mask: at matched strength unsharp
# pushes twice as many pixels to clip, which on line art is a halo down every
# contour. cas at 0.8 lifts high-frequency energy 40% with clipping essentially
# unchanged (0.45% -> 0.52%).
GRADE = ('cas=strength=0.8,'
         'deband=1thr=0.01:2thr=0.01:3thr=0.01:range=24:blur=1:coupling=1,'
         'noise=alls=2:allf=t+u')

# CRF 14, not 18. The dither costs bitrate, and at 18 the encoder spends it by
# smoothing exactly the detail the sharpen just added: measured against the
# plate, CRF 18 keeps a laplacian of 3.02 where CRF 14 keeps 3.92. Sharpening
# into too low a bitrate is work thrown away.
CRF = '14'

SHOTS = ['shot01_release', 'shot02_sink', 'shot03_bankai', 'shot04_declare',
         'shot05_firstjet', 'shot06_columns', 'shot07_wall', 'shot08_arcs',
         'shot09_stand']

HOLD_SHOT = 'shot03_bankai'
HOLD_FRAMES = 42
PETAL_SHOT = 'shot07_wall'
PETAL_OPACITY = 0.30


def build_sequence():
    lst = ROOT / 'shots' / 'review' / '_seq.txt'
    files = []
    for s in SHOTS:
        files += sorted((ROOT / 'shots' / s / 'plate').glob('*.png'))
    lst.parent.mkdir(parents=True, exist_ok=True)
    lst.write_text(''.join(f"file '{f}'\nduration {1/FPS}\n" for f in files)
                   + f"file '{files[-1]}'\n")
    out = OUT / 'sequence.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-f', 'concat', '-safe', '0', '-i', str(lst),
                    '-vf', f'{GRADE},fps={FPS}',
                    '-c:v', 'libx264', '-preset', 'veryslow', '-crf', CRF,
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    str(out)], check=True)
    lst.unlink()
    print(f'  sequence.mp4  {len(files)} frames, {len(files)/FPS:.2f}s, '
          f'{out.stat().st_size/1e6:.1f} MB')


def build_idle():
    hold = sorted((ROOT / 'shots' / HOLD_SHOT / 'plate').glob('*.png'))[:HOLD_FRAMES]
    petal = sorted((ROOT / 'shots' / PETAL_SHOT / 'matte_packed').glob('*.png'))
    if not petal:
        sys.exit('no matte frames; run tools/matte.py first')

    # Both layers ping-pong over the same number of frames, which is what makes
    # the loop seamless -- the last frame is the first frame's neighbour.
    order = list(range(len(hold))) + list(range(len(hold) - 1, -1, -1))
    porder = list(range(len(petal))) + list(range(len(petal) - 1, -1, -1))
    n = min(len(order), len(porder))

    tmp = ROOT / 'shots' / 'review' / '_idle'
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob('*.png'):
        f.unlink()

    lumas = []
    for i in range(n):
        bg = np.asarray(Image.open(hold[order[i]]).convert('RGB')).astype(np.float32)
        pk = np.asarray(Image.open(petal[porder[i]]).convert('RGB')).astype(np.float32)
        w = pk.shape[1] // 2
        rgb, a = pk[:, :w], (pk[:, w:, :1] / 255.0) * PETAL_OPACITY
        # The matte is straight, not premultiplied, so composite the long way.
        comp = bg * (1.0 - a) + rgb * a
        lumas.append(comp[300:660, 640:1280].mean())
        Image.fromarray(comp.round().clip(0, 255).astype(np.uint8)).save(tmp / f'{i+1:04d}.png')

    out = OUT / 'idle_loop.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-framerate', str(FPS), '-start_number', '1',
                    '-i', str(tmp / '%04d.png'),
                    '-vf', GRADE,
                    '-c:v', 'libx264', '-preset', 'veryslow', '-crf', CRF,
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    str(out)], check=True)
    for f in tmp.glob('*.png'):
        f.unlink()
    tmp.rmdir()
    print(f'  idle_loop.mp4 {n} frames, {n/FPS:.2f}s, '
          f'{out.stat().st_size/1e6:.1f} MB; panel-region luma '
          f'{np.mean(lumas):.1f} (was 11.0 bare)')

    # A still for the preview harness, which cannot screenshot a video node.
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(out), '-frames:v', '1',
                    str(OUT / 'idle_still.png')], check=True)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    build_idle()
    build_sequence()
