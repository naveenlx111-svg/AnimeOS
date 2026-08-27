#!/usr/bin/env python3
"""Remove the fan edit's burned-in titles from a shot's plate.

    tools/detext.py shot03_swords --preview 20
    tools/detext.py shot03_swords

The titles are pink/magenta glyphs sitting on top of the frame. Rather than
blanking a rectangle (which is what ffmpeg's delogo does, and why it smears
across anything with structure), this finds the glyph pixels themselves,
grows the mask to cover their glow, and fills only those pixels by diffusing
the surrounding image inward. On flat skin or flat sky the fill is invisible;
where a hair strand crosses, the strand is carried through from both sides.

Frames with no title are passed through untouched.
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def glyph_mask(rgb):
    """Pink/magenta title glyphs: red and blue both clearly above green."""
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    core = (r > 80) & (b > 60) & (r - g > 32) & (b - g > 14)
    # the glow is the same hue but much weaker; catch it with a looser test
    halo = (r - g > 16) & (b - g > 6) & (r > 60)
    return core, halo


def dilate(m, k):
    out = m.copy()
    for _ in range(k):
        p = np.pad(out, 1, constant_values=False)
        out = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] | out)
    return out


def _down(a):
    h, w = a.shape[:2]
    h2, w2 = h - (h % 2), w - (w % 2)
    a = a[:h2, :w2]
    return (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) * 0.25


def _up(a, shape):
    o = np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)
    # _down crops odd dimensions away, so doubling can land one row/column
    # short of the level above; replicate the edge to make up the difference.
    dy, dx = shape[0] - o.shape[0], shape[1] - o.shape[1]
    if dy > 0:
        o = np.concatenate([o, np.repeat(o[-1:], dy, axis=0)], axis=0)
    if dx > 0:
        o = np.concatenate([o, np.repeat(o[:, -1:], dx, axis=1)], axis=1)
    return o[:shape[0], :shape[1]]


def inpaint(img, mask, smooth=40):
    """Pull-push fill.

    A Jacobi relaxation alone cannot do this: information travels one pixel
    per iteration, so the middle of a 50px glyph never hears about the skin
    around it and keeps whatever grey it was seeded with. Instead, pull the
    known pixels down an image pyramid until the holes are covered, then push
    the result back up, preferring real data wherever it exists. A short
    relaxation at full resolution then hides the seam.
    """
    if mask.sum() == 0:
        return img
    f = img.astype(np.float32)
    known = (~mask).astype(np.float32)[..., None]

    pyr = [(f * known, np.repeat(known, 3, axis=2))]
    while min(pyr[-1][0].shape[:2]) > 4:
        v, w = pyr[-1]
        pyr.append((_down(v), _down(w)))

    v, w = pyr[-1]
    cur = v / np.maximum(w, 1e-6)
    for v, w in reversed(pyr[:-1]):
        up = _up(cur, v.shape)
        a = np.minimum(w, 1.0)
        cur = a * (v / np.maximum(w, 1e-6)) + (1.0 - a) * up

    out = np.where(mask[..., None], cur, f)

    m3 = mask[..., None]
    for _ in range(smooth):
        pad = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode='edge')
        avg = (pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:]) * 0.25
        out = np.where(m3, avg, out)

    return np.clip(out, 0, 255).astype(np.uint8)


def parse_ranges(spec):
    out = []
    for part in spec.split(','):
        if '-' in part:
            a, b = part.split('-')
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def clean_plate(frames, rect):
    """Temporal median of a rectangle over frames known to be title-free."""
    x0, y0, x1, y1 = rect
    stack = np.stack([np.asarray(Image.open(f).convert('RGB')).astype(np.float32)[y0:y1, x0:x1]
                      for f in frames])
    return np.median(stack, axis=0)


def patch_plate(path, plate, rect, feather=12):
    """Composite a clean plate over the title, feathered at the edges.

    Only valid where the background really is static -- checked before use.
    On flat sky this is exact, where an inpaint can only ever approximate.
    """
    x0, y0, x1, y1 = rect
    img = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    h, w = y1 - y0, x1 - x0
    wy = np.minimum(np.arange(h), np.arange(h)[::-1]) / max(feather, 1)
    wx = np.minimum(np.arange(w), np.arange(w)[::-1]) / max(feather, 1)
    a = np.clip(np.minimum(wy[:, None], wx[None, :]), 0, 1)[..., None]
    img[y0:y1, x0:x1] = a * plate + (1 - a) * img[y0:y1, x0:x1]
    return np.clip(img, 0, 255).astype(np.uint8)


def process(path, grow=4):
    rgb = np.asarray(Image.open(path).convert('RGB'))
    core, halo = glyph_mask(rgb)
    if core.sum() < 200:
        return None, 0
    # Grow freely outward from the glyph cores. The glyphs carry a dark
    # outline and drop shadow that are not magenta at all, so clipping the
    # dilation back to magenta pixels leaves that ring behind and the fill
    # then diffuses from it -- which reads as a grey ghost of the text.
    m = dilate(core | (halo & dilate(core, 3)), grow)
    return inpaint(rgb, m), int(m.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shot')
    ap.add_argument('--preview', type=int, help='render one frame to scratch and stop')
    ap.add_argument('--grow', type=int, default=4)
    ap.add_argument('--plate', action='store_true',
                    help='patch a static rectangle from a temporal median instead '
                         'of inpainting (use where the background does not move)')
    ap.add_argument('--rect', help='x0,y0,x1,y1 for --plate')
    ap.add_argument('--clean', help='frame ranges with no title, e.g. 1-8,34-60')
    ap.add_argument('--frames', help='frame ranges to patch, e.g. 9-30')
    ap.add_argument('--keep', help='explicit frame ranges to keep, e.g. 1-23,68-74; '
                                   'overrides --drop-titled detection')
    ap.add_argument('--drop-titled', action='store_true',
                    help='rebuild the plate from only the title-free frames, '
                         'renumbered. For shots where the title sits on detail '
                         'that no fill can reconstruct.')
    args = ap.parse_args()

    plate = ROOT / 'shots' / args.shot / 'plate'
    if not plate.is_dir():
        sys.exit(f'no plate: {plate}')

    if args.drop_titled or args.keep:
        src = plate.parent / 'plate_raw'
        if not src.exists():
            shutil.copytree(plate, src)
            print(f'  archived original plate -> {src.name}/')
        if args.keep:
            want = set(parse_ranges(args.keep))
            keep = [f for f in sorted(src.glob('*.png')) if int(f.stem) in want]
        else:
            keep = []
            for f in sorted(src.glob('*.png')):
                rgb = np.asarray(Image.open(f).convert('RGB'))
                core, _ = glyph_mask(rgb)
                if core.sum() < 150:
                    keep.append(f)
        for f in plate.glob('*.png'):
            f.unlink()
        for n, f in enumerate(keep, 1):
            shutil.copyfile(f, plate / f'{n:04d}.png')
        total = len(list(src.glob('*.png')))
        print(f'  {args.shot}: kept {len(keep)} of {total} frames '
              f'({total - len(keep)} dropped as titled)')
        return

    if args.plate:
        if not (args.rect and args.clean and args.frames):
            sys.exit('--plate needs --rect, --clean and --frames')
        rect = tuple(int(v) for v in args.rect.split(','))
        src = plate.parent / 'plate_raw'
        if not src.exists():
            shutil.copytree(plate, src)
            print(f'  archived original plate -> {src.name}/')
        cp = clean_plate([src / f'{i:04d}.png' for i in parse_ranges(args.clean)], rect)
        todo = set(parse_ranges(args.frames))
        for f in sorted(src.glob('*.png')):
            n = int(f.stem)
            tgt = plate / f.name
            if n in todo:
                Image.fromarray(patch_plate(f, cp, rect)).save(tgt)
            else:
                shutil.copyfile(f, tgt)
        print(f'  {args.shot}: patched {len(todo)} frames from a clean plate')
        return

    if args.preview:
        f = plate / f'{args.preview:04d}.png'
        res, n = process(f, args.grow)
        if res is None:
            sys.exit(f'  f{args.preview}: no title detected')
        out = Path('/var/tmp/detext_preview.png')
        Image.fromarray(res).save(out)
        print(f'  f{args.preview}: {n} px filled -> {out}')
        return

    # keep a pristine copy so this is re-runnable
    orig = plate.parent / 'plate_raw'
    if not orig.exists():
        shutil.copytree(plate, orig)
        print(f'  archived original plate -> {orig.name}/')

    done = 0
    for f in sorted(orig.glob('*.png')):
        res, n = process(f, args.grow)
        tgt = plate / f.name
        if res is None:
            shutil.copyfile(f, tgt)
        else:
            Image.fromarray(res).save(tgt)
            done += 1
    print(f'  {args.shot}: cleaned {done} frames of {len(list(orig.glob("*.png")))}')


if __name__ == '__main__':
    main()
