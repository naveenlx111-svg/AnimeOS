import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The login panel.
//
// No box, but it does not float unguarded over the footage either -- a soft
// vertical scrim darkens the band the panel sits on, so the name, the line
// field and BANKAI stay legible when the sequence behind them is bright. The
// composition is bare: a name, a hairline, a field that is nothing but a
// line, and the Bankai as an underline rather than a button.
//
// SDDM injects `sddm`, `userModel`, `sessionModel` and `keyboard` as globals.
// They are taken as properties here rather than referenced directly so the
// theme can also run standalone under qmlscene with mocks -- otherwise the
// only way to see a change is to log out, which is a miserable way to iterate.
FocusScope {
    id: root

    property var sddmHost: null
    property var users: null
    property var sessions: null
    property var keyboardState: null

    property string userName: ""
    property int userIndex: 0
    property int sessionIndex: 0
    property string sessionName: ""
    property string message: ""
    property bool busy: false

    signal authAccepted()

    implicitWidth: 460
    implicitHeight: column.implicitHeight + 48

    function submit() {
        if (busy || password.text.length === 0)
            return
        busy = true
        message = ""
        if (sddmHost) {
            sddmHost.login(root.userName, password.text, root.sessionIndex)
            stuck.restart()
        } else {
            authAccepted()                  // standalone preview
        }
    }

    // If the host never answers -- which is exactly what happens under
    // --test-mode, where the greeter posts the login to a daemon socket with
    // nothing listening on it -- the action would otherwise sit on its busy
    // dots forever and the field would stay disabled, locking the user out of
    // their own login screen.
    //
    // The interval has to clear the delay PAM deliberately imposes on a WRONG
    // password, or this fires while a perfectly normal rejection is still in
    // flight and reports "no response" for something that is about to answer
    // "authentication failed" -- and the message visibly flips when the real
    // one lands. FAIL_DELAY is 3s on this machine, and pam_unix's own default
    // is 2s, so four seconds left only a second of margin. Ten is clear of
    // that and still recovers a wedged button long before anyone would start
    // hunting for a TTY; the wait is not a dead one, the button runs its dots
    // throughout.
    Timer {
        id: stuck
        interval: 10000
        onTriggered: root.onFailed("No response from the login service")
    }

    function onFailed(text) {
        stuck.stop()
        busy = false
        message = text || "Authentication failed"
        password.text = ""
        password.forceActiveFocus()
        shake.restart()
    }

    function setPassword(t) { password.text = t }

    function selectUser(i) {
        if (!users || users.count === 0)
            return
        userIndex = (i + users.count) % users.count
        var idx = users.index(userIndex, 0)
        userName = users.data(idx, Qt.UserRole + 1) || ""
        password.text = ""
        password.forceActiveFocus()
    }

    SequentialAnimation {
        id: shake
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to: -7; duration: 45 }
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to:  7; duration: 90 }
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to:  0; duration: 45 }
    }

    // The scrim: a soft vertical band behind the panel, transparent at the
    // edges and deepest behind the text. It is what keeps the name and the
    // field legible while the sequence plays on -- not a box, just enough dark
    // to sit on.
    Rectangle {
        id: scrim
        anchors.centerIn: parent
        width: 480
        height: 230
        radius: 26
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0, 0, 0, 0) }
            GradientStop { position: 0.5;
                color: Qt.rgba(Theme.abyss.r, Theme.abyss.g, Theme.abyss.b, 0.55) }
            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0) }
        }
    }

    ColumnLayout {
        id: column
        anchors.centerIn: parent
        spacing: 0

        // ------------------------------------------------------------ name

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 4
            spacing: 10

            GlyphButton {
                visible: root.users && root.users.count > 1
                implicitWidth: 24; implicitHeight: 24
                kind: "prev"
                tooltip: ""
                onClicked: root.selectUser(root.userIndex - 1)
            }

            Text {
                text: root.userName.toUpperCase()
                color: Theme.petalLight
                font.pixelSize: 15
                font.letterSpacing: 5
                horizontalAlignment: Text.AlignHCenter
            }

            GlyphButton {
                visible: root.users && root.users.count > 1
                implicitWidth: 24; implicitHeight: 24
                kind: "next"
                tooltip: ""
                onClicked: root.selectUser(root.userIndex + 1)
            }
        }

        // ------------------------------------------------------- hairline

        // A blade edge, not a divider: one faint horizontal stroke that tells
        // the eye where the field begins before the field itself is focused.
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 22
            width: 210
            height: 1
            color: Qt.rgba(Theme.rim.r, Theme.rim.g, Theme.rim.b, 0.28)
        }

        // ------------------------------------------------------- password

        TextField {
            id: password
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 16
            Layout.preferredWidth: 320
            Layout.preferredHeight: 36
            focus: true
            echoMode: TextInput.Password
            passwordCharacter: "\u2022"
            placeholderText: "password"
            placeholderTextColor: Qt.rgba(Theme.muted.r, Theme.muted.g, Theme.muted.b, 0.4)
            color: Theme.petalLight
            font.pixelSize: 16
            font.letterSpacing: 1
            selectionColor: Theme.glow
            selectedTextColor: Theme.night
            enabled: !root.busy
            horizontalAlignment: TextInput.AlignHCenter

            // The field is just a line. At rest it is a cool blade edge, quiet
            // enough to sit over the petals; focused it becomes the one petal
            // accent on the screen and grows out from the middle.
            background: Rectangle {
                color: "transparent"
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: password.activeFocus ? parent.width : parent.width * 0.55
                    height: 2
                    radius: 1
                    color: password.activeFocus
                           ? Theme.glow
                           : Qt.rgba(Theme.rim.r, Theme.rim.g, Theme.rim.b, 0.30)
                    Behavior on width { NumberAnimation { duration: Theme.normal } }
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                }
            }

            Keys.onReturnPressed: root.submit()
            Keys.onEnterPressed: root.submit()
        }

        // Caps lock keeps its height whether or not it is showing. It used to
        // appear and disappear inside a layout, which moved the action under
        // the cursor at the exact moment someone was reaching for it.
        Text {
            Layout.fillWidth: true
            Layout.topMargin: 8
            Layout.preferredHeight: 13
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            text: "caps lock is on"
            color: Theme.petalLight
            font.pixelSize: 11
            font.letterSpacing: 1.4
            opacity: (root.keyboardState && root.keyboardState.capsLock) ? 0.8 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        }

        // ----------------------------------------------------------- bankai

        Button {
            id: go
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 18
            Layout.preferredWidth: 170
            Layout.preferredHeight: 44
            enabled: !root.busy && password.text.length > 0

            // An action, not a button: letter-spaced type with an underline
            // that only shows when it is worth reaching for. Busy is the same
            // three dots as before, running under where the word was.
            contentItem: Item {
                Text {
                    id: goText
                    anchors.centerIn: parent
                    text: "BANKAI"
                    color: go.enabled ? Theme.petalLight : Theme.muted
                    font.pixelSize: 14
                    font.bold: true
                    font.letterSpacing: 6
                    opacity: root.busy ? 0 : (go.enabled ? 1 : 0.45)
                    Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                }

                Rectangle {
                    anchors.horizontalCenter: goText.horizontalCenter
                    anchors.top: goText.bottom
                    anchors.topMargin: 7
                    width: goText.width
                    height: 1
                    color: Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.85)
                    opacity: (go.hovered || go.activeFocus) && go.enabled ? 0.9 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                }

                Row {
                    anchors.centerIn: parent
                    spacing: 6
                    opacity: root.busy ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.fast } }

                    Repeater {
                        model: 3
                        Rectangle {
                            required property int index
                            width: 4; height: 4; radius: 2
                            color: Theme.petalLight
                            opacity: 0.25
                            SequentialAnimation on opacity {
                                running: root.busy
                                loops: Animation.Infinite
                                PauseAnimation { duration: index * 150 }
                                NumberAnimation { to: 1.0; duration: 220 }
                                NumberAnimation { to: 0.25; duration: 220 }
                                PauseAnimation { duration: (2 - index) * 150 }
                            }
                        }
                    }
                }
            }

            background: Rectangle { color: "transparent" }
            onClicked: root.submit()
        }

        // Two lines held open. A failure message that grows the composition
        // moves the field it is about, which is the wrong thing to do to
        // someone who has just been told to type it again.
        Text {
            Layout.fillWidth: true
            Layout.topMargin: 8
            Layout.preferredHeight: 30
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignTop
            text: root.message
            color: Theme.danger
            font.pixelSize: 12
            font.letterSpacing: 0.4
            wrapMode: Text.WordWrap
            opacity: root.message.length > 0 ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.normal } }
        }
    }
}
