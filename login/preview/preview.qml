import QtQuick
import QtQuick.Window
import "../senbonzakura"

// Standalone harness: runs the greeter with mock SDDM objects so the theme
// can be iterated without logging out.
Window {
    width: 1920; height: 1080
    visible: true
    title: "Senbonzakura greeter preview"
    color: "black"

    Loader {
        anchors.fill: parent
        source: "../senbonzakura/Main.qml"
    }
}
