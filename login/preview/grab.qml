import QtQuick
import QtQuick.Window

// Offscreen screenshot harness.
//
// grabToImage cannot capture a VideoOutput scene-graph node, so the backdrop
// is swapped for a still frame taken from the same footage. Everything above
// it -- panel, petals, vignette -- is the real thing.
Window {
    width: 1920; height: 1080
    visible: true
    color: "black"

    property string still: "../../shots/shot03_swords/plate/0040.png"
    property string outFile: "/var/tmp/greeter_login.png"

    Loader {
        id: loader
        anchors.fill: parent
        source: "../senbonzakura/Main.qml"
        onLoaded: {
            item.previewUser = "naveen"
            item.backdropItem.stillOverride = still
            item.ready = true
        }
    }

    Timer {
        interval: 2600; running: true
        onTriggered: loader.grabToImage(function(res) {
            res.saveToFile(outFile)
            Qt.callLater(Qt.quit)
        }, Qt.size(1920, 1080))
    }
}
