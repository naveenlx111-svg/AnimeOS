import QtQuick
import QtMultimedia

// AnimeOS - Senbonzakura splash.
//
// The Plasma splash shown while the session starts. It plays the same petal
// storm the SDDM greeter ends on -- the packed colour|matte video, unpicked by
// the reveal's shader -- so the login hands straight into it.
//
// KSplashQML drives `stage` as startup progresses (1 initial, 2 kcminit,
// 3 wm, 4 startPlasma, 5 ksmserver/ready, 6 desktop->exit). At stage 5 the
// session's desktop is behind this window, so we fade the black backdrop out
// (the desktop appears behind the storm) and then dissolve the petals
// individually, revealing it through the clearing storm. KSplashQML closes the
// window at stage 6; anything not yet faded is transparent by then.
//
// The splash window itself is transparent (SplashWindow sets
// Qt::transparent + an alpha buffer), so what the shader does not cover shows
// the compositor underneath.
Rectangle {
    id: root
    color: "transparent"

    property int stage: 0
    property real progress: 0

    onStageChanged: {
        if (stage == 5 && !handoff.running)
            handoff.running = true
    }

    // Fallback: the stage-5 signal is driven over DBus by the session manager,
    // and if the provider is not registered the call silently never lands. The
    // storm must still clear, so dissolve regardless once the session has had
    // time to come up. Anything earlier is a no-op because handoff runs once.
    Timer {
        id: fallback
        interval: 9000
        running: true
        onTriggered: {
            if (!handoff.running)
                handoff.running = true
        }
    }

    // Solid backdrop while the session (and the desktop behind us) is still
    // settling. Faded out at handoff so the desktop shows through the storm.
    Rectangle {
        id: bg
        anchors.fill: parent
        color: "black"
    }

    Item {
        id: content
        anchors.fill: parent
        opacity: 0

        MediaPlayer {
            id: player
            source: "assets/petals.mp4"
            videoOutput: sink
            loops: MediaPlayer.Infinite
            Component.onCompleted: play()
            // Don't gate the fade-in on a splash stage -- stages 1-3 are set
            // before this QML finishes loading, so the storm would never show.
            // Fade in as soon as the first frame is decodable.
            onMediaStatusChanged: {
                if (mediaStatus === MediaPlayer.BufferedMedia
                        || mediaStatus === MediaPlayer.LoadedMedia)
                    contentFade.running = true
            }
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
            fragmentShader: "shaders/petals.frag.qsb"
            property variant source: tex
            property real progress: root.progress
            property real noiseScale: 7.0
            property real grain: 0.85
            // Sakura, not confetti: the petals that survive the dissolve are
            // their white-hot cores, so they get pushed back toward pink.
            property real tintAmount: 0.85
            property vector4d tint: Qt.vector4d(1.0, 0.62, 0.82, 1.0)
            blending: true
        }
    }

    NumberAnimation {
        id: contentFade
        target: content
        property: "opacity"
        from: 0; to: 1
        duration: 400
        easing.type: Easing.InOutQuad
        running: false
    }

    // Handoff: desktop behind us, then the per-petal dissolve. Backdrop first
    // and fast, so the desktop is visible even if stage 6 lands early; the
    // petals then clear over it. Same shader profile as the reveal: slow at
    // first so the holes creep open, quick at the end so it clears.
    SequentialAnimation {
        id: handoff
        running: false
        NumberAnimation {
            target: bg; property: "opacity"
            from: 1; to: 0
            duration: 300
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: root; property: "progress"
            from: 0; to: 1
            duration: 900
            easing.type: Easing.InCubic
        }
    }
}
