"""Mod icon / CurseForge avatar: Freddy's face out of the dark, rendered from the mod's own model.

    exec(open(r"<repo>/tools/blender/props.py").read())
    exec(open(r"<repo>/tools/blender/jumpscares.py").read())
    exec(open(r"<repo>/tools/blender/mod_icon.py").read())
    render_icon()                   # -> blender/icon/icon_raw.png, then tools/pizzeria/gen_icon.py adds the title

Uses the "jumpscare" scene (scene(), rig(), from jumpscares.py) so the rest of the file is untouched.
"""
import math
import os

import bpy
from mathutils import Euler, Vector

ICON_RAW = os.path.join(ROOT, "blender", "icon", "icon_raw.png")


def smooth_normals(sc):
    """The parts come with split vertices (UV seams); average normals over coincident positions so the
    low-poly shell renders smooth instead of faceted."""
    import numpy as np
    for o in sc.objects:
        if o.type != "MESH":
            continue
        me = o.data
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        nor = np.empty(n * 3)
        me.vertices.foreach_get("normal", nor)
        nor = nor.reshape(-1, 3)
        key = np.round(co / 1e-4).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        acc = np.zeros((inv.max() + 1, 3))
        np.add.at(acc, inv.ravel(), nor)
        acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-9)
        me.normals_split_custom_set_from_vertices(acc[inv.ravel()].tolist())


def render_icon(name="freddy", size=1024):
    sc = scene()
    sc.render.film_transparent = False
    sc.render.resolution_x = sc.render.resolution_y = size
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.006, 0.004, 0.005, 1)
    em = rig(name, sc)
    smooth_normals(sc)
    # pose: head tilted and slightly down, jaw a little open, staring at you
    em["head"].rotation_euler = Euler((math.radians(-8), math.radians(-6), math.radians(14)))
    em["jaw"].rotation_euler = Euler((math.radians(16), 0, 0))
    sc.view_layers[0].update()
    face = em["head"].matrix_world @ Vector((0, -0.28, 0.18))

    def light(n, kind, energy, loc, color, size=0.2, spot=None):
        l = bpy.data.objects.new(n, bpy.data.lights.new(n, kind))
        l.data.energy = energy
        l.data.color = color
        l.data.shadow_soft_size = size
        l.location = loc
        if spot:
            l.data.spot_size = math.radians(spot)
            l.data.spot_blend = 0.6
            d = face - Vector(loc)
            l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(l)

    light("key", "SPOT", 140, face + Vector((0.1, -0.35, 1.1)), (1.0, 0.8, 0.55), 0.05, 26)    # harsh lamp straight above
    light("rim", "POINT", 160, face + Vector((-0.75, 0.6, 0.3)), (1.0, 0.08, 0.05), 0.12)      # red rim from behind
    light("rim2", "POINT", 70, face + Vector((0.8, 0.5, 0.15)), (0.85, 0.1, 0.06), 0.12)
    light("fill", "POINT", 1.5, face + Vector((-0.3, -0.9, -0.35)), (0.35, 0.45, 0.9), 0.4)    # faint monitor glow

    cam = bpy.data.objects.new("icon_cam", bpy.data.cameras.new("icon_cam"))
    cam.data.lens = 50
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = face + Vector((0.12, -1.25, -0.12))
    cam.rotation_euler = (face + Vector((0, 0, 0.03)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    os.makedirs(os.path.dirname(ICON_RAW), exist_ok=True)
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = ICON_RAW
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return ICON_RAW
