import QtQuick

// The drifting petal field. Kept sparse on purpose: the footage behind it is
// already the hero, and a dense swarm here would fight the panel for
// attention. Three depth bands give parallax without a particle system.
Item {
    id: field
    property bool active: true

    Repeater {
        model: field.active ? 22 : 0
        Petal {
            x: Math.random() * field.width
            y: Math.random() * field.height
            petalScale: 0.22 + Math.random() * 0.3
            petalOpacity: 0.10 + Math.random() * 0.22
            fallSpeed: 0.30 + Math.random() * 0.4
            driftAmount: 14 + Math.random() * 28
            driftSpeed: 0.3 + Math.random() * 0.6
            rotationSpeed: 35 + Math.random() * 90
            glowAmount: 0.12
        }
    }

    Repeater {
        model: field.active ? 26 : 0
        Petal {
            x: Math.random() * field.width
            y: Math.random() * field.height
            petalScale: 0.42 + Math.random() * 0.5
            petalOpacity: 0.28 + Math.random() * 0.34
            fallSpeed: 0.5 + Math.random() * 0.75
            driftAmount: 22 + Math.random() * 52
            driftSpeed: 0.45 + Math.random() * 0.9
            rotationSpeed: 60 + Math.random() * 130
            glowAmount: 0.22
        }
    }

    Repeater {
        model: field.active ? 7 : 0
        Petal {
            x: Math.random() * field.width
            y: Math.random() * field.height
            petalScale: 0.85 + Math.random() * 0.7
            petalOpacity: 0.34 + Math.random() * 0.22
            fallSpeed: 0.75 + Math.random() * 1.0
            driftAmount: 34 + Math.random() * 70
            driftSpeed: 0.6 + Math.random() * 1.1
            rotationSpeed: 85 + Math.random() * 150
            glowAmount: 0.3
        }
    }
}
