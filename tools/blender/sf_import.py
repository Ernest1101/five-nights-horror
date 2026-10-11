"""Turn downloaded FNAF 1 models (Sketchfab, CC BY 999angry) into mod assets.

The source meshes are split by material, not by body part, but every suit piece is its own
loose island. Each island is assigned to a GeckoLib bone by where it sits (landmarks found from
the geometry), T-posed arms are swung down to hang at the sides, everything is baked into one
1024 texture and exported as:
  assets/fnaf/meshes/<id>.fmesh, textures/entity/<id>_hd(_glowmask).png, geo/entity/<id>.geo.json
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import fnaf_blender as fb

BONES = ["root", "body", "head", "jaw", "left_arm", "left_forearm", "right_arm", "right_forearm", "left_leg", "right_leg"]
PARENT = {"body": "root", "head": "body", "jaw": "head", "left_arm": "body", "left_forearm": "left_arm",
          "right_arm": "body", "right_forearm": "right_arm", "left_leg": "root", "right_leg": "root"}
HEIGHT = {"freddy": 2.45, "golden_freddy": 2.45, "bonnie": 2.62, "chica": 2.35, "foxy": 2.35}
ARM_DROP = 80.0


def src_meshes(name):
    return [o for o in bpy.data.collections["src_" + name].all_objects if o.type == "MESH"]


def world_mesh(o):
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    me.transform(o.matrix_world)
    return me


def islands(me):
    """Connected components of a mesh: list of (face_indices, vertex_indices)."""
    n = len(me.vertices)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    groups = {}
    for p in me.polygons:
        groups.setdefault(find(p.vertices[0]), []).append(p.index)
    out = []
    for faces in groups.values():
        vs = sorted({v for f in faces for v in me.polygons[f].vertices})
        out.append((faces, vs))
    return out


def landmarks(meshes):
    co = np.concatenate([np.array([v.co[:] for v in me.vertices]) for me in meshes])
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    H = z.max()
    ax = np.abs(x)
    far = ax > np.percentile(ax, 99.0)
    arm_z = float(np.median(z[far]))
    band = (z > arm_z - 0.38) & (z < arm_z - 0.22)
    torso_w = float(np.percentile(ax[band], 98))
    # neck: narrowest silhouette slice above the shoulders
    best, neck_z = 9, arm_z + 0.15
    for zz in np.arange(arm_z + 0.1, arm_z + 0.45, 0.01):
        s = (z > zz) & (z < zz + 0.02)
        if s.sum() < 3:
            continue
        w = np.percentile(ax[s], 95)
        if w < best:
            best, neck_z = w, float(zz)
    # crotch: lowest height where geometry crosses the centre line between the legs
    crotch = 0.45 * H
    for zz in np.arange(0.3 * H, 0.6 * H, 0.005):
        s = (z > zz) & (z < zz + 0.01) & (ax < 0.03)
        if s.sum() >= 5:
            crotch = float(zz)
            break
    return dict(H=float(H), arm_z=arm_z, torso_w=torso_w, neck_z=neck_z, crotch=crotch,
                max_x_pos=float(x.max()), max_x_neg=float(-x.min()))


def assign(c, L, jaw_rule):
    """Bone for an island centroid c (Blender coords)."""
    x, y, z = c
    side = "left" if x > 0 else "right"
    reach = L["max_x_pos"] if x > 0 else L["max_x_neg"]
    shoulder = L["torso_w"] * 0.9
    if abs(x) > L["torso_w"] * 0.95 and abs(z - L["arm_z"]) < 0.32 and z < L["neck_z"] + 0.1:
        elbow = shoulder + 0.5 * (reach - shoulder)
        return f"{side}_forearm" if abs(x) > elbow else f"{side}_arm"
    if z > L["neck_z"]:
        return "jaw" if jaw_rule(x, y, z) else "head"
    if z < L["crotch"] + 0.02 and abs(x) > 0.03:
        return f"{side}_leg"
    return "body"


# per-model landmarks read off close-up renders (normalized units, Blender Z up / -Y front)
SPEC = {
    "freddy": dict(neck_z=1.745, jaw=dict(z=1.83, y=-0.05)),
    "golden_freddy": dict(neck_z=1.745, jaw=dict(z=1.83, y=-0.05)),
    "bonnie": dict(neck_z=1.64, jaw=dict(z=1.755, y=-0.05)),
    "chica": dict(neck_z=1.77, jaw=dict(z=1.885, y=-0.1)),
    "foxy": dict(neck_z=1.765, crotch=1.02, jaw=dict(z=1.865, y=-0.1)),
}


def build(name, jaw=None, preview=True):
    """jaw = dict(z=..., y=...) in normalized units: head islands below z and in front of y go to the jaw."""
    meshes, mats_of = [], []
    for o in src_meshes(name):
        me = world_mesh(o)
        if len(me.polygons):
            # source objects name their UV maps differently; unify so joining keeps every face's UVs
            for i, uvl in enumerate(list(me.uv_layers)):
                uvl.name = "src" if i == 0 else f"src_extra{i}"
            meshes.append(me)
    L0 = landmarks(meshes)
    k = HEIGHT[name] / L0["H"]
    for me in meshes:
        me.transform(Matrix.Scale(k, 4))
    L = landmarks(meshes)
    spec = SPEC.get(name, {})
    for key in ("neck_z", "crotch"):
        if key in spec:
            L[key] = spec[key]
    jaw = jaw or spec.get("jaw")
    jz = (jaw or {}).get("z")
    jy = (jaw or {}).get("y", -0.05)
    jaw_rule = (lambda x, y, z: z < jz and y < jy) if jz else (lambda x, y, z: False)

    bone_of_island = []
    counts = {b: 0 for b in BONES}
    arm_pts = {"left": [], "right": []}
    for mi, me in enumerate(meshes):
        for faces, vs in islands(me):
            c = sum((me.vertices[v].co for v in vs), Vector()) / len(vs)
            b = assign(c, L, jaw_rule)
            bone_of_island.append((mi, faces, vs, b))
            counts[b] += len(faces)

    # pivots (Blender coords)
    leg_x = {}
    for side in ("left", "right"):
        xs = [meshes[mi].vertices[v].co.x for mi, f, vs, b in bone_of_island if b == f"{side}_leg" for v in vs]
        leg_x[side] = float(np.mean(xs)) if xs else (0.2 if side == "left" else -0.2)
    shoulder = L["torso_w"] * 0.9
    piv = {"root": Vector((0, 0, 0)), "body": Vector((0, 0, L["crotch"] + 0.06)),
           "head": Vector((0, 0, L["neck_z"])),
           "left_leg": Vector((leg_x["left"], 0, L["crotch"] + 0.06)), "right_leg": Vector((leg_x["right"], 0, L["crotch"] + 0.06))}
    rot = {}
    for side, s in (("left", 1), ("right", -1)):
        reach = L["max_x_pos"] if s > 0 else L["max_x_neg"]
        sh = Vector((s * shoulder, 0, L["arm_z"]))
        R = Matrix.Rotation(math.radians(s * ARM_DROP), 4, "Y")
        M = Matrix.Translation(sh) @ R @ Matrix.Translation(-sh)
        rot[side] = M
        piv[f"{side}_arm"] = sh
        piv[f"{side}_forearm"] = M @ Vector((s * (shoulder + 0.5 * (reach - shoulder)), 0, L["arm_z"]))
    if jz:
        jy_back = max((meshes[mi].vertices[v].co.y for mi, f, vs, b in bone_of_island if b == "jaw" for v in vs), default=0.0)
        piv["jaw"] = Vector((0, jy_back, jz))
    else:
        piv["jaw"] = Vector((0, 0, L["neck_z"] + 0.1))

    # swing arms down, tag faces with their bone, then join into one object
    objs = []
    for mi, me in enumerate(meshes):
        vb = {}
        fb_ = {}
        for (m2, faces, vs, b) in bone_of_island:
            if m2 != mi:
                continue
            for v in vs:
                vb[v] = b
            for f in faces:
                fb_[f] = b
        for v in me.vertices:
            b = vb.get(v.index, "body")
            if b.endswith("arm"):
                v.co = rot[b.split("_")[0]] @ v.co
        attr = me.attributes.new("bone_id", "INT", "FACE")
        attr.data.foreach_set("value", [BONES.index(fb_.get(p.index, "body")) for p in me.polygons])
        o = bpy.data.objects.new(f"{name}_bk_{mi}", me)
        bpy.context.scene.collection.objects.link(o)
        objs.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = f"{name}_game"
    stats = dict(L={k2: round(v, 3) for k2, v in L.items()}, faces=counts)
    return joined, piv, stats


def bake_export(name, joined, piv, tex=1024, max_tris=24000):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    me = joined.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    bpy.ops.object.select_all(action="DESELECT")
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    # imported faces are disconnected (split vertices); weld them so pieces unwrap as whole islands
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    bm.to_mesh(me)
    bm.free()
    if tris > max_tris:
        mod = joined.modifiers.new("dec", "DECIMATE")
        mod.ratio = max_tris / tris
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # bake into a fresh UV map, keeping the original UVs for the source textures
    src_uv = me.uv_layers.get("src") or me.uv_layers.active
    for uvl in [u for u in me.uv_layers if u.name.startswith("src_extra")]:
        me.uv_layers.remove(uvl)
    src_uv = me.uv_layers.get("src")
    bake_uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = bake_uv
    # textured materials get real UV islands; flat-colour materials share one swatch each
    tex_mats, flat_mats = set(), []
    for i, m in enumerate(me.materials):
        if m and any(n.type == "TEX_IMAGE" and n.image for n in m.node_tree.nodes):
            tex_mats.add(i)
        else:
            flat_mats.append(i)
    for v in me.vertices:
        v.select = False
    for e in me.edges:
        e.select = False
    for p in me.polygons:
        p.select = p.material_index in tex_mats
        if p.select:
            for vi in p.vertices:
                me.vertices[vi].select = True
    # eyes get more texture space: inflate them in 3D while unwrapping, then put them back
    eye_mats = {i for i, m in enumerate(me.materials) if m and m.name.lower().startswith("eye") and i in tex_mats}
    eye_vs = {vi for p in me.polygons if p.material_index in eye_mats for vi in p.vertices}
    saved = {vi: me.vertices[vi].co.copy() for vi in eye_vs}
    for side in (1, -1):
        grp = [vi for vi in eye_vs if me.vertices[vi].co.x * side > 0]
        if grp:
            ctr = sum((me.vertices[vi].co for vi in grp), Vector()) / len(grp)
            for vi in grp:
                me.vertices[vi].co = ctr + (me.vertices[vi].co - ctr) * 2.6
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003, area_weight=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    for vi, co in saved.items():
        me.vertices[vi].co = co
    uvd = me.uv_layers["bake"].data
    FIT, SW = 0.94, 0.04
    swatch = {}
    for k, mi in enumerate(flat_mats):
        x0 = 0.005 + (k % 24) * SW
        y0 = FIT + 0.012 + (k // 24) * SW
        swatch[mi] = (x0, y0)
    for p in me.polygons:
        if p.material_index in tex_mats:
            for li in p.loop_indices:
                uvd[li].uv = uvd[li].uv * FIT
        else:
            x0, y0 = swatch.get(p.material_index, (0.005, FIT + 0.012))
            n = len(p.loop_indices)
            for j, li in enumerate(p.loop_indices):
                a = 2 * math.pi * j / n
                uvd[li].uv = (x0 + SW / 2 + math.cos(a) * SW * 0.3, y0 + SW / 2 + math.sin(a) * SW * 0.3)
    if "src" in me.uv_layers:
        me.uv_layers["src"].active_render = True
    src_uv = me.uv_layers.get("src")
    imgs = {k2: bpy.data.images.new(f"{name}_sfbake_{k2}", tex, tex, alpha=True) for k2 in ("col", "ao")}
    for mat in me.materials:
        if not mat:
            continue
        nt = mat.node_tree
        for n in nt.nodes:
            if n.type == "UVMAP" and not n.uv_map:
                n.uv_map = src_uv.name if src_uv else ""
        node = nt.nodes.new("ShaderNodeTexImage")
        node.name = "SF_BAKE"
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], node.inputs["Vector"])
        nt.nodes.active = node

    def target(k2):
        for mat in me.materials:
            if mat:
                mat.node_tree.nodes["SF_BAKE"].image = imgs[k2]

    scene.cycles.samples = 16
    if scene.world:
        scene.world.light_settings.distance = 0.25
    target("col")
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=6, use_clear=True)
    target("ao")
    bpy.ops.object.bake(type="AO", margin=6, use_clear=True)

    def arr(img):
        a = np.empty(tex * tex * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(tex, tex, 4)

    col, ao = arr(imgs["col"]), arr(imgs["ao"])
    for mi, (x0, y0) in swatch.items():
        m = me.materials[mi]
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m else None
        rgb = [c ** (1 / 2.2) for c in bsdf.inputs["Base Color"].default_value[:3]] if bsdf else [0.1, 0.1, 0.1]
        px0, py0, pw = int(x0 * tex), int(y0 * tex), int(SW * tex)
        col[py0:py0 + pw, px0:px0 + pw, :3] = rgb
        ao[py0:py0 + pw, px0:px0 + pw, :] = 1.0
    out = col.copy()
    out[..., :3] = np.clip(col[..., :3] * (1.1 * (0.6 + 0.4 * ao[..., :1])), 0, 1)
    out[..., 3] = 1.0
    # glowmask: the coloured iris pixels of the eyes (GeckoLib needs at least one opaque pixel)
    glow = np.zeros_like(out)
    mask = np.zeros((tex, tex), dtype=bool)
    uvd = me.uv_layers["bake"].data
    for p in me.polygons:
        if p.material_index not in eye_mats:
            continue
        pts = [np.array(uvd[li].uv[:]) * tex for li in p.loop_indices]
        for k in range(1, len(pts) - 1):
            a, b2, c = pts[0], pts[k], pts[k + 1]
            x0, x1 = int(max(0, min(a[0], b2[0], c[0]))), int(min(tex - 1, max(a[0], b2[0], c[0]) + 1))
            y0, y1 = int(max(0, min(a[1], b2[1], c[1]))), int(min(tex - 1, max(a[1], b2[1], c[1]) + 1))
            if x1 <= x0 or y1 <= y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            d = (b2[1] - c[1]) * (a[0] - c[0]) + (c[0] - b2[0]) * (a[1] - c[1])
            if abs(d) < 1e-9:
                continue
            l1 = ((b2[1] - c[1]) * (gx - c[0]) + (c[0] - b2[0]) * (gy - c[1])) / d
            l2 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / d
            inside = (l1 >= -0.01) & (l2 >= -0.01) & (1 - l1 - l2 >= -0.01)
            mask[y0:y1, x0:x1] |= inside
    rgb = out[..., :3]
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    iris = mask & (sat > 0.18) & (rgb.max(axis=2) > 0.15)
    glow[iris, :3] = rgb[iris]
    glow[iris, 3] = 1.0
    glow[tex - 1, tex - 1] = (0.0, 0.0, 0.0, 1.0)
    tex_dir = os.path.join(fb.ASSETS, "textures", "entity")
    for data, fname in ((out, f"{name}_hd.png"), (glow, f"{name}_hd_glowmask.png")):
        img = bpy.data.images.new(f"{name}_sfout", tex, tex, alpha=True)
        img.pixels.foreach_set(data.ravel())
        img.filepath_raw = os.path.join(tex_dir, fname)
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)
    for img in imgs.values():
        bpy.data.images.remove(img)
    for mat in me.materials:
        if mat and "SF_BAKE" in mat.node_tree.nodes:
            mat.node_tree.nodes.remove(mat.node_tree.nodes["SF_BAKE"])

    # the exporter reads the active UV map
    for i, uvl in enumerate(me.uv_layers):
        if uvl.name == "bake":
            me.uv_layers.active_index = i

    class C:
        pass

    c = C()
    c.name = name
    fb.export_mesh(c, joined, BONES)
    write_geo(name, piv, tex)
    return sum(len(p.vertices) - 2 for p in me.polygons)


def write_geo(name, piv, tex):
    bones = []
    for b in BONES:
        p = piv[b]
        e = {"name": b, "pivot": [round(p.x * 16, 3), round(p.z * 16, 3), round(p.y * 16, 3)]}
        if b in PARENT:
            e["parent"] = PARENT[b]
        bones.append(e)
    geo = {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": f"geometry.{name}", "texture_width": tex, "texture_height": tex,
                        "visible_bounds_width": 3, "visible_bounds_height": 3.5, "visible_bounds_offset": [0, 1.5, 0]},
        "bones": bones}]}
    with open(os.path.join(fb.ASSETS, "geo", "entity", f"{name}.geo.json"), "w") as f:
        json.dump(geo, f, indent=1)


PALETTE = [(0.5, 0.5, 0.5), (0.9, 0.9, 0.2), (0.2, 0.8, 0.9), (0.95, 0.2, 0.2), (0.2, 0.9, 0.2), (0.1, 0.5, 0.1),
           (0.3, 0.3, 1.0), (0.1, 0.1, 0.5), (0.9, 0.5, 0.1), (0.6, 0.2, 0.7)]


def preview(name, path, jaw=None):
    """Render the bone segmentation (one colour per bone) from the front and the side."""
    joined, piv, stats = build(name, jaw=jaw)
    me = joined.data
    ca = me.color_attributes.new("bonecol", "FLOAT_COLOR", "CORNER")
    ids = [0] * len(me.polygons)
    me.attributes["bone_id"].data.foreach_get("value", ids)
    for p in me.polygons:
        c = PALETTE[ids[p.index]] + (1.0,)
        for li in p.loop_indices:
            ca.data[li].color = c
    sc = bpy.context.scene
    for col in bpy.data.collections:
        if col.name.startswith("src_"):
            col.hide_render = True
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.color_type = "VERTEX"
    sc.render.resolution_x, sc.render.resolution_y = 1000, 700
    cam = sc.camera
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 3.2
    for tag, loc, rot, off in (("front", (0, -10, 1.3), (math.pi / 2, 0, 0), 0), ):
        cam.location = loc
        cam.rotation_euler = rot
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(joined, do_unlink=True)
    return stats
