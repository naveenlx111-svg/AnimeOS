import QtQuick 2.15

Rectangle {
    id: root

    width: 1920
    height: 1080

    color: "#000000"

    Repeater {
        model: 30

        Petal {
            x: Math.random() * root.width
            y: Math.random() * root.height

            fallSpeed: 0.6 + Math.random() * 1.2
            rotationSpeed: 0.5 + Math.random() * 2
        }
    }

    Text {
        anchors.centerIn: parent

        text: "ANIMEOS"

        color: "white"

        font.pixelSize: 64
        font.bold: true
    }
}
