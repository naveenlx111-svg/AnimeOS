# Desktop reveal

Plays the Senbonzakura clearing sweep once at session start, on top of the
real desktop.

## Why it lives here and not in the greeter

SDDM tears the greeter down before the session exists, so there is no moment
inside the greeter where the desktop is behind the petals. Running it as a
session-start overlay means the reveal is genuine compositing over whatever
is actually on screen -- not a pre-rendered guess at what the desktop looks
like.

## Behaviour

A frameless, always-on-top, fullscreen window with a transparent background.
It opens with an opaque veil in the same near-black as the greeter, so the
session does not pop into existence, then ~190 petals sweep outward from the
centre while growing -- which is what a petal passing the camera actually
does. It quits ~2.8s in.

`Qt.WindowTransparentForInput` means it never swallows clicks, and `run.sh`
redirects all output and can only ever fail silently: a broken decoration
must not be able to hold up a login.

## Installed

    ~/.config/autostart/animeos-reveal.desktop

Remove that file to disable it. To retime, edit `sweepMs` / `veilMs` at the
top of `Reveal.qml`.

## Testing

    qml6 reveal/Reveal.qml

Run it from the repo: `RevealPetal.qml` reaches the petal art with a path
relative to its own location, so a copy elsewhere renders nothing.
