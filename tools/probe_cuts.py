#!/usr/bin/env python3
"""Find scene cuts in a clip and render a contact sheet to eyeball them.

    tools/probe_cuts.py assets/footage/ep.mkv --start 300 --end 340
    tools/probe_cuts.py assets/footage/ep.mkv --start 300 --end 340 --threshold 0.2

Scene detection is a starting point, not an answer: it misses cuts between
visually similar shots and invents them across fast internal action. Always
check the boundary frames before trusting a cut.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRATCH = Path('/var/tmp/probe_cuts')


def detect(clip, start, end, thr):
    out = subprocess.run(
        ['ffmpeg', '-hide_banner', '-ss', str(start), '-to', str(end), '-i', str(clip),
         '-vf', f"select='gt(scene,{thr})',showinfo", '-f', 'null', '-'],
        capture_output=True, text=True).stderr
    return [start + float(m) for m in re.findall(r'pts_time:([0-9.]+)', out)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip', type=Path)
    ap.add_argument('--start', type=float, default=0)
    ap.add_argument('--end', type=float, required=True)
    ap.add_argument('--threshold', type=float, default=0.25)
    ap.add_argument('--fps', type=float, default=2.0, help='contact sheet sampling rate')
    args = ap.parse_args()
    if not args.clip.exists():
        sys.exit(f'no such clip: {args.clip}')

    cuts = detect(args.clip, args.start, args.end, args.threshold)
    marks = [args.start] + cuts + [args.end]
    print(f"  cuts in {args.start}-{args.end}s at threshold {args.threshold}:\n")
    print("   #     start      end     dur    frames@24")
    for i, (a, b) in enumerate(zip(marks, marks[1:]), 1):
        print(f"   {i:2d}  {a:8.3f} {b:8.3f}  {b - a:6.2f}s   {round((b - a) * 24):5d}")

    SCRATCH.mkdir(exist_ok=True)
    for f in SCRATCH.glob('*.png'):
        f.unlink()
    subprocess.run(
        ['ffmpeg', '-hide_banner', '-loglevel', 'error',
         '-ss', str(args.start), '-to', str(args.end), '-i', str(args.clip),
         '-vf', f"fps={args.fps},scale=260:-1,"
                f"drawtext=text='%{{n}}':x=5:y=5:fontsize=18:fontcolor=yellow"
                f":box=1:boxcolor=black@0.7",
         str(SCRATCH / '%03d.png')], check=True)
    sheet = SCRATCH / 'sheet.png'
    subprocess.run(['magick', 'montage', *sorted(str(p) for p in SCRATCH.glob('[0-9]*.png')),
                    '-tile', '8x', '-geometry', '+2+2', '-background', '#222', str(sheet)],
                   check=True)
    n = len(list(SCRATCH.glob('[0-9]*.png')))
    print(f"\n  contact sheet: {sheet}  ({n} frames, index n -> {args.start} + n/{args.fps}s)")


if __name__ == '__main__':
    main()
