"""Bakes static lighting and shadows of the FNAF 1 map into vertex colours (Cycles), so the game draws the
map with real soft shadows (under tables and chairs, in corners, behind the stage props) on top of
Minecraft's own block light.

    exec(open(r"<repo>/tools/blender/map_export.py").read())
    exec(open(r"<repo>/tools/blender/map_bake.py").read())
    prepare(); add_lamps(); bake(); export_map(baked=True)

prepare() makes "bk_" copies of the map objects with the export decimation applied and long edges split
(vertex colours need vertices: big floor/wall quads get a ~0.3 unit grid), add_lamps() puts a point light in
every ceiling lamp bulb, bake() writes colour attributes "ao" and "light".
"""
import math

import bmesh
import bpy
from mathutils import Vector

MAX_EDGE = 0.3          # Blender units (~0.6 blocks)


def bake_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("bk_")]


def prepare():
    for o in bake_objects():
        bpy.data.objects.remove(o, do_unlink=True)
    dg = bpy.context.evaluated_depsgraph_get()
    made = 0
    for o in map_objects():
        if not o.data.materials or all(m is None for m in o.data.materials):
            continue                                   # light-volume helpers of the source scene
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        if n > MAX_OBJ_TRIS:
            mod = o.modifiers.new("export_dec", "DECIMATE")
            mod.ratio = max(MAX_OBJ_TRIS / n, 0.3)
            dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        if n > MAX_OBJ_TRIS:
            o.modifiers.remove(o.modifiers["export_dec"])
            dg = bpy.context.evaluated_depsgraph_get()
        me.transform(o.matrix_world)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        for _ in range(8):
            # only big flat surfaces need the grid (floors, walls, table tops), not wires or small props
            long_edges = [e for e in bm.edges if e.calc_length() > MAX_EDGE
                          and any(f.calc_area() > 0.06 for f in e.link_faces)]
            if not long_edges:
                break
            bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=False)
            bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        bm.to_mesh(me)
        bm.free()
        bo = bpy.data.objects.new("bk_" + o.name, me)
        bpy.context.scene.collection.objects.link(bo)
        o.hide_render = True
        o.hide_viewport = True
        made += 1
    return made


def add_lamps(power=18.0):
    """A warm point light in every bulb of the ceiling lamps (emissive 'Material.005' islands)."""
    for l in [o for o in bpy.data.objects if o.name.startswith("bk_lamp")]:
        bpy.data.objects.remove(l, do_unlink=True)
    centers = []
    for o in bake_objects():
        me = o.data
        idx = [i for i, m in enumerate(me.materials) if m and m.name == "Material.005"]
        if not idx:
            continue
        bm = bmesh.new()
        bm.from_mesh(me)
        faces = [f for f in bm.faces if f.material_index in idx]
        seen = set()
        for f in faces:
            if f.index in seen:
                continue
            stack, island = [f], []
            seen.add(f.index)
            while stack:
                g = stack.pop()
                island.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen and h.material_index in idx:
                            seen.add(h.index)
                            stack.append(h)
            c = sum((g.calc_center_median() for g in island), Vector()) / len(island)
            centers.append(c)
        bm.free()
    for i, c in enumerate(centers):
        l = bpy.data.objects.new(f"bk_lamp{i}", bpy.data.lights.new(f"bk_lamp{i}", "POINT"))
        l.data.energy = power
        l.data.color = (1.0, 0.86, 0.66)
        l.data.shadow_soft_size = 0.12
        l.location = c - Vector((0, 0, 0.12))
        bpy.context.scene.collection.objects.link(l)
    return len(centers)


def bake(samples=24):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
    scene.world.light_settings.distance = 0.6
    objs = bake_objects()
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        for name in ("ao", "light"):
            # one value per vertex (POINT) averages the per-corner noise of a low-sample bake
            old = o.data.color_attributes.get(name)
            if old is not None and old.domain != "POINT":
                o.data.color_attributes.remove(old)
            if name not in o.data.color_attributes:
                o.data.color_attributes.new(name, "FLOAT_COLOR", "POINT")
    bpy.context.view_layer.objects.active = objs[0]
    scene.render.bake.target = "VERTEX_COLORS"
    for name, kind, kwargs in (("ao", "AO", {}), ("light", "DIFFUSE", {"pass_filter": {"DIRECT", "INDIRECT"}})):
        for o in objs:
            o.data.color_attributes.active_color = o.data.color_attributes[name]
        bpy.ops.object.bake(type=kind, **kwargs)
    return len(objs)
