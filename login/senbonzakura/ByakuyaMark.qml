import QtQuick

// Chibi Byakuya, above the password field.
//
// Canvas paths for the same reason GlyphButton's icons are: the greeter runs
// before any user fontconfig exists, so nothing that leans on a font is safe,
// and an SVG would put a qt6-svg dependency behind one small asset.
//
// Five things carry him at this size and everything else was cut: the
// kenseikan, dark hair falling either side of a pale face, the white scarf,
// the haori over a black shihakusho, and a flat half-lidded stare. Detail
// past that does not survive a hundred pixels -- a line-art bust and an
// edge-traced frame were both tried here first and both came out as scribble.
//
// The colours are mixes of the measured Theme tokens rather than new ones.
// The skin and haori tones are measured off his own close-up (see Theme):
// the storm lights everything magenta, so the pale areas are pulled toward
// blade lavender and the warm ones toward petal.
Item {
    id: root

    property real weight: 1.2

    implicitWidth: 104
    implicitHeight: 120

    Canvas {
        id: art
        anchors.fill: parent
        antialiasing: true
        renderStrategy: Canvas.Cooperative

        // Bound rather than computed once, so a palette change repaints
        // instead of silently sticking on the old mix.
        property color cHair:  mix(Theme.night, Theme.blade, 0.24)
        property color cSkin:  Theme.skin
        property color cHaori: Theme.haori
        property color cPale:  Qt.lighter(Theme.haori, 1.04)
        property color cDark:  mix(Theme.abyss, Theme.blade, 0.10)
        // The eye is lifted off the robe's black on purpose. Against the warm
        // face a pure-black wedge reads as a hole rather than a half-lidded
        // look, and the whole expression is in that lid.
        property color cEye:   mix(Theme.abyss, Theme.blade, 0.30)
        property color cRim:   Theme.rim
        property real  w: root.weight

        onCHairChanged: requestPaint()
        onCRimChanged: requestPaint()
        onWChanged: requestPaint()

        // Design space, 100 wide by 120 tall, symmetric about x = 50.
        readonly property real dw: 100
        readonly property real dh: 120

        function mix(a, b, t) {
            return Qt.rgba(a.r + (b.r - a.r) * t,
                           a.g + (b.g - a.g) * t,
                           a.b + (b.b - a.b) * t, 1)
        }

        // Drawn on one side and mirrored, so the mark cannot go quietly
        // lopsided the way two hand-placed curves do.
        function both(c, path) {
            c.save(); path(c); c.restore()
            c.save(); c.translate(dw, 0); c.scale(-1, 1); path(c); c.restore()
        }

        function drawShape(c, path, fill, rimAlpha) {
            path(c)
            c.fillStyle = fill
            c.fill()
            c.strokeStyle = Qt.rgba(cRim.r, cRim.g, cRim.b, rimAlpha)
            c.stroke()
        }

        // ---------------------------------------------------------- shapes

        // Wider than it is tall, which is the whole trick of a chibi head.
        function pHair(c) {
            c.beginPath()
            c.moveTo(50, 5)
            c.bezierCurveTo(28, 5, 18, 21, 18, 41)
            c.bezierCurveTo(18, 56, 21, 65, 25, 71)
            c.lineTo(75, 71)
            c.bezierCurveTo(79, 65, 82, 56, 82, 41)
            c.bezierCurveTo(82, 21, 72, 5, 50, 5)
            c.closePath()
        }

        // One strand in front of the ear, tapering to a point over the
        // shoulder. Without these the hair mass reads as a helmet.
        function pLock(c) {
            c.beginPath()
            c.moveTo(28, 22)
            c.bezierCurveTo(22, 36, 21, 52, 22, 64)
            c.bezierCurveTo(23, 74, 25, 80, 27, 86)
            c.bezierCurveTo(30, 78, 31, 70, 31, 63)
            c.bezierCurveTo(30, 50, 31, 34, 34, 24)
            c.closePath()
        }

        function pFace(c) {
            c.beginPath()
            c.moveTo(50, 13)
            c.bezierCurveTo(33, 13, 26, 24, 26, 39)
            c.bezierCurveTo(26, 54, 37, 63, 50, 63)
            c.bezierCurveTo(63, 63, 74, 54, 74, 39)
            c.bezierCurveTo(74, 24, 67, 13, 50, 13)
            c.closePath()
        }

        // A fringe with a soft scallop either side and one point down the
        // middle -- his hair is centre parted, and that point is most of what
        // survives the shrink.
        function pBangs(c) {
            c.beginPath()
            c.moveTo(26, 29)
            c.bezierCurveTo(26, 16, 33, 9, 50, 9)
            c.bezierCurveTo(67, 9, 74, 16, 74, 29)
            c.bezierCurveTo(67, 32, 59, 24, 50, 32)
            c.bezierCurveTo(41, 24, 33, 32, 26, 29)
            c.closePath()
        }

        function pTorso(c) {
            c.beginPath()
            c.moveTo(40, 62)
            c.lineTo(60, 62)
            c.bezierCurveTo(64, 68, 65, 82, 65, 120)
            c.lineTo(35, 120)
            c.bezierCurveTo(35, 82, 36, 68, 40, 62)
            c.closePath()
        }

        // The haori: a pale panel over each shoulder and down the side,
        // leaving the shihakusho dark down the middle.
        function pHaori(c) {
            c.beginPath()
            c.moveTo(41, 64)
            c.bezierCurveTo(34, 67, 30, 76, 29, 88)
            c.lineTo(28, 120)
            c.lineTo(42, 120)
            c.lineTo(42, 78)
            c.closePath()
        }

        // The scarf, over the top of both. It is the one bright thing on the
        // body, and it is what stops the haori and the shihakusho reading as
        // three vertical stripes.
        function pScarf(c) {
            c.beginPath()
            c.moveTo(50, 60)
            c.bezierCurveTo(38, 60, 31, 63, 30, 69)
            c.bezierCurveTo(29, 75, 35, 78, 42, 77)
            c.bezierCurveTo(46, 76, 48, 74, 50, 74)
            c.bezierCurveTo(52, 74, 54, 76, 58, 77)
            c.bezierCurveTo(65, 78, 71, 75, 70, 69)
            c.bezierCurveTo(69, 63, 62, 60, 50, 60)
            c.closePath()
        }

        function pTail(c) {
            c.beginPath()
            c.moveTo(61, 72)
            c.bezierCurveTo(65, 79, 66, 85, 65, 91)
            c.lineTo(60, 89)
            c.bezierCurveTo(60, 83, 59, 77, 57, 73)
            c.closePath()
        }

        onPaint: {
            var c = getContext("2d")
            c.reset()
            var s = Math.min(width / dw, height / dh)
            c.translate((width - dw * s) / 2, (height - dh * s) / 2)
            c.scale(s, s)

            c.lineWidth = w
            c.lineCap = "round"
            c.lineJoin = "round"

            // ---- body, under the head --------------------------------------
            drawShape(c, pTorso, cDark, 0.45)
            both(c, function (g) { drawShape(g, pHaori, cHaori, 0.55) })
            // The scarf and the haori are both pale, so the scarf takes a
            // dark edge rather than a lit one: a rim in blade would have let
            // the two merge into a single white slab.
            c.strokeStyle = Qt.rgba(Theme.night.r, Theme.night.g, Theme.night.b, 0.45)
            c.fillStyle = cPale
            pTail(c);  c.fill(); c.stroke()
            pScarf(c); c.fill(); c.stroke()

            // ---- head ------------------------------------------------------
            drawShape(c, pHair, cHair, 0.38)
            drawShape(c, pFace, cSkin, 0.22)
            drawShape(c, pBangs, cHair, 0.34)
            both(c, function (g) { drawShape(g, pLock, cHair, 0.26) })

            // ---- the stare -------------------------------------------------
            // A flat top lid over a rounded eye. That flat line is the whole
            // expression, and it is the difference between bored and startled.
            both(c, function (g) {
                g.beginPath()
                g.moveTo(35.4, 41)
                g.lineTo(43.8, 41)
                g.bezierCurveTo(43.6, 46.0, 41.8, 47.4, 39.7, 47.4)
                g.bezierCurveTo(37.6, 47.4, 35.6, 45.8, 35.4, 41)
                g.closePath()
                g.fillStyle = cEye
                g.fill()

                // One highlight each. Without it the eye is a flat wedge and
                // the face reads as angry rather than unimpressed.
                g.beginPath()
                g.ellipse(40.6, 42.0, 2.4, 2.0)
                g.fillStyle = cPale
                g.fill()

                g.strokeStyle = cEye
                g.lineWidth = w * 2.0
                g.beginPath()
                g.moveTo(34.8, 40.4)
                g.lineTo(44.4, 40.4)
                g.stroke()
                g.lineWidth = w
            })

            c.strokeStyle = Qt.rgba(cDark.r, cDark.g, cDark.b, 0.8)
            c.lineWidth = w * 0.9
            c.beginPath()
            c.moveTo(47.8, 54.5)
            c.lineTo(52.2, 54.5)
            c.stroke()
            c.lineWidth = w

            // ---- kenseikan -------------------------------------------------
            var kcx = 50, kcy = 45, kr = 33
            var a0 = -Math.PI * 0.74, a1 = -Math.PI * 0.26

            c.strokeStyle = cPale
            c.lineWidth = w * 1.9
            c.beginPath()
            c.arc(kcx, kcy, kr, a0, a1)
            c.stroke()
            c.lineWidth = w

            c.fillStyle = cPale
            c.strokeStyle = Qt.rgba(Theme.night.r, Theme.night.g, Theme.night.b, 0.5)
            for (var i = 0; i < 5; i++) {
                var t = a0 + (a1 - a0) * (i + 0.5) / 5
                var nx = Math.cos(t), ny = Math.sin(t)
                var bx = kcx + nx * (kr - 0.8)
                var by = kcy + ny * (kr - 0.8)
                // The blades stand up off the band rather than out from the
                // head: on the plate they are near vertical whichever side of
                // the crown they sit on, and that is what keeps a kenseikan
                // from reading as a row of horns.
                var ux = nx * 0.26, uy = ny * 0.26 - 0.97
                var m = Math.sqrt(ux * ux + uy * uy)
                ux /= m; uy /= m
                var px = -uy, py = ux
                var len = 6.4, half = 1.8
                c.beginPath()
                c.moveTo(bx + px * half, by + py * half)
                c.quadraticCurveTo(bx + ux * len * 0.55 + px * half * 0.85,
                                   by + uy * len * 0.55 + py * half * 0.85,
                                   bx + ux * len, by + uy * len)
                c.quadraticCurveTo(bx + ux * len * 0.55 - px * half * 0.85,
                                   by + uy * len * 0.55 - py * half * 0.85,
                                   bx - px * half, by - py * half)
                c.closePath()
                c.fill()
                c.stroke()
            }
        }
    }
}
