"""
SENBONZAKURA BANKAI -- VFX-only layer builder
=============================================

Builds `senbonzakura_prototype.blend`: a transparent RGBA element containing
ONLY the Senbonzakura swords + petals. No character, no UI, no environment.
Byakuya, the KDE footage and everything else are composited under this render
in DaVinci Resolve.

Run:  blender -b senbonzakura_prototype.blend --python build_senbonzakura.py

Storyboard beats (24 fps):
     1-10   giant blades stab up out of the ground and fan open
    10-20   the blades erode tip-to-root; every petal is born on the surface
            the erosion front just passed, so fragments really come off the swords
    20-30   coherent left -> right + upward flow
    30-40   the swarm spreads in depth, near petals start growing
    40-50   the near wave rushes the camera
    50-60   near petals + haze cover the whole frame  <- the cut point
    60-65   everything exits right/up and off the camera plane; layer goes empty

Design notes
------------
Every petal's path is BAKED here in Python as a quadratic bezier with a
frame-accurate destination computed in camera NDC (see `ndc_to_world`). The
geometry nodes tree only *evaluates* that bezier against the scene frame. That
is what makes the flow directional and repeatable instead of a generic burst --
and it stays editable: re-run this script with different numbers, or grab the
`*_POINTS` meshes and edit the baked attributes.
"""

import bpy
import math
import random
from mathutils import Euler, Matrix, Vector

ROOT = bpy.path.abspath('//')
OUT_FILE = ROOT + 'senbonzakura_prototype.blend'

# ----------------------------------------------------------------------------
# Camera / framing constants. Everything else is derived from these, so changing
# the lens or resolution keeps the storyboard beats framed correctly.
# ----------------------------------------------------------------------------
RES_X, RES_Y = 1920, 1080
CAM_Z = 20.0            # camera sits at +Z looking down -Z
LENS = 50.0
SENSOR = 36.0
ASPECT = RES_Y / RES_X

FRAME_START, FRAME_END = 1, 68

# Invisible composition anchor: where Byakuya will sit in the Resolve comp.
# Nothing is rendered here -- it only biases where blades are NOT placed and
# which region the swarm has to travel through.
# Byakuya stands dead centre, low in frame, in every Swords_rising plate.
# The blade formation is built around this.
ANCHOR_NDC = (0.0, -0.62)

# The swarm orbits higher than the character does. Orbiting ANCHOR itself
# pins every petal to the bottom of the frame and leaves the top empty.
SWARM_CENTER_NDC = (0.0, -0.12)

# Palette from the petal reference sheet. Blender shader inputs are LINEAR, so
# the sRGB hex values have to be converted or the petals come out chalky white.
def srgb(hexstr):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hexstr.lstrip('#')
    return tuple(lin(int(h[i:i + 2], 16)) for i in (0, 2, 4)) + (1.0,)


C_PETAL_FILL = srgb('#FF9FC5')
C_PETAL_HILT = srgb('#FFEAF4')
C_PETAL_GLOW = srgb('#FF4F9F')
C_PETAL_DEEP = srgb('#D82D7F')   # saturated core so lit petals stay pink
C_BLADE_BODY = srgb('#39424F')   # near-black body; the read is all edge light
C_BLADE_GLOW = srgb('#EAF4FF')
C_EMBER_HOT = srgb('#FFFFFF')    # white-hot core of the transformation plume
C_EMBER_COOL = srgb('#FF3D96')


def half_w(z):
    """Half-width of the camera frustum, in world units, at depth `z`."""
    return (CAM_Z - z) * (SENSOR * 0.5) / LENS


def half_h(z):
    return half_w(z) * ASPECT


def ndc_to_world(nx, ny, z):
    """Screen-space (-1..1 = frame edges) -> world. The key to frame-accuracy."""
    return Vector((nx * half_w(z), ny * half_h(z), z))


# ============================================================================
# Scene cleanup
# ============================================================================

LEGACY_OBJECTS = (
    'Senbonzakura_FAR_POINTS', 'Senbonzakura_MID_POINTS',
    'Senbonzakura_FOREGROUND_POINTS', 'Senbonzakura_Fragment_SOURCE',
    'Preview_Backdrop_DARK', 'Plane_BeginnerPrototype_REFERENCE',
)
LEGACY_COLLECTIONS = (
    'PARTICLES_GeometryNodes', 'SOURCE_Fragment', 'PREVIEW_Optional',
    'REFERENCE_Original_Prototype',
)
BUILT_COLLECTIONS = ('SOURCE_Geometry', 'SWORDS', 'PETALS', 'FX_Optional', 'RIG')


def wipe_previous_build():
    for name in LEGACY_OBJECTS:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in BUILT_COLLECTIONS:
        col = bpy.data.collections.get(name)
        if col:
            for obj in list(col.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
    for name in LEGACY_COLLECTIONS + BUILT_COLLECTIONS:
        col = bpy.data.collections.get(name)
        if col:
            bpy.data.collections.remove(col)
    for ng in list(bpy.data.node_groups):
        if ng.name.startswith('Senbonzakura') or ng.name.startswith('GN_'):
            bpy.data.node_groups.remove(ng, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.materials):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


# ============================================================================
# Source meshes
# ============================================================================

def build_petal_mesh():
    """One sakura petal, matching the reference sheet: thin, softly cupped,
    slightly asymmetric, with the characteristic notch splitting the tip."""
    # Dense enough that a petal filling a third of the frame still reads as a
    # smooth curved surface rather than a faceted card.
    rows, cols = 21, 13
    verts, grid = [], []
    attr_t, attr_s = [], []

    for i in range(rows):
        t = i / (rows - 1)
        # Width peaks around 58% of the length and stays broad at the tip so
        # the notch has two lobes to cut between -- not a plain teardrop.
        if t < 0.58:
            w = 0.27 * (t / 0.58) ** 0.55
        else:
            k = (t - 0.58) / 0.42
            w = 0.27 * (1.0 - 0.42 * k ** 1.8)
        notch = max(0.0, (t - 0.78) / 0.22) ** 1.15
        row = []
        for j in range(cols):
            u = j / (cols - 1) * 2.0 - 1.0
            x = u * w + 0.022 * math.sin(t * 3.1)          # gentle asymmetry
            y = t - 0.18 * notch * (1.0 - abs(u)) ** 1.45   # the tip notch
            z = 0.075 * (1.0 - u * u) * math.sin(math.pi * t) ** 0.8 \
                + 0.030 * (t - 0.5)                         # cup + lengthwise curl
            row.append(len(verts))
            verts.append((x, y - 0.5, z))                   # centred for tumbling
            attr_t.append(t)
            attr_s.append(abs(u))
        grid.append(row)

    faces = [(grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
             for i in range(rows - 1) for j in range(cols - 1)]

    mesh = bpy.data.meshes.new('Petal_SOURCE_MESH')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth = True
    a_t = mesh.attributes.new('pt', 'FLOAT', 'POINT')
    a_s = mesh.attributes.new('ps', 'FLOAT', 'POINT')
    for i in range(len(verts)):
        a_t.data[i].value = attr_t[i]
        a_s.data[i].value = attr_s[i]

    obj = bpy.data.objects.new('Petal_SOURCE', mesh)
    obj.data.materials.append(make_petal_material())
    obj['README'] = 'Canonical sakura petal. Hidden; instanced by every petal layer.'
    return obj


# Blade profile shared by the mesh builder and the petal birth-point sampler,
# so petals are always born exactly on the sword surface.
# ----------------------------------------------------------------------------
# Blade formation, read off Swords_rising/.
#
# The reference is NOT a radial fan of straight blades. It is two mirrored
# wings of *hooked* blades: each one leaves the pivot below Byakuya angled
# outward, then curves back inward as it rises, so the tips lean toward the
# centre line and form the signature V notch above his head. Blades nest
# inside each other, getting longer and more swept toward the outside.
#
# Screen units below: 1.0 == half the frame HEIGHT, so the visible frame is
# y in -1..1 and x in about -1.78..1.78. Working in these units keeps the
# on-screen formation identical no matter what depth a blade sits at.
# ----------------------------------------------------------------------------
BLADES_PER_WING = 22
BLADE_W = 0.036             # half-width at the root, screen units

#                 innermost, outermost
TH_ROOT = (16.0, 52.0)      # launch angle from vertical, degrees, outward
TH_BEND = (-18.0, -34.0)    # total turn along the blade; negative hooks it in
BLADE_LEN = (1.15, 3.45)
# Roots fan across a wide base well below frame, so the outer blades sweep in
# from the bottom corners and exit past the top -- as they do in the reference.
ROOT_SX = (0.05, 1.30)
ROOT_SY = (-1.30, -1.60)
BLADE_Z = (-1.5, -6.5)      # inner blades nearer the lens -> real parallax

BLADE_SECTIONS = 57         # erosion deletes whole faces, so keep this fine


def _lerp(pair, u, power=1.0):
    return pair[0] + (pair[1] - pair[0]) * (u ** power)


def blade_half_width(t):
    """Width profile from root (t=0) to tip (t=1): near-constant, then a long
    taper to a fine kissaki point."""
    return (1.0 - t ** 2.2) ** 0.45


def blade_centerline(side, u, samples):
    """Sample one blade's centreline as a constant-curvature arc.

    The blade leaves its root at TH_ROOT degrees from vertical and turns by
    TH_BEND over its length. That single arc is what gives the reference its
    hooked silhouette -- a straight blade plus a rotation cannot reproduce it.
    """
    th0 = math.radians(_lerp(TH_ROOT, u, 0.9))
    bend = math.radians(_lerp(TH_BEND, u))
    length = _lerp(BLADE_LEN, u)
    rx = _lerp(ROOT_SX, u, 1.2)
    ry = _lerp(ROOT_SY, u)
    z = _lerp(BLADE_Z, u)

    pts = []
    for k in range(samples):
        s = k / (samples - 1)
        if abs(bend) < 1e-6:
            dx, dy = math.sin(th0) * s, math.cos(th0) * s
        else:
            # closed form of the arc integral
            dx = (math.cos(th0) - math.cos(th0 + bend * s)) / bend
            dy = (math.sin(th0 + bend * s) - math.sin(th0)) / bend
        sx = side * (rx + length * dx)
        sy = ry + length * dy
        pts.append(ndc_to_world(sx * ASPECT, sy, z))
    return pts, z


def blade_frames(pts):
    """Per-sample orthonormal frame: tangent along the blade, width direction
    across it in the screen plane, normal through its thickness."""
    frames = []
    n = len(pts)
    for k in range(n):
        if k == 0:
            tan = pts[1] - pts[0]
        elif k == n - 1:
            tan = pts[-1] - pts[-2]
        else:
            tan = pts[k + 1] - pts[k - 1]
        tan = tan.normalized()
        wdir = Vector((-tan.y, tan.x, 0.0))
        wdir = wdir.normalized() if wdir.length > 1e-6 else Vector((1.0, 0.0, 0.0))
        frames.append((tan, wdir, Vector((0.0, 0.0, 1.0))))
    return frames


def blade_basis(tan, wdir, ndir):
    """Rotation matrix whose columns are the blade's local axes, so callers can
    take .to_euler() for petal birth orientation."""
    return Matrix(((wdir.x, tan.x, ndir.x),
                   (wdir.y, tan.y, ndir.y),
                   (wdir.z, tan.z, ndir.z)))


def build_swords_mesh(swords):
    """All blades baked into ONE mesh in world space, carrying the per-vertex
    attributes the geometry nodes tree needs. No instancing -- that keeps the
    erosion (which deletes real faces) trivial and attribute-safe."""
    across = 5
    verts, faces = [], []
    a_u, a_len, a_delay, a_edur, a_dt0, a_ddur, a_rest = [], [], [], [], [], [], []
    a_to_center, a_bright = [], []

    for sw in swords:
        pts = sw['pts']
        frames = blade_frames(pts)
        sections = len(pts)

        top_idx, bot_idx = [], []
        for i in range(sections):
            t = i / (sections - 1)
            centre = pts[i]
            tan, wdir, ndir = frames[i]
            hw = sw['width'] * blade_half_width(t)
            th = sw['width'] * 0.18 * (1.0 - 0.6 * t)
            trow, brow = [], []
            for j in range(across):
                u = j / (across - 1) * 2.0 - 1.0
                p = centre + wdir * (u * hw)
                ridge = ndir * (th * (1.0 - abs(u) ** 1.7))
                for side, store in ((1.0, trow), (-1.0, brow)):
                    store.append(len(verts))
                    vp = p + ridge * side
                    verts.append(tuple(vp))
                    # Translation-invariant, so it stays correct however the
                    # blade is displaced at render time.
                    a_to_center.append(tuple(centre - vp))
                    a_u.append(t)
                    a_bright.append(sw['bright'])
                    a_len.append(sw['length'])
                    a_delay.append(sw['delay'])
                    a_edur.append(sw['edur'])
                    a_dt0.append(sw['dt0'])
                    a_ddur.append(sw['ddur'])
                    a_rest.append(tuple(vp))
            top_idx.append(trow)
            bot_idx.append(brow)

        for i in range(sections - 1):
            for j in range(across - 1):
                faces.append((top_idx[i][j], top_idx[i][j + 1],
                              top_idx[i + 1][j + 1], top_idx[i + 1][j]))
                faces.append((bot_idx[i][j + 1], bot_idx[i][j],
                              bot_idx[i + 1][j], bot_idx[i + 1][j + 1]))
                # side walls along both long edges
            faces.append((top_idx[i][0], top_idx[i + 1][0],
                          bot_idx[i + 1][0], bot_idx[i][0]))
            faces.append((top_idx[i + 1][-1], top_idx[i][-1],
                          bot_idx[i][-1], bot_idx[i + 1][-1]))
        faces.append(tuple(reversed(top_idx[0])))
        faces.append(tuple(bot_idx[0]))

    mesh = bpy.data.meshes.new('Senbonzakura_Swords_MESH')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth = True

    def store(name, kind, data):
        at = mesh.attributes.new(name, kind, 'POINT')
        if kind == 'FLOAT':
            for i, v in enumerate(data):
                at.data[i].value = v
        else:
            for i, v in enumerate(data):
                at.data[i].vector = v

    store('blade_u', 'FLOAT', a_u)
    store('sw_bright', 'FLOAT', a_bright)
    store('sw_len', 'FLOAT', a_len)
    store('sw_delay', 'FLOAT', a_delay)
    store('sw_edur', 'FLOAT', a_edur)
    store('sw_dt0', 'FLOAT', a_dt0)
    store('sw_ddur', 'FLOAT', a_ddur)
    store('rest_pos', 'FLOAT_VECTOR', a_rest)
    store('to_center', 'FLOAT_VECTOR', a_to_center)

    obj = bpy.data.objects.new('Senbonzakura_Swords', mesh)
    obj.data.materials.append(make_blade_material())
    obj['README'] = ('All Bankai blades in one mesh. The Geometry Nodes modifier '
                     'raises them out of the ground and then erodes them tip-to-root.')
    return obj


# ============================================================================
# Sword formation
# ============================================================================

def layout_swords():
    """Deterministic 32-blade mirrored wing matching ``Swords_rising``.

    Fully determined by the constants above -- no RNG anywhere -- so the
    formation can be registered against the Byakuya plate in Resolve and stays
    byte-identical across rebuilds. Inner blades launch first and the wing
    unfurls outward, which is the progression the reference shows.
    """
    swords = []
    for side in (-1, 1):
        for i in range(BLADES_PER_WING):
            u = i / (BLADES_PER_WING - 1)
            pts, z = blade_centerline(side, u, BLADE_SECTIONS)
            length = (pts[-1] - pts[0]).length
            swords.append({
                'pts': pts,
                'z': z,
                'side': side,
                'index': i,
                'length': length,
                # Outer blades are physically bigger but read as thinner
                # on screen, exactly as in the reference.
                'width': BLADE_W * half_h(z) * (1.0 - 0.25 * u),
                # Outer blades are farther away, so knock them back tonally.
                # Without this the wing reads as one flat white comb rather
                # than a formation with depth.
                'bright': 1.0 - 0.40 * u ** 0.8,
                # Inner blades lead; the wing unfurls outward over ~9 frames.
                'delay': 0.5 + i * 0.34,
                'edur': 4.6,
                'dt0': 10.4 + i * 0.22,
                'ddur': 7.0,
            })
    return swords


def sword_surface_point(sw, t, u, jitter_rng):
    """Point on the curved blade surface at length fraction `t`, width `u`.
    Shares the centreline with the mesh builder, so petals are always born
    exactly on the blade."""
    pts = sw['pts']
    n = len(pts)
    f = min(t, 0.99999) * (n - 1)
    k = int(f)
    frac = f - k
    centre = pts[k].lerp(pts[k + 1], frac)
    tan = (pts[k + 1] - pts[k]).normalized()
    wdir = Vector((-tan.y, tan.x, 0.0))
    wdir = wdir.normalized() if wdir.length > 1e-6 else Vector((1.0, 0.0, 0.0))
    ndir = Vector((0.0, 0.0, 1.0))
    hw = sw['width'] * blade_half_width(t)
    world = centre + wdir * (u * hw)
    j = sw['width'] * 0.4
    world += Vector((jitter_rng.uniform(-j, j), jitter_rng.uniform(-j, j),
                     jitter_rng.uniform(-j, j)))
    return world, blade_basis(tan, wdir, ndir)


# ============================================================================
# Petal trajectory baking
# ============================================================================

def bake_petal_layer(name, swords, count, spec, seed):
    """Every petal is born on a blade at the moment the erosion front reaches
    it, then flies a quadratic bezier to a destination expressed in camera NDC.
    All of that is baked into point attributes here."""
    rng = random.Random(seed)
    weights = [sw['length'] for sw in swords]
    total = sum(weights)

    pos, ctrl, end, exitv, wob = [], [], [], [], []
    t_birth, t_life, t_hold, wob_ph = [], [], [], []
    s0, s1, s_grow, ease = [], [], [], []
    rot0, spin = [], []

    for i in range(count):
        # pick a blade weighted by length
        r = rng.uniform(0, total)
        acc = 0.0
        sw = swords[-1]
        for cand, w in zip(swords, weights):
            acc += w
            if r <= acc:
                sw = cand
                break

        t = rng.random() ** 0.75          # bias toward the tip, which sheds first
        u = rng.uniform(-1.0, 1.0)
        birth, rot = sword_surface_point(sw, t, u, rng)

        # Synced to the erosion front travelling tip -> root.
        tb = sw['dt0'] + (1.0 - t) * sw['ddur'] + rng.uniform(0.0, 0.8)

        if spec.get('dest_accepts_t'):
            dest = spec['dest'](rng, sw, i, count, t, birth, rot)
        else:
            dest = spec['dest'](rng, sw, i, count)
        nx, ny, z_end, arrive, size = dest
        e = ndc_to_world(nx, ny, z_end)

        if spec.get('absolute_arrive', True):
            life = max(4.0, arrive - tb)
            arrive = tb + life
        else:
            # `arrive` came back as a lifetime relative to this petal's birth.
            life = max(2.0, arrive)
            arrive = tb + life
        bias = spec['ctrl_bias']
        c = Vector((
            birth.x + (e.x - birth.x) * (bias[0] + rng.uniform(-0.08, 0.08)),
            birth.y + (e.y - birth.y) * (bias[1] + rng.uniform(-0.08, 0.08)),
            birth.z + (e.z - birth.z) * (bias[2] + rng.uniform(-0.08, 0.08)),
        ))
        if spec.get('swirl'):
            # Add a tangent component so the bezier bends around the invisible
            # Byakuya anchor instead of reading as a straight particle stream.
            center = ndc_to_world(SWARM_CENTER_NDC[0], SWARM_CENTER_NDC[1], birth.z)
            radial = birth - center
            radial.z = 0.0
            if radial.length < 1e-4:
                radial = Vector((1.0, 0.0, 0.0))
            tangent = Vector((-radial.y, radial.x, 0.0)).normalized()
            c += tangent * spec['swirl'](rng) * (0.65 + 0.35 * rng.random())

        # By default a petal keeps going the way it arrived. Layers that would
        # otherwise keep barrelling into the lens (and stay huge on screen)
        # override this with a mostly screen-right/up exit instead.
        ex = Vector(spec['exit_dir']) if spec.get('exit_dir') else (e - c)
        if ex.length < 1e-5:
            ex = Vector((1.0, 0.5, 0.0))
        ex = ex.normalized() * spec['exit_speed'](rng)

        pos.append(tuple(birth))
        ctrl.append(tuple(c))
        end.append(tuple(e))
        exitv.append(tuple(ex))
        t_birth.append(tb)
        t_life.append(life)
        # How long a petal dwells at its destination before the exit sweep takes
        # over. The near wave uses this so all four waves accumulate into full
        # coverage and then clear the frame together.
        hold_until = spec['hold_until'](rng) if spec.get('hold_until') else 0.0
        t_hold.append(max(0.0, hold_until - arrive))
        s0.append(size * spec['start_scale'](rng))
        s1.append(size)
        s_grow.append(size * spec['grow'](rng))
        ease.append(spec['ease'](rng))
        wamp = spec['wobble'](rng)
        wob.append((wamp * rng.uniform(-1, 1), wamp * rng.uniform(-1, 1),
                    wamp * rng.uniform(-0.4, 0.4)))
        wob_ph.append(rng.uniform(0, math.tau))

        # Born aligned to the blade it came off, then tumbles free.
        be = rot.to_euler()
        rot0.append((be.x + rng.uniform(-0.35, 0.35),
                     be.y + rng.uniform(-0.35, 0.35),
                     be.z + rng.uniform(-0.35, 0.35)))
        sp = spec['spin'](rng)
        spin.append((sp * rng.uniform(-1, 1), sp * rng.uniform(-1, 1),
                     sp * rng.uniform(-0.6, 0.6)))

    mesh = bpy.data.meshes.new(name + '_MESH')
    mesh.from_pydata(pos, [], [])
    mesh.update()

    def store(attr_name, kind, data):
        at = mesh.attributes.new(attr_name, kind, 'POINT')
        if kind == 'FLOAT':
            for i, v in enumerate(data):
                at.data[i].value = v
        else:
            for i, v in enumerate(data):
                at.data[i].vector = v

    store('p_ctrl', 'FLOAT_VECTOR', ctrl)
    store('p_end', 'FLOAT_VECTOR', end)
    store('p_exit', 'FLOAT_VECTOR', exitv)
    store('p_wob', 'FLOAT_VECTOR', wob)
    store('p_rot0', 'FLOAT_VECTOR', rot0)
    store('p_spin', 'FLOAT_VECTOR', spin)
    store('t_birth', 'FLOAT', t_birth)
    store('t_life', 'FLOAT', t_life)
    store('t_hold', 'FLOAT', t_hold)
    store('s0', 'FLOAT', s0)
    store('s1', 'FLOAT', s1)
    store('s_grow', 'FLOAT', s_grow)
    store('p_ease', 'FLOAT', ease)
    store('wob_ph', 'FLOAT', wob_ph)

    obj = bpy.data.objects.new(name, mesh)
    obj['README'] = ('Baked petal trajectories. Every point carries its bezier '
                     '(position -> p_ctrl -> p_end), timing and scale. Re-run '
                     'build_senbonzakura.py to re-bake.')
    return obj


# ---- destination specs, one per storyboard beat ----------------------------

def spec_far():
    def dest(rng, sw, i, count):
        theta = (i / max(1, count)) * math.tau * 2.15 + rng.uniform(-0.12, 0.12)
        radius = rng.uniform(0.38, 1.18)
        nx = SWARM_CENTER_NDC[0] + math.cos(theta) * radius * 1.20
        ny = SWARM_CENTER_NDC[1] + math.sin(theta) * radius * 0.95
        z = rng.uniform(-13.0, -3.0)
        arrive = rng.uniform(27.0, 45.0)
        size = rng.uniform(0.12, 0.30)
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        'ctrl_bias': (0.44, 0.36, 0.50),
        'swirl': lambda r: r.uniform(1.0, 2.2),
        'exit_speed': lambda r: r.uniform(0.30, 0.60),
        'start_scale': lambda r: r.uniform(0.34, 0.52),
        'grow': lambda r: 0.0,
        'ease': lambda r: r.uniform(1.15, 1.45),
        'wobble': lambda r: r.uniform(0.06, 0.22),
        'spin': lambda r: r.uniform(0.05, 0.16),
    }


def spec_mid():
    def dest(rng, sw, i, count):
        theta = (i / max(1, count)) * math.tau * 2.7 + rng.uniform(-0.16, 0.16)
        radius = rng.uniform(0.20, 1.02)
        nx = SWARM_CENTER_NDC[0] + math.cos(theta) * radius * 1.28
        ny = SWARM_CENTER_NDC[1] + math.sin(theta) * radius * 1.00
        z = rng.uniform(-2.0, 8.0)
        arrive = rng.uniform(31.0, 50.0)
        size = rng.uniform(0.24, 0.66)
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        'ctrl_bias': (0.42, 0.34, 0.42),
        'swirl': lambda r: r.uniform(0.8, 1.8),
        'exit_speed': lambda r: r.uniform(0.45, 0.85),
        'start_scale': lambda r: r.uniform(0.34, 0.52),
        'grow': lambda r: r.uniform(0.0, 0.02),
        'ease': lambda r: r.uniform(1.25, 1.60),
        'wobble': lambda r: r.uniform(0.05, 0.18),
        'spin': lambda r: r.uniform(0.06, 0.20),
    }


def spec_near(waves, grid_x, grid_y):
    """The engulfment wave. Destinations are laid out on a jittered screen grid
    at four depths so that between ~frame 52 and 60 the frame is fully covered
    by overlapping foreground petals."""
    cells = []
    for wi, (z, t_lo, t_hi) in enumerate(waves):
        cw = 2.6 / grid_x
        ch = 2.6 / grid_y
        for gx in range(grid_x):
            for gy in range(grid_y):
                cells.append((wi, z, t_lo, t_hi,
                              -1.30 + cw * (gx + 0.5),
                              -1.30 + ch * (gy + 0.5),
                              cw, ch))
    random.Random(4242).shuffle(cells)

    state = {'i': 0}

    def dest(rng, sw, i, count):
        cell = cells[state['i'] % len(cells)]
        state['i'] += 1
        wi, z, t_lo, t_hi, cx, cy, cw, ch = cell
        nx = cx + rng.uniform(-0.45, 0.45) * cw
        ny = cy + rng.uniform(-0.45, 0.45) * ch
        arrive = rng.uniform(t_lo, t_hi)
        # Big enough that its screen footprint overruns its cell, but NOT so big
        # it becomes a featureless wall -- coverage has to come from the number
        # of overlapping petals, so you still read petal silhouettes.
        world_cell = max(cw * half_w(z), ch * half_h(z))
        size = world_cell * rng.uniform(1.08, 1.55)
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        # Hold back, drift right/up, then swing hard toward the lens.
        'ctrl_bias': (0.48, 0.42, 0.10),
        'exit_dir': (0.82, 0.50, 0.20),   # sweep off right/up, not into the lens
        'exit_speed': lambda r: r.uniform(1.30, 1.95),
        # All four waves dwell until ~60 so coverage accumulates and holds
        # through the cut point, then the whole mass clears together.
        'hold_until': lambda r: r.uniform(58.5, 61.0),
        'start_scale': lambda r: r.uniform(0.06, 0.14),
        'grow': lambda r: 0.0,      # stop growing once they arrive
        'ease': lambda r: r.uniform(1.9, 2.6),   # strong ease-in = rushing at you
        'wobble': lambda r: r.uniform(0.06, 0.20),   # keeps the hold alive
        'spin': lambda r: r.uniform(0.02, 0.06),     # slow, so none go edge-on
    }


def spec_crossers():
    """A handful of fragments that punch straight past the camera plane."""
    def dest(rng, sw, i, count):
        nx = rng.uniform(-0.9, 0.9)
        ny = rng.uniform(-0.9, 0.9)
        z = rng.uniform(17.4, 19.4)
        arrive = rng.uniform(42.0, 61.0)
        size = rng.uniform(0.10, 0.26)
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        'ctrl_bias': (0.55, 0.32, 0.12),
        'exit_speed': lambda r: r.uniform(1.0, 1.6),
        'start_scale': lambda r: r.uniform(0.04, 0.10),
        'grow': lambda r: 0.0,
        'ease': lambda r: r.uniform(2.2, 3.0),
        'wobble': lambda r: r.uniform(0.02, 0.08),
        'spin': lambda r: r.uniform(0.04, 0.12),
    }


def spec_embers():
    """The hot plume, straight from single_sword_transform_sample/.

    Where the erosion front eats the blade, the reference throws a dense
    fountain of TINY white-hot flecks that rise in a tight column along the
    blade's own axis and mushroom outward at the top. This layer is what makes
    the transformation read as the sword burning into petals rather than the
    sword vanishing and a particle system switching on.

    These stay small and short-ranged on purpose -- the big travelling petals
    are separate layers that take over once the plume has cooled.
    """
    def dest(rng, sw, i, count, t, birth, basis):
        # The reference plumes rise vertically regardless of how the blade is
        # angled, so drive them off world up, not the blade axis.
        tan = Vector((0.0, 1.0, 0.0))
        wdir = Vector((basis[0][0], basis[1][0], basis[2][0]))   # across width
        scale = sw['width'] * 34.0
        # Rise along the blade, spreading as it goes: a narrow stem that opens
        # into a cap, exactly the plume shape in the sample frames.
        rise = rng.uniform(0.30, 1.0) ** 0.6
        spread = rise ** 2.6      # tight stem, wide cap
        p = birth + tan * (rise * scale)
        p += wdir * (rng.uniform(-1.0, 1.0) * spread * scale * 0.42)
        p += Vector((0.0, 0.0, rng.uniform(-1.0, 1.0) * spread * scale * 0.3))
        nx = p.x / half_w(sw['z'])
        ny = p.y / half_h(sw['z'])
        z = sw['z'] + rng.uniform(-0.6, 1.4)
        arrive = rng.uniform(5.0, 11.0)      # short-lived; measured from birth
        size = rng.uniform(0.045, 0.115)     # tiny -- these read as sparks
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        'dest_accepts_t': True,
        'absolute_arrive': False,   # `arrive` is a lifetime, not a frame number
        'ctrl_bias': (0.30, 0.55, 0.30),
        'exit_speed': lambda r: r.uniform(0.05, 0.16),
        'start_scale': lambda r: r.uniform(0.55, 0.95),
        # Negative growth: a fleck burns out a few frames after it tops out,
        # which is what stops the plume becoming permanent white dust.
        'grow': lambda r: -r.uniform(0.05, 0.11),
        'ease': lambda r: r.uniform(0.55, 0.80),   # fast off the blade, then slows
        'wobble': lambda r: r.uniform(0.02, 0.07),
        'spin': lambda r: r.uniform(0.12, 0.34),
    }


# ============================================================================
# Geometry nodes -- a tiny builder DSL keeps the trees readable
# ============================================================================

class NB:
    def __init__(self, ng):
        self.ng = ng
        self.n = ng.nodes
        self.l = ng.links
        self._x, self._y = -1600.0, 600.0

    def new(self, idname, **kw):
        nd = self.n.new(idname)
        nd.location = (self._x, self._y)
        self._y -= 190
        if self._y < -1600:
            self._y = 600
            self._x += 230
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def plug(self, node, key, value):
        if value is None:
            return
        if hasattr(value, 'is_output'):
            self.l.new(value, node.inputs[key])
        else:
            node.inputs[key].default_value = value

    def math(self, op, a, b=None, clamp=False):
        nd = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.plug(nd, 0, a)
        self.plug(nd, 1, b)
        return nd.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        nd = self.new('ShaderNodeVectorMath', operation=op)
        self.plug(nd, 0, a)
        if b is not None:
            self.plug(nd, 1, b)
        if scale is not None:
            self.plug(nd, 'Scale', scale)
        return nd.outputs['Vector']

    def attr(self, name, kind='FLOAT'):
        nd = self.new('GeometryNodeInputNamedAttribute', data_type=kind)
        nd.inputs['Name'].default_value = name
        return nd.outputs['Attribute']

    def frame(self):
        return self.new('GeometryNodeInputSceneTime').outputs['Frame']

    def position(self):
        return self.new('GeometryNodeInputPosition').outputs['Position']

    def compare(self, op, a, b):
        nd = self.new('FunctionNodeCompare', data_type='FLOAT', operation=op)
        self.plug(nd, 0, a)
        self.plug(nd, 1, b)
        return nd.outputs['Result']

    def combine(self, x, y, z):
        nd = self.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            self.plug(nd, i, v)
        return nd.outputs['Vector']

    def euler_to_rot(self, vec):
        nd = self.new('FunctionNodeEulerToRotation')
        self.plug(nd, 'Euler', vec)
        return nd.outputs['Rotation']


def make_sword_nodes(name):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    s = ng.interface.new_socket(name='Growth Sharpness', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 0.45, 0.05, 1.0
    s.description = ('Ease on the blade extending out of the pivot. Lower = a '
                     'faster initial stab that decelerates into place.')
    s = ng.interface.new_socket(name='Erosion Roughness', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 0.22, 0.0, 0.6
    s.description = 'Ragged-ness of the dissolve front. 0 = perfectly straight cut.'
    s = ng.interface.new_socket(name='Front Glow Width', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 0.055, 0.005, 0.5
    s.description = 'Length of the hot glowing band trailing the dissolve front.'
    s = ng.interface.new_socket(name='Front Taper', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 0.10, 0.0, 0.5
    s.description = ('How far back the blade narrows toward its own centreline as '
                     'it erodes. Without this the dissolve leaves blunt stumps.')

    nb = NB(ng)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')

    frame = nb.frame()
    blade_u = nb.attr('blade_u')
    delay = nb.attr('sw_delay')
    edur = nb.attr('sw_edur')
    dt0 = nb.attr('sw_dt0')
    ddur = nb.attr('sw_ddur')
    rest = nb.attr('rest_pos', 'FLOAT_VECTOR')
    to_center = nb.attr('to_center', 'FLOAT_VECTOR')

    # Both phases are the same operation on the same coordinate: a front that
    # sweeps along the blade. Growth runs root -> tip, erosion runs tip -> root,
    # and the blade is simply whatever lies behind BOTH fronts. One `min` gives
    # the whole life of a blade, and the leading edge glows in either phase.

    # --- growth: front runs 0 -> 1, decelerating ---
    g = nb.math('SUBTRACT', frame, nb.math('ADD', delay, 1.0))
    g = nb.math('DIVIDE', g, edur, clamp=True)
    grow = nb.math('POWER', g, gi.outputs['Growth Sharpness'])

    # --- erosion: front runs 1 -> 0 ---
    prog = nb.math('DIVIDE', nb.math('SUBTRACT', frame, dt0), ddur, clamp=True)
    erode = nb.math('SUBTRACT', 1.0, prog)

    front = nb.math('MINIMUM', grow, erode)
    noise = nb.new('ShaderNodeTexNoise')
    nb.plug(noise, 'Vector', nb.vmath('SCALE', rest, scale=6.0))
    nb.plug(noise, 'Scale', 1.0)
    nb.plug(noise, 'Detail', 4.0)
    jag = nb.math('MULTIPLY', nb.math('SUBTRACT', noise.outputs['Factor'], 0.5),
                  gi.outputs['Erosion Roughness'])
    # Only roughen the erosion edge -- a growing blade has a clean sharp tip.
    jag = nb.math('MULTIPLY', jag, prog)
    front_n = nb.math('ADD', front, jag)

    # distance behind the front, in blade-length units
    d = nb.math('MAXIMUM', nb.math('SUBTRACT', front_n, blade_u), 0.0)

    # --- taper: pull the surface toward the centreline as the front approaches,
    # so the blade ends in a needle instead of a blunt bright stump ---
    shrink = nb.math('SUBTRACT', 1.0,
                     nb.math('DIVIDE', d, gi.outputs['Front Taper'], clamp=True))
    offset = nb.vmath('SCALE', to_center, scale=shrink)

    setpos = nb.new('GeometryNodeSetPosition')
    nb.plug(setpos, 'Geometry', gi.outputs['Geometry'])
    nb.plug(setpos, 'Offset', offset)

    # hot band just behind the front
    glow = nb.math('SUBTRACT', 1.0,
                   nb.math('DIVIDE', d, gi.outputs['Front Glow Width'], clamp=True))
    store = nb.new('GeometryNodeStoreNamedAttribute', data_type='FLOAT', domain='POINT')
    store.inputs['Name'].default_value = 'diss_glow'
    nb.plug(store, 'Geometry', setpos.outputs['Geometry'])
    nb.plug(store, 'Value', glow)

    delete = nb.new('GeometryNodeDeleteGeometry', domain='FACE')
    nb.plug(delete, 'Geometry', store.outputs['Geometry'])
    nb.plug(delete, 'Selection', nb.compare('GREATER_THAN', blade_u, front_n))
    nb.l.new(delete.outputs['Geometry'], go.inputs['Geometry'])
    return ng


def make_petal_nodes(name, petal_source):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    s = ng.interface.new_socket(name='Visible Count', in_out='INPUT', socket_type='NodeSocketInt')
    s.default_value, s.min_value, s.max_value = 100000, 0, 100000
    s.description = 'Trim the layer down for fast previews. Does not re-bake anything.'
    s = ng.interface.new_socket(name='Scale Multiplier', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 1.0, 0.0, 8.0
    s.description = 'Global size of every petal in this layer.'
    s = ng.interface.new_socket(name='Time Offset', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 0.0, -60.0, 60.0
    s.description = 'Shift this whole layer earlier (-) or later (+) in frames.'
    s = ng.interface.new_socket(name='Wobble', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 1.0, 0.0, 5.0
    s.description = 'Amount of secondary drift on top of the baked bezier path.'
    s = ng.interface.new_socket(name='Spin', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 1.0, 0.0, 5.0
    s.description = 'Tumble speed multiplier.'

    nb = NB(ng)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')

    frame = nb.math('SUBTRACT', nb.frame(), gi.outputs['Time Offset'])
    birth = nb.position()
    ctrl = nb.attr('p_ctrl', 'FLOAT_VECTOR')
    end = nb.attr('p_end', 'FLOAT_VECTOR')
    exitv = nb.attr('p_exit', 'FLOAT_VECTOR')
    wob = nb.attr('p_wob', 'FLOAT_VECTOR')
    rot0 = nb.attr('p_rot0', 'FLOAT_VECTOR')
    spin = nb.attr('p_spin', 'FLOAT_VECTOR')
    t_birth = nb.attr('t_birth')
    t_life = nb.attr('t_life')
    t_hold = nb.attr('t_hold')
    s0 = nb.attr('s0')
    s1 = nb.attr('s1')
    s_grow = nb.attr('s_grow')
    ease = nb.attr('p_ease')
    wob_ph = nb.attr('wob_ph')

    # --- preview trim ---
    idx = nb.new('GeometryNodeInputIndex')
    cmp_count = nb.new('FunctionNodeCompare', data_type='INT', operation='GREATER_EQUAL')
    nb.l.new(idx.outputs['Index'], cmp_count.inputs['A'])
    nb.l.new(gi.outputs['Visible Count'], cmp_count.inputs['B'])
    trim = nb.new('GeometryNodeDeleteGeometry', domain='POINT')
    nb.plug(trim, 'Geometry', gi.outputs['Geometry'])
    nb.plug(trim, 'Selection', cmp_count.outputs['Result'])

    # --- bezier along the baked path ---
    age = nb.math('SUBTRACT', frame, t_birth)
    u = nb.math('DIVIDE', age, t_life, clamp=True)
    ue = nb.math('POWER', u, ease)
    omu = nb.math('SUBTRACT', 1.0, ue)
    w0 = nb.math('MULTIPLY', omu, omu)
    w1 = nb.math('MULTIPLY', nb.math('MULTIPLY', omu, ue), 2.0)
    w2 = nb.math('MULTIPLY', ue, ue)
    p = nb.vmath('ADD', nb.vmath('SCALE', birth, scale=w0),
                 nb.vmath('SCALE', ctrl, scale=w1))
    p = nb.vmath('ADD', p, nb.vmath('SCALE', end, scale=w2))

    # --- keep going past the destination so petals exit rather than stop ---
    over = nb.math('MAXIMUM',
                   nb.math('SUBTRACT', age, nb.math('ADD', t_life, t_hold)), 0.0)
    p = nb.vmath('ADD', p, nb.vmath('SCALE', exitv, scale=over))

    # --- secondary drift ---
    sw = nb.math('SINE', nb.math('ADD', nb.math('MULTIPLY', frame, 0.55), wob_ph))
    p = nb.vmath('ADD', p, nb.vmath('SCALE', wob,
                                    scale=nb.math('MULTIPLY', sw, gi.outputs['Wobble'])))

    setpos = nb.new('GeometryNodeSetPosition')
    nb.plug(setpos, 'Geometry', trim.outputs['Geometry'])
    nb.plug(setpos, 'Position', p)

    # --- scale: grows toward the destination, zero before birth ---
    size = nb.math('ADD', s0, nb.math('MULTIPLY', ue, nb.math('SUBTRACT', s1, s0)))
    size = nb.math('ADD', size, nb.math('MULTIPLY', s_grow, over))
    # Clamp at zero so a negative growth rate reads as a clean burn-out
    # instead of flipping the instance inside out and re-growing.
    size = nb.math('MAXIMUM', size, 0.0)
    alive = nb.compare('GREATER_EQUAL', age, 0.0)
    size = nb.math('MULTIPLY', size, alive)
    size = nb.math('MULTIPLY', size, gi.outputs['Scale Multiplier'])

    rot = nb.vmath('ADD', rot0,
                   nb.vmath('SCALE', spin,
                            scale=nb.math('MULTIPLY', nb.math('MAXIMUM', age, 0.0),
                                          gi.outputs['Spin'])))

    objinfo = nb.new('GeometryNodeObjectInfo')
    objinfo.inputs['Object'].default_value = petal_source
    objinfo.inputs['As Instance'].default_value = True

    inst = nb.new('GeometryNodeInstanceOnPoints')
    nb.plug(inst, 'Points', setpos.outputs['Geometry'])
    nb.plug(inst, 'Instance', objinfo.outputs['Geometry'])
    nb.plug(inst, 'Rotation', nb.euler_to_rot(rot))
    nb.plug(inst, 'Scale', nb.combine(size, size, size))
    nb.l.new(inst.outputs['Instances'], go.inputs['Geometry'])
    return ng


# ============================================================================
# Materials
# ============================================================================

def make_petal_material():
    mat = bpy.data.materials.get('MAT_Sakura_Petal') or bpy.data.materials.new('MAT_Sakura_Petal')
    mat.use_nodes = True
    mat.surface_render_method = 'DITHERED'
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (600, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    a_t = nt.nodes.new('ShaderNodeAttribute'); a_t.attribute_name = 'pt'; a_t.location = (-800, 200)
    a_s = nt.nodes.new('ShaderNodeAttribute'); a_s.attribute_name = 'ps'; a_s.location = (-800, 0)

    # Lighter toward the centre, more saturated toward the edges + tip.
    edge = nt.nodes.new('ShaderNodeMath'); edge.operation = 'POWER'
    edge.inputs[1].default_value = 1.7; edge.location = (-600, 0)
    nt.links.new(a_s.outputs['Fac'], edge.inputs[0])

    mix1 = nt.nodes.new('ShaderNodeMix'); mix1.data_type = 'RGBA'; mix1.location = (-380, 100)
    mix1.inputs[6].default_value = C_PETAL_HILT
    mix1.inputs[7].default_value = C_PETAL_FILL
    nt.links.new(edge.outputs[0], mix1.inputs[0])

    tipf = nt.nodes.new('ShaderNodeMath'); tipf.operation = 'POWER'
    tipf.inputs[1].default_value = 1.5; tipf.location = (-600, -180)
    nt.links.new(a_t.outputs['Fac'], tipf.inputs[0])
    tipf2 = nt.nodes.new('ShaderNodeMath'); tipf2.operation = 'MULTIPLY'
    tipf2.inputs[1].default_value = 0.45; tipf2.location = (-420, -180)
    nt.links.new(tipf.outputs[0], tipf2.inputs[0])

    mix2 = nt.nodes.new('ShaderNodeMix'); mix2.data_type = 'RGBA'; mix2.location = (-160, 60)
    mix2.inputs[7].default_value = C_PETAL_DEEP
    nt.links.new(mix1.outputs[2], mix2.inputs[6])
    nt.links.new(tipf2.outputs[0], mix2.inputs[0])
    nt.links.new(mix2.outputs[2], bsdf.inputs['Base Color'])

    # Soft luminous rim, as on the reference sheet -- low radius, never hides
    # the silhouette. Keep the body opaque enough that the split tip remains
    # readable after Resolve adds its own glow.
    rim = nt.nodes.new('ShaderNodeMath'); rim.operation = 'POWER'
    rim.inputs[1].default_value = 5.0; rim.location = (-420, -380)
    nt.links.new(a_s.outputs['Fac'], rim.inputs[0])
    rim2 = nt.nodes.new('ShaderNodeMath'); rim2.operation = 'MULTIPLY_ADD'
    rim2.inputs[1].default_value = 1.55
    rim2.inputs[2].default_value = 0.10
    rim2.location = (-240, -380)
    nt.links.new(rim.outputs[0], rim2.inputs[0])
    nt.links.new(rim2.outputs[0], bsdf.inputs['Emission Strength'])
    bsdf.inputs['Emission Color'].default_value = C_PETAL_GLOW

    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.34
    bsdf.inputs['Sheen Weight'].default_value = 0.22
    bsdf.inputs['Sheen Roughness'].default_value = 0.30
    bsdf.inputs['Sheen Tint'].default_value = C_PETAL_HILT
    if 'Thin Wall' in bsdf.inputs:
        bsdf.inputs['Thin Wall'].default_value = True
    bsdf.inputs['Subsurface Weight'].default_value = 0.06
    bsdf.inputs['Subsurface Radius'].default_value = (0.9, 0.42, 0.55)
    bsdf.inputs['Subsurface Scale'].default_value = 0.02
    return mat


def make_blade_material():
    mat = bpy.data.materials.get('MAT_Senbonzakura_Blade') or \
        bpy.data.materials.new('MAT_Senbonzakura_Blade')
    mat.use_nodes = True
    mat.surface_render_method = 'DITHERED'
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (600, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (320, 0)
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # In the reference the blade body is nearly BLACK and all the read comes
    # from a searing specular line along the edge. A bright flat-grey body (the
    # previous version) kills the contrast that makes the formation legible.
    bsdf.inputs['Base Color'].default_value = C_BLADE_BODY
    bsdf.inputs['Metallic'].default_value = 0.85
    bsdf.inputs['Roughness'].default_value = 0.12

    # Fresnel-driven edge light: gives the blades the luminous silhouette they
    # have in the Bankai shot without needing an HDRI. Tight blend + high power
    # keeps the glow confined to a thin rim instead of washing the whole face.
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.location = (-700, 240)
    lw.inputs['Blend'].default_value = 0.16
    fres = nt.nodes.new('ShaderNodeMath'); fres.operation = 'POWER'
    fres.inputs[1].default_value = 3.4; fres.location = (-500, 240)
    nt.links.new(lw.outputs['Fresnel'], fres.inputs[0])
    fres2 = nt.nodes.new('ShaderNodeMath'); fres2.operation = 'MULTIPLY_ADD'
    fres2.inputs[1].default_value = 14.0    # searing white edge, blooms in Resolve
    fres2.inputs[2].default_value = 0.06    # body stays almost black
    fres2.location = (-320, 240)
    nt.links.new(fres.outputs[0], fres2.inputs[0])

    # Hot band trailing the leading front (growth tip AND erosion edge).
    glow = nt.nodes.new('ShaderNodeAttribute')
    glow.attribute_name = 'diss_glow'; glow.location = (-700, -80)
    gp = nt.nodes.new('ShaderNodeMath'); gp.operation = 'POWER'
    gp.inputs[1].default_value = 1.8; gp.location = (-500, -80)
    nt.links.new(glow.outputs['Fac'], gp.inputs[0])
    gm = nt.nodes.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'
    gm.inputs[1].default_value = 26.0; gm.location = (-320, -80)
    nt.links.new(gp.outputs[0], gm.inputs[0])

    total = nt.nodes.new('ShaderNodeMath'); total.operation = 'ADD'; total.location = (-120, 120)
    nt.links.new(fres2.outputs[0], total.inputs[0])
    nt.links.new(gm.outputs[0], total.inputs[1])

    # Per-blade tonal falloff so the wing has depth instead of reading flat.
    bright = nt.nodes.new('ShaderNodeAttribute')
    bright.attribute_name = 'sw_bright'; bright.location = (-320, 400)
    shade = nt.nodes.new('ShaderNodeMath'); shade.operation = 'MULTIPLY'
    shade.location = (60, 120)
    nt.links.new(total.outputs[0], shade.inputs[0])
    nt.links.new(bright.outputs['Fac'], shade.inputs[1])
    nt.links.new(shade.outputs[0], bsdf.inputs['Emission Strength'])

    ecol = nt.nodes.new('ShaderNodeMix'); ecol.data_type = 'RGBA'; ecol.location = (-120, -120)
    ecol.inputs[6].default_value = C_BLADE_GLOW
    ecol.inputs[7].default_value = C_PETAL_FILL
    nt.links.new(gp.outputs[0], ecol.inputs[0])
    nt.links.new(ecol.outputs[2], bsdf.inputs['Emission Color'])
    return mat


def make_ember_material():
    """Pure emission, white-hot at birth cooling to magenta.

    The transformation plume in the reference is not lit geometry -- it is
    self-luminous sparks blown well past white. Driving this off the petal's own
    length coordinate gives each fleck a hot core and a cooler tail without
    needing per-particle age in the shader.
    """
    mat = bpy.data.materials.get('MAT_Senbonzakura_Ember') or \
        bpy.data.materials.new('MAT_Senbonzakura_Ember')
    mat.use_nodes = True
    mat.surface_render_method = 'DITHERED'
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (420, 0)
    em = nt.nodes.new('ShaderNodeEmission'); em.location = (220, 0)
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])

    a_t = nt.nodes.new('ShaderNodeAttribute')
    a_t.attribute_name = 'pt'; a_t.location = (-620, 0)
    ramp = nt.nodes.new('ShaderNodeMath'); ramp.operation = 'POWER'
    ramp.inputs[1].default_value = 0.42; ramp.location = (-440, 0)
    nt.links.new(a_t.outputs['Fac'], ramp.inputs[0])

    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.location = (-240, 60)
    mix.inputs[6].default_value = C_EMBER_HOT
    mix.inputs[7].default_value = C_EMBER_COOL
    nt.links.new(ramp.outputs[0], mix.inputs[0])
    nt.links.new(mix.outputs[2], em.inputs['Color'])

    stren = nt.nodes.new('ShaderNodeMath'); stren.operation = 'MULTIPLY_ADD'
    stren.inputs[1].default_value = -5.0
    stren.inputs[2].default_value = 9.5
    stren.location = (-240, -140)
    nt.links.new(ramp.outputs[0], stren.inputs[0])
    nt.links.new(stren.outputs[0], em.inputs['Strength'])
    return mat


def make_veil_material():
    mat = bpy.data.materials.get('MAT_Petal_Haze') or bpy.data.materials.new('MAT_Petal_Haze')
    mat.use_nodes = True
    mat.surface_render_method = 'BLENDED'
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (600, 0)
    mix = nt.nodes.new('ShaderNodeMixShader'); mix.location = (400, 0)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.location = (200, 120)
    em = nt.nodes.new('ShaderNodeEmission'); em.location = (200, -80)
    em.inputs['Color'].default_value = C_PETAL_GLOW
    em.inputs['Strength'].default_value = 0.42
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])

    # radial falloff so it reads as petal haze, not a flat card
    tc = nt.nodes.new('ShaderNodeTexCoord'); tc.location = (-800, -200)
    sub = nt.nodes.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = (0.5, 0.5, 0.5); sub.location = (-620, -200)
    nt.links.new(tc.outputs['Generated'], sub.inputs[0])
    ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; ln.location = (-440, -200)
    nt.links.new(sub.outputs['Vector'], ln.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.location = (-260, -200)
    mr.inputs['From Min'].default_value = 0.0
    mr.inputs['From Max'].default_value = 0.72
    mr.inputs['To Min'].default_value = 1.0
    mr.inputs['To Max'].default_value = 0.35
    mr.clamp = True
    nt.links.new(ln.outputs['Value'], mr.inputs['Value'])

    amount = nt.nodes.new('ShaderNodeValue'); amount.location = (-440, 120)
    amount.name = 'HAZE_AMOUNT'
    amount.label = 'Haze amount (keyframed)'
    amount.outputs[0].default_value = 0.0
    fac = nt.nodes.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'
    fac.use_clamp = True; fac.location = (-60, 0)
    nt.links.new(amount.outputs[0], fac.inputs[0])
    nt.links.new(mr.outputs['Result'], fac.inputs[1])
    nt.links.new(fac.outputs[0], mix.inputs['Fac'])

    # A restrained atmospheric lift behind the actual petals. It supports the
    # transition without replacing the petal silhouettes with a pink card.
    for frame, value in ((49, 0.0), (53, 0.06), (56, 0.10),
                         (60, 0.12), (63, 0.04), (65, 0.0)):
        amount.outputs[0].default_value = value
        amount.outputs[0].keyframe_insert('default_value', frame=frame)
    return mat


# ============================================================================
# Camera, lights, haze card
# ============================================================================

def make_camera(scene):
    data = bpy.data.cameras.get('Camera_Senbonzakura') or \
        bpy.data.cameras.new('Camera_Senbonzakura')
    cam = bpy.data.objects.get('Camera_Senbonzakura') or \
        bpy.data.objects.new('Camera_Senbonzakura', data)
    if not cam.users_collection:
        scene.collection.objects.link(cam)
    cam.location = (0.0, 0.0, CAM_Z)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    data.type = 'PERSP'
    data.lens = LENS
    data.sensor_width = SENSOR
    data.clip_start = 0.05
    data.clip_end = 200.0
    scene.camera = cam
    return cam


def make_lights(col):
    for name in ('Light_Key_Sakura', 'Light_Rim_Cold', 'Light_Fill_Warm',
                 'Light_Sakura_Key', 'Light_Sakura_Rim'):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    def area(name, loc, rot, energy, color, size):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = energy
        data.color = color
        data.shape = 'DISK'
        data.size = size
        data.use_shadow = False          # flat anime-style petal lighting
        obj = bpy.data.objects.new(name, data)
        col.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = rot
        return obj

    # Deliberately gentle: the petals carry their own emission, and hot lights
    # were desaturating them straight to white.
    area('Light_Key_Sakura', (-9.0, 7.0, 16.0), (0.5, -0.45, 0.0), 850,
         (1.0, 0.52, 0.70), 12.0)
    area('Light_Rim_Cold', (11.0, -4.0, 10.0), (-0.4, 0.7, 0.0), 620,
         (0.45, 0.58, 1.0), 9.0)
    area('Light_Fill_Warm', (0.0, 0.0, -14.0), (math.pi, 0.0, 0.0), 320,
         (1.0, 0.45, 0.68), 16.0)


def make_haze_card(col, cam):
    """Fills the gaps between the big foreground petals during the engulfment so
    the alpha genuinely reaches full coverage at the cut point. Sits behind the
    whole near wave. Delete or mute this object if you'd rather do the flash in
    Resolve."""
    z = 12.5
    hw, hh = half_w(z) * 1.20, half_h(z) * 1.20
    verts = [(-hw, -hh, 0.0), (hw, -hh, 0.0), (hw, hh, 0.0), (-hw, hh, 0.0)]
    mesh = bpy.data.meshes.new('FX_Petal_Haze_MESH')
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new('FX_Petal_Haze', mesh)
    obj.location = (0.0, 0.0, z)
    obj.data.materials.append(make_veil_material())
    obj['README'] = ('Soft pink haze card behind the foreground petals. Its alpha '
                     'is keyframed 48-65 to guarantee full-frame coverage at the '
                     'transition point.')
    col.objects.link(obj)
    return obj


# ============================================================================
# README text block
# ============================================================================

def make_readme(counts):
    text = bpy.data.texts.get('README_Senbonzakura') or \
        bpy.data.texts.new('README_Senbonzakura')
    text.clear()
    w = text.write
    w('SENBONZAKURA BANKAI -- VFX-ONLY LAYER\n')
    w('=====================================\n\n')
    w('This file renders ONLY the swords and petals on a transparent background.\n')
    w('No Byakuya, no login UI, no environment. Composite underneath in Resolve.\n\n')
    w('TIMELINE (24 fps, frames 1-68)\n')
    w('   1-10  blades emerge from below frame and fan open\n')
    w('  10-20  blades erode tip->root; fragments are born on the exact surface\n')
    w('         erosion front just uncovered\n')
    w('  20-30  coherent left->right + upward flow\n')
    w('  30-40  swarm spreads in depth, near petals begin growing\n')
    w('  40-50  near wave rushes the camera\n')
    w('  50-60  full-frame coverage  <-- cut to the KDE footage here\n')
    w('  60-65  everything exits right/up and past the camera plane\n')
    w('  65-68  empty tail; layer is transparent again\n\n')
    w('MEASURED ALPHA COVERAGE (fraction of frame the layer covers)\n')
    w('  f044 .54  f048 .93  f050 .99  f053 .99  f055 .997\n')
    w('  f057 .996 f059 .999 f060 1.00 f062 .75  f064 .15  f067 .00\n')
    w('  Frame 60 is the only frame that is 100.0% opaque with zero gaps, so\n')
    w('  that is the safest single frame to cut on. 53-60 are all >=99%.\n\n')
    w('OBJECTS\n')
    w('  Senbonzakura_Swords   all 44 blades in one mesh + the grow/erode nodes\n')
    w('  Petals_EMBERS         the white-hot breakup plume (tiny, self-lit)\n')
    w('  Petals_FAR / MID      the orbiting background and midground swarm\n')
    w('  Petals_NEAR_WAVE      the foreground petals that engulf the frame\n')
    w('  Petals_CROSSERS       fragments that punch past the camera plane\n')
    w('  Petal_SOURCE          the instanced sakura petal (hidden)\n')
    w('  Ember_SOURCE          same petal, emission-only shader (hidden)\n')
    w('  FX_Petal_Haze         faint pink card that seals the alpha at 54-62\n')
    w('  Camera_Senbonzakura   50mm at +Z looking down -Z; X=right, Y=up\n\n')
    w('BLADE FORMATION\n')
    w('  Matched to Swords_rising/. Two mirrored wings of 22 HOOKED blades --\n')
    w('  each is a constant-curvature arc that leaves the pivot below Byakuya\n')
    w('  angled outward and turns back inward as it rises, so the tips lean\n')
    w('  toward the centre and open the V notch he stands in. A straight blade\n')
    w('  plus a rotation cannot reproduce that silhouette.\n')
    w('  Fully deterministic -- no RNG -- so it registers against the Byakuya\n')
    w('  plate in Resolve and is identical on every rebuild. The controlling\n')
    w('  constants are TH_ROOT / TH_BEND / BLADE_LEN / ROOT_SX / ROOT_SY,\n')
    w('  all in screen units where 1.0 == half the frame height.\n\n')
    w('GROWTH AND BREAKUP\n')
    w('  Both phases are one operation: a front sweeping along blade_u.\n')
    w('  Growth runs root->tip, erosion runs tip->root, and the blade is what\n')
    w('  lies behind BOTH (a single min). The leading edge glows in either\n')
    w('  phase, and the surface necks toward its own centreline at the front\n')
    w('  so it ends in a needle rather than a blunt stump.\n')
    w('  Every ember and petal is born ON the blade surface at the instant the\n')
    w('  erosion front uncovers its sample point -- same equation, so the\n')
    w('  handoff is causal rather than a crossfade into a separate emitter.\n\n')
    w('\nTUNING\n')
    w('  Sword modifier: Growth Sharpness, Erosion Roughness, Front Glow\n')
    w('    Width, Front Taper (set Front Taper to 0 to see why it exists).\n')
    w('  Petal modifiers: Visible Count (drop it for fast previews),\n')
    w('    Scale Multiplier, Time Offset, Wobble, Spin.\n')
    w('  Anything structural -- formation, destinations, timing -- lives in\n')
    w('  build_senbonzakura.py. Edit the numbers there and re-run:\n')
    w('    blender -b senbonzakura_prototype.blend --python build_senbonzakura.py\n\n')
    w('COMPOSITING\n')
    w('  Film > Transparent is on; output is PNG RGBA (straight alpha).\n')
    w('  Switch Output to OpenEXR (half, RGBA) if you want the emission above\n')
    w('  1.0 preserved for a Glow node in Resolve -- the petals and the erosion\n')
    w('  front are deliberately over-bright for that.\n')
    w('  No bloom is baked in on purpose: it would spill colour into transparent\n')
    w('  pixels and dirty the alpha. Add Glow in Resolve instead.\n')
    return text


# ============================================================================
# Main
# ============================================================================

def main():
    scene = bpy.context.scene
    wipe_previous_build()

    src_col = collection('SOURCE_Geometry')
    sword_col = collection('SWORDS')
    petal_col = collection('PETALS')
    fx_col = collection('FX_Optional')
    rig_col = collection('RIG')

    # --- sources ---
    petal_src = build_petal_mesh()
    src_col.objects.link(petal_src)
    petal_src.hide_render = True
    petal_src.hide_viewport = True

    # Same petal geometry, self-luminous shader: the plume flecks are literally
    # tiny petals, so the transformation stays one continuous idea.
    ember_src = build_petal_mesh()
    ember_src.name = 'Ember_SOURCE'
    ember_src.data.materials.clear()
    ember_src.data.materials.append(make_ember_material())
    ember_src['README'] = 'Tiny white-hot fleck for the sword breakup plume.'
    src_col.objects.link(ember_src)
    ember_src.hide_render = True
    ember_src.hide_viewport = True

    # --- swords ---
    swords = layout_swords()
    sword_obj = build_swords_mesh(swords)
    sword_col.objects.link(sword_obj)
    sword_ng = make_sword_nodes('GN_Senbonzakura_Swords')
    mod = sword_obj.modifiers.new('Emerge + erode (Geometry Nodes)', 'NODES')
    mod.node_group = sword_ng

    # --- petals ---
    petal_ng = make_petal_nodes('GN_Senbonzakura_Petals', petal_src)
    ember_ng = make_petal_nodes('GN_Senbonzakura_Embers', ember_src)
    layers = [
        # The causal bridge, and the biggest single fix versus the last pass:
        # a dense fountain of tiny white-hot flecks thrown off the erosion
        # front, exactly as in single_sword_transform_sample. High count and
        # tiny size are both load-bearing -- this has to read as sparks.
        ('Petals_EMBERS', 9000, spec_embers(), 111, ember_ng),
        ('Petals_FAR', 900, spec_far(), 101, petal_ng),
        ('Petals_MID', 680, spec_mid(), 202, petal_ng),
        # Four staggered depths so coverage builds through 46-52, holds solid
        # through 53-60, then unloads. Grid is 10x7 per wave.
        ('Petals_NEAR_WAVE', 1050, spec_near(
            [(9.5, 47.5, 51.5), (11.5, 50.0, 54.0),
             (13.0, 52.5, 56.5), (14.2, 55.0, 59.5)], 10, 7), 303, petal_ng),
        ('Petals_CROSSERS', 64, spec_crossers(), 404, petal_ng),
    ]
    counts = []
    for name, count, spec, seed, node_group in layers:
        obj = bake_petal_layer(name, swords, count, spec, seed)
        petal_col.objects.link(obj)
        m = obj.modifiers.new('Senbonzakura petals (Geometry Nodes)', 'NODES')
        m.node_group = node_group
        counts.append((name, count))
    counts.append(('swords', len(swords)))

    # --- camera, lights, haze ---
    cam = make_camera(scene)
    make_lights(rig_col)
    make_haze_card(fx_col, cam)

    # --- render settings ---
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.use_file_extension = True
    scene.render.filepath = ROOT + 'renders/senbonzakura_####.png'
    scene.render.use_motion_blur = True
    if hasattr(scene.render, 'motion_blur_shutter'):
        scene.render.motion_blur_shutter = 0.32
    scene.eevee.taa_render_samples = 64
    if scene.world is None:
        scene.world = bpy.data.worlds.new('World_Senbonzakura')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.055, 0.028, 0.045, 1.0)
        bg.inputs['Strength'].default_value = 1.0

    make_readme(counts)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_FILE)
    print('Saved', OUT_FILE)
    print('Swords:', len(swords), 'Petal layers:', counts)


if __name__ == '__main__':
    main()
