"""Realistic FNAF animatronics built procedurally inside Blender (run through the Blender MCP).

Coordinates in this file are Blockbench pixels (16 px = 1 block, Y up, -Z = front) so parts
line up with the GeckoLib skeleton from rigs.json. In Blender 1 unit = 1 block, Z up, -Y front.

Pipeline per character:
  build parts (parented to one empty per bone) -> bake copy (joined, unwrapped, baked
  color*AO + emission) -> export assets/fnaf/meshes/<id>.fmesh + textures/entity/<id>_hd*.png
  -> apply rest pose for renders.
"""
import json
import math
import os
import struct

import bmesh
import bpy
from mathutils import Matrix, Vector

S = 1.0 / 16.0
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf")
RIGS = json.load(open(os.path.join(HERE, "rigs.json"), encoding="utf-8"))
P_SWAP = Matrix(((1, 0, 0), (0, 0, 1), (0, 1, 0)))  # bb (x,y,z) <-> blender (x,z,y)


def V(x, y, z):
    return Vector((x * S, z * S, y * S))


def bb_rot(rot):
    """Blockbench euler degrees (applied Z*Y*X) -> Blender 3x3 rotation."""
    rx, ry, rz = (math.radians(a) for a in (rot or (0, 0, 0)))
    r = Matrix.Rotation(rz, 3, "Z") @ Matrix.Rotation(ry, 3, "Y") @ Matrix.Rotation(rx, 3, "X")
    return P_SWAP @ r @ P_SWAP


def lin(c):
    return tuple(((v / 255.0) ** 2.2) for v in c) + (1.0,)


# ====================================================================== materials

def _nodes(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    return m, nt, bsdf


def _sock(node, ident):
    return next(s for s in list(node.inputs) + list(node.outputs) if s.identifier == ident and s.enabled)


def _mix(nt, fac, a, b):
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    _link(nt, fac, _sock(mx, "Factor_Float"))
    for val, ident in ((a, "A_Color"), (b, "B_Color")):
        sock = _sock(mx, ident)
        if isinstance(val, tuple):
            sock.default_value = val
        else:
            _link(nt, val, sock)
    return _sock(mx, "Result_Color")


def _link(nt, out, inp):
    if isinstance(out, (int, float)):
        inp.default_value = out
    else:
        nt.links.new(out, inp)


def _noise(nt, scale, detail=4.0, rough=0.55, coord="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    nt.links.new(tc.outputs[coord], n.inputs["Vector"])
    return n


def _ramp(nt, fac, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    _link(nt, fac, r.inputs["Fac"])
    els = r.color_ramp.elements
    while len(els) > len(stops):
        els.remove(els[-1])
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = col if len(col) == 4 else col + (1.0,)
    return r


def _math(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    _link(nt, a, n.inputs[0])
    if b is not None:
        _link(nt, b, n.inputs[1])
    return n.outputs[0]


def _dirt(nt, base, amount, dirt_col=(48, 36, 24)):
    """Darken crevices (AO) and add grime blotches."""
    if amount <= 0:
        return base
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.12
    crev = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, ao.outputs["AO"]), amount * 1.6)
    out = _mix(nt, _math(nt, "MINIMUM", crev, 1.0), base, lin(dirt_col))
    blot = _noise(nt, 3.5, 8, 0.6)
    patches = _ramp(nt, blot.outputs["Fac"], [(0.5 - amount * 0.25, (0, 0, 0)), (0.62, (1, 1, 1))])
    out = _mix(nt, _math(nt, "MULTIPLY", patches.outputs["Color"], min(0.7, amount)), out, lin(_mul(dirt_col, 0.8)))
    return out


def _mul(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _bump(nt, bsdf, scale, strength, detail=2.0):
    n = _noise(nt, scale, detail, 0.6)
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = 0.002
    nt.links.new(n.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])


def mat_fur(name, color, dirt=0.25, sheen=0.7):
    m, nt, bsdf = _nodes(name)
    var = _noise(nt, 7.0, 6, 0.6)
    base = _ramp(nt, var.outputs["Fac"], [(0.3, lin(_mul(color, 0.68))), (0.7, lin(_mul(color, 1.0)))]).outputs["Color"]
    streak = _noise(nt, 60.0, 3, 0.7)
    base = _mix(nt, _math(nt, "MULTIPLY", streak.outputs["Fac"], 0.25), base, lin(_mul(color, 0.6)))
    base = _dirt(nt, base, dirt)
    nt.links.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    bsdf.inputs["Sheen Weight"].default_value = sheen * 0.6
    bsdf.inputs["Sheen Roughness"].default_value = 0.5
    bsdf.inputs["Sheen Tint"].default_value = lin(_mul(color, 1.3))
    _fur_bump(nt, bsdf)
    return m


def _fur_bump(nt, bsdf):
    """Clumpy, slightly streaked fibres: two noise layers into one bump."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (140.0, 140.0, 45.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Detail"].default_value = 10.0
    n1.inputs["Roughness"].default_value = 0.7
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    n2 = _noise(nt, 18.0, 4, 0.5)
    h = _math(nt, "ADD", _math(nt, "MULTIPLY", n1.outputs["Fac"], 0.7), _math(nt, "MULTIPLY", n2.outputs["Fac"], 0.3))
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.65
    b.inputs["Distance"].default_value = 0.006
    nt.links.new(h, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])


def mat_plastic(name, color, rough=0.3, coat=0.5, dirt=0.1):
    m, nt, bsdf = _nodes(name)
    var = _noise(nt, 4.0, 3, 0.5)
    base = _ramp(nt, var.outputs["Fac"], [(0.35, lin(_mul(color, 0.92))), (0.65, lin(_mul(color, 1.05)))]).outputs["Color"]
    base = _dirt(nt, base, dirt)
    nt.links.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.08
    return m


def mat_metal(name, color, rough=0.38, rust=0.15):
    m, nt, bsdf = _nodes(name)
    scratches = _noise(nt, 80.0, 6, 0.7)
    base = _ramp(nt, scratches.outputs["Fac"], [(0.35, lin(_mul(color, 0.8))), (0.65, lin(_mul(color, 1.1)))]).outputs["Color"]
    if rust > 0:
        rn = _noise(nt, 5.0, 8, 0.65)
        mask = _ramp(nt, rn.outputs["Fac"], [(0.6 - rust * 0.3, (0, 0, 0)), (0.7, (1, 1, 1))]).outputs["Color"]
        base = _mix(nt, mask, base, lin((96, 54, 28)))
        rgh = _math(nt, "ADD", rough, _math(nt, "MULTIPLY", _ramp(nt, rn.outputs["Fac"], [(0.5, (0, 0, 0)), (0.7, (1, 1, 1))]).outputs["Color"], 0.45))
        nt.links.new(rgh, bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
    base = _dirt(nt, base, rust * 0.8)
    nt.links.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 1.0
    _bump(nt, bsdf, 160.0, 0.15)
    return m


def mat_glow(name, color, strength=8.0):
    m, nt, bsdf = _nodes(name)
    bsdf.inputs["Base Color"].default_value = lin(color)
    bsdf.inputs["Emission Color"].default_value = lin(color)
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = 0.15
    bsdf.inputs["Coat Weight"].default_value = 1.0
    m["glow"] = True
    return m


def mat_simple(name, color, rough=0.5, metallic=0.0, coat=0.0, sss=0.0, sheen=0.0):
    m, nt, bsdf = _nodes(name)
    bsdf.inputs["Base Color"].default_value = lin(color)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Subsurface Weight"].default_value = sss
    bsdf.inputs["Sheen Weight"].default_value = sheen
    return m


def mat_stripes(name, c1, c2, axis="Z", freq=10.0, rough=0.6, sheen=0.3, radial=False, dirt=0.05):
    """Hard stripes along an object axis (or around it when radial)."""
    m, nt, bsdf = _nodes(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    if radial:
        ang = _math(nt, "ARCTAN2", sep.outputs["Y"], sep.outputs["X"])
        coord = _math(nt, "MULTIPLY", ang, freq / math.tau)
    else:
        coord = _math(nt, "MULTIPLY", sep.outputs[axis], freq)
    band = _math(nt, "GREATER_THAN", _math(nt, "FRACT", coord), 0.5)
    base = _mix(nt, band, lin(c1), lin(c2))
    base = _dirt(nt, base, dirt)
    nt.links.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Sheen Weight"].default_value = sheen
    return m


# ====================================================================== geometry

class Char:
    def __init__(self, name):
        self.name = name
        self.rig = RIGS[name]
        self.a = self.rig["anchors"]
        self.p = self.rig["params"]
        self.coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(self.coll)
        self.empties = {}
        self.mats = {}
        self.parts = []
        self.n = 0
        for b in self.rig["bones"]:
            e = bpy.data.objects.new(f"{name}:{b['name']}", None)
            e.empty_display_size = 0.05
            e.location = V(*b["pivot"])
            self.coll.objects.link(e)
            self.empties[b["name"]] = e
        bpy.context.view_layer.update()
        for b in self.rig["bones"]:
            if b["parent"]:
                e, p = self.empties[b["name"]], self.empties[b["parent"]]
                e.parent = p
                e.matrix_parent_inverse = p.matrix_world.inverted()

    # ---- materials registry
    def mat(self, key, factory, *args, **kw):
        self.mats[key] = factory(f"{self.name}_{key}", *args, **kw)

    # ---- objects
    def _finish(self, me, bone, mat, smooth=True):
        self.n += 1
        if len(me.vertices):
            ctr = sum((v.co for v in me.vertices), Vector()) / len(me.vertices)
            me.transform(Matrix.Translation(-ctr))
        else:
            ctr = Vector()
        obj = bpy.data.objects.new(f"{self.name}_{bone}_{self.n:03d}", me)
        obj.location = ctr
        if smooth:
            for poly in me.polygons:
                poly.use_smooth = True
        me.materials.append(self.mats[mat])
        self.coll.objects.link(obj)
        emp = self.empties[bone]
        obj.parent = emp
        obj.matrix_parent_inverse = emp.matrix_world.inverted()
        obj["bone"] = bone
        self.parts.append(obj)
        return obj

    def _bm_obj(self, bm, bone, mat, smooth=True):
        me = bpy.data.meshes.new(f"{self.name}_m{self.n}")
        bm.to_mesh(me)
        bm.free()
        return self._finish(me, bone, mat, smooth)

    def ellipsoid(self, bone, mat, c, r, rot=None, segs=24, rings=14):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
        R = bb_rot(rot)
        sc = Matrix.Diagonal((r[0] * S, r[2] * S, r[1] * S))
        M = R @ sc
        for v in bm.verts:
            v.co = M @ v.co + V(*c)
        return self._bm_obj(bm, bone, mat)

    def sphere(self, bone, mat, c, r, **kw):
        return self.ellipsoid(bone, mat, c, (r, r, r), **kw)

    def rbox(self, bone, mat, c, size, bevel=0.3, rot=None, segments=3):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        sc = Matrix.Diagonal((size[0] * S, size[2] * S, size[1] * S))
        for v in bm.verts:
            v.co = sc @ v.co
        if bevel > 0:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bevel, min(size) / 2 - 0.01) * S, segments=segments,
                            profile=0.5, affect="EDGES", clamp_overlap=True)
        R = bb_rot(rot)
        for v in bm.verts:
            v.co = R @ v.co + V(*c)
        return self._bm_obj(bm, bone, mat)

    def lathe(self, bone, mat, a, b, profile, segs=18, smooth=True):
        """Surface of revolution between bb points a and b. profile = [(s_px_along_axis, radius_px)]."""
        A, B = V(*a), V(*b)
        axis = (B - A).normalized() if (B - A).length > 1e-6 else Vector((0, 0, 1))
        rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix()
        bm = bmesh.new()
        rings = []
        for s, r in profile:
            if r <= 1e-4:
                rings.append([bm.verts.new(A + rot @ Vector((0, 0, s * S)))])
            else:
                ring = []
                for i in range(segs):
                    t = i / segs * math.tau
                    ring.append(bm.verts.new(A + rot @ Vector((math.cos(t) * r * S, math.sin(t) * r * S, s * S))))
                rings.append(ring)
        for r0, r1 in zip(rings, rings[1:]):
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                for i in range(segs):
                    bm.faces.new((r0[0], r1[(i + 1) % segs], r1[i]))
            elif len(r1) == 1:
                for i in range(segs):
                    bm.faces.new((r0[i], r0[(i + 1) % segs], r1[0]))
            else:
                for i in range(segs):
                    bm.faces.new((r0[i], r0[(i + 1) % segs], r1[(i + 1) % segs], r1[i]))
        if len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return self._bm_obj(bm, bone, mat, smooth)

    def capsule(self, bone, mat, a, b, r0, r1=None, segs=18, cap=4):
        r1 = r0 if r1 is None else r1
        L = (Vector(b) - Vector(a)).length
        prof = []
        for i in range(cap + 1):
            ph = -math.pi / 2 + math.pi / 2 * i / cap
            prof.append((r0 * math.sin(ph), r0 * math.cos(ph)))
        for i in range(cap + 1):
            ph = math.pi / 2 * i / cap
            prof.append((L + r1 * math.sin(ph), r1 * math.cos(ph)))
        return self.lathe(bone, mat, a, b, prof, segs)

    def cylinder(self, bone, mat, a, b, r, bevel=0.15, segs=20, r_end=None):
        r_end = r if r_end is None else r_end
        L = (Vector(b) - Vector(a)).length
        bv = min(bevel, r * 0.4, L * 0.3)
        prof = [(0, 0), (0, r - bv), (bv * 0.3, r - bv * 0.3), (bv, r), (L - bv, r_end), (L - bv * 0.3, r_end - bv * 0.3),
                (L, r_end - bv), (L, 0)]
        return self.lathe(bone, mat, a, b, prof, segs)

    def cone(self, bone, mat, a, b, r, segs=12):
        L = (Vector(b) - Vector(a)).length
        return self.lathe(bone, mat, a, b, [(0, 0), (0, r), (L * 0.55, r * 0.6), (L, 0.02)], segs)

    def blob(self, bone, mat, elements, res=0.045, decimate=None):
        """Metaball union of ellipsoids: elements = [(center, half_extents, rot)] in px."""
        self.n += 1
        nm = f"mb_{self.name}_{bone}_{self.n:03d}_x"
        mb = bpy.data.metaballs.new(nm)
        mb.resolution = res
        mb.render_resolution = res
        mb.threshold = 0.6
        for el in elements:
            c, h = el[0], el[1]
            rot = el[2] if len(el) > 2 else None
            e = mb.elements.new()
            e.type = "ELLIPSOID"
            e.co = V(*c)
            hb = (h[0] * S, h[2] * S, h[1] * S)
            R = max(hb) / 0.672
            e.radius = R
            e.size_x, e.size_y, e.size_z = (x / max(hb) for x in hb)
            e.rotation = bb_rot(rot).to_quaternion()
            e.stiffness = 2.0
        obj = bpy.data.objects.new(nm, mb)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        bpy.data.objects.remove(obj)
        bpy.data.metaballs.remove(mb)
        part = self._finish(me, bone, mat)
        if decimate:
            mod = part.modifiers.new("dec", "DECIMATE")
            mod.ratio = decimate
        return part

    def sym(self, fn, bone, mat, *pts, **kw):
        """Mirror pair; for paired bones pass bone='{side}_arm' style templates with {side}."""
        out = []
        for s, side in ((1, "left"), (-1, "right")):
            args = []
            for p in pts:
                if isinstance(p, (list, tuple)) and len(p) == 3 and all(isinstance(v, (int, float)) for v in p) and \
                        not getattr(p, "_size", False):
                    args.append((p[0] * s, p[1], p[2]))
                else:
                    args.append(p)
            k = dict(kw)
            if k.get("rot"):
                r = k["rot"]
                k["rot"] = (r[0], r[1] * s, r[2] * s)
            out.append(fn(bone.format(side=side), mat, *args, **k))
        return out

    def text(self, bone, mat_keys, text, c, size, depth=0.25, rot=None):
        cu = bpy.data.curves.new(f"{self.name}_txt{self.n}", "FONT")
        cu.body = text
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.extrude = depth * S / 2
        cu.size = size * S
        cu.bevel_depth = 0.0
        tmp = bpy.data.objects.new("tmp_txt", cu)
        bpy.context.scene.collection.objects.link(tmp)
        bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        bpy.data.objects.remove(tmp)
        bpy.data.curves.remove(cu)
        # text lies in XY plane facing +Z; stand it up facing -Y (front) then place
        R = bb_rot(rot) @ Matrix.Rotation(math.pi / 2, 3, "X")
        me.transform(R.to_4x4())
        me.transform(Matrix.Translation(V(*c)))
        obj = self._finish(me, bone, mat_keys[0], smooth=False)
        if len(mat_keys) > 1:
            # colour letters by splitting faces along X into bands
            me.materials.clear()
            for k in mat_keys:
                me.materials.append(self.mats[k])
            xs = [p.center.x for p in me.polygons]
            lo, hi = min(xs), max(xs)
            n = len(mat_keys)
            for p in me.polygons:
                p.material_index = min(n - 1, int((p.center.x - lo) / (hi - lo + 1e-9) * n))
        return obj


# ====================================================================== shared anatomy

def std_mats(c, metal=(120, 120, 126), rust=0.15):
    c.mat("metal", mat_metal, metal, 0.38, rust)
    c.mat("metal_dark", mat_metal, _mul(metal, 0.55), 0.5, rust)
    c.mat("chrome", mat_metal, (200, 202, 208), 0.18, 0.0)
    c.mat("teeth", mat_simple, (232, 226, 200), 0.35, 0, 0.3, 0.15)
    c.mat("mouth", mat_simple, (40, 12, 12), 0.6)
    c.mat("black", mat_plastic, (16, 15, 15), 0.25, 0.6, 0.0)
    c.mat("eye_white", mat_simple, (238, 236, 228), 0.12, 0, 1.0)
    c.mat("pupil", mat_simple, (6, 6, 8), 0.05, 0, 1.0)
    c.mat("void", mat_simple, (3, 3, 4), 0.9)
    c.mat("wire_r", mat_plastic, (170, 30, 30), 0.4, 0.2, 0.0)
    c.mat("wire_b", mat_plastic, (40, 70, 180), 0.4, 0.2, 0.0)


def joint(c, bone, at, r):
    c.sphere(bone, "metal", at, r * 0.75, segs=14, rings=8)
    c.cylinder(bone, "metal_dark", (at[0] - r, at[1], at[2]), (at[0] + r, at[1], at[2]), r * 0.45, segs=12)


def piston(c, bone, x, y0, y1, z=0.0):
    h = y1 - y0
    c.cylinder(bone, "metal", (x, y0, z + 0.4), (x, y1, z + 0.4), 0.65, segs=12)
    c.cylinder(bone, "metal_dark", (x, y0 + h * 0.45, z - 0.8), (x, y1 - 0.3, z - 0.8), 0.5, segs=12)
    c.cylinder(bone, "chrome", (x, y0 + 0.3, z - 0.8), (x, y0 + h * 0.5, z - 0.8), 0.28, segs=10)


def eye(c, bone, center, r, iris_mat, look=(0.0, -0.1), lid_mat=None, lid=0.35):
    x, y, z = center
    c.sphere(bone, "eye_white", center, r, segs=24, rings=16)
    ix, iy = x + look[0] * r, y + look[1] * r
    c.ellipsoid(bone, iris_mat, (ix, iy, z - r * 0.86), (r * 0.52, r * 0.52, r * 0.22), segs=20, rings=10)
    c.ellipsoid(bone, "pupil", (ix, iy, z - r * 0.97), (r * 0.24, r * 0.24, r * 0.1), segs=14, rings=8)
    if lid_mat:
        c.ellipsoid(bone, lid_mat, (x, y + r * (1.25 - lid), z - r * 0.02), (r * 1.16, r * 0.48, r * 1.1), rot=(-14, 0, 0))


def socket(c, bone, center, r, pin=(255, 255, 255)):
    x, y, z = center
    c.ellipsoid(bone, "void", (x, y, z), (r, r * 0.92, r * 0.5))
    c.sphere(bone, "pin", (x, y - r * 0.08, z - r * 0.45), r * 0.16, segs=10, rings=6)


def teeth_row(c, bone, y, z0, width, n, h=0.8, up=True, pointed=False, curve=1.2, mat="teeth"):
    for i in range(n):
        t = (i + 0.5) / n - 0.5
        x = t * width
        z = z0 + (t * 2) ** 2 * curve
        if pointed:
            tip = y - h if up else y + h
            c.cone(bone, mat, (x, y, z), (x, tip, z - 0.15), width / n * 0.45, segs=8)
        else:
            c.rbox(bone, mat, (x, y - (h / 2 if up else -h / 2), z), (width / n * 0.86, h, 0.7), bevel=0.18, segments=2)


def limb_suit(c, side, s, fur, fur2=None, hand_style="paw", hand_mat=None, endo_fore=False):
    """Shoulder, upper arm, elbow, forearm, wrist and hand for a suited animatronic."""
    a, p = c.a, c.p
    tw = a["tw"]
    aw, ua, fa = p["arm_w"], p["upper_arm"], p["forearm"]
    N = a["N"]
    ax = s * (tw / 2 + aw / 2 + 0.1)
    sy = N - 1.6
    ey = sy - ua - 0.5
    hy = sy - ua - 1 - fa
    arm, fore = f"{side}_arm", f"{side}_forearm"
    r = aw / 2
    c.sphere(arm, fur, (ax, sy + 0.2, 0), r * 1.35)
    c.capsule(arm, fur, (ax, sy, 0), (ax, sy - ua + 0.3, 0), r * 1.12, r * 1.0)
    joint(c, arm, (ax, ey, 0), r * 0.85)
    if endo_fore:
        piston(c, fore, ax, hy, ey - 0.6)
    else:
        c.capsule(fore, fur, (ax, ey - 0.7, 0), (ax, hy + 0.4, 0), r * 1.02, r * 0.88)
    joint(c, fore, (ax, hy - 0.1, 0), r * 0.6)
    hand(c, fore, ax, hy - 0.5, s, aw, hand_style, hand_mat or fur)
    return ax, hy - 0.5, fore


def hand(c, bone, ax, top, s, aw, style, mat):
    zw = aw + 0.6
    if style == "none":
        return
    endo = style == "endo"
    thin = style in ("endo", "puppet")
    m = "metal" if endo else mat
    c.ellipsoid(bone, m, (ax, top - 1.4, 0), (aw * (0.3 if thin else 0.42), 1.5, zw * 0.5))
    fr = 0.28 if endo else (0.32 if thin else zw / 8 * 0.85)
    ln = 1.5 if endo else (2.6 if style == "puppet" else 1.25)
    for i in range(4):
        fz = -zw / 2 + zw * (i + 0.5) / 4
        k0 = (ax, top - 2.6, fz)
        k1 = (ax - s * 0.15, top - 2.6 - ln, fz)
        k2 = (ax - s * 0.75, top - 2.6 - ln * 1.85, fz - 0.1)
        c.capsule(bone, m, k0, k1, fr, fr * 0.92, segs=10, cap=3)
        c.capsule(bone, m, k1, k2, fr * 0.92, fr * 0.8, segs=10, cap=3)
        if endo:
            c.sphere(bone, "metal_dark", k1, fr * 1.35, segs=10, rings=6)
    c.capsule(bone, m, (ax, top - 1.2, -zw / 2 + 0.2), (ax - s * 0.3, top - 2.8, -zw / 2 - 0.9), fr * 1.1, fr * 0.9, segs=10, cap=3)


def leg_suit(c, side, s, thigh, shin, foot_mat, foot_style="paw", endo_shin=False, sole="black", metal_toes=False):
    p, L = c.p, c.a["L"]
    lw = p["leg_w"]
    ld = p.get("leg_d", lw)
    x = s * p["hip_x"]
    leg = f"{side}_leg"
    k0, k1 = L * 0.45, L * 0.56
    r = lw / 2
    c.capsule(leg, thigh, (x, L + 0.2, 0), (x, k1 + 0.2, 0), r * 1.12, r * 1.0)
    joint(c, leg, (x, (k0 + k1) / 2, 0), r * 0.75)
    if endo_shin:
        piston(c, leg, x, 2.4, k0)
    else:
        c.capsule(leg, shin, (x, k0 - 0.3, 0), (x, 2.6, 0), r * 0.98, r * 0.86)
    joint(c, leg, (x, 2.4, 0), r * 0.55)
    f = p.get("foot", 2.4)
    if foot_style == "paw":
        els = [((x, 1.35, -f * 0.4), (r + 0.75, 1.3, ld / 2 + f * 0.55)), ((x, 1.5, 0.9), (r + 0.3, 1.35, 1.7))]
        if not metal_toes:
            els += [((x + i * lw * 0.3, 1.0, -ld / 2 - f + 0.5), (0.95, 0.85, 1.0)) for i in (-1, 0, 1)]
        c.blob(leg, foot_mat, els, res=0.035)
        if metal_toes:
            for i in (-1, 0, 1):
                c.capsule(leg, "metal", (x + i * lw * 0.3, 0.8, -ld / 2 - f + 0.6), (x + i * lw * 0.33, 0.6, -ld / 2 - f - 0.9), 0.4, 0.32, segs=10)
    elif foot_style == "bird":
        c.blob(leg, foot_mat, [((x, 1.2, 0), (r + 0.4, 1.2, ld / 2 + 0.5))], res=0.04)
        for i in (-1, 0, 1):
            ang = math.radians(i * 18)
            end = (x + math.sin(ang) * (f + 1.6), 0.7, -math.cos(ang) * (f + 1.6) - ld / 2 + 0.6)
            c.capsule(leg, foot_mat, (x, 0.9, -0.5), end, 0.75, 0.6, segs=12)
            tip = (end[0] + math.sin(ang) * 0.9, 0.35, end[2] - math.cos(ang) * 0.9)
            c.cone(leg, "black", end, tip, 0.5, segs=8)
        c.capsule(leg, foot_mat, (x, 0.9, 0.4), (x, 0.6, ld / 2 + 1.5), 0.65, 0.5, segs=10)
    elif foot_style == "endo":
        c.rbox(leg, "metal_dark", (x, 0.8, -f * 0.4), (lw + 0.8, 1.2, ld + f), bevel=0.3)
        for i in (-1, 0, 1):
            tx = x + i * 1.1
            c.capsule(leg, "metal", (tx, 0.7, -ld / 2 - f * 0.5), (tx, 0.5, -ld / 2 - f - 1.0), 0.35, 0.3, segs=10)
        c.sphere(leg, "metal", (x, 0.9, ld / 2 + 0.5), 0.8, segs=12, rings=8)
    elif foot_style == "shoe":
        c.blob(leg, foot_mat, [((x, 1.1, -f * 0.4), (r + 0.5, 1.1, ld / 2 + f * 0.7))], res=0.035)
        c.rbox(leg, sole, (x, 0.15, -f * 0.4), (lw + 1.0, 0.3, ld + f * 1.3), bevel=0.12)


def torso_suit(c, fur, belly=None, pelvis=None):
    a = c.a
    L, N, tw, td = a["L"], a["N"], a["tw"], a["td"]
    c.blob("body", fur, [((0, (L + N) / 2 + 1.2, 0), (tw / 2 + 0.2, (N - L) / 2 - 0.4, td / 2 + 0.2)),
                         ((0, L + 3.5, -0.4), (tw / 2 - 0.4, 3.4, td / 2 + 0.3)),
                         ((0, N - 1.5, 0), (tw / 2 + 0.8, 2.2, td / 2 - 0.6))], res=0.05)
    c.blob("body", pelvis or fur, [((0, L + 0.6, 0), (tw / 2 - 1.0, 2.6, td / 2 - 0.6))], res=0.05)
    if belly:
        c.ellipsoid("body", belly, (0, L + 5.6, -td / 2 + 0.25), (tw / 2 - 2.0, (N - L) / 2 - 1.8, 1.25))
    c.cylinder("head", "metal", (0, N - 1.0, 0), (0, N + 2.2, 0), 1.2, segs=14)


def bear_head(c, fur, fur2, iris=None, sockets=False, pin=(255, 255, 255), ear_tilt=0, nose="black"):
    y0 = c.a["y0"]
    c.blob("head", fur, [((0, y0 + 4.8, 0.2), (5.6, 4.6, 5.0)),
                         ((0, y0 + 2.2, -1.2), (6.1, 2.4, 4.3)),
                         ((0, y0 + 6.8, -3.0), (4.9, 1.5, 2.0))], res=0.04)
    c.blob("head", fur2, [((0, y0 + 3.4, -5.6), (3.9, 1.9, 2.5)), ((0, y0 + 2.6, -5.2), (3.4, 1.2, 2.4))], res=0.035)
    c.ellipsoid("head", nose, (0, y0 + 4.85, -7.9), (1.65, 0.85, 0.95))
    c.ellipsoid("head", "mouth", (0, y0 + 1.5, -5.4), (3.2, 0.9, 2.2))
    teeth_row(c, "head", y0 + 1.9, -7.55, 5.8, 8, h=0.75, up=True, curve=1.4)
    c.blob("jaw", fur2, [((0, y0 + 0.1, -5.2), (3.7, 1.05, 2.6)), ((0, y0 + 0.2, -3.4), (3.0, 0.9, 1.2))], res=0.035)
    teeth_row(c, "jaw", y0 + 0.95, -7.45, 5.6, 8, h=0.7, up=False, curve=1.4)
    for s in (1, -1):
        ex = s * 2.55
        if sockets:
            socket(c, "head", (ex, y0 + 6.0, -4.3), 1.35, pin)
        else:
            eye(c, "head", (ex, y0 + 6.0, -4.1), 1.35, "iris", look=(-s * 0.08, -0.1), lid_mat=fur)
        c.rbox("head", "black", (ex, y0 + 7.9, -4.75), (3.2, 0.7, 0.8), bevel=0.25, rot=(0, 0, -s * 12))
        c.ellipsoid("head", fur, (s * 4.5, y0 + 9.4, 0.4), (1.8, 1.7, 0.9), rot=(0, 0, -s * (14 - ear_tilt)))
        c.ellipsoid("head", fur2, (s * 4.5, y0 + 9.35, -0.25), (1.15, 1.1, 0.4), rot=(0, 0, -s * (14 - ear_tilt)))


def rabbit_head(c, fur, fur2, iris=None, sockets=False, pin=(255, 255, 255), broken_ear=False):
    y0 = c.a["y0"]
    c.blob("head", fur, [((0, y0 + 4.6, 0.2), (5.1, 4.4, 4.7)),
                         ((0, y0 + 2.0, -1.0), (5.6, 2.3, 4.0)),
                         ((0, y0 + 6.6, -2.8), (4.4, 1.4, 1.8))], res=0.04)
    c.blob("head", fur2, [((0, y0 + 3.2, -5.3), (4.0, 1.9, 2.4)), ((0, y0 + 2.4, -4.8), (3.6, 1.2, 2.2))], res=0.035)
    c.ellipsoid("head", "nose", (0, y0 + 4.65, -7.45), (1.3, 0.7, 0.8))
    c.ellipsoid("head", "mouth", (0, y0 + 1.3, -5.0), (3.3, 0.9, 2.1))
    teeth_row(c, "head", y0 + 1.7, -7.1, 6.0, 8, h=0.75, up=True, curve=1.3)
    c.blob("jaw", fur2, [((0, y0 - 0.1, -4.9), (3.7, 1.05, 2.5)), ((0, y0, -3.2), (3.0, 0.9, 1.2))], res=0.035)
    teeth_row(c, "jaw", y0 + 0.75, -7.0, 5.8, 8, h=0.7, up=False, curve=1.3)
    for s in (1, -1):
        ex = s * 2.4
        if sockets:
            socket(c, "head", (ex, y0 + 5.8, -4.0), 1.3, pin)
        else:
            eye(c, "head", (ex, y0 + 5.8, -3.85), 1.3, "iris", look=(-s * 0.08, -0.1), lid_mat=fur)
        c.rbox("head", "black", (ex, y0 + 7.6, -4.45), (2.9, 0.65, 0.8), bevel=0.25, rot=(0, 0, -s * 14))
    for side, s in (("left", 1), ("right", -1)):
        bn = f"{side}_ear"
        broken = broken_ear and side == "right"
        x = s * 2.4
        top = y0 + (14.5 if broken else 19.4)
        mid = (y0 + 8.2 + top) / 2
        c.ellipsoid(bn, fur, (x, mid, 0.6), (1.45, (top - y0 - 8.2) / 2 + 0.6, 0.85))
        c.ellipsoid(bn, fur2, (x, mid + 0.2, 0.05), (0.85, (top - y0 - 8.2) / 2 - 0.4, 0.35))
        if broken:
            c.cylinder(bn, "metal", (x, top - 0.5, 0.6), (x + s * 0.4, top + 2.5, 1.0), 0.28, segs=8)
            c.capsule(bn, "wire_r", (x + 0.3, top - 0.3, 0.4), (x + s * 1.2, top + 1.4, 0.2), 0.14, segs=6, cap=2)


def hat(c, mat, band):
    y0 = c.a["y0"]
    c.cylinder("head", mat, (0, y0 + 8.75, -0.3), (0, y0 + 9.3, -0.3), 3.6, bevel=0.2, segs=28)
    c.cylinder("head", mat, (0, y0 + 9.2, -0.3), (0, y0 + 13.6, -0.3), 2.35, bevel=0.25, segs=28, r_end=2.25)
    c.cylinder("head", band, (0, y0 + 9.3, -0.3), (0, y0 + 10.0, -0.3), 2.4, bevel=0.05, segs=28)


def bowtie(c, mat):
    N, td = c.a["N"], c.a["td"]
    z = -td / 2 - 0.2
    c.ellipsoid("body", mat, (0, N - 1.6, z - 0.2), (0.8, 0.75, 0.5))
    for s in (1, -1):
        c.blob("body", mat, [((s * 1.9, N - 1.6, z), (1.4, 1.1, 0.4), (0, 0, s * 8)),
                             ((s * 1.0, N - 1.6, z - 0.1), (0.6, 0.6, 0.4))], res=0.025)


# ====================================================================== characters

def build_freddy(name="freddy", golden=False):
    c = Char(name)
    std_mats(c)
    if golden:
        c.mat("fur", mat_fur, (196, 150, 46), 0.75)
        c.mat("fur2", mat_fur, (214, 182, 92), 0.7)
        c.mat("hat", mat_plastic, (24, 32, 66), 0.4, 0.3, 0.3)
        c.mat("pin", mat_glow, (255, 255, 255), 12)
    else:
        c.mat("fur", mat_fur, (98, 56, 30), 0.35)
        c.mat("fur2", mat_fur, (170, 116, 70), 0.3)
        c.mat("hat", mat_plastic, (16, 16, 18), 0.35, 0.4, 0.05)
        c.mat("iris", mat_glow, (50, 120, 230), 1.5)
    c.mat("band", mat_plastic, (40, 40, 44), 0.5, 0.2, 0.0)
    c.mat("mic", mat_plastic, (40, 40, 44), 0.4, 0.3, 0.05)
    c.mat("grille", mat_metal, (150, 150, 156), 0.3, 0.0)
    torso_suit(c, "fur", belly="fur2")
    bear_head(c, "fur", "fur2", sockets=golden, ear_tilt=6 if golden else 0)
    hat(c, "hat", "band")
    bowtie(c, "hat")
    for side, s in (("left", 1), ("right", -1)):
        ax, top, fore = limb_suit(c, side, s, "fur")
        leg_suit(c, side, s, "fur", "fur", "fur")
        if side == "right" and not golden:
            z = -2.9
            c.cylinder(fore, "mic", (ax, top - 4.0, z), (ax, top - 0.2, z), 0.5, segs=14)
            c.sphere(fore, "grille", (ax, top + 0.6, z), 1.05)
    if golden:
        holes(c, [("body", (3.4, c.a["L"] + 6.5, -c.a["td"] / 2 - 0.5), 1.4),
                  ("right_leg", (-3.2, 9.0, -2.2), 1.0), ("head", (-4.0, c.a["y0"] + 3.0, -3.6), 0.8)])
    return c


def holes(c, spots):
    """Torn suit: dark cavity, a strut and a few wires poking out."""
    for bone, (x, y, z), r in spots:
        c.ellipsoid(bone, "void", (x, y, z), (r, r * 0.9, 0.35))
        c.cylinder(bone, "metal", (x - r * 0.8, y + r * 0.2, z - 0.25), (x + r * 0.8, y - r * 0.1, z - 0.25), 0.18, segs=8)
        c.capsule(bone, "wire_r", (x - r * 0.2, y, z - 0.3), (x - r * 0.4, y - r * 1.4, z - 0.7), 0.1, segs=6, cap=2)
        c.capsule(bone, "wire_b", (x + r * 0.3, y - 0.1, z - 0.3), (x + r * 0.7, y - r * 1.1, z - 0.6), 0.1, segs=6, cap=2)


def build_bonnie():
    c = Char("bonnie")
    std_mats(c)
    c.mat("fur", mat_fur, (78, 80, 176), 0.3)
    c.mat("fur2", mat_fur, (150, 148, 216), 0.25)
    c.mat("iris", mat_glow, (215, 30, 80), 1.5)
    c.mat("nose", mat_plastic, (190, 40, 80), 0.3, 0.5, 0.05)
    c.mat("bow", mat_plastic, (175, 20, 26), 0.4, 0.3, 0.05)
    c.mat("guitar", mat_plastic, (196, 24, 30), 0.18, 1.0, 0.05)
    c.mat("wood", mat_fur, (82, 52, 32), 0.1, 0.0)
    c.mat("strap", mat_simple, (24, 20, 18), 0.8, 0, 0, 0, 0.3)
    torso_suit(c, "fur", belly="fur2")
    rabbit_head(c, "fur", "fur2")
    bowtie(c, "bow")
    for side, s in (("left", 1), ("right", -1)):
        limb_suit(c, side, s, "fur")
        leg_suit(c, side, s, "fur", "fur", "fur")
    a = c.a
    L, N, td = a["L"], a["N"], a["td"]
    g = (0.6, L + 5.5, td / 2 + 1.3)
    rot = (0, 0, 32)
    R = bb_rot(rot)

    def at(dx, dy, dz=0.0):
        v = R @ Vector((dx, dz, dy))
        return (g[0] + v.x, g[1] + v.z, g[2] + v.y)

    c.blob("body", "guitar", [(at(0, -1.4), (3.8, 2.7, 0.75), rot), (at(0, 2.5), (2.9, 1.9, 0.75), rot),
                              (at(-2.3, 4.4), (0.8, 1.2, 0.7), rot)], res=0.03)
    c.rbox("body", "wood", at(0, 9.4, 0.15), (1.3, 10.0, 0.9), bevel=0.2, rot=rot)
    c.rbox("body", "wood", at(0, 15.4, 0.15), (2.2, 2.8, 0.8), bevel=0.3, rot=rot)
    c.rbox("body", "black", at(0, -0.8, 0.85), (3.0, 0.6, 0.3), bevel=0.1, rot=rot)
    c.rbox("body", "black", at(0, 0.6, 0.85), (3.0, 0.6, 0.3), bevel=0.1, rot=rot)
    for i in range(4):
        c.cylinder("body", "chrome", at(-0.45 + i * 0.3, -2.5, 0.7), at(-0.45 + i * 0.3, 14.0, 0.7), 0.05, segs=4, bevel=0)
    for i in range(3):
        for sx in (1, -1):
            c.cylinder("body", "chrome", at(sx * 1.1, 14.4 + i * 0.9), at(sx * 1.7, 14.4 + i * 0.9), 0.2, segs=8)
    for sz, rz in ((-td / 2 - 0.25, -38), (td / 2 + 0.25, 38)):
        c.rbox("body", "strap", (0, N - 5.2, sz), (15.5, 0.9, 0.35), bevel=0.1, rot=(0, 0, rz))
    return c


def build_chica():
    c = Char("chica")
    std_mats(c)
    c.mat("fur", mat_fur, (230, 192, 40), 0.3)
    c.mat("fur2", mat_fur, (242, 216, 100), 0.25)
    c.mat("iris", mat_glow, (180, 50, 200), 1.5)
    c.mat("beak", mat_plastic, (240, 124, 28), 0.3, 0.5, 0.15)
    c.mat("leg_o", mat_fur, (236, 150, 40), 0.3)
    c.mat("bib", mat_simple, (242, 242, 234), 0.7, 0, 0, 0, 0.3)
    c.mat("trim", mat_simple, (130, 60, 200), 0.6, 0, 0, 0, 0.3)
    for i, col in enumerate([(230, 70, 150), (240, 140, 30), (130, 60, 200), (60, 170, 70), (50, 120, 220)]):
        c.mat(f"l{i}", mat_plastic, col, 0.4, 0.2, 0.0)
    c.mat("plate", mat_metal, (220, 220, 226), 0.2, 0.0)
    c.mat("wrapper", mat_stripes, (236, 110, 165), (250, 185, 215), "X", 24, 0.5, 0.0, True)
    c.mat("frosting", mat_plastic, (246, 140, 190), 0.35, 0.4, 0.0)
    c.mat("candle", mat_stripes, (250, 236, 150), (90, 160, 230), "Z", 30, 0.4, 0.0)
    c.mat("flame", mat_glow, (255, 170, 40), 20)
    c.mat("cake_iris", mat_simple, (60, 120, 230), 0.1, 0, 1.0)
    a = c.a
    L, N, td, y0 = a["L"], a["N"], a["td"], a["y0"]
    torso_suit(c, "fur", belly=None)
    c.blob("head", "fur", [((0, y0 + 4.8, 0.2), (5.3, 4.7, 4.8)), ((0, y0 + 2.0, -0.8), (5.7, 2.3, 4.0))], res=0.04)
    c.blob("head", "beak", [((0, y0 + 3.4, -6.0), (3.9, 1.35, 2.6)), ((0, y0 + 2.9, -8.2), (2.3, 0.85, 1.2))], res=0.03)
    for s in (1, -1):
        c.ellipsoid("head", "black", (s * 0.9, y0 + 4.3, -7.9), (0.3, 0.18, 0.3))
    c.ellipsoid("head", "mouth", (0, y0 + 1.6, -5.2), (3.3, 0.9, 2.4))
    teeth_row(c, "head", y0 + 2.1, -7.9, 6.0, 7, h=0.75, up=True, curve=1.5)
    c.blob("jaw", "beak", [((0, y0 + 0.3, -5.6), (3.5, 0.95, 2.6)), ((0, y0 + 0.4, -7.6), (2.2, 0.7, 1.2))], res=0.03)
    teeth_row(c, "jaw", y0 + 1.1, -7.6, 5.6, 7, h=0.7, up=False, curve=1.5)
    for s in (1, -1):
        eye(c, "head", (s * 2.5, y0 + 6.2, -3.95), 1.4, "iris", look=(-s * 0.06, -0.1), lid_mat="fur")
        c.rbox("head", "black", (s * 2.5, y0 + 8.1, -4.5), (3.0, 0.65, 0.8), bevel=0.25, rot=(0, 0, -s * 16))
    for i, (dx, rz) in enumerate(((-1.5, 22), (0, 0), (1.5, -22))):
        R = bb_rot((-12, 0, rz))
        base = Vector((dx, y0 + 9.0, 0.3))
        tip = R @ Vector((0, 4.2, 0))
        c.cone("head", "fur", (base.x, base.y, base.z), (base.x - tip.x, base.y + tip.z, base.z + tip.y), 0.9, segs=10)
    # bib + letters
    top, bot = N - 0.8, L + 3.6
    c.rbox("body", "bib", (0, (top + bot) / 2, -td / 2 - 0.55), (10.6, top - bot, 0.5), bevel=0.2)
    c.rbox("body", "trim", (0, top - 0.15, -td / 2 - 0.62), (10.8, 0.45, 0.55), bevel=0.1)
    c.text("body", ["l0", "l1", "l2", "l3", "l4"], "LET'S", (0, (top + bot) / 2 + 2.1, -td / 2 - 0.85), 3.4, 0.25)
    c.text("body", ["l4", "l3", "l2", "l1", "l0"], "EAT!!", (0, (top + bot) / 2 - 1.7, -td / 2 - 0.85), 3.4, 0.25)
    for side, s in (("left", 1), ("right", -1)):
        ax, top_h, fore = limb_suit(c, side, s, "fur")
        leg_suit(c, side, s, "fur", "leg_o", "leg_o", foot_style="bird")
    # cupcake bone (counter-rotates the raised forearm)
    ax, top_h = c.rig["anchors"]["hands"]["left"][0], c.rig["anchors"]["hands"]["left"][1]
    hx, hyc = ax, top_h - 1.4
    cb = "cupcake"
    c.cylinder(cb, "plate", (hx, hyc + 1.75, 0), (hx, hyc + 2.2, 0), 2.7, bevel=0.15, segs=28)
    c.lathe(cb, "wrapper", (hx, hyc + 2.2, 0), (hx, hyc + 4.2, 0), [(0, 0), (0, 1.25), (2.0, 1.55), (2.0, 0)], segs=24)
    c.lathe(cb, "frosting", (hx, hyc + 4.0, 0), (hx, hyc + 7.0, 0),
            [(0, 1.75), (0.5, 1.8), (0.8, 1.35), (1.1, 1.45), (1.5, 1.0), (1.8, 1.05), (2.3, 0.45), (2.6, 0.0)], segs=24)
    c.cylinder(cb, "candle", (hx, hyc + 6.4, 0), (hx, hyc + 8.0, 0), 0.22, segs=10)
    c.ellipsoid(cb, "flame", (hx, hyc + 8.5, 0), (0.28, 0.5, 0.28), segs=10, rings=8)
    for dx in (-0.65, 0.65):
        c.sphere(cb, "eye_white", (hx + dx, hyc + 4.7, -1.45), 0.5, segs=12, rings=8)
        c.sphere(cb, "pupil", (hx + dx, hyc + 4.65, -1.9), 0.2, segs=8, rings=6)
    teeth_row(c, cb, hyc + 3.7, -1.6, 1.8, 5, h=0.5, up=True, pointed=True, curve=0.2)
    return c


def build_foxy():
    c = Char("foxy")
    std_mats(c, rust=0.35)
    c.mat("fur", mat_fur, (156, 44, 32), 0.6)
    c.mat("fur2", mat_fur, (206, 152, 116), 0.55)
    c.mat("pants", mat_fur, (100, 64, 36), 0.6, 0.4)
    c.mat("iris", mat_glow, (250, 195, 30), 2.5)
    c.mat("patch", mat_plastic, (14, 12, 12), 0.6, 0.0, 0.1)
    c.mat("hook", mat_metal, (200, 200, 206), 0.25, 0.25)
    c.mat("nose", mat_plastic, (24, 18, 18), 0.3, 0.5, 0.2)
    a = c.a
    L, N, td, tw, y0 = a["L"], a["N"], a["td"], a["tw"], a["y0"]
    torso_suit(c, "fur", belly="fur2", pelvis="pants")
    holes(c, [("body", (-1.6, L + 7.6, -td / 2 - 0.9), 2.0)])
    c.blob("head", "fur", [((0, y0 + 4.2, 0.2), (4.8, 4.0, 4.6)), ((0, y0 + 2.0, -0.8), (5.1, 2.1, 3.8)),
                           ((0, y0 + 3.6, -6.4), (2.9, 1.5, 3.4))], res=0.035)
    c.blob("head", "fur2", [((0, y0 + 2.4, -6.3), (2.9, 0.9, 3.3))], res=0.03)
    c.ellipsoid("head", "nose", (0, y0 + 4.4, -9.6), (1.15, 0.75, 0.8))
    c.ellipsoid("head", "mouth", (0, y0 + 1.2, -6.4), (2.4, 0.8, 3.0))
    teeth_row(c, "head", y0 + 1.6, -9.1, 4.6, 7, h=1.1, up=True, pointed=True, curve=0.6)
    c.blob("jaw", "fur2", [((0, y0 - 0.1, -6.2), (2.6, 0.75, 3.3))], res=0.03)
    teeth_row(c, "jaw", y0 + 0.5, -8.9, 4.2, 6, h=0.9, up=False, pointed=True, curve=0.6)
    c.cylinder("jaw", "metal", (-2.8, y0 + 0.4, -3.4), (2.8, y0 + 0.4, -3.4), 0.45, segs=12)
    eye(c, "head", (2.2, y0 + 5.4, -3.7), 1.25, "iris", look=(-0.1, -0.1), lid_mat="fur")
    c.ellipsoid("head", "patch", (-2.2, y0 + 5.4, -4.3), (1.6, 1.4, 0.5))
    c.lathe("head", "patch", (0, y0 + 5.9, 0.1), (0, y0 + 6.4, 0.1), [(0, 4.85), (0.5, 4.85)], segs=28, smooth=True)
    for s in (1, -1):
        c.rbox("head", "black", (s * 2.2, y0 + 7.0, -4.3), (2.6, 0.55, 0.7), bevel=0.2, rot=(0, 0, -s * 18))
        R = bb_rot((0, 0, -s * 14))
        base = (s * 3.1, y0 + 7.8, 0.4)
        tip = R @ Vector((0, 0, 4.8 * S))
        c.cone("head", "fur", base, (base[0] - tip.x / S * 0 + s * 0.8, base[1] + 4.6, base[2]), 1.5, segs=12)
        c.cone("head", "fur2", (base[0], base[1] + 0.3, base[2] - 0.7), (base[0] + s * 0.6, base[1] + 3.6, base[2] - 0.75), 0.9, segs=10)
    for side, s in (("left", 1), ("right", -1)):
        if side == "right":
            ax, top, fore = limb_suit(c, side, s, "fur", hand_style="none")
            c.cylinder(fore, "metal", (ax, top + 0.3, 0), (ax, top - 1.2, 0), 1.5, segs=20)
            c.cylinder(fore, "hook", (ax, top - 1.2, 0), (ax, top - 4.4, 0), 0.38, segs=12)
            pts = [(ax, top - 4.4, 0)] + [(ax, top - 4.4 - math.sin(t) * 1.6, -1.6 + math.cos(t) * 1.6)
                                          for t in [i * math.pi / 8 for i in range(1, 10)]]
            for p0, p1 in zip(pts, pts[1:]):
                c.capsule(fore, "hook", p0, p1, 0.36, 0.33 if p1 != pts[-1] else 0.18, segs=10, cap=2)
        else:
            limb_suit(c, side, s, "fur", hand_style="endo", endo_fore=False)
        leg_suit(c, side, s, "pants", "fur", "fur", endo_shin=True, metal_toes=True)
        x = s * c.p["hip_x"]
        c.lathe(f"{side}_leg", "pants", (x, L * 0.62, 0), (x, L * 0.5, 0),
                [(0, 2.6), (0.4, 2.75), (0.9, 2.55), (1.2, 2.7), (1.5, 0)], segs=14)
    return c


def build_springtrap():
    c = Char("springtrap")
    std_mats(c, metal=(104, 98, 88), rust=0.55)
    c.mat("fur", mat_fur, (112, 116, 58), 0.9)
    c.mat("fur2", mat_fur, (142, 138, 84), 0.85)
    c.mat("nose", mat_plastic, (90, 70, 50), 0.6, 0.0, 0.5)
    c.mat("pin", mat_glow, (235, 235, 210), 10)
    a = c.a
    L, N, td, tw, y0 = a["L"], a["N"], a["td"], a["tw"], a["y0"]
    torso_suit(c, "fur", belly="fur2")
    rabbit_head(c, "fur", "fur2", sockets=True, pin=(235, 235, 210), broken_ear=True)
    teeth_row(c, "head", y0 + 1.2, -6.2, 4.6, 6, h=0.6, up=True, mat="metal", curve=0.8)
    holes(c, [("body", (-0.8, L + 7.4, -td / 2 - 1.0), 2.6), ("body", (tw / 2 + 0.2, L + 5.0, 0), 1.3),
              ("head", (3.4, y0 + 2.4, -3.9), 0.8), ("left_leg", (3.1, 8.0, -2.3), 1.1),
              ("right_arm", (c.rig["anchors"]["hands"]["right"][0], N - 5.0, -1.9), 0.9)])
    for i in range(3):
        c.rbox("body", "metal", (-0.8, L + 6.4 + i * 1.1, -td / 2 - 0.9), (4.2, 0.35, 0.4), bevel=0.1)
    for side, s in (("left", 1), ("right", -1)):
        limb_suit(c, side, s, "fur", hand_style="endo" if side == "left" else "paw")
        leg_suit(c, side, s, "fur", "fur", "fur")
    return c


def build_balloon_boy():
    c = Char("balloon_boy")
    std_mats(c)
    c.mat("skin", mat_plastic, (240, 206, 174), 0.28, 0.6, 0.02)
    c.mat("hair", mat_fur, (96, 58, 32), 0.1, 0.3)
    c.mat("shirt", mat_stripes, (206, 40, 40), (40, 70, 190), "Z", 8, 0.6, 0.2)
    c.mat("pants", mat_fur, (44, 70, 182), 0.05, 0.3)
    c.mat("shoe", mat_plastic, (92, 56, 30), 0.35, 0.4, 0.05)
    c.mat("hat", mat_stripes, (210, 40, 40), (40, 80, 200), "X", 8, 0.45, 0.1, True)
    c.mat("prop", mat_plastic, (245, 210, 40), 0.3, 0.4, 0.0)
    c.mat("balloon", mat_stripes, (230, 40, 40), (245, 215, 40), "X", 8, 0.15, 0.0, True, 0.0)
    c.mat("string", mat_simple, (40, 40, 40), 0.8)
    c.mat("button", mat_plastic, (245, 245, 245), 0.3, 0.4, 0.0)
    c.mat("cheek", mat_plastic, (240, 140, 140), 0.3, 0.3, 0.0)
    c.mat("iris", mat_glow, (50, 110, 230), 0.8)
    c.mat("sign", mat_simple, (242, 242, 232), 0.6)
    c.mat("stick", mat_fur, (120, 80, 40), 0.05, 0.0)
    c.mat("t_r", mat_plastic, (220, 40, 40), 0.4, 0.2, 0.0)
    c.mat("t_b", mat_plastic, (40, 80, 200), 0.4, 0.2, 0.0)
    c.mat("t_y", mat_plastic, (230, 170, 20), 0.4, 0.2, 0.0)
    a = c.a
    L, N, td, tw = a["L"], a["N"], a["td"], a["tw"]
    y0 = a["y0"] - 0.6
    c.blob("body", "shirt", [((0, (L + N) / 2 + 0.6, 0), (tw / 2 + 0.2, (N - L) / 2, td / 2 + 0.3))], res=0.04)
    c.blob("body", "pants", [((0, L + 0.3, 0), (tw / 2 - 0.3, 2.0, td / 2 - 0.2))], res=0.04)
    for i in range(2):
        c.sphere("body", "button", (0, N - 2.2 - i * 2.4, -td / 2 - 0.45), 0.5, segs=12, rings=8)
    c.cylinder("head", "skin", (0, N - 0.5, 0), (0, N + 1.5, 0), 1.5, segs=14)
    c.blob("head", "skin", [((0, y0 + 5.1, 0), (5.5, 5.0, 5.0))], res=0.04)
    c.blob("head", "hair", [((0, y0 + 7.4, 1.4), (5.6, 2.6, 4.0))], res=0.04)
    for s in (1, -1):
        eye(c, "head", (s * 2.4, y0 + 5.6, -3.9), 1.55, "iris", look=(0, -0.05))
        c.ellipsoid("head", "cheek", (s * 3.7, y0 + 3.4, -4.15), (1.0, 0.6, 0.35))
        c.rbox("head", "hair", (s * 2.4, y0 + 7.7, -4.3), (2.4, 0.45, 0.5), bevel=0.15, rot=(0, 0, s * 8))
    c.sphere("head", "skin", (0, y0 + 4.3, -5.0), 0.6, segs=12, rings=8)
    c.ellipsoid("head", "mouth", (0, y0 + 2.2, -4.55), (2.6, 1.15, 0.6))
    teeth_row(c, "head", y0 + 3.0, -4.95, 4.2, 6, h=0.55, up=True, curve=0.4)
    c.ellipsoid("jaw", "skin", (0, y0 + 0.9, -3.4), (3.4, 1.0, 2.2))
    c.blob("head", "hat", [((0, y0 + 8.8, 0), (5.9, 3.0, 5.6))], res=0.04)
    c.cylinder("head", "hat", (0, y0 + 8.0, -4.6), (0, y0 + 8.5, -6.4), 3.2, bevel=0.15, segs=24)
    c.sphere("head", "prop", (0, y0 + 11.9, 0), 0.8, segs=12, rings=8)
    c.cylinder("head", "prop", (0, y0 + 12.0, 0), (0, y0 + 13.8, 0), 0.25, segs=8)
    for ang in (30, 210):
        R = bb_rot((0, ang, 8))
        tip = R @ Vector((4.0 * S, 0, 0))
        c.ellipsoid("head", "prop", (tip.x / S * 0.5, y0 + 13.8, tip.y / S * 0.5), (2.1, 0.12, 0.6), rot=(0, ang, 8))
    for side, s in (("left", 1), ("right", -1)):
        ax, top, fore = limb_suit(c, side, s, "shirt", hand_mat="skin")
        leg_suit(c, side, s, "pants", "pants", "shoe", foot_style="shoe")
    ax, top = a["hands"]["right"][0], a["hands"]["right"][1]
    fore = "right_forearm"
    c.cylinder(fore, "string", (ax, top - 1.4, -1.6), (ax - 3.5, top + 16.4, -1.6), 0.08, segs=6, bevel=0)
    c.ellipsoid(fore, "balloon", (ax - 3.5, top + 20.0, -1.6), (3.0, 3.5, 3.0))
    c.cone(fore, "balloon", (ax - 3.5, top + 16.2, -1.6), (ax - 3.5, top + 16.9, -1.6), 0.6, segs=10)
    ax, top = a["hands"]["left"][0], a["hands"]["left"][1]
    fore = "left_forearm"
    c.cylinder(fore, "stick", (ax, top - 3.0, -2.4), (ax, top + 5.0, -2.4), 0.25, segs=8)
    c.rbox(fore, "sign", (ax, top + 6.6, -2.8), (7.6, 3.8, 0.4), bevel=0.15)
    c.text(fore, ["t_r", "t_b", "t_y"], "BALLOONS!", (ax, top + 6.6, -3.1), 1.45, 0.2)
    return c


def build_puppet():
    c = Char("puppet")
    std_mats(c)
    c.mat("body", mat_fur, (20, 20, 24), 0.05, 0.4)
    c.mat("stripe", mat_stripes, (234, 234, 234), (20, 20, 24), "Z", 13, 0.5, 0.2)
    c.mat("mask", mat_plastic, (244, 244, 240), 0.22, 0.8, 0.05)
    c.mat("cheek", mat_plastic, (205, 36, 50), 0.3, 0.6, 0.0)
    c.mat("tear", mat_plastic, (125, 55, 160), 0.3, 0.6, 0.0)
    c.mat("lips", mat_plastic, (200, 30, 40), 0.25, 0.6, 0.0)
    c.mat("pin", mat_glow, (255, 255, 255), 10)
    c.mat("button", mat_plastic, (240, 240, 240), 0.3, 0.6, 0.0)
    a = c.a
    L, N, td, tw, y0 = a["L"], a["N"], a["td"], a["tw"], a["y0"]
    c.blob("body", "body", [((0, (L + N) / 2 + 0.5, 0), (tw / 2, (N - L) / 2 + 0.2, td / 2)),
                            ((0, N - 1.2, 0), (tw / 2 + 0.8, 1.6, td / 2 - 0.4))], res=0.035)
    c.blob("body", "body", [((0, L + 0.5, 0), (tw / 2 - 0.6, 2.2, td / 2 - 0.4))], res=0.035)
    for i in range(3):
        c.sphere("body", "button", (0, N - 3.2 - i * 2.8, -td / 2 - 0.15), 0.6, segs=12, rings=8)
    c.cylinder("head", "body", (0, N - 0.5, 0), (0, y0 + 0.5, 0), 0.9, segs=12)
    c.blob("head", "body", [((0, y0 + 4.4, 0.3), (3.5, 4.4, 3.3))], res=0.03)
    c.blob("head", "mask", [((0, y0 + 4.3, -2.6), (3.3, 4.2, 1.2))], res=0.025)
    for s in (1, -1):
        ex = s * 1.25
        c.ellipsoid("head", "void", (ex, y0 + 5.1, -3.75), (0.85, 0.65, 0.25))
        c.sphere("head", "pin", (ex, y0 + 5.1, -3.95), 0.16, segs=8, rings=6)
        c.capsule("head", "tear", (ex, y0 + 4.3, -3.82), (ex, y0 + 1.6, -3.55), 0.13, 0.08, segs=8, cap=2)
        c.ellipsoid("head", "cheek", (s * 2.3, y0 + 2.9, -3.45), (0.7, 0.7, 0.25))
        c.rbox("head", "black", (ex, y0 + 6.3, -3.8), (1.5, 0.22, 0.2), bevel=0.05, rot=(0, 0, -s * 10))
    c.ellipsoid("head", "lips", (0, y0 + 1.2, -3.7), (1.3, 0.45, 0.3))
    c.ellipsoid("jaw", "mask", (0, y0 + 0.2, -3.0), (1.6, 0.6, 0.9))
    for side, s in (("left", 1), ("right", -1)):
        ax, top, fore = limb_suit(c, side, s, "body", hand_style="puppet")
        c.cylinder(fore, "stripe", (ax, top + 0.2, 0), (ax, top + 3.8, 0), 1.15, segs=16)
        leg_suit(c, side, s, "body", "body", "body", sole="black")
        c.cylinder(f"{side}_leg", "stripe", (s * c.p["hip_x"], 2.0, 0), (s * c.p["hip_x"], 5.6, 0), 1.35, segs=16)
    return c


def build_endoskeleton():
    c = Char("endoskeleton")
    std_mats(c, metal=(128, 128, 134), rust=0.25)
    c.mat("iris", mat_glow, (235, 30, 30), 3)
    a = c.a
    L, N, td, tw, y0 = a["L"], a["N"], a["td"], a["tw"], a["y0"]
    p = c.p
    # pelvis + spine + ribs
    c.rbox("body", "metal_dark", (0, L, 0), (tw - 1.6, 3.0, td - 0.8), bevel=0.6)
    c.cylinder("body", "metal", (-p["hip_x"] - 1, L, 0), (p["hip_x"] + 1, L, 0), 0.55, segs=12)
    for i in range(7):
        y = L + 1.8 + i * (N - L - 2.5) / 7
        c.sphere("body", "metal_dark", (0, y, td / 2 - 0.9), 0.75, segs=12, rings=8)
    c.cylinder("body", "metal", (0, L + 1, td / 2 - 0.9), (0, N, td / 2 - 0.9), 0.4, segs=10)
    for i in range(5):
        y = L + 3.2 + i * (N - L - 5) / 4.5
        w = tw / 2 - 0.3 - i * 0.15
        c.lathe("body", "metal", (0, y, 0), (0, y + 0.6, 0), [(0, w), (0.6, w)], segs=24, smooth=True)
        bm_obj = c.parts[-1]
        bm_obj.scale = (1.0, (td / 2) / w, 1.0)
    c.rbox("body", "metal_dark", (0, N - 1.0, 0), (tw + 0.8, 1.8, td - 1.2), bevel=0.5)
    c.rbox("body", "metal_dark", (0, L + 3.0, -0.3), (3.2, 2.4, 2.6), bevel=0.4)
    c.capsule("body", "wire_r", (1.6, L + 9, -td / 2 - 0.2), (2.4, L + 3, -td / 2 - 0.4), 0.18, segs=6, cap=2)
    c.capsule("body", "wire_b", (-1.4, L + 8.5, -td / 2 - 0.2), (-2.2, L + 3.5, -td / 2 - 0.4), 0.18, segs=6, cap=2)
    c.cylinder("head", "metal", (0, N - 0.5, 0), (0, y0 + 1.0, 0), 0.7, segs=12)
    # skull
    c.blob("head", "metal", [((0, y0 + 5.2, 0.3), (4.3, 3.0, 3.9)), ((0, y0 + 7.8, 0.6), (3.6, 1.4, 3.2))], res=0.035)
    c.rbox("head", "metal_dark", (0, y0 + 5.6, -3.7), (7.6, 4.0, 0.9), bevel=0.4)
    for s in (1, -1):
        eye(c, "head", (s * 2.0, y0 + 5.6, -4.1), 1.15, "iris", look=(0, 0))
        c.rbox("head", "metal", (s * 2.0, y0 + 6.95, -4.4), (2.6, 0.5, 1.8), bevel=0.2, rot=(-10, 0, 0))
        c.cylinder("head", "metal_dark", (s * 3.3, y0 + 8.0, 0.4), (s * 3.3, y0 + 10.6, 0.4), 0.4, segs=10)
        c.cylinder("head", "metal", (s * 3.3, y0 + 11.0, 0.1), (s * 3.3, y0 + 11.0, 0.7), 1.1, segs=18)
    teeth_row(c, "head", y0 + 3.1, -5.2, 6.0, 7, h=1.0, up=True, curve=0.5)
    c.rbox("head", "mouth", (0, y0 + 1.8, -3.9), (5.8, 1.6, 2.4), bevel=0.3)
    c.rbox("jaw", "metal", (0, y0 + 0.5, -3.0), (7.0, 1.2, 5.2), bevel=0.4)
    teeth_row(c, "jaw", y0 + 1.1, -5.2, 5.8, 7, h=0.9, up=False, curve=0.5)
    for s in (1, -1):
        c.cylinder("jaw", "chrome", (s * 3.4, y0 + 1.3, -1.6), (s * 3.4, y0 + 4.0, -2.4), 0.22, segs=8)
    # limbs
    for side, s in (("left", 1), ("right", -1)):
        ax = s * (tw / 2 + p["arm_w"] / 2 + 0.1)
        sy = N - 1.6
        ey = sy - p["upper_arm"] - 0.5
        hy = sy - p["upper_arm"] - 1 - p["forearm"]
        c.sphere(f"{side}_arm", "metal", (ax, sy, 0), 1.3)
        piston(c, f"{side}_arm", ax, ey, sy)
        joint(c, f"{side}_arm", (ax, ey, 0), 1.0)
        piston(c, f"{side}_forearm", ax, hy, ey - 0.6)
        joint(c, f"{side}_forearm", (ax, hy - 0.1, 0), 0.7)
        hand(c, f"{side}_forearm", ax, hy - 0.5, s, p["arm_w"], "endo", "metal")
        x = s * p["hip_x"]
        k0, k1 = L * 0.45, L * 0.56
        c.sphere(f"{side}_leg", "metal", (x, L, 0), 1.3)
        piston(c, f"{side}_leg", x, k1, L)
        joint(c, f"{side}_leg", (x, (k0 + k1) / 2, 0), 1.1)
        piston(c, f"{side}_leg", x, 2.4, k0)
        joint(c, f"{side}_leg", (x, 2.4, 0), 0.8)
    for side, s in (("left", 1), ("right", -1)):
        leg_suit_feet_only(c, side, s)
    return c


def leg_suit_feet_only(c, side, s):
    p = c.p
    lw = p["leg_w"]
    ld = p.get("leg_d", lw)
    x = s * p["hip_x"]
    f = p.get("foot", 2.4)
    leg = f"{side}_leg"
    c.rbox(leg, "metal_dark", (x, 0.8, -f * 0.4), (lw + 0.8, 1.2, ld + f), bevel=0.3)
    for i in (-1, 0, 1):
        tx = x + i * 1.1
        c.capsule(leg, "metal", (tx, 0.7, -ld / 2 - f * 0.5), (tx, 0.5, -ld / 2 - f - 1.0), 0.35, 0.3, segs=10)
    c.sphere(leg, "metal", (x, 0.9, ld / 2 + 0.5), 0.8, segs=12, rings=8)


BUILDERS = {
    "freddy": lambda: build_freddy("freddy"),
    "golden_freddy": lambda: build_freddy("golden_freddy", golden=True),
    "bonnie": build_bonnie,
    "chica": build_chica,
    "foxy": build_foxy,
    "springtrap": build_springtrap,
    "balloon_boy": build_balloon_boy,
    "puppet": build_puppet,
    "endoskeleton": build_endoskeleton,
}


# ====================================================================== scene / bake / export

def clear_char(name):
    coll = bpy.data.collections.get(name)
    if coll:
        for o in list(coll.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(coll)
    for m in [m for m in bpy.data.materials if m.name.startswith(name + "_")]:
        bpy.data.materials.remove(m)
    for me in [me for me in bpy.data.meshes if me.users == 0]:
        bpy.data.meshes.remove(me)
    for img in [i for i in bpy.data.images if i.name.startswith(name + "_bake")]:
        bpy.data.images.remove(img)


def apply_rest_pose(c):
    for b in c.rig["bones"]:
        if any(b["rot"]):
            e = c.empties[b["name"]]
            e.rotation_mode = "QUATERNION"
            e.rotation_quaternion = bb_rot(b["rot"]).to_quaternion()


def bake_and_export(c, tex=1024, max_tris=26000, samples=16):
    """Join a copy of all parts, unwrap, bake colour*AO + emission, export mesh + textures."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    bones = [b["name"] for b in c.rig["bones"]]
    dg = bpy.context.evaluated_depsgraph_get()
    copies = []
    for obj in c.parts:
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
        me.transform(obj.matrix_world)
        attr = me.attributes.new("bone_id", "INT", "FACE")
        bid = bones.index(obj["bone"])
        attr.data.foreach_set("value", [bid] * len(me.polygons))
        o = bpy.data.objects.new(obj.name + "_bk", me)
        c.coll.objects.link(o)
        copies.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in copies:
        o.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = f"{c.name}_bake"
    me = joined.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    if tris > max_tris:
        mod = joined.modifiers.new("dec", "DECIMATE")
        mod.ratio = max_tris / tris
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")

    imgs = {k: bpy.data.images.new(f"{c.name}_bake_{k}", tex, tex, alpha=True) for k in ("col", "ao", "emit")}
    for mat in me.materials:
        nt = mat.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.name = "BAKE_TARGET"
        nt.nodes.active = node
    def target(k):
        for mat in me.materials:
            mat.node_tree.nodes["BAKE_TARGET"].image = imgs[k]
    scene.cycles.samples = samples
    if scene.world:
        scene.world.light_settings.distance = 0.25
    scene.render.bake.margin = 6
    target("col")
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=6, use_clear=True)
    target("ao")
    bpy.ops.object.bake(type="AO", margin=6, use_clear=True)
    target("emit")
    bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)

    import numpy as np
    def arr(img):
        a = np.empty(tex * tex * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(tex, tex, 4)
    col, ao, emit = arr(imgs["col"]), arr(imgs["ao"]), arr(imgs["emit"])
    shade = 1.12 * (0.62 + 0.38 * ao[..., :1])
    out = col.copy()
    out[..., :3] = np.clip(col[..., :3] * shade, 0, 1)
    out[..., 3] = 1.0
    glow = emit.copy()
    lum = emit[..., :3].max(axis=2)
    glow[..., :3] = np.clip(emit[..., :3] / np.maximum(lum[..., None], 1e-4), 0, 1) * (lum[..., None] > 0.02)
    glow[..., 3] = (lum > 0.02).astype(np.float32)
    tex_dir = os.path.join(ASSETS, "textures", "entity")
    os.makedirs(tex_dir, exist_ok=True)
    for key, data, fname in (("col", out, f"{c.name}_hd.png"), ("emit", glow, f"{c.name}_hd_glowmask.png")):
        img = bpy.data.images.new(f"{c.name}_bake_out_{key}", tex, tex, alpha=True)
        img.pixels.foreach_set(data.ravel())
        img.filepath_raw = os.path.join(tex_dir, fname)
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)

    export_mesh(c, joined, bones)
    stats = dict(tris=sum(len(p.vertices) - 2 for p in me.polygons), parts=len(c.parts))
    bpy.data.objects.remove(joined, do_unlink=True)
    for img in imgs.values():
        bpy.data.images.remove(img)
    for mat in [m for m in bpy.data.materials if m.name.startswith(c.name + "_")]:
        n = mat.node_tree.nodes.get("BAKE_TARGET")
        if n:
            mat.node_tree.nodes.remove(n)
    return stats


def export_mesh(c, joined, bones):
    """Binary .fmesh: per bone an indexed triangle list in GeckoLib model space (blocks, X mirrored)."""
    me = joined.data
    me.calc_loop_triangles()
    bone_attr = me.attributes["bone_id"].data
    uv = me.uv_layers.active.data
    normals = me.corner_normals
    verts = me.vertices
    per_bone = {}
    for lt in me.loop_triangles:
        bid = bone_attr[lt.polygon_index].value
        per_bone.setdefault(bid, []).append(lt.loops)
    out = bytearray()
    out += b"FMSH" + struct.pack(">ii", 1, len(per_bone))
    for bid, tris in sorted(per_bone.items()):
        remap, vdata, idx = {}, [], []
        for loops in tris:
            for li in reversed(loops):
                vi = me.loops[li].vertex_index
                n = normals[li].vector
                u = uv[li].uv
                key = (vi, round(u.x, 5), round(u.y, 5), round(n.x, 3), round(n.y, 3), round(n.z, 3))
                if key not in remap:
                    remap[key] = len(remap)
                    v = verts[vi].co
                    vdata.append((-v.x, v.z, v.y, -n.x, n.z, n.y, u.x, 1.0 - u.y))
                idx.append(remap[key])
        name = bones[bid].encode("utf-8")
        out += struct.pack(">h", len(name)) + name
        out += struct.pack(">i", len(vdata))
        for t in vdata:
            out += struct.pack(">8f", *t)
        out += struct.pack(">i", len(idx))
        out += struct.pack(f">{len(idx)}i", *idx)
    mdir = os.path.join(ASSETS, "meshes")
    os.makedirs(mdir, exist_ok=True)
    with open(os.path.join(mdir, f"{c.name}.fmesh"), "wb") as f:
        f.write(bytes(out))


def setup_stage():
    """Pizzeria-ish stage: checker floor, dark wall, warm key + cold rim lights."""
    for o in [o for o in bpy.data.objects if o.name in ("Cube", "Light")]:
        bpy.data.objects.remove(o, do_unlink=True)
    if "stage" in bpy.data.collections:
        return
    coll = bpy.data.collections.new("stage")
    bpy.context.scene.collection.children.link(coll)
    m, nt, bsdf = _nodes("stage_floor")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    chk = nt.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Scale"].default_value = 40.0
    chk.inputs["Color1"].default_value = lin((225, 225, 220))
    chk.inputs["Color2"].default_value = lin((18, 18, 20))
    nt.links.new(tc.outputs["UV"], chk.inputs["Vector"])
    base = _dirt(nt, chk.outputs["Color"], 0.35)
    nt.links.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.data.materials.append(m)
    wall_m = mat_plastic("stage_wall", (52, 44, 60), 0.85, 0.0, 0.6)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 4.5, 6), rotation=(math.pi / 2, 0, 0))
    wall = bpy.context.active_object
    wall.data.materials.append(wall_m)
    for o in (floor, wall):
        for cl in o.users_collection:
            cl.objects.unlink(o)
        coll.objects.link(o)

    def light(name, kind, loc, energy, color, size=1.0, rot=None):
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.color = color
        if kind == "AREA":
            ld.size = size
        if kind == "SPOT":
            ld.spot_size = math.radians(55)
            ld.spot_blend = 0.5
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        coll.objects.link(lo)
        tgt = Vector((loc[0] * 0.2, 0, 1.2))
        lo.rotation_euler = (tgt - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return lo

    light("key", "AREA", (-4, -6, 6), 1800, (1.0, 0.85, 0.7), 3)
    light("rim", "AREA", (5, 3, 4), 900, (0.55, 0.65, 1.0), 2)
    light("top", "SPOT", (0, -2, 8), 2500, (1.0, 0.95, 0.85))
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.01, 0.01, 0.015, 1)
    bg.inputs["Strength"].default_value = 0.3


def build(names=None, bake=True):
    setup_stage()
    names = names or list(BUILDERS)
    stats = {}
    for i, nm in enumerate(names):
        clear_char(nm)
        c = BUILDERS[nm]()
        bpy.context.view_layer.update()
        if bake:
            stats[nm] = bake_and_export(c)
        apply_rest_pose(c)
        stats.setdefault(nm, {})["parts"] = len(c.parts)
    return stats


def lineup(names=None, spacing=1.15):
    names = names or list(BUILDERS)
    n = len(names)
    for i, nm in enumerate(names):
        root = bpy.data.objects.get(f"{nm}:root")
        if root:
            root.location = ((i - (n - 1) / 2) * spacing, 0, 0)
