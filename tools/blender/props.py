"""Realistic props for the pizzeria (portable generator, flashlight), modelled procedurally in Blender,
baked to one texture each and exported as .fmesh for the mod.

Run inside Blender:  exec(open(r"<repo>/tools/blender/props.py").read()); build_all()

Units: 1 Blender metre = 1 Minecraft block. Blender (x, y, z) -> Minecraft (x, z, -y), so Blender -Y is the
model's front (Minecraft +Z / south). Faces whose material name starts with "glow" go into a separate
"glow" mesh part (drawn full-bright in game, e.g. the flashlight lens).
"""
import math
import os
import struct

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = r"D:\Five Nights at Freddy’s (Horror)"
ASSETS = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf")


# ---------------------------------------------------------------- materials

def _sock(node, name, kind=None, out=False):
    for s in (node.outputs if out else node.inputs):
        if s.name == name and s.enabled and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def _mix(nt, a, b, fac):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    nt.links.new(fac, _sock(m, "Factor", "VALUE"))
    for name, v in (("A", a), ("B", b)):
        s = _sock(m, name, "RGBA")
        if isinstance(v, tuple):
            s.default_value = (*v, 1.0)
        else:
            nt.links.new(v, s)
    return _sock(m, "Result", "RGBA", out=True)


def _noise(nt, scale, detail=6.0, stretch=(1, 1, 1), lo=0.45, hi=0.62):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = stretch
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = lo
    mr.inputs["From Max"].default_value = hi
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    return mr.outputs["Result"]


def material(name, rgb, rough=0.5, metal=0.0, dirt=0.35, scratches=0.0, grime=(0.09, 0.075, 0.06), image=None):
    """Worn surface: base colour, grime in the noise valleys, thin bright scratches (painted metal)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0   # DIFFUSE bakes come out black for metals; shading comes from AO
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image, check_existing=True)
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "src"
        nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        col = tex.outputs["Color"]
    else:
        rgbn = nt.nodes.new("ShaderNodeRGB")
        rgbn.outputs[0].default_value = (*[(c / 255) ** 2.2 for c in rgb], 1)
        col = rgbn.outputs[0]
    if scratches:
        sc = _noise(nt, 30.0, 2.0, (1, 1, 30), 0.68, 0.71)
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = scratches
        nt.links.new(sc, mul.inputs[0])
        col = _mix(nt, col, (0.16, 0.16, 0.15), mul.outputs[0])
    if dirt:
        d = _noise(nt, 7.0, 10.0, (1, 1, 1), 0.42, 0.62)
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "MULTIPLY_ADD"
        inv.inputs[1].default_value = -dirt
        inv.inputs[2].default_value = dirt
        nt.links.new(d, inv.inputs[0])
        col = _mix(nt, col, tuple(c ** 2.2 for c in grime), inv.outputs[0])
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m


# ---------------------------------------------------------------- geometry helpers

PARTS = []


def _obj(bm, name, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    PARTS.append(o)
    return o


def box(name, center, size, mat, bevel=0.008, segs=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=segs, profile=0.5, affect="EDGES")
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _obj(bm, name, mat)


def cyl(name, center, r, depth, mat, axis="Z", r2=None, verts=28, bevel=0.004, caps=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=verts, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    if bevel and caps:
        rim = [e for e in bm.edges if len(e.link_faces) == 2 and
               abs(e.link_faces[0].normal.dot(e.link_faces[1].normal)) < 0.5]
        bmesh.ops.bevel(bm, geom=rim, offset=bevel, segments=2, profile=0.5, affect="EDGES")
    rot = {"Z": Matrix(), "X": Matrix.Rotation(math.pi / 2, 4, "Y"), "Y": Matrix.Rotation(-math.pi / 2, 4, "X")}[axis]
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _obj(bm, name, mat)


def tube(name, pts, r, mat, closed=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o)
    bpy.data.curves.remove(cu)
    me.materials.clear()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    PARTS.append(ob)
    return ob


def rounded_loop(x0, x1, z0, z1, y, rad=0.05, n=4):
    """Closed rectangle with rounded corners in the XZ plane at depth y."""
    pts = []
    for cx, cz, a0 in ((x1 - rad, z1 - rad, 0), (x0 + rad, z1 - rad, 90), (x0 + rad, z0 + rad, 180), (x1 - rad, z0 + rad, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + rad * math.cos(a), y, cz + rad * math.sin(a)))
    return pts


def label(name, center, w, h, mat, normal="-Y"):
    """Flat decal quad with 0..1 UVs (UV map "src") for an image material."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("src")
    vs = [bm.verts.new(v) for v in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
    f = bm.faces.new(vs)
    for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uvl].uv = uv
    rot = {"-Y": Matrix(), "+Y": Matrix.Rotation(math.pi, 4, "Z"), "+X": Matrix.Rotation(math.pi / 2, 4, "Z"),
           "-X": Matrix.Rotation(-math.pi / 2, 4, "Z")}[normal]
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _obj(bm, name, mat)


# ---------------------------------------------------------------- the props

def clear():
    PARTS.clear()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def generator():
    tmp = os.path.join(ROOT, "blender", "renders")
    os.makedirs(tmp, exist_ok=True)
    red = material("gen_red", (168, 26, 20), 0.45, 0.0, 0.45, 0.5)
    black = material("gen_black", (22, 22, 24), 0.55, 0.6, 0.3, 0.35)
    engine = material("gen_engine", (70, 72, 74), 0.6, 0.7, 0.55, 0.15, (0.05, 0.045, 0.04))
    alu = material("gen_alu", (150, 150, 146), 0.35, 1.0, 0.4, 0.2)
    rubber = material("gen_rubber", (18, 18, 18), 0.9, 0.0, 0.2)
    chrome = material("gen_chrome", (200, 200, 205), 0.15, 1.0, 0.25)
    rust = material("gen_muffler", (60, 44, 36), 0.8, 0.5, 0.7, 0.0, (0.16, 0.08, 0.04))
    panel = material("gen_panel", (34, 36, 38), 0.6, 0.2, 0.25)
    orange = material("gen_outlet", (210, 120, 30), 0.5, 0.0, 0.3)

    pimg = os.path.join(tmp, "gen_panel_decal.png")   # drawn by tools/blender/prop_decals.py
    timg = os.path.join(tmp, "gen_tank_decal.png")
    panel_decal = material("gen_panel_decal", None, 0.5, 0.0, 0.25, 0.0, image=pimg)
    tank_decal = material("gen_tank_decal", None, 0.4, 0.0, 0.3, 0.3, image=timg)

    # tubular frame: two side loops, cross bars, lifting handles
    L, Wd, Hh, r = 0.46, 0.30, 0.66, 0.02
    for y in (-Wd, Wd):
        tube("frame_side", rounded_loop(-L, L, 0.04, Hh, y, 0.07), r, black, closed=True)
    for x in (-L + 0.012, L - 0.012):
        for z in (0.06, Hh - 0.02):
            tube("frame_cross", [(x, -Wd, z), (x, Wd, z)], r, black)
    for x in (-0.2, 0.2):
        tube("frame_base", [(x, -Wd, 0.05), (x, Wd, 0.05)], r * 0.9, black)
    for x in (-L - 0.02, L + 0.02):
        s = 1 if x > 0 else -1
        tube("handle", [(x - s * 0.03, -0.17, Hh - 0.05), (x, -0.15, Hh + 0.0), (x, 0.15, Hh + 0.0),
                        (x - s * 0.03, 0.17, Hh - 0.05)], r * 0.9, black)
        cyl("handle_grip", (x, 0, Hh), 0.03, 0.22, rubber, axis="Y")
    # rubber feet
    for x in (-0.36, 0.36):
        for y in (-Wd, Wd):
            cyl("foot", (x, y, 0.025), 0.035, 0.05, rubber)

    # fuel tank with cap and gauge
    box("tank", (0, 0, 0.555), (0.62, 0.48, 0.15), red, bevel=0.05, segs=4)
    box("tank_seam", (0, 0, 0.483), (0.64, 0.5, 0.014), red, bevel=0.005)
    cyl("cap", (0.17, 0.08, 0.645), 0.045, 0.03, black)
    cyl("cap_top", (0.17, 0.08, 0.663), 0.038, 0.012, black)
    for k in range(10):
        a = k * math.pi / 5
        box("cap_rib", (0.17 + 0.046 * math.cos(a), 0.08 + 0.046 * math.sin(a), 0.645), (0.008, 0.008, 0.028), black, 0)
    cyl("gauge", (-0.15, -0.05, 0.633), 0.04, 0.012, chrome)
    cyl("gauge_glass", (-0.15, -0.05, 0.64), 0.032, 0.006, panel)
    label("tank_decal", (0, -0.2415, 0.55), 0.42, 0.11, tank_decal)
    label("tank_decal_b", (0, 0.2415, 0.55), 0.42, 0.11, tank_decal, "+Y")

    # engine block (x < 0): crankcase, finned cylinder head, recoil starter, air filter
    box("crankcase", (-0.2, 0, 0.2), (0.32, 0.36, 0.26), engine, bevel=0.03, segs=3)
    for k in range(9):
        box("fin", (-0.2, -0.03, 0.34 + k * 0.012), (0.24, 0.26, 0.005), engine, 0)
    box("head", (-0.2, -0.03, 0.4), (0.2, 0.2, 0.05), engine, bevel=0.01)
    cyl("spark_boot", (-0.3, -0.03, 0.44), 0.016, 0.05, rubber, axis="X")
    tube("spark_wire", [(-0.32, -0.03, 0.44), (-0.37, -0.06, 0.44), (-0.37, -0.12, 0.35)], 0.006, rubber)
    cyl("starter", (-0.38, 0, 0.22), 0.11, 0.06, black, axis="X")
    cyl("starter_hub", (-0.415, 0, 0.22), 0.05, 0.02, alu, axis="X")
    for k in range(12):
        a = k * math.pi / 6
        box("starter_vent", (-0.411, 0.08 * math.cos(a), 0.22 + 0.08 * math.sin(a)), (0.006, 0.012, 0.03), panel, 0)
    tube("pull_rope", [(-0.42, 0, 0.22), (-0.44, -0.04, 0.19)], 0.004, black)
    box("pull_handle", (-0.445, -0.06, 0.18), (0.03, 0.08, 0.025), rubber, bevel=0.01)
    box("air_filter", (-0.25, -0.2, 0.28), (0.18, 0.06, 0.16), black, bevel=0.02)
    cyl("filter_knob", (-0.25, -0.235, 0.28), 0.015, 0.012, alu, axis="Y")

    # alternator (x > 0): cylinder with vented end cap
    cyl("alternator", (0.17, 0, 0.21), 0.14, 0.26, red, axis="X", bevel=0.02)
    cyl("alt_ring", (0.04, 0, 0.21), 0.15, 0.02, black, axis="X")
    cyl("alt_cap", (0.31, 0, 0.21), 0.12, 0.03, black, axis="X")
    for k in range(8):
        box("alt_slot", (0.327, 0, 0.21 + (k - 3.5) * 0.024), (0.006, 0.16, 0.009), panel, 0)
    for z in (0.12, 0.3):
        cyl("bolt", (0.33, 0.08, z), 0.01, 0.012, chrome, axis="X")

    # control panel on the front (facing -Y), outlets + breaker
    box("panel_box", (0.17, -0.22, 0.25), (0.25, 0.08, 0.2), panel, bevel=0.012)
    label("panel_decal", (0.17, -0.2615, 0.25), 0.23, 0.115, panel_decal)
    for x in (0.12, 0.2):
        box("outlet_cover", (x, -0.265, 0.27), (0.045, 0.01, 0.055), orange, bevel=0.004)
    cyl("breaker", (0.26, -0.27, 0.27), 0.012, 0.02, black, axis="Y")

    # muffler with perforated heat shield and exhaust
    cyl("muffler", (-0.1, 0.22, 0.25), 0.07, 0.22, rust, axis="X", bevel=0.015)
    cyl("shield", (-0.1, 0.235, 0.27), 0.08, 0.2, black, axis="X", caps=False, verts=20)
    tube("exhaust", [(0.01, 0.22, 0.25), (0.05, 0.24, 0.25), (0.06, 0.26, 0.29)], 0.016, rust)
    cyl("exhaust_tip", (0.06, 0.262, 0.3), 0.019, 0.02, chrome)
    tube("fuel_line", [(0.0, -0.05, 0.48), (-0.05, -0.15, 0.42), (-0.15, -0.17, 0.33)], 0.007, rubber)
    return "generator"


def flashlight():
    body = material("fl_body", (24, 24, 26), 0.4, 0.8, 0.25, 0.4)
    grip = material("fl_grip", (36, 36, 38), 0.7, 0.6, 0.3, 0.0)
    bezel = material("fl_bezel", (175, 175, 170), 0.25, 1.0, 0.3, 0.3)
    rubber = material("fl_rubber", (20, 20, 20), 0.9, 0.0, 0.2)
    yellow = material("fl_yellow", (220, 170, 20), 0.5, 0.0, 0.3, 0.3)
    refl = material("fl_reflector", (225, 225, 228), 0.1, 1.0, 0.0)
    lens = material("glow_lens", (255, 248, 220), 0.1, 0.0, 0.0)
    # along +Y: tail at -0.32, head at +0.32
    cyl("tail", (0, -0.30, 0), 0.042, 0.05, body, axis="Y", bevel=0.008)
    cyl("lanyard", (0, -0.335, 0), 0.016, 0.02, bezel, axis="Y")
    tube("lanyard_ring", [(0, -0.345, 0.0), (0, -0.37, 0.0)], 0.008, bezel)
    cyl("barrel", (0, -0.1, 0), 0.04, 0.36, body, axis="Y", bevel=0.0, caps=False)
    for k in range(16):
        cyl("grip_ring", (0, -0.24 + k * 0.016, 0), 0.0425, 0.008, grip, axis="Y", bevel=0.002, verts=24)
    box("switch_base", (0, 0.04, 0.04), (0.035, 0.07, 0.02), rubber, bevel=0.008)
    box("switch", (0, 0.04, 0.052), (0.022, 0.04, 0.012), yellow, bevel=0.005)
    cyl("neck", (0, 0.11, 0), 0.04, 0.08, body, axis="Y", r2=0.065, bevel=0.0, caps=False)
    cyl("head", (0, 0.2, 0), 0.066, 0.1, body, axis="Y", bevel=0.0, caps=False)
    for k in range(12):
        a = k * math.pi / 6
        box("head_rib", (0.068 * math.cos(a), 0.2, 0.068 * math.sin(a)), (0.008, 0.09, 0.008), grip, 0.002)
    cyl("bezel", (0, 0.265, 0), 0.074, 0.035, bezel, axis="Y", bevel=0.006)
    cyl("reflector", (0, 0.24, 0), 0.01, 0.05, refl, axis="Y", r2=0.062, caps=False)
    cyl("lens", (0, 0.276, 0), 0.062, 0.006, lens, axis="Y", bevel=0.0)
    return "flashlight"


def desk_fan():
    """Office desk fan; blades + hub are the "spin" part, rotating about the Blender Y axis through FAN_HUB."""
    metal = material("fan_metal", (58, 60, 62), 0.45, 0.8, 0.45, 0.3)
    cage = material("fan_cage", (150, 150, 146), 0.3, 1.0, 0.35, 0.0)
    base = material("fan_base", (40, 40, 42), 0.5, 0.5, 0.4, 0.3)
    blade = material("spin_blade", (120, 124, 120), 0.4, 0.6, 0.5, 0.2)
    hub = material("spin_hub", (40, 40, 40), 0.4, 0.6, 0.3)
    badge = material("fan_badge", (190, 150, 40), 0.3, 1.0, 0.2)
    hz, hy = FAN_HUB
    cyl("base", (0, 0.02, 0.018), 0.13, 0.036, base, bevel=0.012)
    cyl("base_top", (0, 0.02, 0.04), 0.06, 0.012, metal)
    box("switch", (0.0, -0.08, 0.04), (0.03, 0.02, 0.012), cage, bevel=0.003)
    cyl("stem", (0, 0.02, 0.15), 0.016, 0.22, metal, bevel=0.0)
    tube("yoke", [(-0.075, 0.03, hz - 0.01), (-0.075, 0.03, 0.24), (0.075, 0.03, 0.24), (0.075, 0.03, hz - 0.01)], 0.009, metal)
    cyl("motor", (0, 0.06, hz), 0.07, 0.11, metal, axis="Y", bevel=0.02)
    cyl("motor_back", (0, 0.12, hz), 0.05, 0.02, base, axis="Y")
    for side in (-1, 1):
        cyl("pivot", (side * 0.075, 0.03, hz), 0.014, 0.012, cage, axis="X")
    R = 0.17
    for y, r in ((hy - 0.05, R), (hy - 0.03, R * 0.98), (hy + 0.03, R * 0.98), (hy - 0.06, R * 0.6), (hy - 0.065, R * 0.3)):
        tube("cage_ring", [(r * math.cos(a * math.pi / 16), y, hz + r * math.sin(a * math.pi / 16)) for a in range(32)], 0.0035, cage, closed=True)
    tube("cage_rim", [(R * math.cos(a * math.pi / 16), hy - 0.01, hz + R * math.sin(a * math.pi / 16)) for a in range(32)], 0.008, cage, closed=True)
    for k in range(16):
        a = k * math.pi / 8
        c, sn = math.cos(a), math.sin(a)
        tube("spoke_f", [(0.02 * c, hy - 0.068, hz + 0.02 * sn), (R * 0.6 * c, hy - 0.06, hz + R * 0.6 * sn),
                         (R * c, hy - 0.05, hz + R * sn), (R * c, hy - 0.01, hz + R * sn)], 0.003, cage)
        tube("spoke_b", [(R * c, hy - 0.01, hz + R * sn), (R * 0.98 * c, hy + 0.03, hz + R * 0.98 * sn), (0.06 * c, hy + 0.04, hz + 0.06 * sn)], 0.003, cage)
    cyl("badge", (0, hy - 0.072, hz), 0.025, 0.008, badge, axis="Y")
    cyl("hub", (0, hy, hz), 0.03, 0.04, hub, axis="Y", bevel=0.008)
    for k in range(3):
        a = k * 2 * math.pi / 3
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.07, radius2=0.07, depth=0.005)
        bmesh.ops.scale(bm, vec=Vector((1.0, 0.6, 1.0)), verts=bm.verts)
        bmesh.ops.translate(bm, vec=Vector((0.08, 0, 0)), verts=bm.verts)
        m = Matrix.Rotation(a, 4, "Y") @ Matrix.Rotation(math.pi / 2 - 0.35, 4, "X")
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
        bmesh.ops.translate(bm, vec=Vector((0, hy, hz)), verts=bm.verts)
        _obj(bm, "blade", blade)
    return "desk_fan"


FAN_HUB = (0.34, -0.02)   # (Blender z, Blender y) of the blade axis -> Minecraft (y=0.34, z=0.02)


# ---------------------------------------------------------------- bake + export

def join_all(name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in PARTS:
        o.select_set(True)
        me = o.data
        if "src" not in me.uv_layers:
            if me.uv_layers:
                me.uv_layers[0].name = "src"
            else:
                me.uv_layers.new(name="src")
    bpy.context.view_layer.objects.active = PARTS[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
    bm.to_mesh(o.data)
    bm.free()
    return o


def bake(o, name, tex):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = 24
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.light_settings.distance = 0.06
    me = o.data
    bake_uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = bake_uv
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    me.uv_layers["src"].active_render = True
    imgs = {k: bpy.data.images.new(f"{name}_{k}", tex, tex, alpha=True) for k in ("col", "ao")}
    for m in me.materials:
        nt = m.node_tree
        n = nt.nodes.new("ShaderNodeTexImage")
        n.name = "BAKE"
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], n.inputs["Vector"])
        nt.nodes.active = n
    for k in ("col", "ao"):
        for m in me.materials:
            m.node_tree.nodes["BAKE"].image = imgs[k]
        if k == "col":
            bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=4, use_clear=True)
        else:
            bpy.ops.object.bake(type="AO", margin=4, use_clear=True)

    def arr(img):
        a = np.empty(tex * tex * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(tex, tex, 4)

    col, ao = arr(imgs["col"]), arr(imgs["ao"])
    out = col.copy()
    out[..., :3] = np.clip(col[..., :3] * (0.5 + 0.6 * ao[..., :1]), 0, 1)
    out[..., 3] = 1.0
    path = os.path.join(ASSETS, "textures", "prop", f"{name}.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = bpy.data.images.new(f"{name}_out", tex, tex, alpha=True)
    img.pixels.foreach_set(out.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    for m in me.materials:
        m.node_tree.nodes.remove(m.node_tree.nodes["BAKE"])
    for i, u in enumerate(me.uv_layers):
        if u.name == "bake":
            me.uv_layers.active_index = i
    # show the baked result in the viewport
    baked = bpy.data.materials.new(f"{name}_baked")
    baked.use_nodes = True
    t = baked.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    bs = next(n for n in baked.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    baked.node_tree.links.new(t.outputs["Color"], bs.inputs["Base Color"])
    return path


def export(o, name):
    """FMSH v1 in block units: parts "main" and (optional) "glow"."""
    me = o.data
    me.calc_loop_triangles()
    uv = me.uv_layers["bake"].data
    normals = me.corner_normals
    parts = {}
    for lt in me.loop_triangles:
        mat = me.materials[me.polygons[lt.polygon_index].material_index]
        part = next((k for k in ("glow", "spin") if mat.name.startswith(k)), "main")
        parts.setdefault(part, []).append(lt.loops)
    out = bytearray(b"FMSH" + struct.pack(">ii", 1, len(parts)))
    for pname, tris in parts.items():
        remap, vdata, idx = {}, [], []
        for loops in tris:
            for li in loops:
                vi = me.loops[li].vertex_index
                n = normals[li].vector
                u = uv[li].uv
                key = (vi, round(u.x, 5), round(u.y, 5), round(n.x, 3), round(n.y, 3), round(n.z, 3))
                if key not in remap:
                    remap[key] = len(remap)
                    v = me.vertices[vi].co
                    vdata.append((v.x, v.z, -v.y, n.x, n.z, -n.y, u.x, 1.0 - u.y))
                idx.append(remap[key])
        b = pname.encode()
        out += struct.pack(">h", len(b)) + b + struct.pack(">i", len(vdata))
        for t in vdata:
            out += struct.pack(">8f", *t)
        out += struct.pack(">i", len(idx)) + struct.pack(f">{len(idx)}i", *idx)
    path = os.path.join(ASSETS, "meshes", f"{name}.fmesh")
    with open(path, "wb") as f:
        f.write(bytes(out))
    return len(me.loop_triangles)


def build(fn, tex):
    clear()
    name = fn()
    o = join_all(name)
    bake(o, name, tex)
    tris = export(o, name)
    return name, tris


def build_all():
    res = [build(generator, 1024), build(flashlight, 512), build(desk_fan, 512)]
    print(res)
    return res


def preview(name, target=(0, 0, 0.3), dist=1.6, elev=24, azim=-35, size=(900, 650)):
    """Quick Cycles render of the current scene to blender/renders/<name>_preview.png."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = 48
    scene.render.resolution_x, scene.render.resolution_y = size
    for o in [o for o in bpy.data.objects if o.name.startswith("pv_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    cam = bpy.data.objects.new("pv_cam", bpy.data.cameras.new("pv_cam"))
    scene.collection.objects.link(cam)
    t = Vector(target)
    a, e = math.radians(azim), math.radians(elev)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    scene.camera = cam
    for nm, loc, en, col in (("pv_key", (1.5, -2, 2.5), 400, (1, 0.92, 0.8)), ("pv_rim", (-2, 2, 1.5), 250, (0.6, 0.75, 1))):
        L = bpy.data.objects.new(nm, bpy.data.lights.new(nm, "AREA"))
        L.data.energy, L.data.size, L.data.color = en, 1.5, col
        L.location = loc
        L.rotation_euler = (t - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(L)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.03, 0.03, 0.035, 1)
    path = os.path.join(ROOT, "blender", "renders", f"{name}_preview.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def load_fmesh(name, offset=(0, 0, 0)):
    """Re-import an exported prop (.fmesh + baked texture) to check what the game will draw."""
    with open(os.path.join(ASSETS, "meshes", f"{name}.fmesh"), "rb") as f:
        data = f.read()
    _, n = struct.unpack(">ii", data[4:12])
    p = 12
    img = bpy.data.images.load(os.path.join(ASSETS, "textures", "prop", f"{name}.png"), check_existing=False)
    m = bpy.data.materials.new(f"{name}_check")
    m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Closest"
    bs = next(x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
    m.node_tree.links.new(t.outputs["Color"], bs.inputs["Base Color"])
    for _ in range(n):
        ln, = struct.unpack(">h", data[p:p + 2])
        part = data[p + 2:p + 2 + ln].decode()
        p += 2 + ln
        nv, = struct.unpack(">i", data[p:p + 4])
        p += 4
        v = np.frombuffer(data[p:p + nv * 32], dtype=">f4").reshape(nv, 8)
        p += nv * 32
        ni, = struct.unpack(">i", data[p:p + 4])
        p += 4
        idx = np.frombuffer(data[p:p + ni * 4], dtype=">i4").reshape(-1, 3)
        p += ni * 4
        me = bpy.data.meshes.new(f"{name}_{part}")
        me.from_pydata([(x + offset[0], -z + offset[1], y + offset[2]) for x, y, z in v[:, :3].tolist()], [], idx.tolist())
        uvl = me.uv_layers.new(name="uv")
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                uvl.data[li].uv = (float(v[vi, 6]), 1.0 - float(v[vi, 7]))
            poly.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(o)


def preview_ortho(name, center, size, height=40.0, res=(1400, 1000), top=True):
    """Orthographic top-down Cycles/EEVEE render of the scene (for map layout checks)."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = res
    for o in [o for o in bpy.data.objects if o.name.startswith("pv_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    cam = bpy.data.objects.new("pv_cam", bpy.data.cameras.new("pv_cam"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size
    cam.data.clip_end = 500
    cam.location = (center[0], center[1], height)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    sun = bpy.data.objects.new("pv_sun", bpy.data.lights.new("pv_sun", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (0.3, 0.2, 0)
    scene.collection.objects.link(sun)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.4, 0.4, 0.4, 1)
    bg.inputs["Strength"].default_value = 1.0
    path = os.path.join(ROOT, "blender", "renders", f"{name}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def load_entity_fmesh(name):
    """Imports an animatronic .fmesh (GeckoLib space: x mirrored, y up) with its baked texture."""
    path = os.path.join(ASSETS, "meshes", f"{name}.fmesh")
    with open(path, "rb") as f:
        data = f.read()
    _, n = struct.unpack(">ii", data[4:12])
    p = 12
    img = bpy.data.images.load(os.path.join(ASSETS, "textures", "entity", f"{name}_hd.png"), check_existing=True)
    m = bpy.data.materials.new(f"{name}_menu")
    m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    bs = next(x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
    m.node_tree.links.new(t.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.6
    objs = []
    for _ in range(n):
        ln, = struct.unpack(">h", data[p:p + 2])
        part = data[p + 2:p + 2 + ln].decode()
        p += 2 + ln
        nv, = struct.unpack(">i", data[p:p + 4])
        p += 4
        v = np.frombuffer(data[p:p + nv * 32], dtype=">f4").reshape(nv, 8)
        p += nv * 32
        ni, = struct.unpack(">i", data[p:p + 4])
        p += 4
        idx = np.frombuffer(data[p:p + ni * 4], dtype=">i4").reshape(-1, 3)
        p += ni * 4
        me = bpy.data.meshes.new(f"{name}_{part}")
        me.from_pydata([(-x, z, y) for x, y, z in v[:, :3].tolist()], [], idx[:, ::-1].tolist())
        uvl = me.uv_layers.new(name="uv")
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                uvl.data[li].uv = (float(v[vi, 6]), 1.0 - float(v[vi, 7]))
            poly.use_smooth = True
        me.materials.append(m)
        o = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(o)
        objs.append(o)
    return objs
