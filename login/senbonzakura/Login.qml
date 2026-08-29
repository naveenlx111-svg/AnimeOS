import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The login panel.
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
    implicitHeight: column.implicitHeight + 64

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
    // nothing listening on it -- the button would otherwise sit on its busy
    // dash forever and the field would stay disabled, locking the user out of
    // their own login screen.
    //
    // Four seconds, not twelve. Twelve was chosen as a generous ceiling for a
    // slow PAM stack, but it is far past the point where a dead button has
    // already been read as broken: nothing comes back, so the only thing the
    // wait buys is the user pressing Enter again into a disabled field.
    Timer {
        id: stuck
        interval: 4000
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

    // ---------------------------------------------------------------- panel

    Rectangle {
        id: panel
        anchors.fill: parent
        radius: Theme.radius
        border.width: 1
        // Blade, not petal. The panel has to keep its shape while a full-frame
        // magenta wash passes behind it, and a pink edge disappears into that.
        border.color: Qt.rgba(Theme.rim.r, Theme.rim.g, Theme.rim.b,
                              root.busy ? 0.75 : 0.34)
        Behavior on border.color { ColorAnimation { duration: Theme.normal } }

        // Denser at the bottom, so the panel sits into the dark rather than
        // floating on it.
        gradient: Gradient {
            GradientStop { position: 0.0
                color: Qt.rgba(Theme.panel.r, Theme.panel.g, Theme.panel.b, 0.80) }
            GradientStop { position: 1.0
                color: Qt.rgba(Theme.abyss.r, Theme.abyss.g, Theme.abyss.b, 0.90) }
        }

        // A single soft inner edge rather than a drop shadow: it matches the
        // way the blades in the footage read, which is all rim and no body.
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(Theme.blade.r, Theme.blade.g, Theme.blade.b, 0.08)
        }

        // The lit top edge every blade in the sequence has.
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top }
            anchors.margins: Theme.radius
            height: 1
            color: Qt.rgba(Theme.blade.r, Theme.blade.g, Theme.blade.b, 0.22)
        }
    }

    SequentialAnimation {
        id: shake
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to: -9; duration: 45 }
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to:  9; duration: 90 }
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to:  0; duration: 45 }
    }

    // Spacing is set per item rather than by one uniform gap, so the panel
    // reads as three groups -- who you are, where you type, what happened --
    // instead of an evenly spaced list of six unrelated things.
    ColumnLayout {
        id: column
        anchors.centerIn: parent
        width: parent.width - 72
        spacing: 0

        // ------------------------------------------------------- identity

        // This replaces the initial-in-a-circle that used to sit here. That
        // circle repeated the username directly under it and said nothing
        // else, and stacking it above the mark would have pushed the field
        // off the panel's centre. On a machine with one account an avatar is
        // decoration either way, so it may as well be the right decoration.
        ByakuyaMark {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 112
            Layout.preferredHeight: 129
            opacity: root.busy ? 0.55 : 1.0
            Behavior on opacity { NumberAnimation { duration: Theme.normal } }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 4
            spacing: 8

            GlyphButton {
                visible: root.users && root.users.count > 1
                implicitWidth: 26; implicitHeight: 26
                kind: "prev"
                tooltip: ""
                onClicked: root.selectUser(root.userIndex - 1)
            }

            Text {
                text: root.userName
                color: Theme.petalLight
                font.pixelSize: 25
                font.letterSpacing: 1.4
                horizontalAlignment: Text.AlignHCenter
            }

            GlyphButton {
                visible: root.users && root.users.count > 1
                implicitWidth: 26; implicitHeight: 26
                kind: "next"
                tooltip: ""
                onClicked: root.selectUser(root.userIndex + 1)
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.topMargin: 4
            horizontalAlignment: Text.AlignHCenter
            text: "SENBONZAKURA KAGEYOSHI"
            color: Theme.muted
            font.pixelSize: 11
            font.letterSpacing: 2.6
            opacity: 0.6
        }

        // ------------------------------------------------------- password

        TextField {
            id: password
            Layout.fillWidth: true
            Layout.topMargin: 22
            Layout.preferredHeight: 46
            focus: true
            echoMode: TextInput.Password
            passwordCharacter: "\u2022"
            placeholderText: "password"
            placeholderTextColor: Qt.rgba(Theme.muted.r, Theme.muted.g, Theme.muted.b, 0.45)
            color: Theme.petalLight
            font.pixelSize: 16
            selectionColor: Theme.glow
            selectedTextColor: Theme.night
            enabled: !root.busy
            horizontalAlignment: TextInput.AlignHCenter

            background: Rectangle {
                radius: 9
                color: Qt.rgba(Theme.abyss.r, Theme.abyss.g, Theme.abyss.b, 0.62)
                border.width: 1
                // Resting state is blade; focus is the one moment the petal
                // colour is worth spending, because it marks where to type.
                border.color: password.activeFocus
                              ? Theme.glow
                              : Qt.rgba(Theme.rim.r, Theme.rim.g, Theme.rim.b, 0.26)
                Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            }

            Keys.onReturnPressed: root.submit()
            Keys.onEnterPressed: root.submit()
        }

        // Caps lock keeps its height whether or not it is showing. It used to
        // appear and disappear inside a layout, which moved the button under
        // the cursor at the exact moment someone was reaching for it.
        Text {
            Layout.fillWidth: true
            Layout.topMargin: 7
            Layout.preferredHeight: 13
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            text: "caps lock is on"
            // Advisory, not an accent and not a failure: warm enough to catch
            // the eye without claiming the petal colour, which on this panel
            // means "this is the thing to act on".
            color: Theme.petalLight
            font.pixelSize: 11
            font.letterSpacing: 1.4
            opacity: (root.keyboardState && root.keyboardState.capsLock) ? 0.8 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        }

        Button {
            id: go
            Layout.fillWidth: true
            Layout.topMargin: 7
            Layout.preferredHeight: 44
            enabled: !root.busy && password.text.length > 0

            // Busy is three dots running, not a dash. A dash reads as an
            // em-rule someone left in the string, and the button also has to
            // stop looking disabled while it waits -- it is working, and the
            // disabled treatment says the opposite.
            contentItem: Item {
                Text {
                    anchors.centerIn: parent
                    text: "BANKAI"
                    color: go.enabled ? Theme.petalLight : Theme.muted
                    font.pixelSize: 15
                    font.bold: true
                    font.letterSpacing: 4.5
                    opacity: root.busy ? 0 : (go.enabled ? 1.0 : 0.4)
                    Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                }

                Row {
                    anchors.centerIn: parent
                    spacing: 7
                    opacity: root.busy ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.fast } }

                    Repeater {
                        model: 3
                        Rectangle {
                            required property int index
                            width: 5; height: 5; radius: 2.5
                            color: Theme.petalLight
                            opacity: 0.25
                            SequentialAnimation on opacity {
                                running: root.busy
                                loops: Animation.Infinite
                                PauseAnimation { duration: index * 170 }
                                NumberAnimation { to: 1.0; duration: 230 }
                                NumberAnimation { to: 0.25; duration: 230 }
                                PauseAnimation { duration: (2 - index) * 170 }
                            }
                        }
                    }
                }
            }

            background: Rectangle {
                radius: 9
                color: go.pressed ? Theme.deep
                     : (go.hovered || root.busy)
                       ? Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.34)
                       : Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.16)
                border.width: 1
                border.color: Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b,
                                      (go.enabled || root.busy) ? 0.75 : 0.18)
                Behavior on color { ColorAnimation { duration: Theme.fast } }
                Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            }

            onClicked: root.submit()
        }

        // Two lines held open. A failure message that grows the panel moves
        // the field it is about, which is the wrong thing to do to someone
        // who has just been told to type it again.
        Text {
            Layout.fillWidth: true
            Layout.topMargin: 9
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
