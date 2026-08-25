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
from mathutils import Euler, Vector

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
ANCHOR_NDC = (-0.05, -0.15)

# Palette from the petal reference sheet. Blender shader inputs are LINEAR, so
# the sRGB hex values have to be converted or the petals come out chalky white.
def srgb(hexstr):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hexstr.lstrip('#')
    return tuple(lin(int(h[i:i + 2], 16)) for i in (0, 2, 4)) + (1.0,)


C_PETAL_FILL = srgb('#FFC2D6')
C_PETAL_HILT = srgb('#FFE8F1')
C_PETAL_GLOW = srgb('#FF8DB8')
C_PETAL_DEEP = srgb('#F273AC')   # saturated core so lit petals stay pink
C_BLADE_BODY = srgb('#B9C9DC')
C_BLADE_GLOW = srgb('#DCEBFF')


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
        notch = max(0.0, (t - 0.82) / 0.18) ** 1.2
        row = []
        for j in range(cols):
            u = j / (cols - 1) * 2.0 - 1.0
            x = u * w + 0.022 * math.sin(t * 3.1)          # gentle asymmetry
            y = t - 0.10 * notch * (1.0 - abs(u)) ** 1.6   # the tip notch
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
SWORD_W = 0.080


def sword_half_width(t):
    return SWORD_W * (1.0 - t ** 2.4) ** 0.55


def sword_local(t, u):
    """Point on the blade surface in blade-local space (length along +Y, 1 unit
    long). `u` in -1..1 runs across the width."""
    w = sword_half_width(t)
    cx = 0.030 * math.sin(t * math.pi * 0.85)
    x = cx + u * w
    z = 0.011 * (1.0 - abs(u) ** 1.7) * (1.0 - t * 0.6)
    return Vector((x, t, z))


def build_swords_mesh(swords):
    """All blades baked into ONE mesh in world space, carrying the per-vertex
    attributes the geometry nodes tree needs. No instancing -- that keeps the
    erosion (which deletes real faces) trivial and attribute-safe."""
    # Lots of sections along the length: the erosion deletes whole faces, so
    # face size is what limits how ragged the dissolve front can look.
    sections, across = 44, 5
    verts, faces = [], []
    a_u, a_axis, a_len, a_delay, a_edur, a_dt0, a_ddur, a_rest = [], [], [], [], [], [], [], []
    a_to_center = []

    for sw in swords:
        rot = Euler(sw['rot'], 'XYZ').to_matrix()
        axis = (rot @ Vector((0.0, 1.0, 0.0))).normalized()
        base = Vector(sw['root'])
        scale = Vector((sw['wid'], sw['len'], sw['wid']))

        def place(t, u):
            p = sword_local(t, u)
            p = Vector((p.x * scale.x, p.y * scale.y, p.z * scale.z))
            return base + rot @ p

        top_idx, bot_idx = [], []
        for i in range(sections):
            t = i / (sections - 1)
            trow, brow = [], []
            for j in range(across):
                u = j / (across - 1) * 2.0 - 1.0
                p = place(t, u)
                centre = place(t, 0.0)
                n = rot @ Vector((0.0, 0.0, 1.0))
                for side, store in ((1.0, trow), (-1.0, brow)):
                    store.append(len(verts))
                    vp = p + n * (side * 0.010 * sw['wid'])
                    verts.append(tuple(vp))
                    # Translation-invariant, so it stays correct after the blade
                    # has been slid up out of the ground.
                    a_to_center.append(tuple(centre - vp))
                    a_u.append(t)
                    a_axis.append(tuple(axis))
                    a_len.append(sw['len'])
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
    store('sw_axis', 'FLOAT_VECTOR', a_axis)
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
    """Three depth rows fanning open behind the anchor, as in the Bankai shot:
    blades near screen centre stay vertical, outer blades splay outward."""
    rng = random.Random(20260825)
    rows = [
        # (z depth, count, ndc half-spread, length range, width range)
        (-11.0, 13, 1.34, (14.0, 19.0), (1.5, 2.2)),
        (-5.5, 9, 1.16, (11.5, 15.5), (1.2, 1.8)),
        (-1.5, 6, 1.00, (9.0, 12.5), (1.0, 1.4)),
    ]
    swords = []
    for ri, (z, count, spread, lrange, wrange) in enumerate(rows):
        for i in range(count):
            nx = -spread + (2 * spread) * (i / max(1, count - 1))
            nx += rng.uniform(-0.05, 0.05)
            # Keep the blade line clear of the exact anchor column so the swarm
            # reads as emerging *around* the character, not through them.
            if abs(nx - ANCHOR_NDC[0]) < 0.10:
                nx += 0.14 * (1 if nx >= ANCHOR_NDC[0] else -1)
            root = ndc_to_world(nx, -1.30 - rng.uniform(0.0, 0.12), z)
            # Outer blades lean outward -> the signature fan.
            lean = -nx * 0.52 + rng.uniform(-0.07, 0.07)
            tilt = rng.uniform(-0.16, 0.16)
            swords.append({
                'root': tuple(root),
                'rot': (tilt, rng.uniform(-0.5, 0.5), lean),
                'len': rng.uniform(*lrange),
                'wid': rng.uniform(*wrange),
                'z': z,
                # Emergence finishes by frame 10; erosion starts after that, so
                # blades are static while they shed petals (birth points stay put).
                'delay': abs(nx) * 1.9 + rng.uniform(0.0, 0.5),
                'edur': rng.uniform(5.5, 7.0),
                'dt0': 10.0 + abs(nx) * 1.6 + rng.uniform(0.0, 1.2),
                'ddur': rng.uniform(6.0, 8.0),
                'row': ri,
            })
    return swords


def sword_surface_point(sw, t, u, jitter_rng):
    rot = Euler(sw['rot'], 'XYZ').to_matrix()
    p = sword_local(t, u)
    p = Vector((p.x * sw['wid'], p.y * sw['len'], p.z * sw['wid']))
    world = Vector(sw['root']) + rot @ p
    world += Vector((jitter_rng.uniform(-0.05, 0.05),
                     jitter_rng.uniform(-0.05, 0.05),
                     jitter_rng.uniform(-0.05, 0.05)))
    return world, rot


# ============================================================================
# Petal trajectory baking
# ============================================================================

def bake_petal_layer(name, swords, count, spec, seed):
    """Every petal is born on a blade at the moment the erosion front reaches
    it, then flies a quadratic bezier to a destination expressed in camera NDC.
    All of that is baked into point attributes here."""
    rng = random.Random(seed)
    weights = [sw['len'] for sw in swords]
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

        dest = spec['dest'](rng, sw, i, count)
        nx, ny, z_end, arrive, size = dest
        e = ndc_to_world(nx, ny, z_end)

        life = max(4.0, arrive - tb)
        bias = spec['ctrl_bias']
        c = Vector((
            birth.x + (e.x - birth.x) * (bias[0] + rng.uniform(-0.08, 0.08)),
            birth.y + (e.y - birth.y) * (bias[1] + rng.uniform(-0.08, 0.08)),
            birth.z + (e.z - birth.z) * (bias[2] + rng.uniform(-0.08, 0.08)),
        ))

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
        nx = rng.uniform(1.20, 2.40)
        ny = rng.uniform(0.55, 1.90)
        z = rng.uniform(-13.0, -2.0)
        arrive = rng.uniform(40.0, 56.0)
        size = rng.uniform(0.14, 0.40)
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        'ctrl_bias': (0.62, 0.20, 0.50),   # go right first, curve up later
        'exit_speed': lambda r: r.uniform(0.30, 0.60),
        'start_scale': lambda r: r.uniform(0.45, 0.75),
        'grow': lambda r: 0.0,
        'ease': lambda r: r.uniform(1.15, 1.45),
        'wobble': lambda r: r.uniform(0.06, 0.22),
        'spin': lambda r: r.uniform(0.05, 0.16),
    }


def spec_mid():
    def dest(rng, sw, i, count):
        nx = rng.uniform(1.10, 2.10)
        ny = rng.uniform(0.45, 1.70)
        z = rng.uniform(-1.0, 8.5)
        arrive = rng.uniform(36.0, 54.0)
        size = rng.uniform(0.30, 0.88)
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        'ctrl_bias': (0.58, 0.22, 0.42),
        'exit_speed': lambda r: r.uniform(0.45, 0.85),
        'start_scale': lambda r: r.uniform(0.40, 0.70),
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
        size = world_cell * rng.uniform(1.65, 2.35)
        return nx, ny, z, arrive, size
    return {
        'dest': dest,
        # Hold back, drift right/up, then swing hard toward the lens.
        'ctrl_bias': (0.60, 0.34, 0.16),
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
        z = rng.uniform(18.2, 20.2)
        arrive = rng.uniform(42.0, 61.0)
        size = rng.uniform(0.22, 0.55)
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
    s = ng.interface.new_socket(name='Emerge Height', in_out='INPUT', socket_type='NodeSocketFloat')
    s.default_value, s.min_value, s.max_value = 1.18, 0.0, 3.0
    s.description = 'How far below ground each blade starts, as a fraction of its length.'
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
    axis = nb.attr('sw_axis', 'FLOAT_VECTOR')
    length = nb.attr('sw_len')
    delay = nb.attr('sw_delay')
    edur = nb.attr('sw_edur')
    dt0 = nb.attr('sw_dt0')
    ddur = nb.attr('sw_ddur')
    rest = nb.attr('rest_pos', 'FLOAT_VECTOR')
    to_center = nb.attr('to_center', 'FLOAT_VECTOR')

    # --- erosion front travels tip (u=1) -> root (u=0) ---
    prog = nb.math('DIVIDE', nb.math('SUBTRACT', frame, dt0), ddur, clamp=True)
    front = nb.math('SUBTRACT', 1.0, prog)
    noise = nb.new('ShaderNodeTexNoise')
    nb.plug(noise, 'Vector', nb.vmath('SCALE', rest, scale=6.0))
    nb.plug(noise, 'Scale', 1.0)
    nb.plug(noise, 'Detail', 4.0)
    jag = nb.math('MULTIPLY', nb.math('SUBTRACT', noise.outputs['Factor'], 0.5),
                  gi.outputs['Erosion Roughness'])
    front_n = nb.math('ADD', front, jag)

    # distance behind the front, in blade-length units
    d = nb.math('MAXIMUM', nb.math('SUBTRACT', front_n, blade_u), 0.0)

    # --- emergence: slide up along the blade's own axis, ease-out ---
    e = nb.math('SUBTRACT', frame, nb.math('ADD', delay, 1.0))
    e = nb.math('DIVIDE', e, edur, clamp=True)
    inv = nb.math('SUBTRACT', 1.0, e)
    inv3 = nb.math('POWER', inv, 3.0)                 # (1-e)^3
    drop = nb.math('MULTIPLY', inv3, nb.math('MULTIPLY', length, gi.outputs['Emerge Height']))
    offset = nb.vmath('SCALE', axis, scale=nb.math('MULTIPLY', drop, -1.0))

    # --- taper: pull the surface toward the centreline as the front approaches,
    # so the blade erodes to a needle instead of a blunt bright stump ---
    shrink = nb.math('SUBTRACT', 1.0,
                     nb.math('DIVIDE', d, gi.outputs['Front Taper'], clamp=True))
    offset = nb.vmath('ADD', offset, nb.vmath('SCALE', to_center, scale=shrink))

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
    edge.inputs[1].default_value = 0.8; edge.location = (-600, 0)
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
    # the silhouette.
    rim = nt.nodes.new('ShaderNodeMath'); rim.operation = 'POWER'
    rim.inputs[1].default_value = 3.0; rim.location = (-420, -380)
    nt.links.new(a_s.outputs['Fac'], rim.inputs[0])
    rim2 = nt.nodes.new('ShaderNodeMath'); rim2.operation = 'MULTIPLY_ADD'
    rim2.inputs[1].default_value = 0.80
    rim2.inputs[2].default_value = 0.24
    rim2.location = (-240, -380)
    nt.links.new(rim.outputs[0], rim2.inputs[0])
    nt.links.new(rim2.outputs[0], bsdf.inputs['Emission Strength'])
    bsdf.inputs['Emission Color'].default_value = C_PETAL_GLOW

    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.42
    bsdf.inputs['Sheen Weight'].default_value = 0.45
    bsdf.inputs['Sheen Roughness'].default_value = 0.30
    bsdf.inputs['Sheen Tint'].default_value = C_PETAL_HILT
    if 'Thin Wall' in bsdf.inputs:
        bsdf.inputs['Thin Wall'].default_value = True
    bsdf.inputs['Subsurface Weight'].default_value = 0.22
    bsdf.inputs['Subsurface Radius'].default_value = (0.9, 0.42, 0.55)
    bsdf.inputs['Subsurface Scale'].default_value = 0.05
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

    bsdf.inputs['Base Color'].default_value = C_BLADE_BODY
    bsdf.inputs['Metallic'].default_value = 0.72
    bsdf.inputs['Roughness'].default_value = 0.17

    # Fresnel-driven edge light: gives the blades the luminous silhouette they
    # have in the Bankai shot without needing an HDRI.
    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.location = (-700, 240)
    lw.inputs['Blend'].default_value = 0.38
    fres = nt.nodes.new('ShaderNodeMath'); fres.operation = 'POWER'
    fres.inputs[1].default_value = 2.2; fres.location = (-500, 240)
    nt.links.new(lw.outputs['Fresnel'], fres.inputs[0])
    fres2 = nt.nodes.new('ShaderNodeMath'); fres2.operation = 'MULTIPLY_ADD'
    fres2.inputs[1].default_value = 6.0     # bright glowing edge
    fres2.inputs[2].default_value = 0.55    # body never goes fully dark
    fres2.location = (-320, 240)
    nt.links.new(fres.outputs[0], fres2.inputs[0])

    # Hot band trailing the erosion front.
    glow = nt.nodes.new('ShaderNodeAttribute')
    glow.attribute_name = 'diss_glow'; glow.location = (-700, -80)
    gp = nt.nodes.new('ShaderNodeMath'); gp.operation = 'POWER'
    gp.inputs[1].default_value = 1.8; gp.location = (-500, -80)
    nt.links.new(glow.outputs['Fac'], gp.inputs[0])
    gm = nt.nodes.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'
    gm.inputs[1].default_value = 3.0; gm.location = (-320, -80)
    nt.links.new(gp.outputs[0], gm.inputs[0])

    total = nt.nodes.new('ShaderNodeMath'); total.operation = 'ADD'; total.location = (-120, 120)
    nt.links.new(fres2.outputs[0], total.inputs[0])
    nt.links.new(gm.outputs[0], total.inputs[1])
    nt.links.new(total.outputs[0], bsdf.inputs['Emission Strength'])

    ecol = nt.nodes.new('ShaderNodeMix'); ecol.data_type = 'RGBA'; ecol.location = (-120, -120)
    ecol.inputs[6].default_value = C_BLADE_GLOW
    ecol.inputs[7].default_value = C_PETAL_FILL
    nt.links.new(gp.outputs[0], ecol.inputs[0])
    nt.links.new(ecol.outputs[2], bsdf.inputs['Emission Color'])
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
    em.inputs['Strength'].default_value = 1.15
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

    # The engulfment window. Peaks exactly on the storyboard's cut point.
    for frame, value in ((49, 0.0), (52, 0.26), (55, 0.50),
                         (60, 0.55), (63, 0.18), (65, 0.0)):
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
    w('  10-20  blades erode tip->root; petals are born on the surface the\n')
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
    w('  Senbonzakura_Swords   all blades in one mesh + the emerge/erode nodes\n')
    w('  Petals_FAR / MID      the flowing background and midground swarm\n')
    w('  Petals_NEAR_WAVE      the foreground petals that engulf the frame\n')
    w('  Petals_CROSSERS       fragments that punch past the camera plane\n')
    w('  Petal_SOURCE          the instanced sakura petal (hidden)\n')
    w('  FX_Petal_Haze         soft pink card that seals the alpha at 53-62\n')
    w('  Camera_Senbonzakura   50mm at +Z looking down -Z; X=right, Y=up\n\n')
    w('COUNTS\n')
    for name, n in counts:
        w('  %-20s %d\n' % (name, n))
    w('\nTUNING\n')
    w('  Sword modifier: Emerge Height, Erosion Roughness, Front Glow Width,\n')
    w('    Front Taper (how far back the blade necks down as it erodes --\n')
    w('    set it to 0 to see why it exists).\n')
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

    # --- swords ---
    swords = layout_swords()
    sword_obj = build_swords_mesh(swords)
    sword_col.objects.link(sword_obj)
    sword_ng = make_sword_nodes('GN_Senbonzakura_Swords')
    mod = sword_obj.modifiers.new('Emerge + erode (Geometry Nodes)', 'NODES')
    mod.node_group = sword_ng

    # --- petals ---
    petal_ng = make_petal_nodes('GN_Senbonzakura_Petals', petal_src)
    layers = [
        ('Petals_FAR', 900, spec_far(), 101),
        ('Petals_MID', 620, spec_mid(), 202),
        # Four staggered depths so coverage builds through 46-52, holds solid
        # through 53-60, then unloads. Grid is 10x7 per wave.
        ('Petals_NEAR_WAVE', 420, spec_near(
            [(9.5, 47.5, 51.5), (11.5, 50.0, 54.0),
             (13.0, 52.5, 56.5), (14.2, 55.0, 59.5)], 10, 7), 303),
        ('Petals_CROSSERS', 80, spec_crossers(), 404),
    ]
    counts = []
    for name, count, spec, seed in layers:
        obj = bake_petal_layer(name, swords, count, spec, seed)
        petal_col.objects.link(obj)
        m = obj.modifiers.new('Senbonzakura petals (Geometry Nodes)', 'NODES')
        m.node_group = petal_ng
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
