import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The login panel.
//
// SDDM injects `sddm`, `userModel` and `sessionModel` as globals. They are
// taken as properties here instead of referenced directly so the theme can
// also be run standalone under qmlscene with mocks -- otherwise the only way
// to see a change is to log out, which is a miserable way to iterate.
FocusScope {
    id: root

    property var sddmHost: null
    property var users: null
    property var sessions: null

    property string userName: ""
    property int sessionIndex: 0
    property string message: ""
    property bool busy: false

    signal authAccepted()

    implicitWidth: Theme.panelWidth
    implicitHeight: column.implicitHeight + 56

    function submit() {
        if (busy || password.text.length === 0)
            return
        busy = true
        message = ""
        if (sddmHost)
            sddmHost.login(root.userName, password.text, root.sessionIndex)
        else
            authAccepted()          // standalone preview
    }

    function onFailed(text) {
        busy = false
        message = text || "Authentication failed"
        password.text = ""
        password.forceActiveFocus()
        shake.restart()
    }

    Rectangle {
        id: panel
        anchors.fill: parent
        radius: Theme.radius
        color: Qt.rgba(Theme.panel.r, Theme.panel.g, Theme.panel.b, 0.82)
        border.color: Qt.rgba(Theme.petalFill.r, Theme.petalFill.g,
                              Theme.petalFill.b, root.busy ? 0.9 : 0.42)
        border.width: 1

        Behavior on border.color { ColorAnimation { duration: Theme.normal } }

        // A single soft edge light rather than a drop shadow: it matches the
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
        NumberAnimation { target: root; property: "x"; to: root.x - 9; duration: 45 }
        NumberAnimation { target: root; property: "x"; to: root.x + 9; duration: 90 }
        NumberAnimation { target: root; property: "x"; to: root.x;     duration: 45 }
    }

    ColumnLayout {
        id: column
        anchors.centerIn: parent
        width: parent.width - 56
        spacing: 16

        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: root.userName
            color: Theme.petalLight
            font.pixelSize: 26
            font.letterSpacing: 1.5
            elide: Text.ElideRight
        }

        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "Kuchiki Byakuya awaits"
            color: Theme.muted
            font.pixelSize: 12
            font.letterSpacing: 2.4
            opacity: 0.65
        }

        Item { Layout.preferredHeight: 4 }

        TextField {
            id: password
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            focus: true
            echoMode: TextInput.Password
            passwordCharacter: "•"
            placeholderText: "password"
            placeholderTextColor: Qt.rgba(Theme.muted.r, Theme.muted.g, Theme.muted.b, 0.5)
            color: Theme.petalLight
            font.pixelSize: 16
            selectionColor: Theme.glow
            selectedTextColor: Theme.night
            enabled: !root.busy
            horizontalAlignment: TextInput.AlignHCenter

            background: Rectangle {
                radius: 9
                color: Qt.rgba(0, 0, 0, 0.35)
                border.width: 1
                border.color: password.activeFocus
                              ? Theme.glow
                              : Qt.rgba(Theme.petalFill.r, Theme.petalFill.g,
                                        Theme.petalFill.b, 0.3)
                Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            }

            Keys.onReturnPressed: root.submit()
            Keys.onEnterPressed: root.submit()
        }

        Button {
            id: go
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            enabled: !root.busy && password.text.length > 0
            text: root.busy ? "—" : "BANKAI"

            contentItem: Text {
                text: go.text
                color: go.enabled ? Theme.petalLight : Theme.muted
                font.pixelSize: 15
                font.bold: true
                font.letterSpacing: 4
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                opacity: go.enabled ? 1.0 : 0.4
            }

            background: Rectangle {
                radius: 9
                color: go.pressed ? Theme.deep
                     : go.hovered ? Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.32)
                                  : Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.16)
                border.width: 1
                border.color: Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b,
                                      go.enabled ? 0.75 : 0.2)
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
            opacity: root.message.length > 0 ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: Theme.normal } }
        }
    }
}
