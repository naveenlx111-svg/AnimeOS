#!/usr/bin/env python3
"""Probe a source clip and cut a frame range out of it as a PNG plate.

    tools/ingest.py probe  assets/footage/clip.mkv
    tools/ingest.py cut    assets/footage/clip.mkv shot01_release --start 0 --frames 25 \
                           --crop 1080:608:0:480

`probe` tells you what you have. `cut` writes shots/<shot>/plate/####.png at the
project fps, which is what every later stage reads. Frames are the unit of work
here, so nothing downstream ever touches the original container again.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 24
RES = (1920, 1080)


def probe(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-print_format', 'json',
         '-show_format', '-show_streams', str(path)],
        capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    num, den = (int(x) for x in v['r_frame_rate'].split('/'))
    return {
        'codec': v['codec_name'],
        'width': v['width'],
        'height': v['height'],
        'fps': num / den if den else 0.0,
        'duration': float(info['format'].get('duration', 0.0)),
        'frames': int(v.get('nb_frames') or 0),
    }


def cmd_probe(args):
    p = probe(args.clip)
    print(f"  codec      {p['codec']}")
    print(f"  resolution {p['width']}x{p['height']}")
    print(f"  fps        {p['fps']:.4f}")
    print(f"  duration   {p['duration']:.2f}s  ({p['frames']} frames)")
    if abs(p['fps'] - FPS) > 0.01:
        print(f"  NOTE       source is not {FPS}fps; cut will resample to {FPS}")
    if (p['width'], p['height']) != RES:
        print(f"  NOTE       source is not {RES[0]}x{RES[1]}; cut will scale to fit")


def cmd_cut(args):
    dest = ROOT / 'shots' / args.shot / 'plate'
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob('*.png'):
        old.unlink()

    # Crop first when asked: a vertical source has to be reframed to 16:9
    # before scaling, or it arrives as a pillarboxed sliver.
    vf = f"fps={FPS},"
    if args.crop:
        vf += f"crop={args.crop},"
    # Scale to fit inside the frame and pad, so a non-16:9 source is never
    # stretched -- the VFX layer is authored against exact frame geometry.
    vf += (f"scale={RES[0]}:{RES[1]}:force_original_aspect_ratio=decrease:"
           f"flags=lanczos,"
           f"pad={RES[0]}:{RES[1]}:(ow-iw)/2:(oh-ih)/2:black")

    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error',
           '-ss', args.start, '-i', str(args.clip)]
    if args.frames:
        cmd += ['-frames:v', str(args.frames)]
    elif args.duration:
        cmd += ['-t', args.duration]
    cmd += ['-vf', vf, '-start_number', '1', str(dest / '%04d.png')]
    subprocess.run(cmd, check=True)

    n = len(list(dest.glob('*.png')))
    print(f"  wrote {n} frames -> {dest.relative_to(ROOT)}  ({n / FPS:.2f}s @ {FPS}fps)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('probe')
    p.add_argument('clip', type=Path)
    p.set_defaults(func=cmd_probe)

    c = sub.add_parser('cut')
    c.add_argument('clip', type=Path)
    c.add_argument('shot')
    c.add_argument('--start', default='0', help='timestamp, e.g. 00:04:12.5')
    c.add_argument('--frames', type=int, help='how many frames to take')
    c.add_argument('--duration', help='alternative to --frames, e.g. 2.5')
    c.add_argument('--crop', help='reframe before scaling: W:H:X:Y, e.g. 1080:608:0:580')
    c.set_defaults(func=cmd_cut)

    args = ap.parse_args()
    if not args.clip.exists():
        sys.exit(f"no such clip: {args.clip}")
    args.func(args)


if __name__ == '__main__':
    main()
