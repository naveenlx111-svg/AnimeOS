#!/usr/bin/env python3
"""Rebuild every shot from the cut list in shots/cuts.json.

    tools/recut.py                 # cut all shots, then run the detext passes
    tools/recut.py --source X.mkv  # same, against a different source
    tools/recut.py --dry-run

The cut list is data so that swapping the source is an edit to one file, not a
hunt through shell history. Timings and crops do NOT carry over to a new
source unchanged -- a different release will have its own cut points, and a
16:9 source needs no crop at all. Use tools/probe_cuts.py to re-derive them.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUTS = ROOT / 'shots' / 'cuts.json'


def run(cmd, dry):
    print('   ', ' '.join(str(c) for c in cmd))
    if not dry:
        subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    cfg = json.loads(CUTS.read_text())
    src = args.source or cfg['source']
    if not Path(src).exists():
        sys.exit(f'no such source: {src}')

    print(f"  source: {src}\n")
    for s in cfg['shots']:
        cmd = [sys.executable, str(ROOT / 'tools' / 'ingest.py'), 'cut', src, s['name'],
               '--start', str(s['start']), '--duration', str(s['duration'])]
        if s.get('crop'):
            cmd += ['--crop', s['crop']]
        if s.get('fill'):
            cmd += ['--fill']
        run(cmd, args.dry_run)

        # Un-composite the watermark while the frame is still untouched: the
        # calibration is tied to the logo's position in the original pixels,
        # so this has to run before any reframe moves or resizes them.
        run([sys.executable, str(ROOT / 'tools' / 'dewatermark.py'), 'apply',
             str(ROOT / 'shots' / s['name'] / 'plate'), '--force'], args.dry_run)

        if s.get('reframe'):
            run([sys.executable, str(ROOT / 'tools' / 'ingest.py'), 'reframe',
                 s['name'], '--crop', s['reframe']], args.dry_run)

    for d in cfg.get('detext', []):
        cmd = [sys.executable, str(ROOT / 'tools' / 'detext.py'), d['shot']]
        if d['mode'] == 'plate':
            cmd += ['--plate', '--rect', d['rect'], '--clean', d['clean'], '--frames', d['frames']]
        elif d['mode'] == 'keep':
            cmd += ['--keep', d['keep']]
        run(cmd, args.dry_run)

    for s in cfg['shots']:
        if s.get('keep'):
            run([sys.executable, str(ROOT / 'tools' / 'detext.py'), s['name'],
                 '--keep', s['keep']], args.dry_run)

    run([sys.executable, str(ROOT / 'tools' / 'assemble.py'), '--slate'], args.dry_run)


if __name__ == '__main__':
    main()
