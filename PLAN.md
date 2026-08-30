# AnimeOS — Senbonzakura Login Cinematic

## Goal

A cinematic anime login on CachyOS/KDE Plasma where Byakuya's Bankai
transitions into the desktop.

## What it does now

    greeter starts
      -> Bankai sequence, 21.5s, with the episode's own audio
      -> login panel over the dark hold
      -> password
      -> greeter gone in one frame
      -> session starts
      -> petals dissolve off the real desktop

The sequence plays **before** the password, not after. That was a correction to
the original plan and it is also forced by SDDM: the greeter is torn down almost
immediately after successful authentication, so a long animation *after* the
password could never have played there.

The desktop reveal cannot live in the greeter either, for the same reason --
there is no moment inside it where the desktop exists to be revealed. It runs
as a session-start overlay instead, compositing over whatever is actually on
screen rather than a pre-rendered guess.

## How it is built

**The footage is the VFX.** The original plan had Blender generate the swords,
the sword-to-petal transformation and the swarm, with the anime footage
composited under it. That is not what happened, and the reason is simple: the
broadcast episode already contains all of it, animated by people who do this
for a living. Nothing generated was going to beat it.

So the pipeline conforms and repairs real footage instead:

| stage | tool |
|-------|------|
| find the cut points | `tools/probe_cuts.py` |
| cut plates, reframe | `tools/ingest.py`, driven by `shots/cuts.json` |
| remove the release watermark | `tools/dewatermark.py` |
| remove burned-in subtitles | `tools/detext.py` |
| rebuild everything from the cut list | `tools/recut.py` |
| pull petals onto transparency | `tools/matte.py` |
| encode the theme's videos | `tools/build_greeter.py` |
| cut, retime and mux the audio | `tools/build_audio.py` |

`shots/SHOTS.md` records what each shot is and why each repair was done the way
it was. Every number in it was measured, not judged by eye.

**Blender is currently unused.** The one genuinely generative piece -- the
petals dissolving over the desktop -- turned out better cut from the episode's
own storm than synthesised, and it runs as a QML shader so it can composite
live over the real desktop instead of being baked. If a future sequence needs
something the footage cannot supply, Blender is still the right tool for it.

## Where things live

    shots/          the cut, as frames, plus the cut list as data
    tools/          the pipeline
    login/          the SDDM greeter theme        -> login/README.md
    reveal/         the desktop reveal overlay    -> reveal/README.md
    assets/footage/ source video (gitignored, not ours to redistribute)

## Not done

- **The theme is not installed.** It replaces the login screen and needs root;
  see `login/README.md`.
- **A real login has never been performed with it.** `--test-mode` has no PAM
  and no daemon, so the success path has only ever run against a mock host.
- Multi-user switching is wired but untested; this machine has one account.

## Long-term

After this sequence is polished, AnimeOS may expand into lock-screen
animations, animated wallpapers, desktop themes, system sounds, and further
character sequences on shared animation infrastructure.

## Principle

Do not build the entire AnimeOS framework before the first sequence is
polished. And do not generate what the source already does better.
