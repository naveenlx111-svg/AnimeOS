pragma Singleton

import QtQuick

// Senbonzakura palette, sampled from the footage rather than picked by eye.
//
// Every colour below was measured off the plates the login sits on: the petal
// tones are the median of ~9M saturated magenta pixels across the three storm
// shots, the blade is the median of the cool arcs in shot08, and night is the
// dark hold in shot03. Hand-chosen values drifted well off -- the previous
// petal pink was #ff9fc5 where the real one is #a55d96, which is most of a
// step of saturation, and it read as a UI colour sitting on top of the film
// instead of a colour out of it.
//
// The one place the measurements are deliberately pushed is the interactive
// accents. A control has to stay findable while the storm behind it is a
// full-frame wash of exactly that hue, so `glow` and `deep` are lifted clear
// of the background they land on.
QtObject {
    // ---- measured, used wherever the UI should agree with the picture ----
    readonly property color night:      "#0a0b10"   // the dark hold
    readonly property color abyss:      "#06070a"   // its deepest reaches
    readonly property color petalFill:  "#a55d96"   // petal body
    readonly property color petalLight: "#dd9dcd"   // petal, lit
    readonly property color petalDeep:  "#7b3b6a"   // petal, in shadow
    readonly property color blade:      "#d0c3de"   // the cool arcs
    // His face and his haori, measured the same way off shot04_declare --
    // 4.3M skin pixels and 1.4M haori pixels. Worth stating plainly because
    // the first pass at the chibi assumed the footage had no skin tone in it
    // and mixed one out of petal pink and blade lavender, which came out
    // mauve and made him look ill rather than composed.
    readonly property color skin:       "#eedbc8"
    readonly property color haori:      "#f1ede5"

    // ---- lifted, so controls stay legible against the storm ----
    readonly property color glow:       "#ff5fb4"
    readonly property color deep:       "#c93b86"
    readonly property color danger:     "#ff6b72"

    readonly property color panel:      "#110b14"
    readonly property color muted:      "#b9a3b5"

    // Structure is drawn in `blade`, not in pink. Senbonzakura is blades that
    // become petals, and the practical half of that is that a cool lavender
    // edge still reads when the background goes full magenta, where a pink
    // edge dissolves into it.
    readonly property color rim:        "#d0c3de"

    readonly property int   radius:     14
    readonly property int   panelWidth: 420

    // One duration scale for the whole theme, so nothing drifts out of step.
    readonly property int   fast:       160
    readonly property int   normal:     280
    readonly property int   slow:       620
}
