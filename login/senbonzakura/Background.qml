import QtQuick
import QtMultimedia

// Two-stage backdrop.
//
// Stage 1 plays the Bankai sequence once. Stage 2 is the dark hold, looping
// for as long as the user takes to type. The hold is the calmest stretch in
// the footage (measured luma 16, local contrast 0.03), which is what lets the
// login panel sit on top of it and stay readable -- the petal storm the
// sequence ends on measures luma 137 and fights the panel badly.
//
// Narratively the handover reads as the petals clearing to leave Byakuya
// standing in the dark, waiting.
Item {
    id: root

    property bool sequenceDone: false
    // Preview aid only: grabToImage cannot capture a VideoOutput node, so the
    // harness swaps in a still to produce a representative screenshot.
    property string stillOverride: ""
    signal finished()

    function skip() {
        if (!sequenceDone) {
            sequence.stop()
            root.sequenceDone = true
            root.finished()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.night
    }

    Image {
        anchors.fill: parent
        source: root.stillOverride
        fillMode: Image.PreserveAspectCrop
        visible: root.stillOverride !== ""
    }

    // ---- stage 2: the looping hold, underneath ----
    VideoOutput {
        id: holdOut
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectCrop
    }

    MediaPlayer {
        id: hold
        source: "assets/video/idle_loop.mp4"
        videoOutput: holdOut
        loops: MediaPlayer.Infinite
    }

    // ---- stage 1: the sequence, on top, fading out when done ----
    VideoOutput {
        id: seqOut
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectCrop
        opacity: root.sequenceDone ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }
    }

    MediaPlayer {
        id: sequence
        source: "assets/video/sequence.mp4"
        videoOutput: seqOut
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.EndOfMedia)
                root.skip()
        }
        onErrorOccurred: function(err, str) {
            console.warn("senbonzakura: sequence unavailable:", str)
            root.skip()
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0, 0, 0, 0.45) }
            GradientStop { position: 0.45; color: Qt.rgba(0, 0, 0, 0.0) }
            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.55) }
        }
        opacity: root.sequenceDone ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }
    }

    Component.onCompleted: {
        hold.play()
        sequence.play()
    }
}
