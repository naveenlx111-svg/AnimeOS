import bpy
import math
import random
from mathutils import Vector


ROOT = bpy.path.abspath('//')
OUT_FILE = ROOT + 'senbonzakura_prototype.blend'


def clear_collection_objects(collection):
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def get_or_create_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def link_only(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)


def make_material():
    mat = bpy.data.materials.get('MAT_SakuraBlade_Pearl') or bpy.data.materials.new('MAT_SakuraBlade_Pearl')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (0.98, 0.32, 0.60, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.18
    bsdf.inputs['Roughness'].default_value = 0.26
    if 'Coat Weight' in bsdf.inputs:
        bsdf.inputs['Coat Weight'].default_value = 0.30
    if 'Coat Roughness' in bsdf.inputs:
        bsdf.inputs['Coat Roughness'].default_value = 0.16
    if 'Emission Color' in bsdf.inputs:
        bsdf.inputs['Emission Color'].default_value = (1.0, 0.025, 0.18, 1.0)
        bsdf.inputs['Emission Strength'].default_value = 0.28
    return mat


def make_dark_material():
    mat = bpy.data.materials.get('MAT_Preview_Backdrop') or bpy.data.materials.new('MAT_Preview_Backdrop')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (0.003, 0.005, 0.012, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.6
    return mat


def make_fragment(source_collection):
    # A thin, gently curved 3-D shard: tapered silhouette, raised center ridge, beveled edges.
    name = 'Senbonzakura_Fragment_SOURCE'
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    sections = 15
    across = 5
    verts = []
    top_idx = []
    bot_idx = []
    for i in range(sections):
        t = i / (sections - 1)
        y = (t - 0.5) * 2.8
        # Asymmetric, blade-like taper; the upper tip is slightly skewed.
        w = 0.032 + 0.19 * math.sin(math.pi * t) ** 0.72
        if t < 0.18:
            w *= 0.55 + 2.5 * t
        if t > 0.82:
            w *= 0.72 + 1.5 * (1.0 - t)
        cx = 0.075 * math.sin((t - 0.10) * math.pi * 1.2) + 0.035 * (t - 0.5)
        top_row = []
        bot_row = []
        for j in range(across):
            u = j / (across - 1) * 2.0 - 1.0
            x = cx + u * w
            ridge = 0.055 * (1.0 - abs(u) ** 1.65) * math.sin(math.pi * t) ** 0.7
            z_top = 0.045 + ridge + 0.02 * math.sin(t * math.pi)
            z_bot = -0.045 + 0.008 * math.cos(t * math.pi)
            top_row.append(len(verts)); verts.append((x, y, z_top))
            bot_row.append(len(verts)); verts.append((x, y, z_bot))
        top_idx.append(top_row)
        bot_idx.append(bot_row)

    faces = []
    for i in range(sections - 1):
        for j in range(across - 1):
            a, b = top_idx[i][j], top_idx[i][j + 1]
            c, d = top_idx[i + 1][j + 1], top_idx[i + 1][j]
            faces.append((a, b, c, d))
            a, b = bot_idx[i][j + 1], bot_idx[i][j]
            c, d = bot_idx[i + 1][j], bot_idx[i + 1][j + 1]
            faces.append((a, b, c, d))
        for row_a, row_b in ((top_idx, bot_idx),):
            a, b = row_a[i][0], row_a[i + 1][0]
            c, d = row_b[i + 1][0], row_b[i][0]
            faces.append((a, b, c, d))
            a, b = row_a[i + 1][-1], row_a[i][-1]
            c, d = row_b[i][-1], row_b[i + 1][-1]
            faces.append((a, b, c, d))
    faces.append(tuple(reversed(top_idx[0])))
    faces.append(tuple(bot_idx[0]))
    faces.append(tuple(top_idx[-1]))
    faces.append(tuple(reversed(bot_idx[-1])))

    mesh = bpy.data.meshes.new('Senbonzakura_Fragment_MESH')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    source_collection.objects.link(obj)
    obj.data.materials.append(make_material())
    for p in mesh.polygons:
        p.use_smooth = True

    bevel = obj.modifiers.new('Edge softness (tiny bevel)', 'BEVEL')
    bevel.width = 0.018
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    weighted = obj.modifiers.new('Weighted blade normals', 'WEIGHTED_NORMAL')
    weighted.keep_sharp = True
    obj.hide_render = True
    obj.hide_set(True)
    obj['README'] = 'Canonical Senbonzakura blade/petal shard. Keep separate from particle layers.'
    return obj


def make_point_mesh(name, count, seed, layer):
    rng = random.Random(seed)
    verts = []
    velocities = []
    rotations = []
    scales = []
    delays = []
    swirls = []
    if layer == 'FAR':
        z0, xspread, ytop = -3.8, 4.6, -3.0
        target_x, target_y, target_z = (-7.8, 7.8), (-4.4, 4.4), (-4.0, 2.5)
        scale_range, delay_range = (0.045, 0.12), (0.0, 12.0)
    elif layer == 'MID':
        z0, xspread, ytop = -1.2, 3.8, -2.75
        target_x, target_y, target_z = (-5.2, 5.2), (-3.1, 3.1), (2.0, 8.0)
        scale_range, delay_range = (0.09, 0.25), (4.0, 18.0)
    else:
        z0, xspread, ytop = 1.5, 3.2, -2.45
        target_x, target_y, target_z = (-2.5, 2.5), (-1.5, 1.5), (9.0, 15.0)
        scale_range, delay_range = (0.18, 0.52), (9.0, 24.0)

    for _ in range(count):
        x = rng.uniform(-xspread, xspread)
        y = rng.uniform(-6.2, ytop)
        z = z0 + rng.uniform(-0.7, 0.7)
        verts.append((x, y, z))
        tx = rng.uniform(*target_x)
        ty = rng.uniform(*target_y)
        # A subtle diagonal bias prevents the field feeling like an even grid.
        tx += 0.18 * ty + rng.uniform(-0.3, 0.3)
        tz = rng.uniform(*target_z)
        vx = tx - x
        vy = ty - y
        vz = tz - z
        velocities.append((vx, vy, vz))
        rotations.append((rng.uniform(-0.7, 0.7), rng.uniform(-0.7, 0.7), rng.uniform(-math.pi, math.pi)))
        scales.append(rng.uniform(*scale_range))
        delays.append(rng.uniform(*delay_range))
        handed = -1.0 if rng.random() < 0.52 else 1.0
        swirls.append((handed * -vy * rng.uniform(0.18, 0.48), handed * vx * rng.uniform(0.18, 0.48), rng.uniform(-1.2, 1.2)))

    mesh = bpy.data.meshes.new(name + '_MESH')
    mesh.from_pydata(verts, [], [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    attr = mesh.attributes.new('blade_velocity', 'FLOAT_VECTOR', 'POINT')
    attr_rot = mesh.attributes.new('blade_rot', 'FLOAT_VECTOR', 'POINT')
    attr_scale = mesh.attributes.new('blade_scale', 'FLOAT', 'POINT')
    attr_delay = mesh.attributes.new('blade_delay', 'FLOAT', 'POINT')
    attr_swirl = mesh.attributes.new('blade_swirl', 'FLOAT_VECTOR', 'POINT')
    for i in range(count):
        attr.data[i].vector = velocities[i]
        attr_rot.data[i].vector = rotations[i]
        attr_scale.data[i].value = scales[i]
        attr_delay.data[i].value = delays[i]
        attr_swirl.data[i].vector = swirls[i]
    obj['Particle layer'] = layer
    obj['README'] = 'Edit this layer modifier inputs to tune count, burst timing, speed, swirl, and scale.'
    return obj


def iface_socket(ng, name, in_out, socket_type, default=None, min_value=None, max_value=None, description=''):
    s = ng.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    if description:
        s.description = description
    if default is not None:
        s.default_value = default
    if min_value is not None:
        s.min_value = min_value
    if max_value is not None:
        s.max_value = max_value
    return s


def make_particle_nodes(name, source, default_count, start_frame, duration, clear_frame, velocity_multiplier, start_scale, burst_scale, seed):
    ng = bpy.data.node_groups.get(name)
    if ng:
        bpy.data.node_groups.remove(ng, do_unlink=True)
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    iface_socket(ng, 'Geometry', 'INPUT', 'NodeSocketGeometry')
    iface_socket(ng, 'Geometry', 'OUTPUT', 'NodeSocketGeometry')
    iface_socket(ng, 'Particle Count', 'INPUT', 'NodeSocketInt', default_count, 1, 10000, 'Visible point count for this layer.')
    iface_socket(ng, 'Burst Frame', 'INPUT', 'NodeSocketFloat', start_frame, 0, 250, 'Frame where acceleration begins.')
    iface_socket(ng, 'Burst Duration', 'INPUT', 'NodeSocketFloat', duration, 1, 120, 'Frames over which particles reach full travel.')
    iface_socket(ng, 'Clear Frame', 'INPUT', 'NodeSocketFloat', clear_frame, 0, 300, 'Particles scale to zero after this frame.')
    iface_socket(ng, 'Drift Speed', 'INPUT', 'NodeSocketFloat', 0.004, 0, 0.1, 'Slow pre-burst motion; small values are best.')
    iface_socket(ng, 'Velocity Multiplier', 'INPUT', 'NodeSocketFloat', velocity_multiplier, 0, 5, 'Multiplies each baked per-particle velocity.')
    iface_socket(ng, 'Direction Bias', 'INPUT', 'NodeSocketVector', (0.0, 0.0, 0.0), description='Adds a global XYZ direction to the varied per-particle paths.')
    iface_socket(ng, 'Swirl Strength', 'INPUT', 'NodeSocketFloat', 0.38, 0, 5, 'Organic sideways sweep during the burst.')
    iface_socket(ng, 'Start Scale', 'INPUT', 'NodeSocketFloat', start_scale, 0, 1, 'Scale before the burst.')
    iface_socket(ng, 'Burst Scale', 'INPUT', 'NodeSocketFloat', burst_scale, 0, 5, 'Scale at full travel.')
    iface_socket(ng, 'Rotation Speed', 'INPUT', 'NodeSocketVector', (0.7, 1.2, 2.0), description='Angular speed vector during the burst.')
    iface_socket(ng, 'Seed Offset', 'INPUT', 'NodeSocketInt', seed, 0, 1000, 'Per-layer variation seed (stored for organization).')

    n = ng.nodes; l = ng.links
    n.clear()
    gi = n.new('NodeGroupInput'); gi.location = (-1100, 120)
    go = n.new('NodeGroupOutput'); go.location = (780, 100)
    idx = n.new('GeometryNodeInputIndex'); idx.location = (-1050, -320)
    cmp_count = n.new('FunctionNodeCompare'); cmp_count.data_type = 'INT'; cmp_count.operation = 'GREATER_EQUAL'; cmp_count.location = (-850, -320)
    l.new(idx.outputs['Index'], cmp_count.inputs['A']); l.new(gi.outputs['Particle Count'], cmp_count.inputs['B'])
    delete = n.new('GeometryNodeDeleteGeometry'); delete.domain = 'POINT'; delete.location = (-660, 100)
    l.new(gi.outputs['Geometry'], delete.inputs['Geometry']); l.new(cmp_count.outputs['Result'], delete.inputs['Selection'])

    time = n.new('GeometryNodeInputSceneTime'); time.location = (-1050, -20)
    sub0 = n.new('ShaderNodeMath'); sub0.operation = 'SUBTRACT'; sub0.location = (-850, -20)
    l.new(time.outputs['Frame'], sub0.inputs[0]); l.new(gi.outputs['Burst Frame'], sub0.inputs[1])
    delay = n.new('GeometryNodeInputNamedAttribute'); delay.data_type = 'FLOAT'; delay.inputs['Name'].default_value = 'blade_delay'; delay.location = (-1050, -170)
    sub1 = n.new('ShaderNodeMath'); sub1.operation = 'SUBTRACT'; sub1.location = (-650, -20)
    l.new(sub0.outputs[0], sub1.inputs[0]); l.new(delay.outputs['Attribute'], sub1.inputs[1])
    div = n.new('ShaderNodeMath'); div.operation = 'DIVIDE'; div.location = (-470, -20)
    l.new(sub1.outputs[0], div.inputs[0]); l.new(gi.outputs['Burst Duration'], div.inputs[1])
    mx = n.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; mx.location = (-290, -20); mx.inputs[1].default_value = 0.0
    l.new(div.outputs[0], mx.inputs[0])
    mn = n.new('ShaderNodeMath'); mn.operation = 'MINIMUM'; mn.location = (-110, -20); mn.inputs[1].default_value = 1.0
    l.new(mx.outputs[0], mn.inputs[0])
    progress = mn.outputs[0]

    vel = n.new('GeometryNodeInputNamedAttribute'); vel.data_type = 'FLOAT_VECTOR'; vel.inputs['Name'].default_value = 'blade_velocity'; vel.location = (-460, 220)
    biasadd = n.new('ShaderNodeVectorMath'); biasadd.operation = 'ADD'; biasadd.location = (-285, 220)
    l.new(vel.outputs['Attribute'], biasadd.inputs[0]); l.new(gi.outputs['Direction Bias'], biasadd.inputs[1])
    vmul = n.new('ShaderNodeVectorMath'); vmul.operation = 'SCALE'; vmul.location = (-100, 220)
    l.new(biasadd.outputs['Vector'], vmul.inputs[0]); l.new(gi.outputs['Velocity Multiplier'], vmul.inputs[3]); l.new(progress, vmul.inputs[1])

    # Slow pre-burst drift, capped at the burst frame so the burst target stays stable.
    drift_cap = n.new('ShaderNodeMath'); drift_cap.operation = 'MINIMUM'; drift_cap.location = (-650, 520)
    l.new(time.outputs['Frame'], drift_cap.inputs[0]); l.new(gi.outputs['Burst Frame'], drift_cap.inputs[1])
    drift_amt = n.new('ShaderNodeMath'); drift_amt.operation = 'MULTIPLY'; drift_amt.location = (-470, 520)
    l.new(drift_cap.outputs[0], drift_amt.inputs[0]); l.new(gi.outputs['Drift Speed'], drift_amt.inputs[1])
    drift_vec = n.new('ShaderNodeVectorMath'); drift_vec.operation = 'SCALE'; drift_vec.location = (-280, 520)
    l.new(vel.outputs['Attribute'], drift_vec.inputs[0]); l.new(drift_amt.outputs[0], drift_vec.inputs[3])
    swirl = n.new('GeometryNodeInputNamedAttribute'); swirl.data_type = 'FLOAT_VECTOR'; swirl.inputs['Name'].default_value = 'blade_swirl'; swirl.location = (-460, 400)
    sine_mul = n.new('ShaderNodeMath'); sine_mul.operation = 'MULTIPLY'; sine_mul.location = (-100, -170); sine_mul.inputs[1].default_value = math.pi
    l.new(progress, sine_mul.inputs[0])
    sine = n.new('ShaderNodeMath'); sine.operation = 'SINE'; sine.location = (80, -170); l.new(sine_mul.outputs[0], sine.inputs[0])
    swirl_scale = n.new('ShaderNodeVectorMath'); swirl_scale.operation = 'SCALE'; swirl_scale.location = (220, 400)
    l.new(swirl.outputs['Attribute'], swirl_scale.inputs[0]); l.new(sine.outputs[0], swirl_scale.inputs[1]); l.new(gi.outputs['Swirl Strength'], swirl_scale.inputs[3])
    burst_offset = n.new('ShaderNodeVectorMath'); burst_offset.operation = 'ADD'; burst_offset.location = (390, 250)
    l.new(vmul.outputs['Vector'], burst_offset.inputs[0]); l.new(swirl_scale.outputs['Vector'], burst_offset.inputs[1])
    offset = n.new('ShaderNodeVectorMath'); offset.operation = 'ADD'; offset.location = (540, 330)
    l.new(burst_offset.outputs['Vector'], offset.inputs[0]); l.new(drift_vec.outputs['Vector'], offset.inputs[1])
    setpos = n.new('GeometryNodeSetPosition'); setpos.location = (-30, 100)
    l.new(delete.outputs['Geometry'], setpos.inputs['Geometry']); l.new(offset.outputs['Vector'], setpos.inputs['Offset'])

    objinfo = n.new('GeometryNodeObjectInfo'); objinfo.location = (0, 640); objinfo.inputs['Object'].default_value = source; objinfo.inputs['As Instance'].default_value = True
    inst = n.new('GeometryNodeInstanceOnPoints'); inst.location = (220, 100)
    l.new(setpos.outputs['Geometry'], inst.inputs['Points']); l.new(objinfo.outputs['Geometry'], inst.inputs['Instance'])

    pscale = n.new('GeometryNodeInputNamedAttribute'); pscale.data_type = 'FLOAT'; pscale.inputs['Name'].default_value = 'blade_scale'; pscale.location = (-20, -420)
    span = n.new('ShaderNodeMath'); span.operation = 'SUBTRACT'; span.location = (140, -330)
    l.new(gi.outputs['Burst Scale'], span.inputs[0]); l.new(gi.outputs['Start Scale'], span.inputs[1])
    span_mul = n.new('ShaderNodeMath'); span_mul.operation = 'MULTIPLY'; span_mul.location = (320, -250); l.new(progress, span_mul.inputs[0]); l.new(span.outputs[0], span_mul.inputs[1])
    add_scale = n.new('ShaderNodeMath'); add_scale.operation = 'ADD'; add_scale.location = (480, -250); l.new(span_mul.outputs[0], add_scale.inputs[0]); l.new(gi.outputs['Start Scale'], add_scale.inputs[1])
    scale_mul = n.new('ShaderNodeMath'); scale_mul.operation = 'MULTIPLY'; scale_mul.location = (650, -250); l.new(pscale.outputs['Attribute'], scale_mul.inputs[0]); l.new(add_scale.outputs[0], scale_mul.inputs[1])
    clear_sub = n.new('ShaderNodeMath'); clear_sub.operation = 'SUBTRACT'; clear_sub.location = (300, -420)
    l.new(time.outputs['Frame'], clear_sub.inputs[0]); l.new(gi.outputs['Clear Frame'], clear_sub.inputs[1])
    clear_div = n.new('ShaderNodeMath'); clear_div.operation = 'DIVIDE'; clear_div.location = (470, -420); clear_div.inputs[1].default_value = 4.0; l.new(clear_sub.outputs[0], clear_div.inputs[0])
    clear_max = n.new('ShaderNodeMath'); clear_max.operation = 'MAXIMUM'; clear_max.location = (630, -420); clear_max.inputs[1].default_value = 0.0; l.new(clear_div.outputs[0], clear_max.inputs[0])
    clear_min = n.new('ShaderNodeMath'); clear_min.operation = 'MINIMUM'; clear_min.location = (790, -420); clear_min.inputs[1].default_value = 1.0; l.new(clear_max.outputs[0], clear_min.inputs[0])
    clear_inv = n.new('ShaderNodeMath'); clear_inv.operation = 'SUBTRACT'; clear_inv.location = (950, -420); clear_inv.inputs[0].default_value = 1.0; l.new(clear_min.outputs[0], clear_inv.inputs[1])
    final_scale = n.new('ShaderNodeMath'); final_scale.operation = 'MULTIPLY'; final_scale.location = (950, -250); l.new(scale_mul.outputs[0], final_scale.inputs[0]); l.new(clear_inv.outputs[0], final_scale.inputs[1])
    scale_vec = n.new('ShaderNodeCombineXYZ'); scale_vec.location = (820, -250)
    for sock in scale_vec.inputs:
        l.new(final_scale.outputs[0], sock)
    scale_instances = n.new('GeometryNodeScaleInstances'); scale_instances.location = (440, 100); l.new(inst.outputs['Instances'], scale_instances.inputs['Instances']); l.new(scale_vec.outputs['Vector'], scale_instances.inputs['Scale'])

    rot = n.new('GeometryNodeInputNamedAttribute'); rot.data_type = 'FLOAT_VECTOR'; rot.inputs['Name'].default_value = 'blade_rot'; rot.location = (0, -580)
    rspeed = n.new('ShaderNodeVectorMath'); rspeed.operation = 'SCALE'; rspeed.location = (180, -580); l.new(gi.outputs['Rotation Speed'], rspeed.inputs[0]); l.new(progress, rspeed.inputs[3])
    rotadd = n.new('ShaderNodeVectorMath'); rotadd.operation = 'ADD'; rotadd.location = (360, -580); l.new(rot.outputs['Attribute'], rotadd.inputs[0]); l.new(rspeed.outputs['Vector'], rotadd.inputs[1])
    rotate = n.new('GeometryNodeRotateInstances'); rotate.location = (620, 100); l.new(scale_instances.outputs['Instances'], rotate.inputs['Instances']); l.new(rotadd.outputs['Vector'], rotate.inputs['Rotation'])
    l.new(rotate.outputs['Instances'], go.inputs['Geometry'])
    return ng


def add_layer(collection, source, name, count, seed, layer, vel_mult, burst_scale):
    mesh_obj = make_point_mesh(name + '_POINTS', count, seed, layer)
    collection.objects.link(mesh_obj)
    ng = make_particle_nodes(name + '_NODES', source, count, 22, 12, 45, vel_mult, 0.018, burst_scale, seed)
    mod = mesh_obj.modifiers.new('Senbonzakura controls (Geometry Nodes)', 'NODES')
    mod.node_group = ng
    mesh_obj['Controls'] = 'Open this modifier: Particle Count, Burst Frame, Burst Duration, Clear Frame, Drift Speed, Velocity Multiplier, Direction Bias, Swirl Strength, Start Scale, Burst Scale, Rotation Speed.'
    return mesh_obj


def make_camera(scene):
    cam_data = bpy.data.cameras.get('Camera_Senbonzakura') or bpy.data.cameras.new('Camera_Senbonzakura')
    cam = bpy.data.objects.get('Camera_Senbonzakura') or bpy.data.objects.new('Camera_Senbonzakura', cam_data)
    if not cam.users_collection:
        scene.collection.objects.link(cam)
    cam.location = (0, 0, 20)
    cam.rotation_euler = (0, 0, 0)
    cam.data.type = 'PERSP'
    cam.data.lens = 50
    cam.data.clip_start = 0.1
    cam.data.clip_end = 100.0
    scene.camera = cam
    return cam


def make_lights(scene):
    for name in ('Light_Sakura_Key', 'Light_Sakura_Rim'):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    def area(name, loc, energy, color, size):
        data = bpy.data.lights.new(name, 'AREA'); data.energy = energy; data.color = color; data.shape = 'DISK'; data.size = size
        obj = bpy.data.objects.new(name, data); scene.collection.objects.link(obj); obj.location = loc
        obj.rotation_euler = (0, 0, 0)
        return obj
    area('Light_Sakura_Key', (-5, 4, 8), 900, (1.0, 0.28, 0.52), 7.0)
    area('Light_Sakura_Rim', (5, -1, 6), 1100, (0.22, 0.34, 1.0), 5.0)


def make_backdrop(collection):
    old = bpy.data.objects.get('Preview_Backdrop_DARK')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -6))
    obj = bpy.context.object; obj.name = 'Preview_Backdrop_DARK'; link_only(obj, collection)
    obj.scale = (12, 7, 1); obj.data.materials.append(make_dark_material())
    obj['README'] = 'Preview only. Disable this collection before transparent compositing if you want alpha over Resolve footage.'
    return obj


def make_readme():
    text = bpy.data.texts.get('README_Senbonzakura') or bpy.data.texts.new('README_Senbonzakura')
    text.clear()
    text.write('SENBONZAKURA PARTICLE PROTOTYPE\n\n')
    text.write('Purpose: reusable thin blade/petal fragment and accelerating screen-sweep effect for DaVinci Resolve compositing.\n\n')
    text.write('IMPORTANT OBJECTS\n')
    text.write('- Senbonzakura_Fragment_SOURCE: canonical polished shard; hidden from render, instanced by all layers.\n')
    text.write('- Senbonzakura_FAR_POINTS / MID_POINTS / FOREGROUND_POINTS: point meshes with Geometry Nodes modifiers.\n')
    text.write('- Camera_Senbonzakura: orthographic 1920x1080 framing.\n')
    text.write('- Preview_Backdrop_DARK: optional dark preview card; put your Resolve footage behind the alpha render later.\n\n')
    text.write('PREVIEW\n')
    text.write('Set the timeline to frames 1-60 and press Space. Sparse drift is frames 1-21; acceleration starts at frame 22; the screen sweep peaks around frames 38-44; fragments clear at frame 45.\n\n')
    text.write('TUNING\n')
    text.write('Select a *_POINTS object, open the Geometry Nodes modifier, and change Particle Count, Burst Frame, Burst Duration, Clear Frame, Drift Speed, Velocity Multiplier, Direction Bias, Swirl Strength, Start Scale, Burst Scale, or Rotation Speed.\n')
    text.write('The point mesh stores deterministic per-particle velocity, rotation, scale, delay, and swirl attributes. No hundreds of real mesh objects are created.\n\n')
    text.write('TRANSPARENT RENDER\n')
    text.write('Output Properties > File Format: PNG or OpenEXR. Film > Transparent is enabled in this file. Render RGBA and import the result over the DaVinci footage. Disable or hide Preview_Backdrop_DARK if it is not wanted in the alpha.\n')
    text.write('Use Eevee for quick previews. 1920x1080 at 24 fps is configured.\n')
    return text


def main():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 60
    scene.render.film_transparent = True
    scene.render.use_file_extension = True
    scene.render.filepath = ROOT + 'renders/senbonzakura_####.png'
    scene.world.color = (0.001, 0.002, 0.008)

    # Preserve the user's original prototype for comparison, but keep it out of the new render.
    ref_col = get_or_create_collection('REFERENCE_Original_Prototype')
    old_plane = bpy.data.objects.get('Plane')
    if old_plane:
        old_plane.name = 'Plane_BeginnerPrototype_REFERENCE'
        link_only(old_plane, ref_col)
        old_plane.hide_render = True
        old_plane.hide_set(True)
    ref_col.hide_render = True
    ref_col.hide_viewport = True

    source_col = get_or_create_collection('SOURCE_Fragment')
    particle_col = get_or_create_collection('PARTICLES_GeometryNodes')
    preview_col = get_or_create_collection('PREVIEW_Optional')
    source = make_fragment(source_col)
    for obj in list(particle_col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    add_layer(particle_col, source, 'Senbonzakura_FAR', 300, 11, 'FAR', 1.0, 0.85)
    add_layer(particle_col, source, 'Senbonzakura_MID', 440, 37, 'MID', 1.0, 1.10)
    add_layer(particle_col, source, 'Senbonzakura_FOREGROUND', 150, 71, 'FOREGROUND', 1.0, 1.55)
    make_camera(scene)
    make_lights(scene)
    make_backdrop(preview_col)
    make_readme()
    preview_col.hide_render = True
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_FILE)
    print('Saved', OUT_FILE)


if __name__ == '__main__':
    main()
