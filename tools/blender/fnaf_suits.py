"""FNAF1-accurate suits on top of fnaf_blender (geometry engine, bake and export).

Replaces the anatomy and fur of fnaf_blender with versions modelled after the classic
FNAF1 look: segmented suit pieces with dark endoskeleton gaps, big mitten hands, three-toed
paws, fibrous fur with dirty creases, and per-character heads. Also adds render poses and a
group shot that mirrors the classic promo composition.
"""
import math
import os

import bpy
from mathutils import Vector

import fnaf_blender as fb
from fnaf_blender import (S, V, bb_rot, lin, _nodes, _noise, _ramp, _math, _mix, _mul, _dirt,
                          mat_plastic, mat_metal, mat_glow, mat_simple, mat_stripes, Char)


# ====================================================================== fur

def mat_fur(name, color, dirt=0.45, sheen=0.5):
    """Short synthetic fur: vertical strand streaks, clumps, darker roots, dirty creases."""
    m, nt, bsdf = _nodes(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (42.0, 42.0, 11.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    strand = nt.nodes.new("ShaderNodeTexNoise")
    strand.inputs["Detail"].default_value = 12.0
    strand.inputs["Roughness"].default_value = 0.72
    nt.links.new(mp.outputs["Vector"], strand.inputs["Vector"])
    clump = _noise(nt, 9.0, 5, 0.55)
    tone = _math(nt, "ADD", _math(nt, "MULTIPLY", strand.outputs["Fac"], 0.75), _math(nt, "MULTIPLY", clump.outputs["Fac"], 0.25))
    base = _ramp(nt, tone, [(0.32, lin(_mul(color, 0.55))), (0.5, lin(color)), (0.68, lin(_mul(color, 1.22)))]).outputs["Color"]
    base = _dirt(nt, base, dirt, dirt_col=_mul(color, 0.28))
    nt.links.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.93
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    bsdf.inputs["Sheen Weight"].default_value = sheen
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    bsdf.inputs["Sheen Tint"].default_value = lin(_mul(color, 1.4))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.01
    nt.links.new(tone, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# ====================================================================== primitives

def drum(c, bone, mat, a, b, r0, r1=None, round_=0.45, segs=22):
    """Suit segment: a fat cylinder with soft rounded ends (FNAF limb pieces)."""
    r1 = r0 if r1 is None else r1
    L = (Vector(b) - Vector(a)).length
    k0, k1 = r0 * round_, r1 * round_
    prof = [(0, 0), (0, r0 * 0.62), (k0 * 0.3, r0 * 0.88), (k0, r0), (L - k1, r1), (L - k1 * 0.3, r1 * 0.88),
            (L, r1 * 0.62), (L, 0)]
    return c.lathe(bone, mat, a, b, prof, segs)


def band(c, bone, a, b, r, mat="endo"):
    return c.cylinder(bone, mat, a, b, r, bevel=0.1, segs=18)


def std_mats(c, metal=(120, 120, 126), rust=0.15):
    fb_std(c, metal, rust)
    c.mat("endo", mat_metal, (34, 34, 38), 0.55, 0.05)


fb_std = fb.__dict__.setdefault("_orig_std_mats", fb.std_mats)


# ====================================================================== body

def torso_suit(c, fur, belly=None, pelvis=None, chest_scale=1.0):
    a = c.a
    L, N, tw, td = a["L"], a["N"], a["tw"], a["td"]
    k = chest_scale
    c.blob("body", fur, [((0, L + 8.3, 0), (tw / 2 * k + 0.4, 4.9, td / 2 + 0.6)),
                         ((0, L + 4.6, -0.3), (tw / 2 * k - 0.2, 3.6, td / 2 + 0.5)),
                         ((0, N - 1.2, 0.2), (tw / 2 * k + 0.6, 1.9, td / 2 - 0.4))], res=0.045)
    band(c, "body", (0, L + 0.9, 0), (0, L + 2.3, 0), tw / 2 - 1.4)
    c.blob("body", pelvis or fur, [((0, L + 0.2, 0), (tw / 2 - 0.5, 2.1, td / 2 - 0.2)),
                                   ((0, L - 0.8, -0.4), (tw / 2 - 1.4, 1.6, td / 2 - 0.6))], res=0.045)
    if belly:
        c.ellipsoid("body", belly, (0, L + 6.3, -td / 2 - 0.15), ((tw / 2) * k - 1.5, 5.6, 1.6))
    band(c, "head", (0, N - 1.0, 0), (0, N + 2.4, 0), 1.3)


def limb_suit(c, side, s, fur, fur2=None, hand_style="paw", hand_mat=None, endo_fore=False):
    a, p = c.a, c.p
    tw, N = a["tw"], a["N"]
    aw, ua, fa = p["arm_w"], p["upper_arm"], p["forearm"]
    ax = s * (tw / 2 + aw / 2 + 0.1)
    sy = N - 1.6
    ey = sy - ua - 0.5
    hy = sy - ua - 1 - fa
    arm, fore = f"{side}_arm", f"{side}_forearm"
    r = aw / 2
    c.blob(arm, fur, [((ax - s * 0.2, sy + 0.5, 0), (r * 1.45, r * 1.35, r * 1.5))], res=0.04)
    drum(c, arm, fur, (ax, sy - 0.6, 0), (ax, sy - ua + 0.2, 0), r * 1.12, r * 1.02)
    band(c, arm, (ax, ey - 0.5, 0), (ax, ey + 0.5, 0), r * 0.7)
    if endo_fore:
        fb.piston(c, fore, ax, hy, ey - 0.6)
    else:
        drum(c, fore, fur, (ax, ey - 0.55, 0), (ax, hy + 0.35, 0), r * 1.1, r * 0.95)
    band(c, fore, (ax, hy - 0.45, 0), (ax, hy + 0.5, 0), r * 0.68)
    hand(c, fore, ax, hy - 0.5, s, aw, hand_style, hand_mat or fur)
    return ax, hy - 0.5, fore


def hand(c, bone, ax, top, s, aw, style, mat):
    if style == "none":
        return
    if style in ("endo", "puppet"):
        return fb_hand(c, bone, ax, top, s, aw, style, mat)
    zw = aw + 1.1
    c.blob(bone, mat, [((ax, top - 1.5, 0), (aw * 0.5, 1.8, zw * 0.5)),
                       ((ax - s * 0.2, top - 2.6, 0.1), (aw * 0.45, 1.0, zw * 0.46))], res=0.035)
    fr = zw / 8 * 1.08
    for i in range(4):
        fz = (-zw / 2 + zw * (i + 0.5) / 4) * 0.94
        ln = 1.45 if i in (1, 2) else 1.25
        k0 = (ax, top - 3.0, fz)
        k1 = (ax - s * 0.3, top - 3.0 - ln, fz)
        k2 = (ax - s * 1.0, top - 3.0 - ln * 1.8, fz - 0.05)
        c.capsule(bone, mat, k0, k1, fr, fr * 0.96, segs=12, cap=3)
        c.capsule(bone, mat, k1, k2, fr * 0.96, fr * 0.86, segs=12, cap=3)
    c.capsule(bone, mat, (ax - s * 0.15, top - 1.2, -zw / 2 + 0.4), (ax - s * 0.7, top - 3.0, -zw / 2 - 0.8),
              fr * 1.15, fr * 0.95, segs=12, cap=3)


fb_hand = fb.__dict__.setdefault("_orig_hand", fb.hand)


def leg_suit(c, side, s, thigh, shin, foot_mat, foot_style="paw", endo_shin=False, sole="black", metal_toes=False,
             claw="claw"):
    p, L = c.p, c.a["L"]
    lw = p["leg_w"]
    ld = p.get("leg_d", lw)
    x = s * p["hip_x"]
    leg = f"{side}_leg"
    k0, k1 = L * 0.45, L * 0.56
    r = lw / 2
    drum(c, leg, thigh, (x, L + 0.6, 0), (x, k1 + 0.1, 0), r * 1.2, r * 1.08)
    band(c, leg, (x, k0 - 0.2, 0), (x, k1 + 0.3, 0), r * 0.72)
    if endo_shin:
        c.cylinder(leg, "endo", (x, k0, 0.3), (x, 2.6, 0.3), 0.55, segs=12)
        c.cylinder(leg, "endo", (x - 0.5, k0 - 0.4, -0.5), (x - 0.5, 3.0, -0.5), 0.3, segs=10)
        c.sphere(leg, "endo", (x, k0, 0.2), 0.9, segs=14, rings=8)
    else:
        drum(c, leg, shin, (x, k0 + 0.1, 0), (x, 2.7, 0), r * 1.1, r * 0.98)
    band(c, leg, (x, 1.9, 0), (x, 2.9, 0), r * 0.6)
    f = p.get("foot", 2.4)
    if foot_style == "paw":
        els = [((x, 1.4, -f * 0.35), (r + 1.1, 1.35, ld / 2 + f * 0.55)), ((x, 1.6, 1.0), (r + 0.5, 1.4, 1.8))]
        if not metal_toes:
            els += [((x + i * (r + 0.4) * 0.66, 1.15, -ld / 2 - f + 0.3), (1.15, 1.05, 1.3)) for i in (-1, 0, 1)]
        c.blob(leg, foot_mat, els, res=0.035)
        if metal_toes:
            for i in (-1, 0, 1):
                tx = x + i * (r + 0.4) * 0.6
                c.capsule(leg, "endo", (tx, 0.8, -ld / 2 - f + 0.8), (tx, 0.55, -ld / 2 - f - 1.0), 0.45, 0.35, segs=10)
    elif foot_style == "bird":
        c.blob(leg, foot_mat, [((x, 1.35, -0.2), (r + 0.7, 1.35, ld / 2 + 0.9))], res=0.035)
        for i in (-1, 0, 1):
            ang = math.radians(i * 24)
            ln = f + 2.2
            end = (x + math.sin(ang) * ln, 0.95, -math.cos(ang) * ln - ld / 2 + 0.9)
            c.capsule(leg, foot_mat, (x, 1.1, -1.0), end, 1.05, 0.85, segs=14)
            tip = (end[0] + math.sin(ang) * 1.3, 0.55, end[2] - math.cos(ang) * 1.3)
            c.capsule(leg, claw, end, tip, 0.8, 0.35, segs=12, cap=3)
        c.capsule(leg, foot_mat, (x, 1.0, 0.6), (x, 0.7, ld / 2 + 1.8), 0.9, 0.7, segs=12)
    elif foot_style == "endo":
        c.rbox(leg, "endo", (x, 0.8, -f * 0.4), (lw + 0.6, 1.2, ld + f), bevel=0.3)
        for i in (-1, 0, 1):
            tx = x + i * 1.1
            c.capsule(leg, "endo", (tx, 0.7, -ld / 2 - f * 0.5), (tx, 0.5, -ld / 2 - f - 1.0), 0.35, 0.3, segs=10)
    elif foot_style == "shoe":
        c.blob(leg, foot_mat, [((x, 1.1, -f * 0.4), (r + 0.5, 1.1, ld / 2 + f * 0.7))], res=0.035)
        c.rbox(leg, sole, (x, 0.15, -f * 0.4), (lw + 1.0, 0.3, ld + f * 1.3), bevel=0.12)


# ====================================================================== heads

def eye(c, bone, center, r, iris_mat, look=(0.0, -0.08), lid_mat=None, lid=0.3, rim=False):
    x, y, z = center
    z += r * 0.35
    if rim:
        c.ellipsoid(bone, "black", (x, y, z + 0.25), (r * 1.14, r * 1.12, r * 0.9))
    c.sphere(bone, "eye_white", (x, y, z), r, segs=28, rings=18)
    ix, iy = x + look[0] * r, y + look[1] * r
    c.ellipsoid(bone, iris_mat, (ix, iy, z - r * 0.88), (r * 0.5, r * 0.5, r * 0.2), segs=22, rings=10)
    c.ellipsoid(bone, "pupil", (ix, iy, z - r * 0.98), (r * 0.22, r * 0.22, r * 0.09), segs=14, rings=8)
    if lid_mat:
        c.ellipsoid(bone, lid_mat, (x, y + r * (1.25 - lid), z - r * 0.05), (r * 1.2, r * 0.62, r * 1.12), rot=(-16, 0, 0))


def freckles(c, bone, y, z, mat="black"):
    for s in (1, -1):
        for dx, dy in ((2.0, 0.1), (2.7, -0.4), (2.3, -0.9)):
            c.sphere(bone, mat, (s * dx, y + dy, z), 0.17, segs=8, rings=6)


def bear_head(c, fur, fur2, iris=None, sockets=False, pin=(255, 255, 255), ear_tilt=0, nose="black"):
    y0 = c.a["y0"]
    c.blob("head", fur, [((0, y0 + 5.4, 0.4), (6.0, 4.6, 5.3)),
                         ((0, y0 + 2.8, -0.8), (6.3, 2.8, 4.6)),
                         ((0, y0 + 7.4, -2.6), (5.0, 1.6, 2.6))], res=0.035)
    c.blob("head", fur2, [((0, y0 + 3.3, -4.6), (4.8, 2.25, 2.7)), ((0, y0 + 3.1, -6.0), (3.8, 1.75, 1.9))], res=0.03)
    freckles(c, "head", y0 + 3.6, -7.0)
    c.ellipsoid("head", nose, (0, y0 + 4.9, -7.55), (1.55, 0.78, 0.95))
    c.ellipsoid("head", "mouth", (0, y0 + 1.5, -5.0), (3.6, 0.95, 2.6))
    fb.teeth_row(c, "head", y0 + 1.75, -7.2, 6.4, 8, h=0.8, up=True, curve=1.6)
    c.blob("jaw", fur2, [((0, y0 + 0.2, -4.8), (4.2, 1.25, 2.9)), ((0, y0 + 0.4, -3.0), (3.4, 1.0, 1.4))], res=0.03)
    fb.teeth_row(c, "jaw", y0 + 1.1, -7.05, 6.0, 8, h=0.7, up=False, curve=1.6)
    for s in (1, -1):
        ex = s * 2.55
        if sockets:
            fb.socket(c, "head", (ex, y0 + 6.3, -4.3), 1.45, pin)
        else:
            eye(c, "head", (ex, y0 + 6.3, -4.05), 1.5, "iris", look=(-s * 0.06, -0.06), lid_mat=fur, lid=0.42)
        c.capsule("head", "black", (s * 1.2, y0 + 8.35, -4.75), (s * 3.9, y0 + 8.0, -4.4), 0.42, 0.36, segs=12, cap=3)
        ear = (s * 5.0, y0 + 9.7, 0.6)
        R = (0, 0, -s * (12 - ear_tilt))
        c.ellipsoid("head", fur, ear, (2.05, 2.05, 0.95), rot=R)
        c.ellipsoid("head", fur2, (ear[0], ear[1], -0.15), (1.3, 1.3, 0.4), rot=R)
        c.cylinder("head", "metal", (s * 4.2, y0 + 8.3, 0.0), (s * 4.2, y0 + 8.3, -0.9), 0.3, segs=10)


def rabbit_head(c, fur, fur2, iris=None, sockets=False, pin=(255, 255, 255), broken_ear=False):
    y0 = c.a["y0"]
    c.blob("head", fur, [((0, y0 + 5.2, 0.3), (5.6, 4.7, 5.1)),
                         ((0, y0 + 2.7, -0.8), (5.9, 2.6, 4.5)),
                         ((0, y0 + 7.2, -2.5), (4.6, 1.5, 2.4))], res=0.035)
    c.blob("head", fur2, [((0, y0 + 3.0, -4.5), (4.8, 2.4, 2.8)), ((0, y0 + 2.8, -5.9), (3.9, 1.8, 1.9))], res=0.03)
    c.ellipsoid("head", "nose", (0, y0 + 4.75, -7.3), (1.05, 0.6, 0.7))
    c.ellipsoid("head", "mouth", (0, y0 + 1.3, -4.9), (3.7, 1.1, 2.6))
    fb.teeth_row(c, "head", y0 + 1.65, -7.1, 6.6, 8, h=0.95, up=True, curve=1.6)
    c.blob("jaw", fur2, [((0, y0 - 0.1, -4.7), (4.2, 1.2, 2.8)), ((0, y0 + 0.1, -2.9), (3.4, 1.0, 1.3))], res=0.03)
    fb.teeth_row(c, "jaw", y0 + 0.75, -6.95, 6.2, 8, h=0.85, up=False, curve=1.6)
    for s in (1, -1):
        ex = s * 2.45
        if sockets:
            fb.socket(c, "head", (ex, y0 + 6.1, -4.1), 1.4, pin)
        else:
            eye(c, "head", (ex, y0 + 6.1, -3.85), 1.45, "iris", look=(-s * 0.04, -0.05), lid_mat=fur, lid=0.38)
        c.capsule("head", "black", (s * 1.2, y0 + 8.05, -4.5), (s * 3.7, y0 + 7.75, -4.1), 0.36, 0.3, segs=12, cap=3)
    for side, s in (("left", 1), ("right", -1)):
        bn = f"{side}_ear"
        broken = broken_ear and side == "right"
        x = s * 2.5
        c.cylinder(bn, "metal", (x, y0 + 8.4, 0.6), (x, y0 + 11.2, 0.6), 0.32, segs=10)
        lo = y0 + 10.6
        hi = y0 + (15.0 if broken else 18.6)
        h = (hi - lo) / 2
        c.blob(bn, fur, [((x, lo + h, 0.6), (1.75, h + 0.2, 0.95))], res=0.03)
        c.ellipsoid(bn, fur2, (x, lo + h + 0.3, -0.18), (1.05, h - 0.5, 0.35))
        if broken:
            c.cylinder(bn, "metal", (x, hi - 0.4, 0.6), (x + s * 0.4, hi + 2.4, 1.0), 0.26, segs=8)
            c.capsule(bn, "wire_r", (x + 0.3, hi - 0.3, 0.4), (x + s * 1.2, hi + 1.4, 0.2), 0.14, segs=6, cap=2)


# ====================================================================== characters

def build_freddy(name="freddy", golden=False):
    c = Char(name)
    std_mats(c)
    if golden:
        c.mat("fur", mat_fur, (176, 150, 32), 0.75)
        c.mat("fur2", mat_fur, (176, 150, 32), 0.75)
        c.mat("pin", mat_glow, (255, 255, 255), 12)
    else:
        c.mat("fur", mat_fur, (150, 80, 22), 0.45)
        c.mat("fur2", mat_fur, (188, 122, 56), 0.4)
        c.mat("iris", mat_glow, (40, 110, 230), 0.35)
    c.mat("hat", mat_plastic, (38, 38, 40), 0.35, 0.3, 0.05)
    c.mat("band_h", mat_plastic, (28, 28, 30), 0.5, 0.2, 0.0)
    c.mat("mic", mat_plastic, (20, 20, 22), 0.35, 0.3, 0.05)
    c.mat("grille", mat_metal, (175, 175, 182), 0.28, 0.0)
    c.mat("claw", mat_simple, (235, 235, 230), 0.4)
    torso_suit(c, "fur", belly="fur2" if not golden else None)
    bear_head(c, "fur", "fur2", sockets=golden)
    y0 = c.a["y0"]
    c.cylinder("head", "hat", (0, y0 + 9.6, 0.2), (0, y0 + 10.0, 0.2), 2.9, bevel=0.15, segs=28)
    c.cylinder("head", "hat", (0, y0 + 9.9, 0.2), (0, y0 + 13.3, 0.2), 2.0, bevel=0.2, segs=28, r_end=1.95)
    c.cylinder("head", "band_h", (0, y0 + 10.0, 0.2), (0, y0 + 10.6, 0.2), 2.05, bevel=0.05, segs=28)
    bowtie(c, "hat")
    for side, s in (("left", 1), ("right", -1)):
        ax, top, fore = limb_suit(c, side, s, "fur")
        leg_suit(c, side, s, "fur", "fur", "fur")
        if side == "right" and not golden:
            z = -3.4
            c.cylinder(fore, "mic", (ax, top - 4.4, z), (ax, top + 0.4, z), 0.45, segs=14)
            c.cylinder(fore, "grille", (ax, top + 0.4, z), (ax, top + 0.9, z), 0.6, segs=14)
            c.sphere(fore, "grille", (ax, top + 1.6, z), 1.05)
    if golden:
        fb.holes(c, [("body", (3.6, c.a["L"] + 6.5, -c.a["td"] / 2 - 0.6), 1.2)])
    return c


def bowtie(c, mat):
    N, td = c.a["N"], c.a["td"]
    z = -td / 2 - 1.35
    y = N - 0.7
    c.ellipsoid("body", mat, (0, y, z - 0.25), (0.75, 0.7, 0.55))
    for s in (1, -1):
        c.blob("body", mat, [((s * 2.0, y, z), (1.45, 1.15, 0.45), (0, 0, s * 6)),
                             ((s * 1.0, y, z - 0.1), (0.7, 0.65, 0.45))], res=0.022)


def build_bonnie():
    c = Char("bonnie")
    std_mats(c)
    c.mat("fur", mat_fur, (64, 50, 140), 0.4)
    c.mat("fur2", mat_fur, (154, 148, 182), 0.35)
    c.mat("iris", mat_glow, (220, 50, 120), 0.35)
    c.mat("nose", mat_plastic, (40, 28, 46), 0.3, 0.5, 0.05)
    c.mat("bow", mat_plastic, (182, 12, 16), 0.35, 0.3, 0.05)
    c.mat("guitar", mat_plastic, (196, 20, 26), 0.15, 1.0, 0.1)
    c.mat("g_white", mat_plastic, (236, 236, 236), 0.2, 1.0, 0.05)
    c.mat("g_neck", mat_plastic, (30, 22, 18), 0.4, 0.3, 0.05)
    c.mat("claw", mat_simple, (235, 235, 230), 0.4)
    torso_suit(c, "fur", belly="fur2")
    rabbit_head(c, "fur", "fur2")
    bowtie(c, "bow")
    for side, s in (("left", 1), ("right", -1)):
        limb_suit(c, side, s, "fur")
        leg_suit(c, side, s, "fur", "fur", "fur")
    flying_v(c, "body", (-0.5, c.a["L"] + 4.6, -c.a["td"] / 2 - 2.8), (6, 0, -72))
    return c


def flying_v(c, bone, center, rot):
    """Red Flying-V guitar with white stripes; geometry given in guitar space, rotated into place."""
    R = bb_rot(rot)
    k = 1.3

    def at(dx, dy, dz=0.0):
        v = R @ Vector((dx * k * S, dz * S, dy * k * S))
        return (center[0] + v.x / S, center[1] + v.z / S, center[2] + v.y / S)

    for s in (1, -1):
        c.rbox(bone, "guitar", at(s * 2.6, -3.2), (2.4 * k, 8.5 * k, 1.0), bevel=0.35, rot=(rot[0], rot[1], rot[2] + s * 28))
        c.rbox(bone, "g_white", at(s * 2.35, -3.4, -0.52), (0.5 * k, 7.4 * k, 0.08), bevel=0.0, rot=(rot[0], rot[1], rot[2] + s * 28))
    c.rbox(bone, "guitar", at(0, 0.2), (3.4 * k, 2.8 * k, 1.0), bevel=0.4, rot=rot)
    c.rbox(bone, "g_neck", at(0, 7.4), (1.2, 12.0 * k, 0.8), bevel=0.2, rot=rot)
    c.rbox(bone, "guitar", at(0.4, 14.3), (2.6 * k, 2.2 * k, 0.7), bevel=0.3, rot=(rot[0], rot[1], rot[2] - 18))
    c.rbox(bone, "black", at(0, -0.4, -0.55), (2.4, 0.5, 0.15), bevel=0.05, rot=rot)
    c.rbox(bone, "black", at(0, 0.9, -0.55), (2.4, 0.5, 0.15), bevel=0.05, rot=rot)
    for i in range(4):
        dx = -0.36 + i * 0.24
        c.cylinder(bone, "chrome", at(dx, -1.4, -0.6), at(dx, 13.2, -0.5), 0.04, segs=4, bevel=0)


def build_chica():
    c = Char("chica")
    std_mats(c)
    c.mat("fur", mat_fur, (206, 190, 34), 0.45)
    c.mat("iris", mat_glow, (140, 50, 190), 0.35)
    c.mat("beak", mat_plastic, (222, 118, 30), 0.35, 0.4, 0.2)
    c.mat("leg_o", mat_fur, (205, 98, 24), 0.45)
    c.mat("claw", mat_simple, (240, 240, 236), 0.35, 0, 0.3)
    c.mat("bib", mat_fur, (238, 238, 232), 0.15, 0.2)
    c.mat("letter", mat_plastic, (238, 214, 40), 0.35, 0.3, 0.0)
    c.mat("outline", mat_plastic, (118, 40, 170), 0.4, 0.2, 0.0)
    for i, col in enumerate([(230, 60, 140), (60, 170, 230), (250, 170, 30), (90, 190, 80), (170, 80, 220)]):
        c.mat(f"conf{i}", mat_plastic, col, 0.4, 0.2, 0.0)
    c.mat("plate", mat_plastic, (236, 236, 240), 0.2, 0.6, 0.0)
    c.mat("wrapper", mat_stripes, (225, 100, 40), (245, 150, 70), "X", 22, 0.5, 0.0, True)
    c.mat("frosting", mat_plastic, (240, 90, 165), 0.3, 0.5, 0.0)
    c.mat("candle", mat_stripes, (250, 236, 150), (90, 160, 230), "Z", 30, 0.4, 0.0)
    c.mat("flame", mat_glow, (255, 170, 40), 20)
    c.mat("cake_iris", mat_simple, (150, 90, 200), 0.1, 0, 1.0)
    a = c.a
    L, N, td, y0 = a["L"], a["N"], a["td"], a["y0"]
    torso_suit(c, "fur")
    # head
    c.blob("head", "fur", [((0, y0 + 5.3, 0.3), (5.7, 4.9, 5.1)), ((0, y0 + 2.6, -0.6), (6.0, 2.6, 4.4))], res=0.035)
    c.blob("head", "beak", [((0, y0 + 3.5, -5.0), (4.2, 1.45, 2.9)), ((0, y0 + 3.2, -7.6), (2.6, 1.0, 1.8)),
                            ((0, y0 + 2.9, -9.2), (1.2, 0.7, 1.0))], res=0.028)
    for s in (1, -1):
        c.ellipsoid("head", "black", (s * 1.0, y0 + 4.4, -7.4), (0.3, 0.16, 0.3))
    c.ellipsoid("head", "mouth", (0, y0 + 1.6, -5.0), (3.6, 1.0, 2.7))
    fb.teeth_row(c, "head", y0 + 2.15, -7.5, 6.4, 8, h=0.8, up=True, curve=1.8)
    c.blob("jaw", "beak", [((0, y0 + 0.4, -5.0), (3.8, 1.0, 2.8)), ((0, y0 + 0.6, -7.4), (2.3, 0.75, 1.6)),
                           ((0, y0 + 0.8, -8.7), (1.0, 0.5, 0.8))], res=0.028)
    fb.teeth_row(c, "jaw", y0 + 1.05, -7.3, 6.0, 8, h=0.7, up=False, curve=1.8)
    for s in (1, -1):
        eye(c, "head", (s * 2.6, y0 + 6.4, -3.8), 1.6, "iris", look=(-s * 0.04, -0.03), rim=True)
        c.capsule("head", "black", (s * 1.2, y0 + 8.7, -4.4), (s * 4.0, y0 + 8.5, -3.9), 0.42, 0.36, segs=12, cap=3)
    for i, (dx, rz, ln) in enumerate(((-1.2, 20, 3.4), (0, 0, 4.2), (1.2, -20, 3.4))):
        R = bb_rot((-10, 0, rz))
        tip = R @ Vector((0, 0, ln * S))
        base = (dx, y0 + 9.4, 0.4)
        c.cone("head", "fur", base, (base[0] + tip.x / S, base[1] + tip.z / S, base[2] + tip.y / S), 1.0, segs=12)
    # bib with confetti and LET'S EAT!!
    top, bot = N - 0.6, L + 3.0
    zf = -td / 2 - 0.85
    c.blob("body", "bib", [((0, (top + bot) / 2, zf + 0.45), (5.8, (top - bot) / 2, 0.55))], res=0.03)
    import random
    rnd = random.Random(5)
    for i in range(26):
        x, y = rnd.uniform(-4.8, 4.8), rnd.uniform(bot + 0.6, top - 0.6)
        c.ellipsoid("body", f"conf{i % 5}", (x, y, zf - 0.05), (0.16, 0.16, 0.08), segs=8, rings=4)
    mid = (top + bot) / 2
    for txt, dy in (("LET'S", 1.6), ("EAT!!", -1.6)):
        c.text("body", ["outline"], txt, (0, mid + dy, zf - 0.05), 3.9, 0.2)
        c.text("body", ["letter"], txt, (0, mid + dy, zf - 0.22), 3.4, 0.2)
    for side, s in (("left", 1), ("right", -1)):
        limb_suit(c, side, s, "fur")
        leg_suit(c, side, s, "fur", "leg_o", "leg_o", foot_style="bird")
    # cupcake (bone counter-rotates the raised forearm)
    ax, top_h = a["hands"]["left"][0], a["hands"]["left"][1]
    hx, hyc = ax, top_h - 1.4
    cb = "cupcake"
    c.cylinder(cb, "plate", (hx, hyc + 1.75, 0), (hx, hyc + 2.15, 0), 3.4, bevel=0.15, segs=32)
    c.lathe(cb, "wrapper", (hx, hyc + 2.15, 0), (hx, hyc + 4.6, 0), [(0, 0), (0, 1.55), (2.45, 1.95), (2.45, 0)], segs=26)
    c.blob(cb, "frosting", [((hx, hyc + 5.4, 0), (2.4, 1.6, 2.4))], res=0.025)
    c.cylinder(cb, "candle", (hx, hyc + 6.6, 0), (hx, hyc + 8.4, 0), 0.22, segs=10)
    c.ellipsoid(cb, "flame", (hx, hyc + 8.9, 0), (0.28, 0.5, 0.28), segs=10, rings=8)
    for dx in (-0.85, 0.85):
        c.sphere(cb, "eye_white", (hx + dx, hyc + 5.4, -1.7), 0.72, segs=14, rings=10)
        c.sphere(cb, "cake_iris", (hx + dx, hyc + 5.35, -2.3), 0.36, segs=10, rings=6)
        c.sphere(cb, "pupil", (hx + dx, hyc + 5.35, -2.5), 0.17, segs=8, rings=6)
    fb.teeth_row(c, cb, hyc + 4.35, -1.95, 2.2, 4, h=0.45, up=True, curve=0.2)
    return c


def build_foxy():
    c = Char("foxy")
    std_mats(c, rust=0.35)
    c.mat("fur", mat_fur, (150, 40, 30), 0.7)
    c.mat("fur2", mat_fur, (196, 150, 120), 0.65)
    c.mat("inner", mat_fur, (80, 18, 16), 0.5)
    c.mat("pants", mat_fur, (92, 46, 24), 0.75, 0.3)
    c.mat("iris", mat_glow, (245, 190, 20), 0.6)
    c.mat("patch", mat_plastic, (14, 12, 12), 0.55, 0.0, 0.1)
    c.mat("hook", mat_metal, (64, 64, 68), 0.45, 0.4)
    c.mat("nose", mat_plastic, (24, 18, 18), 0.3, 0.5, 0.2)
    c.mat("teeth", mat_simple, (222, 200, 140), 0.45, 0, 0.2, 0.1)
    a = c.a
    L, N, td, tw, y0 = a["L"], a["N"], a["td"], a["tw"], a["y0"]
    torso_suit(c, "fur", pelvis="pants", chest_scale=0.88)
    c.blob("body", "pants", [((0, L - 0.6, 0), (tw / 2 + 0.2, 2.6, td / 2 + 0.2))], res=0.04)
    fb.holes(c, [("body", (-1.4, L + 7.2, -td / 2 - 0.9), 2.2), ("body", (2.6, L + 3.5, -td / 2 - 0.8), 1.2)])
    c.blob("head", "fur", [((0, y0 + 4.5, 0.3), (5.0, 4.0, 4.7)), ((0, y0 + 2.2, -0.6), (5.2, 2.2, 3.9)),
                           ((0, y0 + 3.8, -6.2), (3.0, 1.45, 3.6))], res=0.032)
    c.blob("head", "fur2", [((0, y0 + 2.6, -6.2), (2.9, 0.85, 3.4))], res=0.03)
    c.ellipsoid("head", "nose", (0, y0 + 4.6, -9.7), (1.2, 0.8, 0.85))
    c.ellipsoid("head", "mouth", (0, y0 + 1.3, -6.4), (2.5, 0.85, 3.2))
    fb.teeth_row(c, "head", y0 + 1.75, -9.3, 4.8, 8, h=1.2, up=True, pointed=True, curve=0.6)
    c.blob("jaw", "fur2", [((0, y0 - 0.2, -6.2), (2.7, 0.8, 3.4))], res=0.03)
    fb.teeth_row(c, "jaw", y0 + 0.45, -9.1, 4.4, 7, h=1.0, up=False, pointed=True, curve=0.6)
    c.cylinder("jaw", "endo", (-2.9, y0 + 0.4, -3.4), (2.9, y0 + 0.4, -3.4), 0.45, segs=12)
    eye(c, "head", (2.25, y0 + 5.6, -3.8), 1.3, "iris", look=(-0.1, -0.1), lid_mat="fur", lid=0.3)
    c.ellipsoid("head", "patch", (-2.25, y0 + 5.6, -4.4), (1.7, 1.45, 0.5))
    c.lathe("head", "patch", (0, y0 + 6.1, 0.2), (0, y0 + 6.6, 0.2), [(0, 5.05), (0.5, 5.05)], segs=30)
    for s in (1, -1):
        c.capsule("head", "black", (s * 1.0, y0 + 7.5, -4.4), (s * 3.4, y0 + 7.1, -3.9), 0.34, 0.28, segs=10, cap=3)
        base = (s * 3.2, y0 + 7.6, 0.6)
        tip = (s * 4.6, y0 + 13.4, 0.6)
        c.lathe("head", "fur", base, tip, [(0, 0), (0, 2.0), (2.2, 1.7), (4.6, 0.8), (6.0, 0.05)], segs=4)
        c.lathe("head", "inner", (base[0], base[1] + 0.4, -0.25), (tip[0] - s * 0.2, tip[1] - 1.0, -0.25),
                [(0, 0), (0, 1.25), (2.2, 0.95), (4.4, 0.05)], segs=4)
    for i, dx in enumerate((-0.6, 0.3)):
        c.cone("head", "fur", (dx, y0 + 8.6, 0.2), (dx * 2.5, y0 + 11.0, -0.4), 0.7, segs=8)
    for side, s in (("left", 1), ("right", -1)):
        if side == "right":
            ax, top, fore = limb_suit(c, side, s, "fur", hand_style="none")
            c.cylinder(fore, "hook", (ax, top + 0.3, 0), (ax, top - 1.4, 0), 1.6, segs=20)
            c.cylinder(fore, "hook", (ax, top - 1.4, 0), (ax, top - 4.6, 0), 0.38, segs=12)
            pts = [(ax, top - 4.6, 0)] + [(ax, top - 4.6 - math.sin(t) * 1.7, -1.7 + math.cos(t) * 1.7)
                                          for t in [i * math.pi / 8 for i in range(1, 11)]]
            for p0, p1 in zip(pts, pts[1:]):
                c.capsule(fore, "hook", p0, p1, 0.36, 0.32 if p1 != pts[-1] else 0.12, segs=10, cap=2)
        else:
            limb_suit(c, side, s, "fur", hand_style="endo")
        leg_suit(c, side, s, "pants", "fur", "endo", foot_style="endo", endo_shin=True)
        x = s * c.p["hip_x"]
        r = c.p["leg_w"] / 2 * 1.3
        import random
        rnd = random.Random(7 + s)
        for k in range(9):
            ang = k / 9 * math.tau + rnd.uniform(-0.2, 0.2)
            ln = rnd.uniform(1.2, 3.0)
            px, pz = x + math.cos(ang) * r, math.sin(ang) * r
            c.rbox(f"{side}_leg", "pants", (px, L * 0.6 - ln / 2, pz), (1.2, ln, 0.22), bevel=0.08,
                   rot=(0, -math.degrees(ang) + 90, rnd.uniform(-8, 8)))
    return c


def build_golden():
    return build_freddy("golden_freddy", golden=True)


# ====================================================================== install into the engine

fb.mat_fur = mat_fur
fb.torso_suit = torso_suit
fb.limb_suit = limb_suit
fb.leg_suit = leg_suit
fb.hand = hand
fb.bear_head = bear_head
fb.rabbit_head = rabbit_head
fb.eye = eye
fb.std_mats = std_mats
fb.BUILDERS.update({"freddy": build_freddy, "golden_freddy": build_golden, "bonnie": build_bonnie,
                    "chica": build_chica, "foxy": build_foxy})


# ====================================================================== poses + group shot

POSES = {
    "freddy": {"right_arm": (25, 0, 22), "right_forearm": (85, -25, 0), "left_arm": (18, 0, -14), "left_forearm": (70, 30, 0)},
    "bonnie": {"right_arm": (20, 0, 10), "right_forearm": (55, 10, 0), "left_arm": (25, 0, -18), "left_forearm": (75, 25, 0),
               "head": (4, 0, 0)},
    "chica": {"right_arm": (10, 0, 6), "right_forearm": (20, 0, 0), "left_arm": (20, 0, -10)},
    "foxy": {"right_arm": (0, 0, -70), "right_forearm": (0, 0, -55), "left_arm": (10, 0, -5), "head": (-6, -10, 8)},
    "golden_freddy": {"right_arm": (0, 0, 4), "left_arm": (0, 0, -4)},
}


def pose(name, extra=None):
    rig = fb.RIGS[name]
    for b in rig["bones"]:
        e = bpy.data.objects.get(f"{name}:{b['name']}")
        if not e:
            continue
        add = (extra or {}).get(b["name"], (0, 0, 0))
        rot = [b["rot"][i] + add[i] for i in range(3)]
        e.rotation_mode = "QUATERNION"
        e.rotation_quaternion = bb_rot(rot).to_quaternion()


def group_shot(path, samples=64):
    """Five FNAF1 animatronics posed like the classic promo render, on white."""
    layout = {"foxy": (-1.25, 0.55, 18), "bonnie": (-0.6, 0.15, 10), "freddy": (0.05, -0.35, 0),
              "chica": (0.75, 0.05, -10), "golden_freddy": (1.3, 0.55, -18)}
    for nm in fb.BUILDERS:
        root = bpy.data.objects.get(f"{nm}:root")
        coll = bpy.data.collections.get(nm)
        if not root or not coll:
            continue
        shown = nm in layout
        coll.hide_render = not shown
        coll.hide_viewport = not shown
        if shown:
            x, y, yaw = layout[nm]
            root.location = (x, y, 0)
            root.rotation_mode = "XYZ"
            root.rotation_euler = (0, 0, math.radians(yaw))
            pose(nm, POSES.get(nm))
    stage = bpy.data.collections.get("stage")
    if stage:
        stage.hide_render = True
    sc = bpy.context.scene
    w = sc.world
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 0.55
    lights = bpy.data.collections.get("shot_lights")
    if not lights:
        lights = bpy.data.collections.new("shot_lights")
        sc.collection.children.link(lights)
        for nm, loc, en, size in (("s_key", (-3, -5, 4.5), 1500, 3), ("s_fill", (4, -4.5, 2.2), 450, 4), ("s_rim", (1.5, 3.5, 4.5), 900, 3)):
            ld = bpy.data.lights.new(nm, "AREA")
            ld.energy = en
            ld.size = size
            lo = bpy.data.objects.new(nm, ld)
            lo.location = loc
            lo.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
            lights.objects.link(lo)
    cam = sc.camera
    cam.location = (0.05, -6.0, 1.55)
    cam.rotation_euler = (Vector((0.05, 0, 1.28)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    sc.render.resolution_x = 1200
    sc.render.resolution_y = 1200
    sc.render.film_transparent = True
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = -0.35
    except TypeError:
        pass
    sc.cycles.samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    on_white(path)


def on_white(path):
    """Composite a transparent render onto plain white (keeps subject colours saturated)."""
    img = bpy.data.images.load(path, check_existing=False)
    import numpy as np
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)
    a[..., :3] = a[..., :3] * a[..., 3:4] + (1.0 - a[..., 3:4])
    a[..., 3] = 1.0
    img.pixels.foreach_set(a.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
