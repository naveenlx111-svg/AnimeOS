import QtQuick
import QtQuick.Window

// AnimeOS - desktop reveal.
//
// Runs once at session start, on top of the real desktop. The greeter cannot
// do this: SDDM tears the greeter down before the session exists, so there is
// no moment inside it where the desktop is behind the petals. Doing it here
// means the reveal is genuine compositing over whatever is actually on screen,
// not a pre-rendered guess at what the desktop looks like.
Window {
    id: win

    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint
           | Qt.WindowStaysOnTopHint
           | Qt.Tool
           | Qt.WindowTransparentForInput      // never swallow the user's clicks
    visibility: Window.FullScreen

    property int petalCount: 190
    property int sweepMs: 1700
    property int veilMs: 850

    // The veil starts as the tail of the greeter's storm and lifts, so the
    // session does not simply pop into existence.
    Rectangle {
        id: veil
        anchors.fill: parent
        color: "#08030b"
        opacity: 1
        NumberAnimation on opacity {
            from: 1; to: 0
            duration: win.veilMs
            easing.type: Easing.OutCubic
            running: true
        }
    }

    Repeater {
        model: win.petalCount
        RevealPetal {
            anchors.fill: undefined
            parent: win.contentItem
            angle: Math.random() * Math.PI * 2
            startR: Math.random() * 240
            endR: 900 + Math.random() * 1100
            startScale: 0.35 + Math.random() * 0.7
            endScale: 1.8 + Math.random() * 2.4
            spin: (Math.random() < 0.5 ? -1 : 1) * (90 + Math.random() * 260)
            span: win.sweepMs * (0.7 + Math.random() * 0.6)
            hold: 0.15 + Math.random() * 0.3
        }
    }

    // Quit once the longest petal has cleared, plus a beat. Leaving an
    // always-on-top window alive after the animation would be worse than not
    // having the animation at all.
    Timer {
        interval: win.sweepMs * 1.4 + 400
        running: true
        onTriggered: Qt.quit()
    }
}
