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

    property int openMs: 260       // bloom up out of the handover's black
    property int holdMs: 1300      // storm plays (crescendo + settle) before clearing
    property int dissolveMs: 1600  // a slow scatter-away, not a snap
    property real progress: 0

    // Starts black and blooms in, rather than snapping to a full storm.
    //
    // Between SDDM stopping and KWin starting there is a beat -- about a
    // second on this machine -- where no compositor is presenting, so nothing
    // can be drawn on screen at all. That black is not ours to remove; there
    // is no client alive to remove it with. What is ours is what sits either
    // side of it, and arriving at full density made the gap read as a
    // dropout. Blooming out of black makes the same second read as the breath
    // before the storm, which is what a dip to black has always been for.
    //
    // Kept short, and deliberately NOT added to holdMs: the video starts its
    // own clock at load whether or not it is visible yet, and holdMs is tuned
    // against that clock -- it clears while the storm is still moving, just
    // before the source settles. Padding the hold by the lead-in would slide
    // the dissolve past that settle frame and undo the tuning.
    opacity: 0
    NumberAnimation on opacity {
        from: 0; to: 1
        duration: root.openMs
        easing.type: Easing.OutQuad
        running: true
    }

    // The video carries colour and matte side by side. It is fed through a
    // ShaderEffectSource rather than shown directly, because the shader has to
    // sample the same frame twice -- once for each half.
    MediaPlayer {
        id: player
        source: Qt.resolvedUrl("assets/petals.mp4")
        videoOutput: sink
        // Play the storm exactly once. The source is not a stationary loop: it
        // crescendos to a dense peak and then settles, so looping it re-starts
        // that crescendo -- a visible "the storm is loading again" blip right
        // before the dissolve. Playing it once ends on the dim, sparse settle
        // frame, which the dissolve then clears.
        loops: 1
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

    // Start clearing while the storm is still moving (the video ends on a dim,
    // mostly-empty frame ~450ms after this), so motion carries through the
    // early dissolve and there is nothing left to freeze at the end.
    Timer {
        interval: root.holdMs
        running: true
        onTriggered: {
            if (!handoff.running)
                handoff.running = true
        }
    }

    // The handoff: per-petal dissolve, eased in and out so it neither jumps in
    // nor snaps at the end. A short pause after everything is clear lets the
    // desktop settle before the window goes.
    SequentialAnimation {
        id: handoff
        running: false
        NumberAnimation {
            target: root; property: "progress"
            from: 0; to: 1
            duration: root.dissolveMs
            easing.type: Easing.InOutCubic
        }
        PauseAnimation { duration: 400 }
        ScriptAction { script: Qt.quit() }
    }

    // A hard backstop. If the media never loads, an always-on-top window that
    // stays alive is far worse than no reveal at all -- so quit regardless.
    Timer {
        interval: 6000
        running: true
        onTriggered: Qt.quit()
    }
}
