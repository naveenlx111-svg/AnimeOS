import QtQuick 2.15

Item {
    id: petal

    property real fallSpeed: 1.0
    property real drift: 30
    property real rotationSpeed: 2

    width: 22
    height: 16

    rotation: 25

    Rectangle {
        anchors.centerIn: parent

        width: 18
        height: 12

        color: "#f4b6c8"

        radius: width * 0.45

        rotation: 45
    }

    NumberAnimation on y {
        from: -30
        to: 1150

        duration: 8000 / petal.fallSpeed

        loops: Animation.Infinite
    }

    NumberAnimation on rotation {
        from: 0
        to: 360

        duration: 5000 / petal.rotationSpeed

        loops: Animation.Infinite
    }
}
