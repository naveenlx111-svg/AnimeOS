import QtQuick 2.15

Item {
    id: petal

    property real fallSpeed: 1.0
    property real driftAmount: 40
    property real driftSpeed: 1.0
    property real rotationSpeed: 120

    property real petalScale: 1.0
    property real petalOpacity: 1.0
    property real driftPhase: Math.random() * Math.PI * 2

    // Keep the glow subtle.
    property real glowAmount: 0.35

    // Picked once per instance so a single swarm shows several
    // slightly different fragment silhouettes (see assets/vectors).
    property int variantIndex: Math.floor(Math.random() * 5)

    readonly property var fragmentSources: [
        "assets/vectors/petal-a.svg",
        "assets/vectors/petal-b.svg",
        "assets/vectors/petal-c.svg",
        "assets/vectors/petal-d.svg",
        "assets/vectors/petal-e.svg"
    ]

    readonly property var glowSources: [
        "assets/images/petal-glow-a.png",
        "assets/images/petal-glow-b.png",
        "assets/images/petal-glow-c.png",
        "assets/images/petal-glow-d.png",
        "assets/images/petal-glow-e.png"
    ]

    // Native aspect of the fragment art is 100:200 (tall, thin).
    width: 22 * petalScale
    height: 44 * petalScale

    opacity: petalOpacity

    // ============================================================
    // SOFT GLOW
    //
    // A separately pre-rendered, properly Gaussian-blurred texture
    // (baked offline, not blurred at runtime) so it stays cheap and
    // needs no QtQuick.Effects / MultiEffect. It shares the exact
    // silhouette of the fragment above it, scaled up slightly, so
    // the glow hugs the edge instead of reading as a generic blob.
    // ============================================================

    Image {
        id: glow

        anchors.centerIn: parent
        width: parent.width * 1.6
        height: parent.height * 1.6

        source: petal.glowSources[petal.variantIndex]

        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        cache: true
        asynchronous: true

        // Fixed, instance-independent decode size so every particle
        // sharing a variant reuses the same cached texture.
        sourceSize.width: 160
        sourceSize.height: 320

        opacity: petal.glowAmount
    }

    // ============================================================
    // FRAGMENT SILHOUETTE
    //
    // Crisp vector art (assets/vectors/petal-*.svg) rendered through
    // Qt's SVG image plugin - sharp at any scale, no procedural
    // approximation. Base fill / inner highlight colors match the
    // Senbonzakura reference guide (#FFC2D6 / #FFE8F1).
    // ============================================================

    Image {
        id: fragment

        anchors.fill: parent

        source: petal.fragmentSources[petal.variantIndex]

        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        cache: true
        asynchronous: true

        sourceSize.width: 100
        sourceSize.height: 200
    }

    // ============================================================
    // FALL
    // ============================================================

    NumberAnimation on y {
        from: -50
        to: 1130

        duration: 9000 / petal.fallSpeed

        loops: Animation.Infinite
    }

    // ============================================================
    // ROTATION
    // ============================================================

    NumberAnimation on rotation {
        from: 0
        to: 360

        // rotationSpeed is degrees/second, so a full 360deg turn
        // takes (360 / rotationSpeed) seconds.
        duration: 360000 / petal.rotationSpeed

        loops: Animation.Infinite
    }

    // ============================================================
    // WIND
    // ============================================================

    Timer {
        interval: 16
        running: true
        repeat: true

        property real time: 0

        onTriggered: {
            time += 0.016

            // Flutter (side-to-side sway) plus a steady sideways carry,
            // so fragments actually get blown across the field instead
            // of just swaying in place around their starting x.
            var flutter = Math.sin(
                time * petal.driftSpeed +
                petal.driftPhase
            ) * (petal.driftAmount * 0.012)

            var carry = petal.driftAmount * 0.006

            petal.x += flutter + carry

            // Wrap around just off-screen so the steady carry never
            // strands fragments permanently off one edge.
            var fieldWidth = (petal.parent ? petal.parent.width : 1920)
            var margin = 120

            if (petal.x > fieldWidth + margin) {
                petal.x -= fieldWidth + margin * 2
            } else if (petal.x < -margin) {
                petal.x += fieldWidth + margin * 2
            }
        }
    }
}
