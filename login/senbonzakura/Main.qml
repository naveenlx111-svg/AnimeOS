import QtQuick
import QtQuick.Controls

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

    PetalField {
        anchors.fill: parent
        active: root.ready && !root.authenticated
        opacity: root.ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }
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

        // SDDM supplies the last user; standalone previews fall back to
        // previewUser so the panel is never blank while iterating.
        userName: (root.users && root.users.lastUser)
                  ? root.users.lastUser
                  : root.previewUser

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

    // Skip on any input while the sequence is running.
    MouseArea {
        anchors.fill: parent
        enabled: !root.ready
        onClicked: backdrop.skip()
    }

    Item {
        anchors.fill: parent
        focus: !root.ready
        Keys.onPressed: function(event) {
            backdrop.skip()
            event.accepted = true
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "black"
        opacity: root.authenticated ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }
    }

    Connections {
        target: root.sddmHost
        ignoreUnknownSignals: true
        function onLoginSucceeded() { root.authenticated = true }
        function onLoginFailed() { login.onFailed("Authentication failed") }
        function onInformationMessage(msg) { login.message = msg }
    }

    // preview aid: lets the harness show the filled / enabled state
    function fillPassword(t) { login.setPassword(t) }

    onReadyChanged: if (ready) login.forceActiveFocus()
}
