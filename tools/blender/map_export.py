"""Exports the downloaded FNAF 1 map (Sketchfab "Fnaf 1 Map" by skylajade69, CC BY 4.0) from Blender
for tools/pizzeria/build_map.py:

    exec(open(r"<repo>/tools/blender/map_export.py").read()); export_map()

Writes blender/map/fnaf1_tris.npz (triangles in Minecraft block coordinates, UVs, material ids, object
ids) and blender/map/textures/<material>.png. Heavy objects are decimated so the whole map stays
around 250k triangles.
"""
import json
import os

import bpy
import numpy as np

ROOT = r"D:\Five Nights at Freddy’s (Horror)"
OUT = os.path.join(ROOT, "blender", "map")
SCALE = 2.1                      # blocks per Blender unit: the 1.9 high ceiling becomes 4 blocks
SKIP = {"Object_669"}            # sky box around the model
MAX_OBJ_TRIS = 3000


def map_objects():
    hidden = bpy.data.collections.get("map_jahbogard")
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name not in SKIP
            and not (hidden and o.name in hidden.objects) and not o.name.startswith(("pv_", "bk_"))]


def shade_colors(me, tri_v):
    """Per triangle corner shade (rgb) from the baked 'ao' and 'light' vertex colours (see map_bake.py):
    soft ambient occlusion times lamp light, with a floor so unlit corners are dim, not black."""
    out = []
    for name in ("ao", "light"):
        a = me.color_attributes.get(name)
        if a is None:
            return None
        v = np.empty(len(a.data) * 4, np.float32)
        a.data.foreach_get("color", v)
        out.append(v.reshape(-1, 4)[:, :3])
    ao, light = out
    if len(ao) != len(me.vertices):
        return None
    lum = light.mean(axis=1, keepdims=True)
    tint = np.clip(light / np.maximum(lum, 1e-4), 0.7, 1.3)
    shade = (0.45 + 0.55 * ao[:, :1]) * (0.38 + 0.62 * np.clip(lum / 0.3, 0, 1))
    col = np.clip(shade * (0.75 + 0.25 * tint), 0, 1.2)
    return col[tri_v].reshape(-1, 3, 3)


def material_info(m):
    """(texture image or None, base colour rgb, emissive, alpha_cutout)"""
    img, col, emissive, cut = None, (0.5, 0.5, 0.5), False, False
    if m and m.node_tree:
        bs = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bs:
            link = bs.inputs["Base Color"].links
            if link and link[0].from_node.type == "TEX_IMAGE":
                img = link[0].from_node.image
            col = tuple(bs.inputs["Base Color"].default_value[:3])
            e = bs.inputs.get("Emission Color") or bs.inputs.get("Emission")
            es = bs.inputs.get("Emission Strength")
            emissive = bool(e and (e.links or max(e.default_value[:3]) > 0.01) and (not es or es.default_value > 0))
            a = bs.inputs["Alpha"]
            cut = bool(a.links)
    return img, col, emissive, cut


def export_map(baked=False):
    os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("bk_")] if baked else map_objects()
    dg = bpy.context.evaluated_depsgraph_get()
    col_all = []
    mats, mat_index = [], {}
    pos_all, uv_all, mat_all, obj_all = [], [], [], []
    obj_meta = []
    # bounds of the floor plan (Blender units) to place the map at (1, 1, 1)
    lo = np.array([1e9] * 3)
    for o in objs:
        bb = np.array([o.matrix_world @ __import__("mathutils").Vector(c) for c in o.bound_box])
        lo = np.minimum(lo, bb.min(axis=0))
    for oi, o in enumerate(objs):
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        if n == 0:
            o.evaluated_get(dg).to_mesh_clear()
            continue
        if n > MAX_OBJ_TRIS and not baked:
            o.evaluated_get(dg).to_mesh_clear()
            mod = o.modifiers.new("export_dec", "DECIMATE")
            mod.ratio = max(MAX_OBJ_TRIS / n, 0.3)
            dg = bpy.context.evaluated_depsgraph_get()
            me = o.evaluated_get(dg).to_mesh()
            me.calc_loop_triangles()
            o.modifiers.remove(mod)
            n = len(me.loop_triangles)
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        tri_v = np.empty(n * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", tri_v)
        tri_l = np.empty(n * 3, np.int32)
        me.loop_triangles.foreach_get("loops", tri_l)
        tri_m = np.empty(n, np.int32)
        me.loop_triangles.foreach_get("material_index", tri_m)
        uvl = me.uv_layers.active
        if uvl:
            uv = np.empty(len(me.loops) * 2, np.float32)
            uvl.data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)[tri_l].reshape(n, 3, 2)
        else:
            uv = np.zeros((n, 3, 2), np.float32)
        p = co[tri_v].reshape(n, 3, 3)
        cols = shade_colors(me, tri_v.reshape(n, 3)) if baked else None
        col_all.append(cols if cols is not None else np.ones((n, 3, 3), np.float32))
        # Blender (x, y, z) -> Minecraft (x, z, -y), in blocks, floor plan starting at (1, 1, 1)
        mc = np.stack([(p[..., 0] - lo[0]) * SCALE + 1, (p[..., 2]) * SCALE + 1 - 0.002, (-(p[..., 1]) + 0) * SCALE], axis=-1)
        gm = []
        for slot in me.materials if me.materials else [None]:
            key = slot.name if slot else "none"
            if key not in mat_index:
                img, col, em, cut = material_info(slot)
                tex = None
                if img is not None and img.size[0] > 0:
                    tex = os.path.join(OUT, "textures", key.replace(".", "_") + ".png")
                    if not os.path.exists(tex):
                        cp = img.copy()
                        cp.filepath_raw = tex
                        cp.file_format = "PNG"
                        cp.save()
                        bpy.data.images.remove(cp)
                mat_index[key] = len(mats)
                mats.append(dict(name=key, texture=tex, color=[float(c) for c in col], emissive=em, cutout=cut))
            gm.append(mat_index[key])
        gm = np.array(gm, np.int32)
        pos_all.append(mc.astype(np.float32))
        uv_all.append(uv)
        mat_all.append(gm[np.clip(tri_m, 0, len(gm) - 1)])
        obj_all.append(np.full(n, len(obj_meta), np.int32))
        src = bpy.data.objects.get(o.name[3:]) if baked else o
        obj_meta.append(dict(name=o.name[3:] if baked else o.name, parent=src.parent.name if src and src.parent else "",
                             lo=mc.reshape(-1, 3).min(axis=0).tolist(), hi=mc.reshape(-1, 3).max(axis=0).tolist(), tris=n))
        o.evaluated_get(dg).to_mesh_clear()
    pos = np.concatenate(pos_all)
    # shift z so the map starts at z = 1
    zmin = pos[..., 2].min()
    pos[..., 2] += 1 - zmin
    for m in obj_meta:
        m["lo"][2] = float(m["lo"][2] + 1 - zmin)
        m["hi"][2] = float(m["hi"][2] + 1 - zmin)
    np.savez_compressed(os.path.join(OUT, "fnaf1_tris.npz"), pos=pos, uv=np.concatenate(uv_all),
                        mat=np.concatenate(mat_all), obj=np.concatenate(obj_all), col=np.concatenate(col_all).astype(np.float16))
    with open(os.path.join(OUT, "fnaf1_meta.json"), "w") as f:
        json.dump(dict(materials=mats, objects=obj_meta, scale=SCALE), f, indent=1)
    return len(pos), len(mats), pos.reshape(-1, 3).max(axis=0).tolist()
