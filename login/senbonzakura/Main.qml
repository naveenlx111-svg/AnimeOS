import QtQuick
import QtQuick.Controls
import QtMultimedia

// AnimeOS - Senbonzakura greeter.
//
// The Bankai sequence plays first; the login appears once it finishes. Any
// key or click skips ahead -- watching seventeen seconds is a pleasure the
// first time and a tax on the hundredth, and a login has to stay usable when
// you are in a hurry.
Rectangle {
    id: root
    width: 1920
    height: 1080
    color: Theme.night

    // SDDM injects these; absent under qmlscene, hence the guards.
    property var sddmHost: (typeof sddm !== "undefined") ? sddm : null
    property var users: (typeof userModel !== "undefined") ? userModel : null
    property var sessions: (typeof sessionModel !== "undefined") ? sessionModel : null
    property var keyboardState: (typeof keyboard !== "undefined") ? keyboard : null

    property string previewUser: ""
    property alias backdropItem: backdrop
    property bool ready: false           // sequence over, login usable
    property bool authenticated: false

    Background {
        id: backdrop
        anchors.fill: parent
        onFinished: root.ready = true
    }

    Login {
        id: login
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -parent.height * 0.06

        sddmHost: root.sddmHost
        users: root.users
        sessions: root.sessions
        keyboardState: root.keyboardState
        sessionIndex: bar.sessionIndex

        // SDDM's lastUser is empty until someone has logged in once, and in
        // test mode it is always empty -- so fall back to the first account
        // in the model rather than showing a bare "?".
        userName: root.resolveUser()

        visible: opacity > 0
        opacity: (root.ready && !root.authenticated) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }

        onAuthAccepted: root.authenticated = true
    }

    // Clock. Present once the sequence is over, so it never competes with the
    // opening; a login screen is also a thing people glance at for the time.
    Column {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: 52
        anchors.topMargin: 42
        spacing: 2
        opacity: (root.ready && !root.authenticated) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }

        Text {
            anchors.right: parent.right
            text: Qt.formatTime(clock.now, "HH:mm")
            color: Theme.petalLight
            font.pixelSize: 40
            font.letterSpacing: 2
            opacity: 0.9
        }
        Text {
            anchors.right: parent.right
            text: Qt.formatDate(clock.now, "dddd, d MMMM")
            color: Theme.muted
            font.pixelSize: 13
            font.letterSpacing: 1.6
            opacity: 0.7
        }
    }

    Timer {
        id: clock
        property date now: new Date()
        interval: 1000
        running: true
        repeat: true
        onTriggered: now = new Date()
    }

    SystemBar {
        id: bar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 14

        sddmHost: root.sddmHost
        sessions: root.sessions

        opacity: (root.ready && !root.authenticated) ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }
    }

    // Skip affordance, held back a beat so it does not step on the opening.
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 46
        text: "press any key to skip"
        color: Theme.muted
        font.pixelSize: 13
        font.letterSpacing: 2.2
        opacity: (!root.ready && hintDelay.triggered) ? 0.4 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }
    }

    Timer {
        id: hintDelay
        interval: 2200
        running: true
        property bool triggered: false
        onTriggered: triggered = true
    }

    // The skip is armed a beat after the window maps, not immediately.
    //
    // Running windowed on a live desktop the greeter has been seen taking a
    // stray event as it maps and skipping the sequence inside a second, with
    // nothing logged; under the offscreen platform, which has no input path at
    // all, the same build plays the full 21.5s. That points at a real event
    // rather than a logic fault. Nobody decides to skip inside the first
    // three-quarters of a second anyway, so the guard costs nothing and the
    // thing it protects is the entire opening.
    Timer {
        id: skipArm
        interval: 800
        running: true
        property bool armed: false
        onTriggered: armed = true
    }

    // Skip on any input while the sequence is running.
    MouseArea {
        anchors.fill: parent
        enabled: !root.ready && skipArm.armed
        onClicked: backdrop.skip()
    }

    Item {
        anchors.fill: parent
        focus: !root.ready
        Keys.onPressed: function(event) {
            if (!skipArm.armed)
                return
            backdrop.skip()
            event.accepted = true
        }
    }

    // The way out is the same storm the session will pick up. The moment the
    // password is accepted the panel fades away and the petal storm fades in
    // over everything; SDDM tears the greeter down around then, and the
    // session's reveal starts where this leaves off -- so the handoff is
    // petals to petals rather than petals to a black screen while the session
    // boots.
    Item {
        id: petalsLayer
        anchors.fill: parent
        opacity: root.authenticated ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: Theme.normal } }

        MediaPlayer {
            id: petalsPlayer
            source: "assets/video/petals.mp4"
            videoOutput: petalsSink
            loops: MediaPlayer.Infinite
        }

        VideoOutput {
            id: petalsSink
            anchors.fill: parent
            visible: false
            fillMode: VideoOutput.Stretch
        }

        ShaderEffectSource {
            id: petalsTex
            sourceItem: petalsSink
            anchors.fill: parent
            visible: false
            live: true
            hideSource: true
        }

        ShaderEffect {
            anchors.fill: parent
            fragmentShader: "shaders/petals.frag.qsb"
            property variant source: petalsTex
            property real progress: 0
            property real noiseScale: 7.0
            property real grain: 0.85
            // Sakura, not confetti: the petals that survive are their
            // white-hot cores, so push them back toward blossom pink.
            property real tintAmount: 0.85
            property vector4d tint: Qt.vector4d(1.0, 0.62, 0.82, 1.0)
            blending: true
        }
    }

    onAuthenticatedChanged: {
        if (root.authenticated)
            petalsPlayer.play()
    }

    Connections {
        target: root.sddmHost
        ignoreUnknownSignals: true
        function onLoginSucceeded() { root.authenticated = true }
        function onLoginFailed() { login.onFailed("Authentication failed") }
        function onInformationMessage(msg) { login.message = msg }
    }

    function resolveUser() {
        if (users) {
            if (users.lastUser && users.lastUser.length > 0)
                return users.lastUser
            if (users.count > 0) {
                var v = users.data(users.index(0, 0), Qt.UserRole + 1)
                if (v && v.length > 0)
                    return v
            }
        }
        return previewUser
    }

    // preview aid: lets the harness show the filled / enabled state
    function fillPassword(t) { login.setPassword(t) }

    onReadyChanged: if (ready) login.forceActiveFocus()
}
