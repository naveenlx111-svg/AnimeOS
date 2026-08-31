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
            // stop() ends the decode, but whatever the sink has already been
            // handed keeps playing, and sound continuing over a login panel
            // that has no picture behind it any more is worse than no sound.
            seqAudio.muted = true
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

    // No audioOutput, deliberately: this loops for as long as the user takes
    // to find their password, and a 3.5-second sting on repeat is a reason to
    // pick a different theme. The file carries no audio stream either.
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
        audioOutput: AudioOutput {
            id: seqAudio
            // Full volume. The sequence audio is normalised to -14 LUFS and the
            // greeter's sink is an unknown, so 0.6 used to land near -22 LUFS,
            // which was genuinely faint on monitor speakers. At 1.0 it is
            // clearly audible without being an announcement.
            volume: 1.0
        }
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.EndOfMedia)
                root.skip()
        }
        onErrorOccurred: function(err, str) {
            console.warn("senbonzakura: sequence player error:", str)
            // A greeter runs before any user session exists, so there may be
            // no PipeWire, no sink, or a device that refuses to open, and the
            // backend reports that on the player rather than on the audio
            // output. Sound is the optional half of this: drop it and let the
            // picture finish. Only skip if the picture died too.
            sequence.audioOutput = null
            if (sequence.playbackState !== MediaPlayer.PlayingState)
                root.skip()
        }
    }

    // Last resort. Nothing in here may leave someone staring at a video with
    // no password field: if the sequence has not reported EndOfMedia by the
    // time it should have -- a stalled decoder, a backend that errors halfway
    // through -- hand over to the login panel regardless.
    Timer {
        interval: 26000
        running: !root.sequenceDone
        onTriggered: root.skip()
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
