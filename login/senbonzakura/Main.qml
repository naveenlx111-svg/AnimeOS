pragma ComponentBehavior: Bound

import QtQuick 2.15

Rectangle {
    id: root

    width: 1920
    height: 1080

    color: "#08030b"

    // ============================================================
    // DISTANT PARTICLES
    // ============================================================

    Repeater {
        model: 25

        Petal {
            x: Math.random() * root.width
            y: Math.random() * root.height

            petalScale: 0.25 + Math.random() * 0.35
            petalOpacity: 0.15 + Math.random() * 0.35

            fallSpeed: 0.35 + Math.random() * 0.45
            driftAmount: 15 + Math.random() * 30
            driftSpeed: 0.3 + Math.random() * 0.7
            rotationSpeed: 40 + Math.random() * 100

            glowAmount: 0.15
        }
    }

    // ============================================================
    // MAIN PARTICLES
    // ============================================================

    Repeater {
        model: 35

        Petal {
            x: Math.random() * root.width
            y: Math.random() * root.height

            petalScale: 0.45 + Math.random() * 0.65
            petalOpacity: 0.45 + Math.random() * 0.5

            fallSpeed: 0.55 + Math.random() * 0.9
            driftAmount: 25 + Math.random() * 60
            driftSpeed: 0.5 + Math.random() * 1.1
            rotationSpeed: 70 + Math.random() * 150

            glowAmount: 0.28 + Math.random() * 0.15
        }
    }

    // ============================================================
    // FOREGROUND PARTICLES
    // ============================================================

    Repeater {
        model: 10

        Petal {
            x: Math.random() * root.width
            y: Math.random() * root.height

            petalScale: 0.9 + Math.random() * 0.8
            petalOpacity: 0.65 + Math.random() * 0.3

            fallSpeed: 0.8 + Math.random() * 1.2
            driftAmount: 40 + Math.random() * 80
            driftSpeed: 0.7 + Math.random() * 1.3
            rotationSpeed: 100 + Math.random() * 180

            glowAmount: 0.35
        }
    }

    // ============================================================
    // TEMPORARY TITLE
    // ============================================================

    Text {
        anchors.centerIn: parent

        text: "ANIMEOS"

        color: "#ffffff"

        font.pixelSize: 64
        font.bold: true

        opacity: 0.85
    }
}
