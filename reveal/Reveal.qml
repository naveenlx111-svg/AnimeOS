import QtQuick
import QtMultimedia

// AnimeOS - desktop reveal.
//
// Runs once at session start, on top of the real desktop. The greeter cannot
// do this: SDDM tears the greeter down before the session exists, so there is
// no moment inside it where the desktop is behind the petals. Doing it here
// means the reveal is genuine compositing over whatever is actually on screen,
// not a pre-rendered guess at what the desktop looks like.
//
// The petals are the real ones -- matted out of the episode's own storm by
// tools/matte.py -- rather than drawn shapes, so what dissolves here is the
// same animation the login screen just finished playing.
//
// The window is provided by main.cpp, which launches one of these per screen
// so the petal scene renders 1:1 on every monitor (the scene is 1920x1080;
// stretching it across a spanning window would double the petal width).
Item {
    id: root

    property int holdMs: 2600      // storm held while the desktop comes up
    property int dissolveMs: 1500
    property real progress: 0

    // The video carries colour and matte side by side. It is fed through a
    // ShaderEffectSource rather than shown directly, because the shader has to
    // sample the same frame twice -- once for each half.
    MediaPlayer {
        id: player
        source: Qt.resolvedUrl("assets/petals.mp4")
        videoOutput: sink
        loops: MediaPlayer.Infinite
        Component.onCompleted: play()
    }

    VideoOutput {
        id: sink
        anchors.fill: parent
        visible: false
        fillMode: VideoOutput.Stretch
    }

    ShaderEffectSource {
        id: tex
        sourceItem: sink
        anchors.fill: parent
        visible: false
        live: true
        hideSource: true
    }

    ShaderEffect {
        anchors.fill: parent
        fragmentShader: Qt.resolvedUrl("shaders/petals.frag.qsb")
        property variant source: tex
        property real progress: root.progress
        property real noiseScale: 7.0
        property real grain: 0.85
        // Sakura, not confetti: the petals that survive the dissolve are their
        // white-hot cores, so they get pushed back toward blossom pink.
        property real tintAmount: 0.85
        property vector4d tint: Qt.vector4d(1.0, 0.62, 0.82, 1.0)
        blending: true
    }

    SequentialAnimation {
        running: true
        PauseAnimation { duration: root.holdMs }
        NumberAnimation {
            target: root; property: "progress"
            from: 0; to: 1
            duration: root.dissolveMs
            // Slow at first so the holes creep open, then quick at the end so
            // it clears rather than lingering as a haze.
            easing.type: Easing.InCubic
        }
        ScriptAction { script: Qt.quit() }
    }

    // A hard backstop. If the media never loads, or the animation is somehow
    // never driven, an always-on-top window that stays alive is far worse than
    // no reveal at all -- so quit regardless.
    Timer {
        interval: root.holdMs + root.dissolveMs + 1500
        running: true
        onTriggered: Qt.quit()
    }
}
