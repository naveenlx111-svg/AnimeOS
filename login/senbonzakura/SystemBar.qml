import QtQuick
import QtQuick.Controls

// Session picker and power controls, along the bottom edge.
//
// Deliberately kept off the panel: they are used rarely, and putting them
// inside the panel would crowd the one thing the screen is actually for.
Item {
    id: root

    property var sddmHost: null
    property var sessions: null
    property alias sessionIndex: sessionList.currentIndex
    property string sessionLabel: ""

    // Show the session that is actually selected rather than a placeholder.
    // SDDM restores lastIndex, so this is whatever the user booted into last.
    function syncLabel() {
        if (!sessions || sessions.count === 0) {
            sessionLabel = "session"
            return
        }
        var i = Math.max(0, Math.min(sessionList.currentIndex, sessions.count - 1))
        var v = sessions.get ? sessions.get(i)
                             : sessions.data(sessions.index(i, 0), Qt.UserRole + 4)
        sessionLabel = (v && v.name !== undefined) ? v.name : (v || "session")
    }

    Component.onCompleted: {
        if (sessions && sessions.lastIndex !== undefined)
            sessionList.currentIndex = sessions.lastIndex
        syncLabel()
    }
    onSessionsChanged: syncLabel()

    height: 60

    // ------------------------------------------------------------ session

    Row {
        id: sessionRow
        anchors.left: parent.left
        anchors.leftMargin: 46
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        GlyphButton {
            kind: "session"
            tooltip: "session"
            active: sessionPopup.visible
            onClicked: sessionPopup.visible ? sessionPopup.close() : sessionPopup.open()
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.sessionLabel
            color: Theme.muted
            font.pixelSize: 12
            font.letterSpacing: 1.4
            opacity: 0.75
        }
    }

    Popup {
        id: sessionPopup
        x: 46
        y: -implicitHeight - 8
        width: 260
        implicitHeight: Math.min(240, sessionList.contentHeight + 16)
        padding: 8

        background: Rectangle {
            radius: Theme.radius
            color: Qt.rgba(Theme.panel.r, Theme.panel.g, Theme.panel.b, 0.96)
            border.width: 1
            border.color: Qt.rgba(Theme.petalFill.r, Theme.petalFill.g,
                                  Theme.petalFill.b, 0.4)
        }

        ListView {
            id: sessionList
            anchors.fill: parent
            clip: true
            model: root.sessions
            currentIndex: 0

            delegate: ItemDelegate {
                required property int index
                required property string name
                width: sessionList.width
                height: 34

                contentItem: Text {
                    text: parent.name
                    color: index === sessionList.currentIndex
                           ? Theme.petalLight : Theme.muted
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 10
                }

                background: Rectangle {
                    radius: 7
                    color: parent.hovered
                           ? Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.16)
                           : "transparent"
                }

                onClicked: {
                    sessionList.currentIndex = index
                    root.sessionLabel = name
                    sessionPopup.close()
                }
            }
        }
    }

    // -------------------------------------------------------------- power

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 46
        anchors.verticalCenter: parent.verticalCenter
        spacing: 14

        GlyphButton {
            kind: "sleep"
            tooltip: "suspend"
            visible: !root.sddmHost || root.sddmHost.canSuspend
            onClicked: if (root.sddmHost) root.sddmHost.suspend()
        }

        GlyphButton {
            kind: "restart"
            tooltip: "restart"
            visible: !root.sddmHost || root.sddmHost.canReboot
            onClicked: if (root.sddmHost) root.sddmHost.reboot()
        }

        GlyphButton {
            kind: "power"
            tooltip: "shut down"
            visible: !root.sddmHost || root.sddmHost.canPowerOff
            onClicked: if (root.sddmHost) root.sddmHost.powerOff()
        }
    }
}
