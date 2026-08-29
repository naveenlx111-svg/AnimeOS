# Desktop reveal

Runs once at session start, over the real desktop.

This cannot live in the greeter. SDDM tears the greeter down before the
session exists, so there is no moment inside it where the desktop is behind
the petals -- anything drawn there would be compositing over a guess. As a
session-start overlay it composites over whatever is actually on screen.

## What it draws

The petals are the episode's own, matted out of the storm by `tools/matte.py`,
not shapes drawn in QML. So the thing that dissolves here is the same
animation the login screen just finished playing.

`assets/petals.mp4` carries the colour on the left and the matte on the right
of one 3840x1080 frame. That packing exists because this ffmpeg's libvpx
silently discards the alpha plane -- a VP9 file that claims to have alpha
decodes back as fully opaque -- while a packed h.264 frame decodes anywhere.
`shaders/petals.frag` splits it back apart.

## The dissolve

Not a fade. Fading the layer's opacity drops every petal together, which reads
as a pink sheet going see-through. Instead the shader raises an alpha cut-off
per pixel against a noise field, so petals wink out at their own moments and
the gaps between them open and grow: the desktop appears through holes in the
storm rather than behind a veil.

Two details that matter:

* What survives a rising cut-off is each petal's near-white hot core, so the
  storm would drift colourless exactly as it thins. The shader pushes what is
  left back toward blossom pink, harder the further the dissolve has gone.
* The window is `WindowTransparentForInput`, and quits on a timer that fires
  whether or not the media ever loaded. An always-on-top window that outlives
  its animation is worse than having no animation.

## Install

    cp animeos-reveal.desktop ~/.config/autostart/

Delete that file to turn it off. `run.sh` fails silently on purpose: a broken
decoration must never be able to hold up a login.

## Rebuild the petals

    tools/matte.py shot07_wall --out reveal/assets/petals.mp4 \
        --core-lo 0.90 --core-hi 1.0

`shot07_wall` is the source because it is the only stretch of the storm that
is pure petals -- no Byakuya, dark background, and real gaps between the
particles. Re-compile the shader after editing it:

    /usr/lib/qt6/bin/qsb --glsl "100es,120,150" --hlsl 50 --msl 12 \
        -o reveal/shaders/petals.frag.qsb reveal/shaders/petals.frag
