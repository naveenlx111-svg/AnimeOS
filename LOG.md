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

### Petal splash (native login→desktop transition) — DONE

Replaced the Plasma splash (`KSplashQML`) with a custom look-and-feel package
`splash/` in the repo, installed to
`~/.local/share/plasma/look-and-feel/animeos-splash.desktop/`. Activated via
`~/.config/ksplashrc`:
```
[KSplash]
Engine=KSplashQML
Theme=animeos-splash.desktop
```
The splash plays the packed petal storm (same colour|matte video + shader as
the reveal) on every screen (KSplashQML opens one transparent layer-shell
window per screen), fades in when the first frame decodes, and at stage 5
(ksmserver/session-ready) fades the black backdrop out and dissolves the
petals, revealing the desktop through the storm. Stage 6 closes the window.
The `~/.config/autostart/animeos-reveal.desktop` reveal overlay was removed —
the splash now owns the transition, so the old reveal would just double the
petals. The `reveal/` C++ tool stays for manual testing.

- Tested in KSplashQML test mode (`ksplashqml --test --nofork
  animeos-splash.desktop`), which advances stages on a 2s timer: captured the
  storm over black, then the handoff revealing the desktop (screenshot luma
  jumps from ~26 to ~69, matching the desktop).
- Stage semantics learned from the plasma-workspace source: 1 initial,
  2 kcminit, 3 wm, 4 startPlasma, 5 ksmserver (ready), 6 desktop (exit).
- Splash `console.log` output is swallowed by KSplashQML (PlasmaQuick engine),
  so verify with screenshots instead.
- **Dissolve reliability:** the stage-5 handoff signal is driven over DBus and
  can silently fail to land if the provider isn't registered (seen at the
  16:25 boot, where the KSplash dbus activations all failed with exit 1). The
  splash now has a 9s fallback timer that runs the handoff regardless, so the
  storm always clears. Verified the storm renders on both screens and the
  dissolve reveals the desktop.
- The splash is started by `plasma-ksplash.service` (ksplashqml, oneshot,
  forks; the ~30s window auto-close is the hard backstop). In a manual
  `systemctl --user start plasma-ksplash.service` there is no session driving
  stages, so the storm holds until the fallback/auto-close -- that is expected,
  not a bug.

### Git housekeeping

- Pulled origin/main (2 new commits: PLAN.md sync, Login.qml stuck-timer
  4000→10000). The Login.qml overlap was reconciled by keeping our rewrite and
  adopting their 10s fix; rebased and pushed as `a858b62`.
