#!/usr/bin/env python3
"""Remove the AnimePahe watermark by inverting the blend that put it there.

    tools/dewatermark.py solve assets/footage/bleach_tybw_ep04.mp4
    tools/dewatermark.py apply shots/shot01_release/plate

The watermark is not baked into the pixels, it is alpha-composited over them:

    observed = alpha * L + (1 - alpha) * background

with a single flat colour L and a fixed per-pixel alpha map. That is an affine
mix, so it inverts exactly:

    background = (observed - alpha * L) / (1 - alpha)

which is why this recovers the real frame instead of inpainting a guess at it.
Nothing is invented; the pixels under the logo are still in the file, just
washed toward white.

`solve` measures the two unknowns from the source itself:

  * alpha * L (the premultiplied logo) is read straight off frames where the
    footage behind the logo is pure black, because there `observed` IS the
    premultiplied logo.
  * L then falls out of frames whose logo corner is bright and flat, where the
    background can be read from the non-glyph pixels beside each glyph.

Both come out consistent across the whole episode, which is the check that the
model is the right one -- a baked-in or per-scene watermark would not hold still
like this.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CAL = ROOT / 'tools' / 'watermark_animepahe.npz'

# The corner the logo lives in. Generous: solving only needs to bracket it.
BOX_W, BOX_H = 260, 70


def _sample(source, fps, w, h):
    """Decode the top-left corner of every nth frame as raw RGB."""
    cmd = ['ffmpeg', '-v', 'error', '-i', str(source),
           '-vf', f'fps={fps},crop={w}:{h}:0:0',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    return np.frombuffer(raw, dtype=np.uint8)[:n * w * h * 3] \
             .reshape(n, h, w, 3).astype(np.float32)


def cmd_solve(args):
    a = _sample(args.source, args.fps, BOX_W, BOX_H)
    print(f'sampled {len(a)} frames')

    # Frames whose logo corner is letterboxed or faded to black. There the
    # background term vanishes and the observation is the premultiplied logo.
    surround = a[:, :, 225:BOX_W].mean(axis=(1, 2, 3))
    black = np.where(surround < 0.35)[0]
    if len(black) < 5:
        sys.exit('not enough pure-black frames to solve from')
    P = np.median(a[black], axis=0)
    print(f'{len(black)} pure-black frames -> premultiplied logo, peak {P.max():.0f}')

    glyph = P.mean(axis=2) > 6
    ys, xs = np.where(glyph)
    print(f'glyph footprint rows {ys.min()}-{ys.max()} cols {xs.min()}-{xs.max()}'
          f' ({glyph.sum()} px)')

    # L from bright flat corners: observed = P + (1-alpha)*bg, alpha = P/L,
    # so L = P*bg / (P + bg - observed).
    ests = []
    for f in a:
        bg_px = f[~glyph]
        if bg_px.mean() > 120 and bg_px.std() < 6:
            bg = np.median(bg_px, axis=0)
            o = np.median(f[glyph], axis=0)
            p = np.median(P[glyph], axis=0)
            ests.append(p * bg / np.maximum(p + bg - o, 1e-3))
    if len(ests) < 10:
        sys.exit('not enough flat bright frames to solve L')
    L = np.median(np.array(ests), axis=0)
    lo, hi = np.percentile(np.array(ests), [25, 75], axis=0)
    print(f'{len(ests)} flat bright frames -> L = {np.round(L, 1)}  iqr {np.round(lo,1)}..{np.round(hi,1)}')

    alpha = np.clip(P / L, 0.0, 0.95)
    np.savez(CAL, P=P, L=L, alpha=alpha)
    print(f'wrote {CAL.relative_to(ROOT)}  max alpha {alpha.max():.3f}')


def load():
    if not CAL.exists():
        sys.exit(f'no calibration at {CAL}; run: tools/dewatermark.py solve <source>')
    d = np.load(CAL)
    return d['P'], d['alpha']


def unblend(img):
    """Invert the composite in place over the logo corner. img is float RGB."""
    P, alpha = load()
    h, w = P.shape[:2]
    roi = img[:h, :w]
    # Straight algebra, then clip: only the rounding that h.264 already did to
    # the frame can push a recovered value outside range.
    img[:h, :w] = np.clip((roi - P) / (1.0 - alpha), 0.0, 255.0)
    return img


def cmd_apply(args):
    from PIL import Image
    d = Path(args.dir)
    # Un-blending twice would over-correct into a dark ghost, and the plates
    # are edited in place, so the pass has to be able to say it already ran.
    done = d / '.dewatermarked'
    if done.exists() and not args.force:
        print(f'{d} already de-watermarked (--force to redo)')
        return
    frames = sorted(d.glob('*.png'))
    if not frames:
        sys.exit(f'no PNGs in {d}')
    for i, p in enumerate(frames):
        im = np.asarray(Image.open(p).convert('RGB')).astype(np.float32)
        # Write beside the frame and rename, so an interrupted run leaves the
        # original intact rather than a half-written PNG.
        tmp = p.with_suffix('.tmp.png')
        Image.fromarray(unblend(im).round().astype(np.uint8)).save(tmp)
        tmp.replace(p)
    done.touch()
    print(f'de-watermarked {len(frames)} frames in {d}')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('solve'); s.add_argument('source')
    s.add_argument('--fps', default='2'); s.set_defaults(func=cmd_solve)
    a = sub.add_parser('apply'); a.add_argument('dir')
    a.add_argument('--force', action='store_true'); a.set_defaults(func=cmd_apply)
    args = ap.parse_args(); args.func(args)


if __name__ == '__main__':
    main()
