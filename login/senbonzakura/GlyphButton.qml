import QtQuick

// Small circular icon button for the session / power row.
//
// Icons are drawn with Canvas rather than a font glyph: the greeter runs
// before any user fontconfig is loaded, so an icon font is not something we
// can rely on being present.
Item {
    id: root

    property string kind: "power"        // power | restart | sleep | session
    property string tooltip: ""
    property bool active: false
    signal clicked()

    implicitWidth: 38
    implicitHeight: 38

    Rectangle {
        id: disc
        anchors.fill: parent
        radius: width / 2
        color: mouse.pressed ? Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.30)
             : (mouse.containsMouse || root.active)
               ? Qt.rgba(Theme.glow.r, Theme.glow.g, Theme.glow.b, 0.14)
               : "transparent"
        border.width: 1
        border.color: (mouse.containsMouse || root.active)
                      ? Qt.rgba(Theme.petalFill.r, Theme.petalFill.g, Theme.petalFill.b, 0.55)
                      : Qt.rgba(Theme.petalFill.r, Theme.petalFill.g, Theme.petalFill.b, 0.18)
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
    }

    Canvas {
        id: icon
        anchors.centerIn: parent
        width: 18
        height: 18
        antialiasing: true

        property color stroke: (mouse.containsMouse || root.active)
                               ? Theme.petalLight : Theme.muted
        onStrokeChanged: requestPaint()

        onPaint: {
            var c = getContext("2d")
            c.reset()
            c.strokeStyle = stroke
            c.lineWidth = 1.6
            c.lineCap = "round"
            var cx = width / 2, cy = height / 2, r = width * 0.36

            if (root.kind === "power" || root.kind === "restart") {
                // open arc with a gap at the top
                var gap = root.kind === "power" ? 0.42 : 0.9
                c.beginPath()
                c.arc(cx, cy, r, -Math.PI / 2 + gap, -Math.PI / 2 - gap + Math.PI * 2)
                c.stroke()
                if (root.kind === "power") {
                    c.beginPath()
                    c.moveTo(cx, cy - r - 1)
                    c.lineTo(cx, cy - 1)
                    c.stroke()
                } else {
                    // arrow head on the arc, marking it as a cycle
                    c.beginPath()
                    c.moveTo(cx + r - 3, cy - r + 1)
                    c.lineTo(cx + r + 2, cy - r + 2)
                    c.lineTo(cx + r, cy - r + 6)
                    c.stroke()
                }
            } else if (root.kind === "sleep") {
                // crescent
                c.beginPath()
                c.arc(cx + 1, cy, r, Math.PI * 0.35, Math.PI * 1.55)
                c.stroke()
            } else {
                // session: three stacked lines
                for (var i = -1; i <= 1; i++) {
                    c.beginPath()
                    c.moveTo(cx - r, cy + i * 5)
                    c.lineTo(cx + r, cy + i * 5)
                    c.stroke()
                }
            }
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.bottom
        anchors.topMargin: 6
        text: root.tooltip
        color: Theme.muted
        font.pixelSize: 10
        font.letterSpacing: 1.2
        opacity: mouse.containsMouse ? 0.8 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
    }
}
