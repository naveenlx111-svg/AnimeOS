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
    // --test-mode -- the button would otherwise sit on its busy dash forever
    // and the field would stay disabled, locking the user out of their own
    // login screen.
    Timer {
        id: stuck
        interval: 12000
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
        color: Qt.rgba(Theme.panel.r, Theme.panel.g, Theme.panel.b, 0.84)
        border.width: 1
        border.color: Qt.rgba(Theme.petalFill.r, Theme.petalFill.g,
                              Theme.petalFill.b, root.busy ? 0.9 : 0.4)
        Behavior on border.color { ColorAnimation { duration: Theme.normal } }

        // A single soft inner edge rather than a drop shadow: it matches the
        // way the blades in the footage read, which is all rim and no body.
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(Theme.petalLight.r, Theme.petalLight.g,
                                  Theme.petalLight.b, 0.07)
        }
    }

    SequentialAnimation {
        id: shake
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to: -9; duration: 45 }
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to:  9; duration: 90 }
        NumberAnimation { target: root; property: "anchors.horizontalCenterOffset"; to:  0; duration: 45 }
    }

    ColumnLayout {
        id: column
        anchors.centerIn: parent
        width: parent.width - 72
        spacing: 14

        // ------------------------------------------------------- identity

        Item {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 74
            Layout.preferredHeight: 74

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.10)
                border.width: 1
                border.color: Qt.rgba(Theme.petalFill.r, Theme.petalFill.g,
                                      Theme.petalFill.b, 0.45)
            }

            Text {
                anchors.centerIn: parent
                text: root.userName.length > 0 ? root.userName.charAt(0).toUpperCase() : "?"
                color: Theme.petalLight
                font.pixelSize: 30
                font.bold: true
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10

            GlyphButton {
                visible: root.users && root.users.count > 1
                implicitWidth: 24; implicitHeight: 24
                kind: "session"
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
                implicitWidth: 24; implicitHeight: 24
                kind: "session"
                onClicked: root.selectUser(root.userIndex + 1)
            }
        }

        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "Kuchiki Byakuya awaits"
            color: Theme.muted
            font.pixelSize: 11
            font.letterSpacing: 2.6
            opacity: 0.6
        }

        Item { Layout.preferredHeight: 2 }

        // ------------------------------------------------------- password

        TextField {
            id: password
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            focus: true
            echoMode: TextInput.Password
            passwordCharacter: "•"
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
                color: Qt.rgba(0, 0, 0, 0.38)
                border.width: 1
                border.color: password.activeFocus
                              ? Theme.glow
                              : Qt.rgba(Theme.petalFill.r, Theme.petalFill.g,
                                        Theme.petalFill.b, 0.28)
                Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            }

            Keys.onReturnPressed: root.submit()
            Keys.onEnterPressed: root.submit()
        }

        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "caps lock is on"
            color: Theme.petalFill
            font.pixelSize: 11
            font.letterSpacing: 1.4
            opacity: (root.keyboardState && root.keyboardState.capsLock) ? 0.85 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        }

        Button {
            id: go
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            enabled: !root.busy && password.text.length > 0
            text: root.busy ? "—" : "BANKAI"

            contentItem: Text {
                text: go.text
                color: go.enabled ? Theme.petalLight : Theme.muted
                font.pixelSize: 15
                font.bold: true
                font.letterSpacing: 4.5
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                opacity: go.enabled ? 1.0 : 0.4
            }

            background: Rectangle {
                radius: 9
                color: go.pressed ? Theme.deep
                     : go.hovered ? Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.34)
                                  : Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.16)
                border.width: 1
                border.color: Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b,
                                      go.enabled ? 0.75 : 0.18)
                Behavior on color { ColorAnimation { duration: Theme.fast } }
            }

            onClicked: root.submit()
        }

        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: root.message
            color: Theme.danger
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            opacity: root.message.length > 0 ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.normal } }
        }
    }
}
