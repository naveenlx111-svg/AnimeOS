# Senbonzakura greeter

An SDDM theme (Qt6 / QML) in `login/senbonzakura/`.

## Flow

    sequence (21.5s, one-shot, skippable, with sound)  ->  login  ->  session

The Bankai plays first. When it ends the picture crossfades to the dark hold
and the login panel fades in. Any key or click skips ahead -- but not for the
first 800ms: the greeter reliably eats a stray input event as its window maps,
and without the grace period that could kill the whole opening in under a
second. Nobody decides to skip inside the first second anyway.

Sequence-first also sidesteps a real SDDM constraint. The greeter is torn down
almost immediately after successful authentication, so a long animation *after*
the password could not have played there at all. Putting it before the prompt
keeps the whole thing inside the greeter's lifetime.

On success the screen goes black in one frame. There is no send-off animation:
the session is already starting behind it, and a fade there is just a delay in
costume.

## Why the login sits on the dark hold

The panel needs a calm, dark backdrop to stay readable. Measuring the region
the panel actually occupies, across the cut:

| stretch | luma | local contrast |
|---------|------|----------------|
| dark hold (shot 3) | 11 | 0.02 |
| swords risen | 45 | 2.0 |
| petal storm | 175 | 1.8 |

The storm the sequence ends on fights the panel badly, so the sequence hands
over to the hold rather than freezing on its own last frame. It reads as the
petals clearing to leave Byakuya standing in the dark, waiting.

Bare, the hold is close enough to black to be a letdown after that climax, so
the matted petals are composited back over it at 30% -- luma 17.6, still well
clear of the panel. That loop uses its own matte, not the one the reveal uses:
see `tools/build_greeter.py` for why the storm's bright jets have to come out.

## Sound

The sequence carries the episode's own audio, cut from the same window and
retimed to match. Details in `tools/build_audio.py`; the short version is that
the picture ends up 79ms *slower* than the source it shows -- each shot's frame
count rounds up against an already-stretched timeline -- so the audio is slowed
to suit rather than sped up.

Normalised to -18.6 LUFS at -1.8 dBTP, played at 0.6. A login screen cannot
know what sink it will get or what volume it is set to, so it stays restrained.
The idle loop is silent by design: it repeats for as long as someone takes to
type. Skipping mutes immediately -- stopping the player still leaves the sink
playing what it already holds.

Audio failing must never stop someone logging in, so the error path drops the
audio output and lets the picture finish.

## Files

| file | role |
|------|------|
| `Main.qml` | flow: sequence -> login -> auth, and the skip handling |
| `Background.qml` | two-stage video backdrop, audio, and a still fallback |
| `Login.qml` | the panel; takes SDDM's objects as properties so it can run standalone |
| `ByakuyaMark.qml` | the chibi above the password field; Canvas paths |
| `SystemBar.qml` | session picker (left) and suspend / restart / shut down (right) |
| `GlyphButton.qml` | small circular icon button; icons drawn with Canvas, not a font |
| `Theme.qml` | palette and timing, every colour measured off the footage |

Icons and the chibi are drawn with `Canvas` rather than a font glyph or an SVG,
because the greeter runs before any user fontconfig is loaded. `qt6-svg` is
installed here, but one small mark is not worth a runtime dependency that has
to be present at login.

## The panel

The chibi, the user name, the password field, and the BANKAI button, which
stays disabled until something is typed. Below that a caps-lock warning and the
failure line, both of which hold their height so nothing moves under the
cursor. A failed attempt shakes the panel and clears the field.

Session and power controls sit along the bottom edge rather than inside the
panel -- they are used rarely, and putting them in the panel would crowd the
one thing the screen is for. The clock is top right.

If the login service never answers, the panel says so after 10 seconds and
re-enables itself. Without that the button latches on its busy state forever,
which would lock someone out of their own login screen.

## Previewing without logging out

    qml6 login/preview/preview.qml                    # interactive
    qml6 -platform offscreen login/preview/grab.qml    # screenshot

`Login.qml` takes `sddmHost`, `users` and `sessions` as properties rather than
reaching for SDDM's globals, so the harness can supply mocks. `grabToImage`
cannot capture a `VideoOutput` node, so the harness swaps in a still frame --
which is why the backdrop there is one frame rather than the loop.

**`--test-mode` can never complete a login.** The greeter posts the attempt to
the SDDM daemon socket and waits; in test mode nothing is listening, so neither
`loginSucceeded` nor `loginFailed` ever arrives and no password is checked,
right or wrong. What you get instead is the timeout message. To
exercise the success path, stand in for the daemon with a mock host object --
that is the only way to see the close without actually logging out.

Note also that SDDM swallows QML `console.log`, so debugging inside the real
greeter means putting state on screen, not logging it.

## Installing

Not installed automatically: it replaces the login screen, and a broken greeter
is awkward to recover from.

    sudo cp -r login/senbonzakura /usr/share/sddm/themes/
    sudo sed -i 's/^current = .*/current = senbonzakura/' /etc/sddm.conf.d/theme.conf

Nothing in the theme uses an absolute path, and it has been checked running
from a copy outside the repo, so it behaves the same once moved.

Keep a TTY available (Ctrl+Alt+F2) the first time. To revert, set `current`
back to `breeze`.

## Still open

- The real close has never been exercised. It cannot be, short of logging in
  for real -- see the test-mode note above.
- Multi-user switching is wired but untested; this machine has one account.
- 21.5s is a long wait on a busy morning. It is skippable, and the cut earns
  its length, but it is the obvious thing to trim if it wears thin.

## The "no response" message, and why the timeout is 10 seconds

This is the message that appears whenever nothing comes back from the login
service, and there are two quite different reasons it can show up.

**In `--test-mode`, always.** There is no daemon on the other end of the
socket, so no answer of any kind arrives. Nothing is wrong with the theme; the
message is doing its job.

**At a real login, it should never be seen -- and the first version of this
timeout could have caused it.** PAM applies a deliberate delay before reporting
a *wrong* password, to slow down guessing. `FAIL_DELAY` is 3 seconds on this
machine and `pam_unix`'s own built-in default is 2. With the timeout at 4
seconds there was only a second of margin, so a slow disk or a probing module
would let this fire first and announce "no response" for what was really just a
mistyped password -- and the message would then visibly flip to "authentication
failed" when the real answer landed a moment later.

Ten seconds sits clear of that. Erring long is cheap here because the wait is
not a dead one: the button runs its dots the whole time. Erring short means
telling someone their login service is broken when they simply mistyped.
