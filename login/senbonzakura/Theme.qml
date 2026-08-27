pragma Singleton

import QtQuick

// Senbonzakura palette. These are the same values the Blender VFX and the
// petal art were built against, so the login reads as one piece with the
// footage behind it rather than a separate UI bolted on top.
QtObject {
    readonly property color night:      "#08030b"   // the dark hold behind everything
    readonly property color panel:      "#140a13"
    readonly property color petalFill:  "#ff9fc5"
    readonly property color petalLight: "#ffeaf4"
    readonly property color glow:       "#ff4f9f"
    readonly property color deep:       "#d82d7f"
    readonly property color blade:      "#eaf4ff"
    readonly property color muted:      "#c9a6b8"
    readonly property color danger:     "#ff5f6d"

    readonly property int   radius:     14
    readonly property int   panelWidth: 420

    // One duration scale for the whole theme, so nothing drifts out of step.
    readonly property int   fast:       160
    readonly property int   normal:     280
    readonly property int   slow:       620
}
