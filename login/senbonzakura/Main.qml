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

        // SDDM supplies the last user; standalone previews fall back to
        // previewUser so the panel is never blank while iterating.
        userName: (root.users && root.users.lastUser)
                  ? root.users.lastUser
                  : root.previewUser

        sessionIndex: root.sessions ? root.sessions.lastIndex : 0

        visible: opacity > 0
        opacity: (root.ready && !root.authenticated) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.slow } }

        onAuthAccepted: root.authenticated = true
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

    onReadyChanged: if (ready) login.forceActiveFocus()
}
