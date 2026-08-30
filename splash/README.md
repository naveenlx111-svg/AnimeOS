# AnimeOS splash — SUPERSEDED

**This approach is retired.** The KSplashQML mechanism proved fragile at a real
boot (the org.kde.KSplash dbus activations failed with exit 1 at the 16:25
boot, so the splash could silently not appear). The petal transition now runs
through the reveal (`reveal/`) upgraded to a layer-shell overlay and started by
the `animeos-reveal.service` user unit (see `LOG.md`). This file is kept as
documentation of the attempt.

---

The Plasma splash (KSplashQML theme) that turns the login handoff into the
Senbonzakura storm. It plays the same packed colour|matte petal video the SDDM
greeter ends on, unpicks it with the reveal's shader, and dissolves the petals
away when the session is ready, so the desktop is revealed through the clearing
storm instead of behind the Plasma logo.

## Install

```bash
# 1. install the theme package
mkdir -p ~/.local/share/plasma/look-and-feel/animeos-splash.desktop
cp -r splash/contents ~/.local/share/plasma/look-and-feel/animeos-splash.desktop/
cp splash/metadata.json ~/.local/share/plasma/look-and-feel/animeos-splash.desktop/

# 2. the petal video (not committed; built from footage by tools/matte.py)
mkdir -p ~/.local/share/plasma/look-and-feel/animeos-splash.desktop/contents/splash/assets
cp reveal/assets/petals.mp4 ~/.local/share/plasma/look-and-feel/animeos-splash.desktop/contents/splash/assets/

# 3. activate it
mkdir -p ~/.config
printf '[KSplash]\nEngine=KSplashQML\nTheme=animeos-splash.desktop\n' > ~/.config/ksplashrc
```

Preview without rebooting:

```bash
ksplashqml --test --nofork animeos-splash.desktop
```

Test mode advances stages on its own timer (stage 5 = handoff), so you see the
storm then the dissolve then the app exits. To revert, delete
`~/.config/ksplashrc` or point `Theme` back at `org.kde.breeze.desktop`.

## How it works

- KSplashQML opens one transparent layer-shell window per screen, so the storm
  spans every monitor. It drives a `stage` property on the QML root:
  1 initial, 2 kcminit, 3 wm, 4 startPlasma, **5 ksmserver (session ready)**,
  6 desktop -> exit.
- The storm fades in as soon as the first frame decodes (media-driven, not
  stage-gated -- stages 1-3 arrive before the QML finishes loading).
- At stage 5 the black backdrop fades out (the freshly-loaded desktop appears
  behind the storm), then the per-petal dissolve runs over ~0.9s, clearing the
  petals individually. Stage 6 closes the window; by then it is transparent.
- A 9s fallback timer runs the handoff if stage 5 never arrives (the stage
  signal is driven over DBus and can silently fail to land if the provider is
  not registered), so the storm always clears instead of hanging.

## Files

| file | role |
|------|------|
| `metadata.json` | `Plasma/LookAndFeel` package declaration |
| `contents/splash/Splash.qml` | the splash: storm + handoff animation |
| `contents/splash/shaders/petals.frag*` | the packed colour|matte unpicker (shared with `reveal/`) |
