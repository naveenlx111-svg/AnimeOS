# Senbonzakura greeter

An SDDM theme (Qt6 / QML) for `login/senbonzakura/`.

## Flow

    sequence (17s, one-shot, skippable)  ->  login (indefinite)  ->  session

The Bankai sequence plays first. When it ends the picture crossfades to the
dark hold and the login panel fades in. Any key or click skips ahead.

This ordering also sidesteps a real SDDM constraint: the greeter is torn down
almost immediately after successful authentication, so a long animation
*after* the password could not have played there anyway. Putting the sequence
before the prompt keeps the whole thing inside the greeter's lifetime.

## Why the login sits on the dark hold

The panel needs a calm, dark backdrop to stay readable. Measuring a
centre-frame panel region across the whole cut:

| stretch | luma | local contrast |
|---------|------|----------------|
| dark hold (shot 3, f1-84) | 16 | 0.03 |
| swords risen | 56 | 2.3 |
| petal storm  | 137 | 0.94 |

The storm the sequence ends on is bright magenta and fights the panel badly.
The hold is the calmest stretch in the footage, so the sequence hands over to
it rather than freezing on its own last frame. It reads as the petals clearing
to leave Byakuya standing in the dark, waiting.

## Files

| file | role |
|------|------|
| `Main.qml` | flow: sequence -> login -> auth, and the skip handling |
| `Background.qml` | two-stage video backdrop, with a still fallback |
| `Login.qml` | the panel; takes SDDM's objects as properties so it can run standalone |
| `PetalField.qml` | three depth bands of drifting petals |
| `Petal.qml` | one petal: vector silhouette plus a baked glow |
| `Theme.qml` | palette and timing, shared with the Blender VFX values |

## Previewing without logging out

    qml6 login/preview/preview.qml              # interactive
    qml6 -platform offscreen login/preview/grab.qml   # screenshot to /var/tmp

`Login.qml` takes `sddmHost`, `users` and `sessions` as properties rather than
reaching for SDDM's globals directly, so the harness can supply mocks. Note
that `grabToImage` cannot capture a `VideoOutput` node -- the harness swaps in
a still frame for screenshots, which is why the backdrop there is a single
frame rather than the loop.

## Installing

Not installed automatically: it replaces the login screen, and a broken
greeter is awkward to recover from. To install:

    sudo cp -r login/senbonzakura /usr/share/sddm/themes/
    sudo sed -i 's/^current = .*/current = senbonzakura/' /etc/sddm.conf.d/theme.conf

Test it before relying on it:

    sddm-greeter-qt6 --test-mode --theme /usr/share/sddm/themes/senbonzakura

Keep a TTY available (Ctrl+Alt+F2) the first time. To revert, set `current`
back to `breeze`.

## Not done yet

- The session and power controls are not built; the panel is password-only.
- The sequence is the 17s cut, which is a long wait on a busy morning. It is
  skippable, but the cut itself probably wants trimming.
- Petal art is the existing five SVGs; they read more like feathers than
  sakura at small sizes.
