# AnimeOS — Change Log

Working log for the AnimeOS Senbonzakura login project. Documents what was
modified, the issues hit, and how things are configured on this machine
(CachyOS / KDE Plasma 6 / Wayland, user `abhi`).

## Session: 2026-08-30 — Login polish, desktop reveal, SDDM bring-up

### Greeter audio at the login screen (2026-08-31)

**Symptom:** the greeter's Bankai sequence plays silently at login (video
fine, no sound); everything is audible after login.

**Root cause — device permission, not code.** The SDDM greeter runs as the
`sddm` user (uid 951) in its own session, which starts its own
PipeWire/wireplumber. `/dev/snd/*` are `root:audio` (rw-rw----) with an ACL
granting access only to `abhi` and the `audio` group; `sddm` is in no group
that can open them (`groups=951(sddm)`). So the greeter session's wireplumber
never creates a sink, QtMultimedia has nowhere to output, and the audio is
silently dropped (QtMultimedia does not error, so nothing is logged). After
login the user session has device access and sound works.

**Fix:** grant the greeter's user access to the sound devices:
```bash
sudo usermod -aG audio sddm      # revert: sudo gpasswd -d sddm audio
```
At the next boot the greeter session's wireplumber should create a real sink
and the sequence audio will play. Verify by checking the sddm session created
a sink, and by listening at the login screen.

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

### Petal splash (native login→desktop transition) — DONE, THEN SUPERSEDED

The KSplashQML splash (`splash/`, installed to `~/.local/share/plasma/
look-and-feel/animeos-splash.desktop/`, `~/.config/ksplashrc`) rendered the
storm correctly when run manually (both screens, dissolve verified), but the
KSplashQML mechanism proved fragile at a real boot: at the 16:25 boot the
org.kde.KSplash dbus activations all failed with exit 1 (the provider never
registered), so the splash could silently not appear. It was also unverifiable
between reboots.

**Replaced with the reveal, upgraded to layer-shell, started by a systemd
user service.** This is the decisive fix:

- `reveal/main.cpp` now opens one **layer-shell overlay** window per screen
  (LayerShellQt), so the compositor shows it above everything from the moment
  it starts — no dependence on the desktop shell having loaded, no dbus stage
  plumbing. That early-start reliability is exactly what KSplashQML lacked.
- **`animeos-reveal.service`** (user unit, `After=plasma-kwin_wayland.service`,
  `WantedBy=graphical-session.target`) starts the reveal as soon as the
  compositor is up, so the petals appear while the desktop loads and dissolve
  into it.
- Assets are installed **local** (`~/.local/share/animeos/reveal/`) — no NTFS
  read at session start.
- Timing tuned for the boot context: storm held 2.6s, dissolve 1.5s, then the
  app quits (hard 6s backstop).
- The default KDE logo splash is blanked out (`ksplashrc` → the minimal
  `animeos-blank.desktop` theme) so nothing competes with the reveal.

Install (done on this machine, documented for re-install):
```bash
mkdir -p ~/.local/share/animeos/reveal
cp -r reveal/* ~/.local/share/animeos/reveal/   # binary + Reveal.qml + assets + shaders
cp ~/.config/systemd/user/animeos-reveal.service \
   <repo>/systemd-user/animeos-reveal.service   # or write the unit
systemctl --user daemon-reload
systemctl --user enable animeos-reveal.service
```

Verified in-session: the service runs the reveal, petals render on both
screens, exits clean (status 0), no warnings (fixed the `qmlEngine()`-vs-
`view->engine()` quit wiring).

### Blank-screen handoff + login legibility — done, then trimmed

- **The greeter now hands off cleanly.** A first attempt made the greeter show
  the petal storm after the password to bridge the handoff; it did not help
  (SDDM tears the greeter down too fast for it to render) and it could read as
  an odd looped sequence, so it was reverted to the one-frame handoff. The
  brief blank between the password and the session's reveal is inherent (SDDM
  kills the greeter before the session's compositor exists; nothing user-space
  can render there) and is the accepted behavior.
- **Login UI legibility.** Dropped the ByakuyaMark avatar above the name; added
  a soft vertical scrim behind the text so the name, the line field and BANKAI
  stay legible when the sequence behind them is bright.
- **Reveal plays the storm exactly once.** The petals video is 1.75s; a long
  hold made it visibly loop. `Reveal.qml` now sets `loops: 1` and dissolves on
  `EndOfMedia` (~1.5s), so the petals play once over the desktop then clear.
  The reveal unit starts with the compositor (`After=plasma-kwin_wayland.service`,
  no ordering relative to the shell) so the one-loop play lands over the home
  screen.
- **Smooth ending.** Stopping the video and dissolving a static frame read as
  an abrupt freeze. The reveal now keeps the storm looping *through* the
  dissolve (a timer starts the handoff after one play, not `EndOfMedia`), so
  the petals are still moving as they scatter; the dissolve is eased
  `InOutCubic` over 2s with a short settle pause before the window closes.
- **Seamless petal loop.** The 1.75s `petals.mp4` had a visible seam at its
  loop point (wrap jump 0.128, 1.5x the mean motion) that read as a tiny
  restart. Rebuilt it with a two-frame crossfade at the wrap (same technique as
  the idle loop): the wrap jump is now 0.0003. The reveal plays the storm once
  (~2.0s) with no loop seam.
- **The real loop problem was the crescendo, not the seam.** A frame-by-frame
  luminance profile of the storm video showed the real cause of the "0.1s of
  the next loop": the clip is *not* a stationary loop. It crescendos from luma
  52 to a dense 84 peak in its opening frames (the "swords loading") then
  settles to ~39. Looping re-started that crescendo, and the crossfade seam
  fix made it worse for a no-loop setup (the crossfade tail ends bright).
  `Reveal.qml` now plays the video **exactly once** (`loops: 1`), starting the
  dissolve at 1.3s so motion carries through the early dissolve, and the video
  ends on its dim, sparse settle frame which the dissolve then clears. No loop
  point is ever rendered, so the re-crescendo blip is gone. (Diagnosis method:
  per-frame video analysis was more precise than screenshots, which are too
  coarse to catch a ~0.1s transient.)

### Git housekeeping

- Pulled origin/main (2 new commits: PLAN.md sync, Login.qml stuck-timer
  4000→10000). The Login.qml overlap was reconciled by keeping our rewrite and
  adopting their 10s fix; rebased and pushed as `a858b62`.
