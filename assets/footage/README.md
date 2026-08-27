# Source footage

Drop the Bleach clips here. Nothing in this directory is committed — it is
gitignored, because the files are large and not ours to redistribute.

Any container ffmpeg can read is fine (`.mkv`, `.mp4`, ...). Resolution and
frame rate do not need to match the project; `tools/ingest.py` conforms them.

    tools/ingest.py probe assets/footage/<clip>          # what am I holding?
    tools/ingest.py cut   assets/footage/<clip> <shot> \
        --start 00:04:12.5 --frames 60                   # cut a plate

`cut` writes `shots/<shot>/plate/####.png` at 1920x1080, 24fps. Everything
downstream reads those frames; the original clip is never touched again.
