import QtQuick

// Stand-ins for the objects SDDM injects, so the theme can be driven
// outside a real greeter session.
QtObject {
    id: mocks

    property QtObject users: QtObject {
        property int count: 1
        property string lastUser: "naveen"
    }

    property ListModel sessions: ListModel {
        ListElement { name: "Plasma (Wayland)" }
        ListElement { name: "Plasma (X11)" }
        ListElement { name: "Hyprland" }
    }

    property QtObject keyboardState: QtObject {
        property bool capsLock: false
        property bool numLock: true
    }

    property QtObject host: QtObject {
        property bool canPowerOff: true
        property bool canReboot: true
        property bool canSuspend: true
        function login(u, p, s) { console.log("mock login:", u, "session", s) }
        function powerOff() { console.log("mock powerOff") }
        function reboot() { console.log("mock reboot") }
        function suspend() { console.log("mock suspend") }
    }
}
