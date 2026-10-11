"""FNAF 1 style jumpscare frames, rendered from the mod's own animatronic meshes (not the game's images):
the animatronic lunges at the camera from its side of the office, jaw wide open, head shaking, eyes lit.
Frames are RGBA so the game draws them over the real view.

    exec(open(r"<repo>/tools/blender/props.py").read())
    exec(open(r"<repo>/tools/blender/jumpscares.py").read())
    render_all()          # or render_one("bonnie")

Works in its own scene ("jumpscare") so the map scene in the same file is left alone.
Output: assets/fnaf/textures/gui/jumpscare/<name>_<frame>.png (FRAMES per animatronic).
"""
import math
import os

import bpy
from mathutils import Euler, Matrix, Vector

FRAMES = 14
LUNGE = 8                        # frames of the lunge, the rest is the shaking hold
RES = (800, 450)
OUT = os.path.join(ASSETS, "textures", "gui", "jumpscare")

# side the animatronic comes from (-1 left, 1 right), start/end camera distance, extra arm raise
STYLE = {
    "freddy": dict(side=-0.25, start=1.4, end=0.62, arms=-35, jaw=48, tilt=6),
    "bonnie": dict(side=-1.0, start=1.3, end=0.58, arms=-80, jaw=45, tilt=-10),
    "chica": dict(side=1.0, start=1.3, end=0.6, arms=-80, jaw=50, tilt=10),
    "foxy": dict(side=-1.6, start=2.4, end=0.5, arms=-40, jaw=60, tilt=-14),
    "golden_freddy": dict(side=0.0, start=0.75, end=0.7, arms=0, jaw=20, tilt=12),
}


def bone_pivots(name):
    import json
    g = json.load(open(os.path.join(ASSETS, "geo", "entity", f"{name}.geo.json")))
    out = {}
    for b in g["minecraft:geometry"][0]["bones"]:
        px, py, pz = b.get("pivot", [0, 0, 0])
        out[b["name"]] = (Vector((px / 16, pz / 16, py / 16)), b.get("parent"))
    return out


def scene():
    sc = bpy.data.scenes.get("jumpscare") or bpy.data.scenes.new("jumpscare")
    for o in list(sc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("jumpscare_world")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.004, 0.004, 0.006, 1)
    bg.inputs["Strength"].default_value = 1.0
    return sc


def glow_material(name, objs):
    """Base colour from the baked texture, eyes (glowmask) emissive."""
    mask = bpy.data.images.load(os.path.join(ASSETS, "textures", "entity", f"{name}_hd_glowmask.png"), check_existing=True)
    m = objs[0].data.materials[0]
    nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image and n.image.name.startswith(name + "_hd") and "glow" not in n.image.name)
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    g = nt.nodes.new("ShaderNodeTexImage")
    g.image = mask
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs["Color"], mul.inputs[6])
    nt.links.new(g.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 6.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.6
    bsdf.inputs["Roughness"].default_value = 0.45


def rig(name, sc):
    """Imports the parts and parents each to an empty at its bone pivot, so bones can be rotated."""
    win = bpy.context.window
    prev = win.scene
    win.scene = sc
    objs = load_entity_fmesh(name)
    win.scene = prev
    piv = bone_pivots(name)
    empties = {}

    def empty(bone):
        if bone in empties:
            return empties[bone]
        pos, parent = piv.get(bone, (Vector(), None))
        e = bpy.data.objects.new(f"js_{bone}", None)
        sc.collection.objects.link(e)
        if parent:
            p = empty(parent)
            e.parent = p
            e.location = pos - piv[parent][0]
        else:
            e.location = pos
        e.rotation_mode = "XYZ"
        empties[bone] = e
        return e

    for o in objs:
        bone = o.name[len(name) + 1:].split(".")[0]
        e = empty(bone)
        o.parent = e
        # mesh is in model space: shift it so the empty's world position is its origin
        o.matrix_parent_inverse = Matrix.Translation(-piv[bone][0])
    glow_material(name, objs)
    return empties


def lights(sc):
    def add(n, kind, energy, loc, color, size=0.3):
        l = bpy.data.objects.new(n, bpy.data.lights.new(n, kind))
        l.data.energy = energy
        l.data.color = color
        if hasattr(l.data, "shadow_soft_size"):
            l.data.shadow_soft_size = size
        l.location = loc
        sc.collection.objects.link(l)
        return l
    add("key", "POINT", 130, (0.4, -1.6, 3.1), (1.0, 0.86, 0.66), 0.15)     # office lamp above the desk
    add("fill", "POINT", 20, (-1.2, -1.0, 1.4), (0.45, 0.55, 0.9), 0.5)      # cold bounce from the monitors
    add("rim", "POINT", 30, (0.0, 1.4, 2.8), (1.0, 0.75, 0.55), 0.2)


def camera(sc):
    cam = bpy.data.objects.new("js_cam", bpy.data.cameras.new("js_cam"))
    cam.data.lens = 20
    cam.data.clip_start = 0.02
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def ease(t):
    return 1 - (1 - t) ** 3


def render_one(name):
    sc = scene()
    em = rig(name, sc)
    lights(sc)
    cam = camera(sc)
    st = STYLE[name]
    root = em["root"]
    face = Vector((0, -0.25, bone_pivots(name)["head"][0].z + 0.18))
    os.makedirs(OUT, exist_ok=True)
    rnd = __import__("random").Random(hash(name) & 0xffff)
    for f in range(FRAMES):
        lunge = min(1.0, f / (LUNGE - 1))
        e = ease(lunge)
        hold = max(0, f - LUNGE + 1)
        # the animatronic slides in from its side while the camera distance collapses
        root.location = Vector((st["side"] * (1 - e), 0, 0))
        root.rotation_euler = Euler((math.radians(-12 * e), 0, math.radians(-25 * st["side"] * (1 - e))))
        dist = st["start"] + (st["end"] - st["start"]) * e
        shake = 0.0 if f < 2 else (1 if f % 2 else -1)
        em["head"].rotation_euler = Euler((math.radians(-10 * e), math.radians(st["tilt"] * shake * 0.6),
                                           math.radians(st["tilt"] * shake)))
        jaw = st["jaw"] * min(1.0, f / 3) * (1.0 if hold == 0 else (0.75 + 0.25 * ((f % 2) * 2 - 1) * -1))
        em["jaw"].rotation_euler = Euler((math.radians(jaw), 0, 0))
        for arm in ("left_arm", "right_arm"):
            if arm in em:
                sgn = 1 if arm == "left_arm" else -1
                em[arm].rotation_euler = Euler((math.radians(st["arms"] * e), 0, math.radians(sgn * 18 * e)))
        jitter = Vector((rnd.uniform(-1, 1), 0, rnd.uniform(-1, 1))) * (0.012 + 0.02 * hold / max(1, FRAMES - LUNGE))
        # aim at the posed face: a bit in front of and above the head pivot
        sc.view_layers[0].update()
        face = em["head"].matrix_world @ Vector((0, -0.3, 0.22))
        cam.location = Vector((face.x * 0.15, face.y - dist, face.z - 0.1)) + jitter
        look = face - cam.location
        cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
        cam.rotation_euler.y += math.radians(rnd.uniform(-3, 3) * (1 if f > 1 else 0))
        sc.render.filepath = os.path.join(OUT, f"{name}_{f}.png")
        bpy.ops.render.render(write_still=True, scene=sc.name)
    return FRAMES


def render_all():
    for n in STYLE:
        render_one(n)
