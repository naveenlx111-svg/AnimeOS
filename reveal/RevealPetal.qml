import QtQuick

// One petal on the clearing sweep.
//
// It travels outward from the centre while growing, which is what a petal
// passing the camera actually does -- the storm does not fade out in place,
// it rushes past you and is gone.
Item {
    id: p

    property real angle: 0          // radians, direction of travel
    property real startR: 0         // starting distance from centre
    property real endR: 1400
    property real startScale: 0.5
    property real endScale: 2.6
    property real spin: 180
    property int  delay: 0
    property int  span: 1600
    property real hold: 0.25        // fraction of span spent at full opacity

    property real t: 0              // 0 -> 1 over the sweep

    readonly property real r: startR + (endR - startR) * (t * t * 0.7 + t * 0.3)

    width: 26; height: 52
    x: parent.width  / 2 + Math.cos(angle) * r - width  / 2
    y: parent.height / 2 + Math.sin(angle) * r - height / 2
    scale: startScale + (endScale - startScale) * t
    rotation: spin * t
    opacity: t < hold ? 1.0 : Math.max(0, 1 - (t - hold) / (1 - hold))

    property int variant: Math.floor(Math.random() * 5)

    Image {
        anchors.fill: parent
        source: "../login/senbonzakura/assets/vectors/petal-" +
                ["a", "b", "c", "d", "e"][p.variant] + ".svg"
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        sourceSize.width: 100
        sourceSize.height: 200
    }

    NumberAnimation on t {
        from: 0; to: 1
        duration: p.span
        easing.type: Easing.InCubic
        running: true
    }
}
