#!/usr/bin/env python3
"""Pull the petals off their background as an alpha matte, for compositing
over the live desktop.

    tools/matte.py shot07_wall --out reveal/assets/petals.mp4

The storm frames are not petals on black -- half the frame is a diffuse
magenta glow, so keying on brightness alone gives a pink veil with no gaps to
see the desktop through. What separates a petal from the glow is scale: petals
are small bright blobs, the glow is a smooth wash. So the matte is driven by a
high-pass -- luminance minus a wide box blur of itself -- which keeps the
particles and drops the wash. That is what opens the holes.

One correction on top: the brightest jets are large AND bright, so the
high-pass reads them as background and punches a hole through the middle of
the storm. Anything near clipping is forced opaque to put those back.

Output is a single h.264 file with the colour on the left and the matte on the
right, because this ffmpeg's VP9 silently discards the alpha plane and a
packed frame decodes anywhere. The shader in reveal/ splits it back apart.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def box_blur(x, r):
    """Mean over a (2r+1) square, via a summed-area table so radius is free."""
    p = np.pad(x, ((r + 1, r), (r + 1, r)), mode='edge')
    c = np.cumsum(np.cumsum(p, 0), 1)
    return ((c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:]
             - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1])
            / ((2 * r + 1) ** 2))


def matte(rgb, radius, lo, hi, core_lo, core_hi):
    L = rgb.max(axis=2)
    hp = L - box_blur(L, radius)
    a = np.clip((hp - lo) / (hi - lo), 0.0, 1.0)
    core = np.clip((L - core_lo) / (core_hi - core_lo), 0.0, 1.0)
    return np.maximum(a, core)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('shot')
    ap.add_argument('--out', required=True)
    ap.add_argument('--radius', type=int, default=24)
    ap.add_argument('--lo', type=float, default=0.03)
    ap.add_argument('--hi', type=float, default=0.20)
    ap.add_argument('--core-lo', type=float, default=0.80)
    ap.add_argument('--core-hi', type=float, default=0.97)
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--mask-logo', action='store_true', default=True,
                    help='force the watermark corner transparent (default on)')
    args = ap.parse_args()

    src = ROOT / 'shots' / args.shot / 'plate'
    frames = sorted(src.glob('*.png'))
    if not frames:
        sys.exit(f'no plate at {src}')

    tmp = ROOT / 'shots' / args.shot / 'matte_packed'
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob('*.png'):
        f.unlink()

    cov = []
    for i, f in enumerate(frames):
        rgb = np.asarray(Image.open(f).convert('RGB')).astype(np.float32) / 255.0
        a = matte(rgb, args.radius, args.lo, args.hi, args.core_lo, args.core_hi)
        if args.mask_logo:
            # The un-composite leaves a few DN of residual in the logo corner,
            # and a high-pass is exactly the operator that would amplify it
            # into visible speckle. Feather that corner out instead.
            yy = np.clip((np.arange(rgb.shape[0])[:, None] - 60) / 24.0, 0, 1)
            xx = np.clip((np.arange(rgb.shape[1])[None, :] - 220) / 40.0, 0, 1)
            a = a * np.maximum(yy, xx)
        cov.append(float((a > 0.01).mean()))
        h, w = a.shape
        packed = np.zeros((h, w * 2, 3), np.uint8)
        packed[:, :w] = (rgb * 255).round().clip(0, 255)
        packed[:, w:] = (a[..., None] * 255).round().clip(0, 255)
        Image.fromarray(packed).save(tmp / f'{i+1:04d}.png')

    print(f'  matted {len(frames)} frames; petal coverage '
          f'{min(cov)*100:.1f}%-{max(cov)*100:.1f}% of frame')

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-framerate', str(args.fps), '-start_number', '1',
                    '-i', str(tmp / '%04d.png'),
                    # The matte half must stay crisp: chroma can be subsampled
                    # but a soft alpha edge shows up as a halo round every petal.
                    '-c:v', 'libx264', '-preset', 'veryslow', '-crf', '19',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    str(out)], check=True)
    mb = out.stat().st_size / 1e6
    print(f'  wrote {out} ({mb:.1f} MB, {len(frames)} frames @ {args.fps}fps, '
          f'colour|alpha packed side by side)')


if __name__ == '__main__':
    main()
