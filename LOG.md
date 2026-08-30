# AnimeOS — Change Log

Working log for the AnimeOS Senbonzakura login project. Documents what was
modified, the issues hit, and how things are configured on this machine
(CachyOS / KDE Plasma 6 / Wayland, user `abhi`).

## Session: 2026-08-30 — Login polish, desktop reveal, SDDM bring-up

### What we changed

- **Idle loop is now forward-only.** `idle_loop.mp4` used to ping-pong
  (play forward then reverse) to hide the loop seam, which made the petals
  visibly drift up and then back every 3.5s. Rebuilt it forward-only at half
  speed with a two-frame crossfade at the wrap (measured wrap jump ~0.0005,
  invisible). `tools/build_greeter.py` now builds the loop forward-only +
  crossfade, so a future plate rebuild reproduces it. Regenerated
  `idle_still.png` from the new loop.
- **Login panel is now a minimal cinematic composition.** Removed the panel
  box/gradient/rim entirely (`login/senbonzakura/Login.qml`). The login now
  floats on the dark hold: smaller `ByakuyaMark` → uppercase letter-spaced
  username → thin blade hairline → password as a glowing underline field
  (grows out from center on focus) → BANKAI as a letter-spaced text-action
  with hover underline → busy dots → failure message. All behavior preserved
  (Enter to submit, caps hint, shake, user steppers, mock-injectable props).
- **Preview harness fixed.** `login/preview/grab.qml` pointed at a stale shot
  path and, worse, the still backdrop sat *under* the sequence VideoOutput so
  screenshots captured random footage frames. It now uses
  `idle_still.png` and calls `backdrop.skip()` so grabs are deterministic.
- **Desktop reveal is now a C++ launcher that mirrors on every screen.**
  `reveal/Reveal.qml`'s root was a `Window`; the window now comes from
  `reveal/main.cpp` (one `QQuickView` per screen). The petal scene is
  1920x1080, so per-screen mirroring keeps the aspect right (a spanning
  window would double the petal width). Includes a hard 3.5s backstop because
  a QML `Qt.quit()` does not reliably reach `QCoreApplication` under
  `QQuickView`. Built via `reveal/CMakeLists.txt` → `reveal/reveal`
  (gitignored). `reveal/run.sh` execs the binary instead of `qml6`.
- **Stuck-timer fix adopted from origin/main.** The "no response from the
  login service" timeout is 10s (was 4s) so it can't race PAM's FAIL_DELAY
  on a wrong password.

### Issues faced

- **SDDM theme wouldn't load in test mode.** `sddm-greeter-qt6 --test-mode
  --theme senbonzakura` resolved `senbonzakura` as a relative path from the
  shell's cwd and fell back to the embedded theme. Use the absolute path:
  `sddm-greeter-qt6 --test-mode --theme /usr/share/sddm/themes/senbonzakura`.
- **Test mode can never authenticate.** There is no SDDM daemon socket in
  test mode, so submitting a password (correct or not) times out with "No
  response from the login service". Real auth only happens after SDDM is the
  live display manager.
- **The machine's display manager is `plasmalogin`, not SDDM.**
  `systemctl enable sddm` fails because `display-manager.service` already
  symlinks to `plasmalogin.service`. To switch:
  ```bash
  sudo systemctl disable plasmalogin.service
  sudo rm -f /etc/systemd/system/display-manager.service
  sudo systemctl enable sddm.service
  ```
- **Reveal showed on only one monitor.** On Wayland, KWin ignores a screen
  hint set *before* a window maps and dumps every new fullscreen window on
  one output. Fix: re-apply `QQuickView::setScreen()` ~400ms after the
  window maps (verified both views land on `HDMI-A-1` @0,0 and `eDP-1`
  @1920,0).
- **Reveal was slow at session start.** It ran as a KDE autostart app
  (phase 2) after the desktop loaded, reading the 9.7MB packed video off the
  NTFS mount. See the splash work below for the native fix.
- **xkb "No Compose file" warnings** and `ImageButton` override notices in
  the greeter log are harmless.

### How things are configured

- **SDDM theme installed:** `/usr/share/sddm/themes/senbonzakura` (copied
  from `login/senbonzakura`, self-contained incl. videos).
- **SDDM config:** `/etc/sddm.conf.d/theme.conf`:
  ```
  [Theme]
  Current=senbonzakura
  ```
- **Reveal autostart:** `~/.config/autostart/animeos-reveal.desktop` →
  `reveal/run.sh` → the built `reveal/reveal` binary. Fails silently by
  design. (Being retired in favour of the splash.)
- **Preview without logging out:**
  ```bash
  qml6 login/preview/preview.qml                    # interactive
  qml6 -platform offscreen login/preview/grab.qml   # screenshot -> /var/tmp/greeter_login.png
  sddm-greeter-qt6 --test-mode --theme /usr/share/sddm/themes/senbonzakura
  ```
- **Source footage is not committed** (gitignored); the built videos are.

### Next: petal splash (native login→desktop transition)

The reveal-overlay approach leaves a 4-5s gap (KDE splash + desktop load
before the autostart app shows petals). Plan: replace the Plasma splash
(`KSplashQML`) with a custom look-and-feel package
`~/.local/share/plasma/look-and-feel/animeos-splash.desktop/` whose
`contents/splash/Splash.qml` plays the packed petal storm through the same
per-petal dissolve shader and dissolves into the desktop when the session is
ready (stage 5). Activated via `~/.config/ksplashrc`:
```
[KSplash]
Engine=KSplashQML
Theme=animeos-splash.desktop
```
KSplashQML opens one layer-shell window per screen, so petals appear on all
monitors. The reveal autostart is then removed.
