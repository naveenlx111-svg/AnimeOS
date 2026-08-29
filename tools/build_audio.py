#!/usr/bin/env python3
"""Cut, retime and normalise the sequence's audio, then mux it into the video.

    tools/build_audio.py

The picture is one continuous 21.46s window of the episode, so the audio is
one continuous take -- there is nothing to re-edit. What there is, is a timing
problem, and it is not the one you would expect.

The plates were retimed from 23.976 to 24 by stretching timestamps, so on its
own the picture runs 0.1% fast. But each shot was cut with `-t` on a stretched
timeline, which rounds its frame count up, and the nine shots between them
round up by two and a half frames. Those repeats outweigh the speed-up: 517
delivered frames play for 21.542s and carry 21.463s of source. Retiming the
audio by the same 0.999 the picture got would end it 101ms early, which is
well past where a sync error stops being subliminal. So the tempo is derived
from what was actually delivered -- frames on disk against the source span
they came from, 0.996325 -- and that pins the audio to the picture at both
ends, leaving at most 24ms of wander at the cuts in between (worst is
shot07_wall, 23.7ms).

Loudness is a two-pass loudnorm because one pass is a feed-forward guess at a
target it has not measured yet. The broadcast mix arrives at -23.5 LUFS, quiet
by desktop standards; -18 LUFS is the compromise for something that plays
unannounced when you sit down, and with the player at 0.6 it lands near -22.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUTS = ROOT / 'shots' / 'cuts.json'
OUT = ROOT / 'login' / 'senbonzakura' / 'assets' / 'video'
FPS = 24
SRC_FPS = 24000 / 1001

# Quiet enough not to startle, loud enough to hear over a fan. See the
# docstring; the measured input is -23.5 LUFS. TP is held 1.5 dB below full
# scale because the greeter has no idea what sink it will land on and an
# intersample overshoot on a cheap DAC is an audible crackle.
TARGET_I = -18.0
TARGET_TP = -1.5
TARGET_LRA = 11.0

# The picture cross-dissolves to the idle hold over Theme.slow (620ms) once the
# sequence ends, so the audio is gone by the time that starts rather than being
# chopped off mid-storm. The head fade is only there to stop the in-point
# clicking: 784.30s is mid-scene, not a zero crossing.
FADE_IN = 0.2
FADE_OUT = 0.6


def timing():
    """Where the audio starts, how long it is, and how much to stretch it.

    Read from the frames on disk rather than from the durations in cuts.json,
    because the durations are what was asked for and the frames are what came
    out -- the two differ by the per-shot rounding this has to correct for.
    """
    cfg = json.loads(CUTS.read_text())
    shots = cfg['shots']
    counts = [len(list((ROOT / 'shots' / s['name'] / 'plate').glob('*.png')))
              for s in shots]
    if not all(counts):
        sys.exit('missing plates; run tools/recut.py first')

    start = shots[0]['start']
    # The last frame's source timestamp is where the take has to end, and the
    # shots are contiguous, so everything between is covered exactly once.
    end = shots[-1]['start'] + counts[-1] / SRC_FPS
    play = sum(counts) / FPS
    return start, end - start, play


def measure(src, start, span, tempo):
    """loudnorm pass one: what the cut actually measures."""
    p = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-v', 'info',
         '-ss', f'{start:.6f}', '-t', f'{span + 0.5:.6f}', '-i', str(src),
         '-vn', '-af', f'atempo={tempo:.9f},'
                       f'loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}'
                       f':print_format=json',
         '-f', 'null', '-'],
        capture_output=True, text=True, check=True).stderr
    # The JSON is the last brace-delimited block on stderr, after the banner.
    return json.loads(p[p.rindex('{'):p.rindex('}') + 1])


def build():
    cfg = json.loads(CUTS.read_text())
    src = ROOT / cfg['source']
    if not src.exists():
        sys.exit(f'no source at {src}; assets/footage is gitignored')

    start, span, play = timing()
    tempo = span / play
    print(f'  {span:.4f}s of source -> {play:.4f}s of picture, '
          f'atempo={tempo:.6f}')

    m = measure(src, start, span, tempo)
    print(f"  measured  I {m['input_i']} LUFS  TP {m['input_tp']} dBTP  "
          f"LRA {m['input_lra']}")

    seq = OUT / 'sequence.mp4'
    dur = float(subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=duration', '-of', 'csv=p=0', str(seq)],
        capture_output=True, text=True, check=True).stdout.strip())

    # Pass two, with the measurement handed back in so the gain is computed
    # against the real programme loudness instead of a running estimate.
    # linear=true keeps it a single gain where it can: the mix is already
    # dynamic and there is no reason to let a limiter breathe on it.
    norm = (f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
            f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
            f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
            f":offset={m['target_offset']}:linear=true:print_format=summary")
    # loudnorm resamples to 192k internally; come back to 48k before the fades
    # so the fade lengths are in the sample rate the encoder will see.
    af = (f"atempo={tempo:.9f},{norm},aresample=48000,"
          f"atrim=0:{dur:.6f},asetpts=N/SR/TB,"
          f"afade=t=in:st=0:d={FADE_IN},"
          f"afade=t=out:st={dur - FADE_OUT:.6f}:d={FADE_OUT}")

    wav = OUT / '_audio.m4a'
    p = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-v', 'info', '-y',
         # A little more source than the picture needs, so the trim above is
         # what sets the length and the tail fade is not fading into nothing.
         '-ss', f'{start:.6f}', '-t', f'{span + 0.5:.6f}', '-i', str(src),
         # The episode carries its own chapter marks, and mp4 renders chapters
         # as a third text track. The greeter has no use for a table of
         # contents to a file it plays 21 seconds of.
         '-vn', '-map_metadata', '-1', '-map_chapters', '-1',
         '-af', af, '-ar', '48000', '-ac', '2',
         '-c:a', 'aac', '-b:a', '192k', str(wav)],
        capture_output=True, text=True, check=True).stderr
    for line in p.splitlines():
        if any(k in line for k in ('Input Integrated', 'Input True Peak',
                                   'Output Integrated', 'Output True Peak',
                                   'Normalization Type')):
            print('  ', line.split(']')[-1].strip())

    # Re-mux, never re-encode. The video is CRF 14 over a graded, sharpened,
    # de-watermarked plate; a second generation would spend all of that to save
    # nothing, since the audio is a separate stream in the same container.
    tmp = OUT / '_muxed.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(seq), '-i', str(wav),
                    '-map', '0:v:0', '-map', '1:a:0', '-map_chapters', '-1',
                    '-c:v', 'copy', '-c:a', 'copy',
                    '-movflags', '+faststart', str(tmp)], check=True)
    tmp.replace(seq)
    wav.unlink()
    print(f'  sequence.mp4  video {dur:.3f}s + audio, '
          f'{seq.stat().st_size/1e6:.1f} MB')


if __name__ == '__main__':
    build()
