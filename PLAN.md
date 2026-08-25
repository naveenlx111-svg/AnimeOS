# AnimeOS — Senbonzakura Login Cinematic

## Goal

Create a cinematic anime-inspired login experience on CachyOS/KDE Plasma where Byakuya's Bankai sequence transitions seamlessly into the desktop.

## Final Sequence

### 1. Login appears

- Dark/minimal background.
- Byakuya is shown through DaVinci Resolve footage.
- Password UI is integrated into the cinematic.

### 2. Bankai declaration

- When the password pane is opened, Byakuya begins saying the Bankai name.
- The Bankai title/text appears cinematically.
- The Senbonzakura swords begin emerging in the scene.

### 3. Sword → Senbonzakura transformation

The giant swords that formed as part of the Bankai do **not** simply disappear.

They are the source of the Senbonzakura swarm:

**Bankai swords → swords fragment → fragments become Sakura-like petals → petals begin swirling around Byakuya → swarm expands outward.**

The transformation should feel continuous and visually connected to the swords.

### 4. Senbonzakura swarm

- Petals begin swirling around the intended Byakuya composition.
- The swarm gradually becomes denser.
- Petals move through different depth layers.
- Some remain distant and small.
- Others move closer to the camera and become larger.
- The overall motion should feel elegant, fluid, and supernatural rather than like generic particle rain.
- The swarm progressively expands until it dominates the frame.

### 5. Full-screen transition

- Petals rapidly approach the camera.
- Large foreground petals cross the frame.
- The entire screen becomes temporarily engulfed by Senbonzakura.
- The VFX then moves outward and clears the frame.

### 6. Desktop transition

- The Blender VFX clears.
- The underlying KDE desktop/home-screen footage is revealed.
- The login cinematic ends.

## Blender

Blender is responsible only for the Senbonzakura VFX:

- Bankai sword emergence
- Sword-to-petal transformation
- Petal shapes and variations
- Swirling particle field
- Depth and foreground particles
- Full-screen engulfment
- Transparent RGBA render

The Blender output does **not** contain Byakuya, the login UI, or the surrounding anime footage.

## DaVinci Resolve

DaVinci handles:

- Byakuya footage
- Sword-drop footage
- Bankai dialogue
- Bankai title/text
- Audio synchronization
- Final cinematic editing
- Compositing the Blender VFX
- Transition into the KDE desktop

## Long-Term AnimeOS

After the Senbonzakura sequence is polished, AnimeOS may expand into:

- Custom SDDM/login sequences
- Lock-screen animations
- Animated wallpapers
- Desktop themes
- Anime system sounds
- Multiple anime/character sequences
- Reusable animation and particle infrastructure

## Principle

Do not build the entire AnimeOS framework before the first sequence is polished.

The first milestone is:

**A convincing Senbonzakura Bankai sequence where the Bankai swords naturally transform into a swirling Sakura blade-petal swarm that engulfs the screen and transitions into the KDE desktop.**
