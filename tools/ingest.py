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

    # A 23.976 source resampled to 24 duplicates roughly one frame in every
    # 42, which reads as a stutter on a slow push. Retiming instead stretches
    # the timestamps by 0.1% and keeps every frame exactly once.
    src_fps = probe(args.clip)['fps']
    vf = ''
    if src_fps and abs(src_fps - FPS) / FPS < 0.005:
        vf += f"setpts=PTS*{src_fps / FPS:.9f},"
    else:
        vf += f"fps={FPS},"

    # Crop first when asked: a vertical source has to be reframed to 16:9
    # before scaling, or it arrives as a pillarboxed sliver.
    if args.crop:
        vf += f"crop={args.crop},"
    if args.fill:
        # Scale up until the crop covers the frame, then take the middle. This
        # is how a shot gets reframed past a burned-in subtitle: crop the band
        # away, then push in to fill. It costs a small upscale, so it is opt-in
        # per shot rather than the default.
        vf += (f"scale={RES[0]}:{RES[1]}:force_original_aspect_ratio=increase:"
               f"flags=lanczos,"
               f"crop={RES[0]}:{RES[1]}")
    else:
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



def cmd_reframe(args):
    """Re-crop and re-scale a plate that is already on disk.

    This is a second pass rather than part of `cut` on purpose: the watermark
    removal is calibrated against the logo's position in the untouched frame,
    so anything that moves or resizes pixels has to happen after it. Order is
    cut -> dewatermark -> reframe.
    """
    src = ROOT / 'shots' / args.shot / 'plate'
    frames = sorted(src.glob('*.png'))
    if not frames:
        sys.exit(f'no plate at {src}')
    tmp = src.parent / 'plate_reframe'
    if tmp.exists():
        for f in tmp.glob('*.png'):
            f.unlink()
    tmp.mkdir(exist_ok=True)
    vf = (f"crop={args.crop},"
          f"scale={RES[0]}:{RES[1]}:force_original_aspect_ratio=increase:flags=lanczos,"
          f"crop={RES[0]}:{RES[1]}")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                    '-start_number', '1', '-i', str(src / '%04d.png'),
                    '-vf', vf, '-start_number', '1', str(tmp / '%04d.png')], check=True)
    out = sorted(tmp.glob('*.png'))
    if len(out) != len(frames):
        sys.exit(f'reframe produced {len(out)} of {len(frames)} frames')
    for f in frames:
        f.unlink()
    for f in out:
        f.rename(src / f.name)
    tmp.rmdir()
    w, h = (int(x) for x in args.crop.split(':')[:2])
    print(f"  reframed {len(out)} frames of {args.shot}: {args.crop} "
          f"-> {RES[0]}x{RES[1]} ({RES[1] / h:.3f}x upscale)")


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
    c.add_argument('--fill', action='store_true',
                   help='scale the crop up to cover the frame instead of letterboxing it')
    c.set_defaults(func=cmd_cut)

    r = sub.add_parser('reframe')
    r.add_argument('shot')
    r.add_argument('--crop', required=True, help='W:H:X:Y taken before the fill scale')
    r.set_defaults(func=cmd_reframe)

    args = ap.parse_args()
    if getattr(args, 'clip', None) is not None and not args.clip.exists():
        sys.exit(f"no such clip: {args.clip}")
    args.func(args)


if __name__ == '__main__':
    main()
