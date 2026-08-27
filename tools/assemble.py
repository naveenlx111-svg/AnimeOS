#!/usr/bin/env python3
"""Concatenate the shots, in order, into one review video.

    tools/assemble.py                      # plates only
    tools/assemble.py --layer out          # composited frames where they exist
    tools/assemble.py --slate              # burn shot name + frame number in

Shot order is the numeric prefix of the directory name, so renaming a shot
never reorders the cut by accident.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / 'shots'
FPS = 24


def shot_dirs():
    ds = [d for d in SHOTS.iterdir() if d.is_dir() and re.match(r'shot\d+', d.name)]
    return sorted(ds, key=lambda d: int(re.match(r'shot(\d+)', d.name).group(1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layer', default='plate',
                    help="which frames to use: plate, vfx, or out (default plate)")
    ap.add_argument('--slate', action='store_true',
                    help='burn shot name and frame number into each frame')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    stage = ROOT / 'shots' / '.assemble'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    n, table = 0, []
    for d in shot_dirs():
        src = d / args.layer
        frames = sorted(src.glob('*.png')) if src.is_dir() else []
        if not frames:
            # fall back to the plate so one missing VFX pass does not gap the cut
            frames = sorted((d / 'plate').glob('*.png'))
            note = f'(no {args.layer}, used plate)' if args.layer != 'plate' else ''
        else:
            note = ''
        if not frames:
            continue
        table.append((d.name, n + 1, n + len(frames), note))
        for f in frames:
            n += 1
            (stage / f'{n:05d}.png').symlink_to(f.resolve())

    if not n:
        sys.exit('no frames found')

    out = Path(args.out).resolve() if args.out else SHOTS / 'review' / f'sequence_{args.layer}.mp4'
    out.parent.mkdir(parents=True, exist_ok=True)

    vf = []
    if args.slate:
        # one drawtext per shot, gated on the global frame range it occupies
        for name, a, b, _ in table:
            vf.append(
                f"drawtext=text='{name}  %{{eif\\:n+1-{a - 1}\\:d}}'"
                f":x=18:y=18:fontsize=30:fontcolor=yellow"
                f":box=1:boxcolor=black@0.65:boxborderw=8"
                f":enable='between(n\\,{a - 1}\\,{b - 1})'")
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error',
           '-framerate', str(FPS), '-i', str(stage / '%05d.png')]
    if vf:
        cmd += ['-vf', ','.join(vf)]
    cmd += ['-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-y', str(out)]
    subprocess.run(cmd, check=True)
    shutil.rmtree(stage)

    print(f"  layer: {args.layer}")
    for name, a, b, note in table:
        print(f"    {name:<22} {a:4d}-{b:<4d} {b - a + 1:4d}f  {note}")
    rel = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"  -> {rel}   {n} frames, {n / FPS:.2f}s")


if __name__ == '__main__':
    main()
