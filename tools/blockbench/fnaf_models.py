"""Detailed animatronic model specs for the FNAF Horror mod.

Built on bbmodel_kit: rounded parts, fingers, joints, props and per-face painted textures.
All models share the bone names root/body/head/jaw/{left,right}_{leg,arm,forearm} so they
use the same animations. build_models.py builds them inside Blockbench through MCP.
"""
from bbmodel_kit import Model, _mul



# =====================================================================
# Shared parts
# =====================================================================

def common(m, metal=(112, 112, 118)):
    m.mat("metal", metal, kind="metal", noise=7)
    m.mat("metal_dark", _mul(metal, 0.58), kind="metal", noise=6)
    m.mat("chrome", (186, 189, 196), kind="metal", noise=8, grime=0.1)
    m.mat("teeth", (228, 222, 196), noise=4, grime=0)
    m.mat("mouth", (42, 14, 14), noise=4, grime=0)
    m.mat("dark", (22, 20, 20), noise=4)
    m.mat("nose", (34, 26, 26), noise=3, grime=0, shade=0.25)
    m.mat("wire_r", (165, 30, 30), noise=8)
    m.mat("wire_b", (40, 60, 170), noise=8)


def joint(m, bone, name, c, size, mat="metal"):
    m.cbox(bone, name + "_a", mat, c, [size, size * 0.8, size * 0.72])
    m.cbox(bone, name + "_b", "metal_dark", c, [size * 0.72, size * 0.8 + 0.2, size])


def endo_rod(m, bone, name, x, y0, y1, z=0.0):
    """Endoskeleton bone: main strut plus a hydraulic piston in front of it."""
    hgt = y1 - y0
    m.cbox(bone, name + "_rod", "metal", [x, (y0 + y1) / 2, z + 0.3], [1.3, hgt, 1.3])
    m.cbox(bone, name + "_cyl", "metal_dark", [x, y0 + hgt * 0.68, z - 0.85], [0.9, hgt * 0.5, 0.9])
    m.cbox(bone, name + "_pis", "chrome", [x, y0 + hgt * 0.3, z - 0.85], [0.5, hgt * 0.5, 0.5])


def hand(m, bone, ax, top, s, aw, style, mat):
    """Hanging hand: palm faces the body, four fingers along Z, thumb in front."""
    zw = aw + 0.6
    if style in ("endo", "puppet"):
        fmat = "metal" if style == "endo" else mat
        m.crbox(bone, "palm", fmat, [ax, top - 1.1, 0], [aw * 0.55, 2.2, zw * 0.85], b=0.3)
        fw = 0.55 if style == "endo" else 0.6
        ln = 1.5 if style == "endo" else 2.4
        for i in range(4):
            fz = -zw * 0.85 / 2 + zw * 0.85 * (i + 0.5) / 4
            m.cbox(bone, f"finger{i}a", fmat, [ax, top - 2.2 - ln / 2, fz], [fw, ln, fw])
            m.cbox(bone, f"finger{i}b", fmat, [ax - s * 0.25, top - 2.2 - ln - ln * 0.4, fz], [fw * 0.9, ln * 0.85, fw * 0.9],
                   rot=[0, 0, -s * 20], origin=[ax, top - 2.2 - ln, fz])
            if style == "endo":
                m.cbox(bone, f"knuckle{i}", "metal_dark", [ax, top - 2.2 - ln, fz], [fw + 0.25, 0.4, fw + 0.25])
        m.cbox(bone, "thumb", fmat, [ax, top - 1.5, -zw * 0.85 / 2 - 0.5], [fw, ln, fw], rot=[-30, 0, 0])
        return
    xt = aw * 0.82
    m.crbox(bone, "palm", mat, [ax, top - 1.4, 0], [xt, 2.8, zw], b=0.55)
    fw = zw / 4 * 0.8
    for i in range(4):
        fz = -zw / 2 + zw * (i + 0.5) / 4
        m.cbox(bone, f"finger{i}a", mat, [ax, top - 2.8 - 0.65, fz], [fw * 1.1, 1.3, fw])
        m.cbox(bone, f"finger{i}b", mat, [ax - s * 0.2, top - 2.8 - 1.3 - 0.55, fz], [fw, 1.1, fw * 0.95],
               rot=[0, 0, -s * 22], origin=[ax, top - 4.1, fz])
    m.crbox(bone, "thumb", mat, [ax - s * 0.25, top - 1.7, -zw / 2 - 0.45], [fw * 1.15, 2.1, 1.0], b=0.3,
            rot=[-28, 0, 0])


def foot(m, leg, x, lw, ld, P):
    f = P.get("foot", 2.4)
    style = P.get("foot_style", "paw")
    fc = P.get("foot_c", "fur")
    if style == "paw":
        m.rbox(leg, "foot", fc, [x - lw / 2 - 0.6, 0.2, -ld / 2 - f], [x + lw / 2 + 0.6, 2.6, ld / 2 + 0.4], b=0.8)
        m.box(leg, "sole", P.get("sole_c", "dark"), [x - lw / 2 - 0.4, 0, -ld / 2 - f + 0.3], [x + lw / 2 + 0.4, 0.3, ld / 2 + 0.2])
        toe_mat = "metal" if P.get("metal_toes") else fc
        for i in (-1, 0, 1):
            m.crbox(leg, f"toe{i + 1}", toe_mat, [x + i * lw * 0.34, 0.9, -ld / 2 - f - 0.35], [lw * 0.3, 1.5, 1.0], b=0.3)
    elif style == "bird":
        m.rbox(leg, "foot", fc, [x - lw / 2 - 0.3, 0.2, -ld / 2 - 0.6], [x + lw / 2 + 0.3, 2.4, ld / 2 + 0.3], b=0.6)
        for i in (-1, 0, 1):
            tx = x + i * 1.7
            m.crbox(leg, f"toe{i + 1}", fc, [tx, 0.75, -ld / 2 - 0.6 - f / 2], [1.4, 1.5, f + 0.4], b=0.4)
            m.crbox(leg, f"claw{i + 1}", "dark", [tx, 0.55, -ld / 2 - 0.9 - f], [0.9, 1.0, 1.0], b=0.25)
        m.crbox(leg, "heel", fc, [x, 0.75, ld / 2 + 0.8], [1.3, 1.4, 1.6], b=0.35)
    elif style == "endo":
        m.rbox(leg, "foot", "metal_dark", [x - lw / 2 - 0.4, 0.2, -ld / 2 - f + 0.4], [x + lw / 2 + 0.4, 1.4, ld / 2 + 0.4], b=0.3)
        for i in (-1, 0, 1):
            tx = x + i * 1.1
            m.cbox(leg, f"toe{i + 1}a", "metal", [tx, 0.6, -ld / 2 - f + 0.2], [0.7, 1.0, 1.3])
            m.cbox(leg, f"toe{i + 1}b", "metal", [tx, 0.45, -ld / 2 - f - 0.9], [0.6, 0.8, 1.2])
        m.cbox(leg, "heel", "metal", [x, 0.8, ld / 2 + 0.6], [1.2, 1.2, 1.2])
    elif style == "shoe":
        m.rbox(leg, "foot", fc, [x - lw / 2 - 0.4, 0.3, -ld / 2 - f], [x + lw / 2 + 0.4, 2.2, ld / 2 + 0.3], b=0.7)
        m.box(leg, "sole", "dark", [x - lw / 2 - 0.4, 0, -ld / 2 - f + 0.2], [x + lw / 2 + 0.4, 0.4, ld / 2 + 0.3])
        m.box(leg, "lace", "laces", [x - 0.8, 2.2, -ld / 2 - f + 0.6], [x + 0.8, 2.3, -ld / 2 + 0.4])


def skeleton(m, P):
    """Root/body/legs/arms/head. Returns anchors used by the character code."""
    L = P["leg_h"]
    lw, ld, hx = P["leg_w"], P.get("leg_d", P["leg_w"]), P["hip_x"]
    tw, th, td = P["torso"]
    aw, ua, fa = P["arm_w"], P["upper_arm"], P["forearm"]
    N = L + th
    endo = P.get("style") == "endo"

    m.bone("root", None, [0, 0, 0])
    m.bone("body", "root", [0, L, 0], P.get("body_rot"))

    for side, s in (("right", -1), ("left", 1)):
        x = s * hx
        leg = f"{side}_leg"
        m.bone(leg, "root", [x, L, 0], P.get(f"{side}_leg_rot"))
        k0, k1 = L * 0.45, L * 0.56
        if endo:
            joint(m, leg, "hip", [x, L, 0], 2.4)
            endo_rod(m, leg, "thigh", x, k1, L)
        else:
            m.rbox(leg, "thigh", P.get("thigh_c", "fur"), [x - lw / 2, k1, -ld / 2], [x + lw / 2, L + 0.6, ld / 2],
                   b=0.8, paint=P.get("thigh_paint"))
        joint(m, leg, "knee", [x, (k0 + k1) / 2, 0], 2.2 if endo else lw * 0.62)
        if endo or P.get("endo_shin"):
            endo_rod(m, leg, "shin", x, 2.4, k0)
        else:
            m.rbox(leg, "shin", P.get("shin_c", "fur"), [x - lw / 2 + 0.3, 2.3, -ld / 2 + 0.3], [x + lw / 2 - 0.3, k0, ld / 2 - 0.3],
                   b=0.7, paint=P.get("shin_paint"))
        joint(m, leg, "ankle", [x, 2.4, 0], 1.8)
        foot(m, leg, x, lw, ld, P)

    # ---- torso ----
    if endo:
        m.rbox("body", "pelvis", "metal_dark", [-tw / 2 + 0.8, L - 1.4, -td / 2 + 0.4], [tw / 2 - 0.8, L + 1.6, td / 2 - 0.4], b=0.4,
               paint={"north": ("rivets", {})})
        m.cbox("body", "hip_bar", "metal", [0, L, 0], [hx * 2 + 1.5, 1.0, 1.0])
        m.cbox("body", "spine", "metal", [0, (L + N) / 2, td / 2 - 0.9], [1.6, th, 1.6])
        for i in range(5):
            y = L + 3 + i * (th - 4) / 4.5
            m.rbox("body", f"rib{i}", "metal", [-tw / 2 + 0.3 + i * 0.15, y, -td / 2], [tw / 2 - 0.3 - i * 0.15, y + 0.8, td / 2],
                   b=0.3)
        m.rbox("body", "shoulders", "metal_dark", [-tw / 2 - 0.4, N - 2.2, -td / 2 + 0.6], [tw / 2 + 0.4, N, td / 2 - 0.6], b=0.4,
               paint={"north": ("rivets", {})})
    else:
        m.rbox("body", "pelvis", P.get("pelvis_c", "fur"), [-tw / 2 + 0.6, L - 1.6, -td / 2 + 0.6], [tw / 2 - 0.6, L + 2.8, td / 2 - 0.6],
               b=0.9, paint=P.get("pelvis_paint"))
        m.rbox("body", "chest", P.get("chest_c", "fur"), [-tw / 2, L + 2.2, -td / 2], [tw / 2, N - 0.6, td / 2],
               b=P.get("chest_bevel", 1.4), paint=P.get("chest_paint", {"south": ("stitch", {})}))
        m.rbox("body", "shoulders", P.get("chest_c", "fur"), [-tw / 2 - 0.2, N - 3.2, -td / 2 + 0.7], [tw / 2 + 0.2, N + 0.3, td / 2 - 0.7],
               b=1.0)
        if P.get("belly"):
            top, bot = N - 0.6 - 1.4, L + 2.2 + 0.6
            m.decal("body", "belly", [0, (top + bot) / 2 - 0.3, -td / 2 - 0.06], [tw - 4.4, (top - bot) * 0.92],
                    ("oval", dict(color=m.mats[P["belly"]]["rgb"], rim=_mul(m.mats[P["belly"]]["rgb"], 0.85))))

    # ---- arms ----
    hands = {}
    for side, s in (("right", -1), ("left", 1)):
        ax = s * (tw / 2 + aw / 2 + 0.1)
        sy = N - 1.6
        arm, fore = f"{side}_arm", f"{side}_forearm"
        upc, foc, hc = P.get("upper_c", "fur"), P.get("fore_c", "fur"), P.get("hand_c", "fur")
        m.bone(arm, "body", [ax, sy, 0], P.get(f"{side}_arm_rot"))
        ey = sy - ua - 0.5
        hy = sy - ua - 1 - fa
        if endo:
            joint(m, arm, "shoulder", [ax, sy, 0], 2.4)
            endo_rod(m, arm, "upper", ax, ey, sy)
        else:
            m.crbox(arm, "shoulder", upc, [ax, sy + 0.1, 0], [aw + 0.8, aw + 0.4, aw + 0.8], b=1.0)
            m.rbox(arm, "upper", upc, [ax - aw / 2, sy - ua, -aw / 2], [ax + aw / 2, sy, aw / 2], b=0.7,
                   paint=P.get("upper_paint"))
        joint(m, arm, "elbow", [ax, ey, 0], aw * 0.62 if not endo else 2.0)
        m.bone(fore, arm, [ax, ey, 0], P.get(f"{side}_forearm_rot"))
        if endo:
            endo_rod(m, fore, "fore", ax, hy, ey - 0.6)
        else:
            m.rbox(fore, "forearm", foc, [ax - aw / 2 + 0.15, hy, -aw / 2 + 0.15], [ax + aw / 2 - 0.15, sy - ua - 1, aw / 2 - 0.15],
                   b=0.6, paint=P.get("fore_paint"))
        joint(m, fore, "wrist", [ax, hy - 0.2, 0], 1.6)
        style = P.get(f"{side}_hand", "endo" if endo else "paw")
        if style not in ("hook", "none"):
            hand(m, fore, ax, hy - 0.5, s, aw, style, hc)
        hands[side] = (ax, hy - 0.5, s, fore)

    # ---- head ----
    m.bone("head", "body", [0, N, 0], P.get("head_rot"))
    nk = P.get("neck", 1.6)
    m.cbox("head", "neck", "metal", [0, N + nk / 2 - 0.4, 0], [2.6, nk + 1.2, 2.6])
    m.cbox("head", "neck_ring", "metal_dark", [0, N + 0.2, 0], [3.2, 0.6, 3.2])
    m.params = P
    m.anchors = dict(L=L, N=N, y0=N + nk, tw=tw, td=td, hands=hands)
    return m.anchors


# =====================================================================
# Heads
# =====================================================================

def bear_head(m, a, iris=None, fur="fur", fur2="fur2", sockets=False, ear_tilt=0, freckles=True):
    y0 = a["y0"]
    F, F2 = m.mats[fur]["rgb"], m.mats[fur2]["rgb"]
    m.rbox("head", "skull", fur, [-5.5, y0 + 0.6, -4.9], [5.5, y0 + 8.8, 5.0], b=1.3, paint={"south": ("stitch", {})})
    m.rbox("head", "jowls", fur, [-6.0, y0, -4.4], [6.0, y0 + 3.8, 3.4], b=1.0)
    m.rbox("head", "muzzle", fur2, [-3.8, y0 + 1.9, -8.0], [3.8, y0 + 5.0, -4.0], b=0.8,
           paint={"north": ("dots", dict(n=10 if freckles else 0, color=_mul(F, 0.45)))})
    m.rbox("head", "nose", "nose", [-1.6, y0 + 4.1, -8.4], [1.6, y0 + 5.5, -6.9], b=0.4, paint={"north": ("nose", {})})
    m.box("head", "mouth", "mouth", [-3.0, y0 + 0.3, -7.4], [3.0, y0 + 2.1, -4.4])
    m.box("head", "teeth_up", "teeth", [-3.2, y0 + 1.35, -7.75], [3.2, y0 + 2.05, -5.0],
          paint={"north": ("teeth", dict(n=8, up=True))})
    m.bone("jaw", "head", [0, y0 + 1.2, -3.5])
    m.rbox("jaw", "jaw", fur2, [-3.6, y0 - 1.1, -7.9], [3.6, y0 + 0.8, -3.0], b=0.6)
    m.box("jaw", "teeth_down", "teeth", [-3.2, y0 + 0.75, -7.75], [3.2, y0 + 1.35, -5.0],
          paint={"north": ("teeth", dict(n=8, up=False))})
    if sockets:
        m.sym(m.decal, "head", "socket", [2.5, y0 + 6.0, -4.96], [2.8, 2.5], ("socket", {}))
    else:
        m.sym(m.decal, "head", "eye", [2.5, y0 + 6.0, -4.96], [2.9, 2.6], ("eye", dict(iris=iris, lid=F, lid_frac=0.3)))
    m.sym(m.cbox, "head", "brow", "dark", [2.6, y0 + 7.8, -5.0], [3.2, 0.75, 0.5], rot=[0, 0, -12])
    m.sym(m.crbox, "head", "ear", fur, [4.4, y0 + 9.4, 0.4], [3.4, 3.2, 2.0], b=0.7, rot=[0, 0, -14 + ear_tilt])
    m.sym(m.decal, "head", "ear_in", [4.4, y0 + 9.3, -0.66], [1.9, 1.7], ("oval", dict(color=F2)),
          rot=[0, 0, -14 + ear_tilt], origin=[4.4, y0 + 9.4, 0.4])


def rabbit_head(m, a, iris=None, fur="fur", fur2="fur2", sockets=False, broken_ear=False, pin=(255, 255, 255)):
    y0 = a["y0"]
    F, F2 = m.mats[fur]["rgb"], m.mats[fur2]["rgb"]
    m.rbox("head", "skull", fur, [-5.0, y0 + 0.6, -4.6], [5.0, y0 + 8.6, 4.6], b=1.2, paint={"south": ("stitch", {})})
    m.rbox("head", "jowls", fur, [-5.6, y0, -4.2], [5.6, y0 + 3.6, 3.0], b=1.0)
    m.rbox("head", "muzzle", fur2, [-3.9, y0 + 1.8, -7.5], [3.9, y0 + 4.8, -3.8], b=0.8)
    m.rbox("head", "nose", "nose", [-1.3, y0 + 4.0, -7.9], [1.3, y0 + 5.1, -6.6], b=0.35, paint={"north": ("nose", {})})
    m.box("head", "mouth", "mouth", [-3.1, y0 + 0.2, -6.9], [3.1, y0 + 1.9, -4.2])
    m.box("head", "teeth_up", "teeth", [-3.3, y0 + 1.2, -7.25], [3.3, y0 + 1.9, -4.6],
          paint={"north": ("teeth", dict(n=8, up=True))})
    m.bone("jaw", "head", [0, y0 + 1.0, -3.2])
    m.rbox("jaw", "jaw", fur2, [-3.6, y0 - 1.1, -7.4], [3.6, y0 + 0.6, -2.8], b=0.6)
    m.box("jaw", "teeth_down", "teeth", [-3.3, y0 + 0.6, -7.25], [3.3, y0 + 1.2, -4.6],
          paint={"north": ("teeth", dict(n=8, up=False))})
    if sockets:
        m.sym(m.decal, "head", "socket", [2.4, y0 + 5.8, -4.66], [2.6, 2.4], ("socket", dict(pin=pin)))
    else:
        m.sym(m.decal, "head", "eye", [2.4, y0 + 5.8, -4.66], [2.7, 2.5], ("eye", dict(iris=iris, lid=F, lid_frac=0.3)))
    m.sym(m.cbox, "head", "brow", "dark", [2.4, y0 + 7.6, -4.7], [2.9, 0.7, 0.5], rot=[0, 0, -14])
    for side, s in (("left", 1), ("right", -1)):
        broken = broken_ear and side == "right"
        bn = f"{side}_ear"
        m.bone(bn, "head", [s * 2.4, y0 + 8.3, 0.6], [-6, 0, -8 * s] if not broken else [-28, 0, 38 * -s * -1])
        top = y0 + (14.5 if broken else 19.6)
        m.rbox(bn, "ear", fur, [s * 2.4 - 1.4, y0 + 8.0, -0.3], [s * 2.4 + 1.4, top, 1.5], b=0.7)
        m.decal(bn, "ear_in", [s * 2.4, (y0 + 9.0 + top - 0.8) / 2, -0.36], [1.6, top - y0 - 9.8], ("oval", dict(color=F2)))
        if broken:
            m.cbox(bn, "ear_wire", "metal", [s * 2.4, top + 1.2, 0.6], [0.6, 2.6, 0.6], rot=[12, 0, 0])
            m.cbox(bn, "ear_wire2", "wire_r", [s * 2.4 + 0.5, top + 0.6, 0.4], [0.3, 1.6, 0.3], rot=[0, 0, -25])


# =====================================================================
# Characters
# =====================================================================

def hat(m, y0, mat, band="dark"):
    m.crbox("head", "hat_brim", mat, [0, y0 + 9.0, -0.3], [6.8, 0.6, 6.2], b=0.25)
    m.crbox("head", "hat_top", mat, [0, y0 + 11.5, -0.3], [4.8, 4.6, 4.4], b=0.5)
    m.cbox("head", "hat_band", band, [0, y0 + 9.75, -0.3], [4.95, 0.7, 4.55])


def bowtie(m, a, mat):
    N, td = a["N"], a["td"]
    m.crbox("body", "bow_knot", mat, [0, N - 1.6, -td / 2 - 0.5], [1.6, 1.5, 1.0], b=0.3)
    m.sym(m.crbox, "body", "bow", mat, [1.95, N - 1.6, -td / 2 - 0.4], [2.5, 2.6, 0.8], b=0.3, rot=[0, 0, 10])


def freddy():
    m = Model("freddy", seed=11, grime=0.18)
    m.mat("fur", (112, 68, 38), kind="fur", noise=7)
    m.mat("fur2", (178, 126, 80), kind="fur", noise=6)
    common(m)
    m.mat("hat", (22, 22, 24), noise=4, shade=0.22)
    m.mat("mic", (52, 52, 56), kind="metal")
    m.mat("mic_head", (150, 150, 156), kind="metal")
    P = dict(leg_h=12, leg_w=4.8, hip_x=3.2, foot=2.4, torso=(13.4, 12, 9.0), arm_w=3.8, upper_arm=6, forearm=5.0,
             belly="fur2")
    a = skeleton(m, P)
    bear_head(m, a, iris=(70, 140, 235))
    hat(m, a["y0"], "hat")
    bowtie(m, a, "hat")
    ax, top, s, fore = a["hands"]["right"]
    z = -(3.8 + 0.6) / 2 - 0.8
    m.cbox(fore, "mic_handle", "mic", [ax, top - 2.2, z], [1.0, 3.8, 1.0])
    m.crbox(fore, "mic_head", "mic_head", [ax, top + 0.3, z], [2.0, 2.1, 2.0], b=0.5,
            paint={f: ("grille", {}) for f in ("north", "south", "east", "west", "up")})
    m.cbox(fore, "mic_ring", "chrome", [ax, top - 0.7, z], [1.4, 0.5, 1.4])
    return m, dict(width=0.8, height=2.3, egg=(0x6E4426, 0x1A1A1A))


def golden_freddy():
    m = Model("golden_freddy", seed=12, grime=0.55)
    m.mat("fur", (196, 152, 48), kind="fur", noise=9)
    m.mat("fur2", (214, 182, 92), kind="fur", noise=8)
    common(m)
    m.mat("hat", (24, 32, 66), noise=4, shade=0.22)
    P = dict(leg_h=12, leg_w=4.8, hip_x=3.2, foot=2.4, torso=(13.4, 12, 9.0), arm_w=3.8, upper_arm=6, forearm=5.0,
             belly="fur2", thigh_paint={"north": ("stitch", dict(axis="h", at=0.6))})
    a = skeleton(m, P)
    bear_head(m, a, sockets=True, ear_tilt=6)
    hat(m, a["y0"], "hat")
    bowtie(m, a, "hat")
    L, td, N = a["L"], a["td"], a["N"]
    m.decal("body", "tear0", [3.4, L + 6.5, -td / 2 - 0.08], [2.6, 3.0], ("hole", dict(bars=1)))
    m.decal("body", "tear1", [-4.0, N - 3.0, -td / 2 + 0.6 - 0.08], [1.8, 1.6], ("hole", dict(bars=0)))
    m.decal("right_leg", "tear", [-3.2, 9.0, -2.48], [2.2, 2.0], ("hole", dict(bars=1, wires=[(170, 30, 30)])))
    m.decal("left_arm", "tear", [m.by_name["left_arm"]["pivot"][0], N - 5.0, -1.98], [1.8, 2.2], ("hole", dict(bars=1)))
    return m, dict(width=0.8, height=2.2, egg=(0xC49830, 0x18203E))


def bonnie():
    m = Model("bonnie", seed=21, grime=0.18)
    m.mat("fur", (82, 82, 172), kind="fur", noise=7)
    m.mat("fur2", (152, 150, 216), kind="fur", noise=6)
    common(m)
    m.mat("bow", (175, 22, 26), noise=5, shade=0.2)
    m.mat("guitar", (192, 26, 32), noise=4, shade=0.2, grime=0.05)
    m.mat("guitar_neck", (70, 44, 30), kind="fur", noise=6)
    m.mat("fret", (40, 28, 20), noise=3)
    P = dict(leg_h=12, leg_w=4.6, hip_x=3.1, foot=3.0, torso=(12.8, 12, 8.6), arm_w=3.6, upper_arm=6, forearm=5.2,
             belly="fur2")
    a = skeleton(m, P)
    rabbit_head(m, a, iris=(215, 40, 90))
    bowtie(m, a, "bow")
    L, td, N = a["L"], a["td"], a["N"]
    # red guitar slung on the back
    gc = [0.6, L + 5.5, td / 2 + 1.1]
    rot = [0, 0, 32]

    def g(name, mat, off, size, b=0.0, paint=None):
        c = [gc[0] + off[0], gc[1] + off[1], gc[2] + off[2]]
        if b:
            m.crbox("body", name, mat, c, size, b=b, rot=rot, origin=gc, paint=paint)
        else:
            m.cbox("body", name, mat, c, size, rot=rot, origin=gc, paint=paint)

    g("guitar_lower", "guitar", [0, -1.4, 0], [7.4, 5.2, 1.6], b=0.8, paint={"south": ("pickups", {})})
    g("guitar_upper", "guitar", [0, 2.6, 0], [5.8, 3.4, 1.6], b=0.7)
    g("guitar_horn", "guitar", [-2.3, 4.4, 0], [1.4, 2.2, 1.6], b=0.5)
    g("guitar_neck", "guitar_neck", [0, 9.4, 0.1], [1.3, 10.0, 1.0], paint={"south": ("strings", dict(n=4))})
    g("guitar_head", "guitar_neck", [0, 15.4, 0.1], [2.2, 2.8, 0.9], b=0.3)
    for i in range(3):
        g(f"peg{i}l", "chrome", [1.4, 14.4 + i * 0.9, 0.1], [0.7, 0.4, 0.4])
        g(f"peg{i}r", "chrome", [-1.4, 14.4 + i * 0.9, 0.1], [0.7, 0.4, 0.4])
    m.cbox("body", "strap_front", "dark", [0, N - 5.2, -td / 2 - 0.12], [15.5, 0.9, 0.3], rot=[0, 0, -38])
    m.cbox("body", "strap_back", "dark", [0, N - 5.2, td / 2 + 0.12], [15.5, 0.9, 0.3], rot=[0, 0, 38])
    return m, dict(width=0.8, height=2.6, egg=(0x5252AC, 0xAF161A))


def chica():
    m = Model("chica", seed=31, grime=0.18)
    m.mat("fur", (226, 190, 42), kind="fur", noise=7)
    m.mat("fur2", (240, 214, 96), kind="fur", noise=6)
    common(m)
    m.mat("beak", (238, 124, 30), noise=5, shade=0.18)
    m.mat("leg_o", (232, 150, 40), kind="fur", noise=6)
    m.mat("plate", (214, 214, 220), kind="metal", noise=4, grime=0)
    m.mat("wrapper", (236, 120, 170), pattern="stripes_v", rgb2=(250, 180, 210), period=0.5, grime=0)
    m.mat("frosting", (245, 140, 190), noise=5, grime=0)
    m.mat("candle", (250, 235, 150), pattern="stripes_h", rgb2=(90, 160, 230), period=0.35, grime=0)
    m.mat("flame", (255, 170, 40), glow=True, grime=0, noise=10)
    P = dict(leg_h=12, leg_w=4.8, hip_x=3.3, foot=3.2, torso=(13.6, 12, 9.4), arm_w=3.8, upper_arm=6, forearm=5.0,
             foot_style="bird", foot_c="leg_o", shin_c="leg_o", left_forearm_rot=[75, 0, 0])
    a = skeleton(m, P)
    y0, N, L, td = a["y0"], a["N"], a["L"], a["td"]
    F = m.mats["fur"]["rgb"]
    m.rbox("head", "skull", "fur", [-5.1, y0 + 0.6, -4.6], [5.1, y0 + 8.9, 4.6], b=1.3, paint={"south": ("stitch", {})})
    m.rbox("head", "jowls", "fur2", [-5.6, y0, -4.2], [5.6, y0 + 3.6, 3.2], b=1.0)
    m.rbox("head", "beak", "beak", [-3.8, y0 + 2.2, -8.6], [3.8, y0 + 4.8, -4.0], b=0.8,
           paint={"north": ("dots", dict(n=0))})
    m.sym(m.cbox, "head", "nostril", "dark", [0.9, y0 + 4.3, -8.62], [0.5, 0.35, 0.1])
    m.crbox("head", "beak_tip", "beak", [0, y0 + 2.9, -8.9], [5.0, 1.6, 1.2], b=0.4)
    m.box("head", "mouth", "mouth", [-3.2, y0 + 0.3, -7.6], [3.2, y0 + 2.3, -4.2])
    m.box("head", "teeth_up", "teeth", [-3.3, y0 + 1.55, -8.2], [3.3, y0 + 2.25, -5.0],
          paint={"north": ("teeth", dict(n=7, up=True))})
    m.bone("jaw", "head", [0, y0 + 1.2, -3.6])
    m.rbox("jaw", "jaw", "beak", [-3.5, y0 - 0.9, -8.4], [3.5, y0 + 1.0, -3.4], b=0.6)
    m.box("jaw", "teeth_down", "teeth", [-3.1, y0 + 0.95, -8.1], [3.1, y0 + 1.55, -5.0],
          paint={"north": ("teeth", dict(n=7, up=False))})
    m.sym(m.decal, "head", "eye", [2.5, y0 + 6.2, -4.66], [2.9, 2.7], ("eye", dict(iris=(190, 60, 200), lid=F, lid_frac=0.28)))
    m.sym(m.cbox, "head", "brow", "dark", [2.5, y0 + 8.0, -4.7], [3.0, 0.7, 0.5], rot=[0, 0, -16])
    for i, (dx, rz) in enumerate(((-1.5, 22), (0, 0), (1.5, -22))):
        m.crbox("head", f"tuft{i}a", "fur", [dx, y0 + 9.6, 0.4], [1.4, 2.4, 1.4], b=0.35, rot=[-12, 0, rz])
        m.cbox("head", f"tuft{i}b", "fur2", [dx * 1.5, y0 + 11.2, 0.1], [0.9, 1.6, 0.9], rot=[-20, 0, rz * 1.5])
    # bib: LET'S EAT!!
    top, bot = N - 0.7, L + 3.6
    m.decal("body", "bib", [0, (top + bot) / 2, -td / 2 - 0.06], [10.4, top - bot],
            [("text", dict(text="LET'S\nEAT!!", bg=(240, 240, 232),
                           colors=[(230, 70, 150), (240, 140, 30), (130, 60, 200), (60, 170, 70), (230, 70, 150),
                                   (50, 120, 220), (240, 140, 30), (130, 60, 200), (60, 170, 70)])),
             ("frame", dict(color=(130, 60, 200), width=2)), ("rounded", dict(r=0.35))], d=8)
    # cupcake on a plate; the "cupcake" bone cancels the forearm tilt
    ax, top_h, s, fore = a["hands"]["left"]
    hx, hyc = ax, top_h - 1.4
    m.bone("cupcake", fore, [hx, hyc, 0], [-75, 0, 0])
    m.crbox("cupcake", "plate", "plate", [hx, hyc + 2.0, 0], [5.4, 0.5, 5.4], b=0.2)
    m.crbox("cupcake", "wrapper", "wrapper", [hx, hyc + 3.2, 0], [2.9, 1.9, 2.9], b=0.3)
    m.crbox("cupcake", "frosting", "frosting", [hx, hyc + 4.6, 0], [3.4, 1.3, 3.4], b=0.5)
    m.crbox("cupcake", "frosting_top", "frosting", [hx, hyc + 5.6, 0], [2.3, 1.0, 2.3], b=0.4)
    m.cbox("cupcake", "candle", "candle", [hx, hyc + 6.8, 0], [0.45, 1.6, 0.45])
    m.cbox("cupcake", "flame", "flame", [hx, hyc + 7.85, 0], [0.55, 0.7, 0.55])
    for i, dx in enumerate((-0.65, 0.65)):
        m.decal("cupcake", f"cake_eye{i}", [hx + dx, hyc + 4.7, -1.76], [1.0, 1.0],
                ("eye", dict(iris=(60, 120, 230), glow=False)), d=10)
    m.decal("cupcake", "cake_teeth", [hx, hyc + 3.6, -1.51], [1.8, 0.6], ("teeth", dict(n=5, pointed=True)), d=10)
    return m, dict(width=0.8, height=2.3, egg=(0xE2BE2A, 0xEE7C1E))


def foxy():
    m = Model("foxy", seed=41, grime=0.6)
    m.mat("fur", (156, 46, 34), kind="fur", noise=9)
    m.mat("fur2", (204, 150, 116), kind="fur", noise=8)
    common(m, metal=(110, 110, 116))
    m.mat("pants", (104, 66, 38), kind="cloth", noise=7)
    m.mat("patch", (16, 14, 14), noise=3)
    m.mat("hook", (196, 196, 202), kind="metal", noise=8, grime=0.2)
    torn = {f: ("torn", dict(depth=1.6)) for f in ("north", "south", "east", "west")}
    P = dict(leg_h=13, leg_w=4.4, hip_x=3.0, foot=2.6, torso=(12.4, 12, 8.4), arm_w=3.4, upper_arm=6.4, forearm=5.4,
             endo_shin=True, thigh_c="pants", pelvis_c="pants", thigh_paint=torn, metal_toes=True,
             right_hand="hook", left_hand="endo", belly="fur2",
             upper_paint={"north": ("stitch", dict(axis="h", at=0.4))})
    a = skeleton(m, P)
    y0, N, L, td = a["y0"], a["N"], a["L"], a["td"]
    F, F2 = m.mats["fur"]["rgb"], m.mats["fur2"]["rgb"]
    m.decal("body", "chest_hole", [-1.6, L + 7.6, -td / 2 - 0.12], [4.2, 4.0], ("hole", dict(bars=2)))
    m.decal("left_forearm", "arm_rip", [a["hands"]["left"][0], L + 4.5, -1.6], [1.8, 2.6], ("hole", dict(bars=1)))
    m.rbox("head", "skull", "fur", [-4.7, y0 + 0.4, -4.5], [4.7, y0 + 8.0, 4.5], b=1.2, paint={"south": ("stitch", {})})
    m.rbox("head", "jowls", "fur", [-5.1, y0, -4.0], [5.1, y0 + 3.4, 3.0], b=0.9)
    m.rbox("head", "snout", "fur", [-2.8, y0 + 2.5, -9.9], [2.8, y0 + 4.9, -4.0], b=0.7)
    m.rbox("head", "snout_low", "fur2", [-2.9, y0 + 1.5, -9.5], [2.9, y0 + 2.9, -4.0], b=0.45)
    m.rbox("head", "nose", "nose", [-1.1, y0 + 3.9, -10.4], [1.1, y0 + 5.0, -9.4], b=0.3, paint={"north": ("nose", {})})
    m.box("head", "mouth", "mouth", [-2.4, y0 + 0.2, -8.9], [2.4, y0 + 1.9, -4.1])
    m.box("head", "teeth_up", "teeth", [-2.5, y0 + 0.75, -9.3], [2.5, y0 + 1.6, -5.2],
          paint={f: ("teeth", dict(n=7 if f == "north" else 6, pointed=True, up=True)) for f in ("north", "east", "west")})
    m.bone("jaw", "head", [0, y0 + 1.0, -3.4], [-10, 0, 0])
    m.rbox("jaw", "jaw", "fur2", [-2.5, y0 - 0.7, -9.4], [2.5, y0 + 0.6, -3.2], b=0.45)
    m.box("jaw", "teeth_down", "teeth", [-2.3, y0 + 0.55, -9.1], [2.3, y0 + 1.35, -5.2],
          paint={f: ("teeth", dict(n=6, pointed=True, up=False)) for f in ("north", "east", "west")})
    m.cbox("jaw", "hinge", "metal", [0, y0 + 0.4, -3.4], [5.4, 1.0, 1.2])
    m.decal("head", "eye_l", [2.2, y0 + 5.5, -4.56], [2.5, 2.2], ("eye", dict(iris=(250, 205, 40), lid=F, lid_frac=0.25)))
    m.decal("head", "eyepatch", [-2.2, y0 + 5.5, -4.6], [2.9, 2.6], ("oval", dict(color=(16, 14, 14), rim=(40, 36, 36))))
    m.cbox("head", "patch_strap", "patch", [0, y0 + 6.6, 0], [9.7, 0.55, 9.3], rot=[0, 0, -16])
    m.sym(m.cbox, "head", "brow", "dark", [2.2, y0 + 7.0, -4.62], [2.6, 0.6, 0.4], rot=[0, 0, -18])
    m.sym(m.crbox, "head", "ear", "fur", [3.1, y0 + 8.6, 0.4], [2.8, 2.6, 1.5], b=0.5, rot=[0, 0, -14])
    m.sym(m.cbox, "head", "ear_tip", "fur", [3.55, y0 + 10.6, 0.4], [1.5, 2.0, 1.2], rot=[0, 0, -14], origin=[3.1, y0 + 8.6, 0.4])
    m.sym(m.decal, "head", "ear_in", [3.15, y0 + 8.9, -0.4], [1.5, 2.6], ("oval", dict(color=F2)),
          rot=[0, 0, -14], origin=[3.1, y0 + 8.6, 0.4])
    # hook
    ax, top, s, fore = a["hands"]["right"]
    m.crbox(fore, "hook_cuff", "metal", [ax, top - 0.4, 0], [3.0, 1.6, 3.0], b=0.4, paint={"north": ("rivets", {})})
    m.cbox(fore, "hook_shaft", "hook", [ax, top - 3.0, 0], [0.8, 3.8, 0.8])
    m.cbox(fore, "hook_bend", "hook", [ax, top - 5.0, -0.95], [0.8, 0.8, 2.7])
    m.cbox(fore, "hook_up", "hook", [ax, top - 4.1, -2.1], [0.8, 2.2, 0.8], rot=[-12, 0, 0])
    m.cbox(fore, "hook_tip", "hook", [ax, top - 2.8, -2.5], [0.6, 1.0, 0.6], rot=[-35, 0, 0])
    return m, dict(width=0.8, height=2.4, egg=(0x9C2E22, 0xCC9674))


def springtrap():
    m = Model("springtrap", seed=51, grime=0.9)
    m.mat("fur", (112, 118, 60), kind="fur", noise=10)
    m.mat("fur2", (142, 140, 86), kind="fur", noise=9)
    common(m, metal=(102, 98, 90))
    m.mat("teeth", (205, 196, 150), noise=5)
    m.mat("nose", (90, 70, 50), noise=4, shade=0.2)
    P = dict(leg_h=13, leg_w=4.6, hip_x=3.1, foot=2.8, torso=(13.0, 12.5, 8.8), arm_w=3.6, upper_arm=6.4, forearm=5.4,
             body_rot=[-8, 0, 0], head_rot=[-6, 0, -6], left_hand="endo", belly="fur2",
             thigh_paint={"north": ("stitch", dict(axis="h", at=0.5))})
    a = skeleton(m, P)
    y0, N, L, td, tw = a["y0"], a["N"], a["L"], a["td"], a["tw"]
    rabbit_head(m, a, sockets=True, broken_ear=True, pin=(235, 235, 210))
    m.by_name["jaw"]["rot"] = [-14, 0, 0]
    m.box("head", "endo_teeth", "metal", [-2.6, y0 + 0.5, -6.6], [2.6, y0 + 1.1, -4.4],
          paint={"north": ("teeth", dict(n=6, color=(170, 170, 176), yellow=0))})
    m.decal("body", "chest_hole", [-0.8, L + 7.4, -td / 2 - 0.12], [6.4, 5.6], ("hole", dict(bars=3)))
    m.decal("body", "side_hole", [tw / 2 + 0.08, L + 5.0, 0], [3.0, 2.6], ("hole", dict(bars=1)), face="east")
    m.decal("head", "cheek_hole", [3.4, y0 + 2.4, -4.28], [1.8, 1.6], ("hole", dict(bars=1, wires=[])))
    m.decal("left_leg", "leg_hole", [3.1, 8.0, -2.4], [2.4, 3.2], ("hole", dict(bars=2)))
    m.decal("right_arm", "arm_hole", [m.by_name["right_arm"]["pivot"][0], N - 5.0, -1.88], [1.9, 2.6], ("hole", dict(bars=1)))
    for i, (x, rz, ln, mat) in enumerate(((-1.4, 18, 4.0, "wire_r"), (1.0, -26, 3.2, "wire_b"), (2.4, 10, 2.6, "wire_r"))):
        m.cbox("body", f"wire{i}", mat, [x, L + 3.6 - ln / 2 + 2.0, -td / 2 - 0.3], [0.35, ln, 0.35], rot=[8, 0, rz])
    return m, dict(width=0.8, height=2.5, egg=(0x70763C, 0x40381E))


def balloon_boy():
    m = Model("balloon_boy", seed=61, grime=0.05)
    common(m)
    m.mat("skin", (238, 204, 172), noise=4, grime=0, shade=0.1)
    m.mat("hair", (96, 58, 32), kind="fur", noise=6)
    m.mat("shirt", (206, 40, 40), kind="cloth", pattern="stripes_h", rgb2=(40, 70, 190), period=0.9, noise=4)
    m.mat("pants", (44, 70, 182), kind="cloth", noise=5)
    m.mat("shoe", (92, 56, 30), noise=5, shade=0.2)
    m.mat("laces", (230, 230, 230), noise=2)
    m.mat("hat", (210, 40, 40), pattern="stripes_v", rgb2=(40, 80, 200), period=1.8, noise=4, shade=0.18)
    m.mat("prop", (245, 210, 40), noise=4)
    m.mat("balloon", (230, 40, 40), pattern="stripes_v", rgb2=(245, 215, 40), period=0.9, noise=3, grime=0, shade=0.2)
    m.mat("string", (40, 40, 40), noise=2)
    m.mat("button", (245, 245, 245), noise=2, grime=0)
    m.mat("sign", (240, 240, 230), noise=3, grime=0)
    m.mat("stick", (120, 80, 40), kind="fur", noise=5)
    P = dict(leg_h=6, leg_w=3.4, hip_x=2.0, foot=1.6, torso=(9.4, 7, 6.4), arm_w=2.6, upper_arm=3.2, forearm=2.8,
             thigh_c="pants", shin_c="pants", foot_c="shoe", foot_style="shoe", pelvis_c="pants", chest_c="shirt",
             upper_c="shirt", fore_c="skin", hand_c="skin", neck=0.8, chest_paint={}, chest_bevel=1.2)
    a = skeleton(m, P)
    y0, N, td = a["y0"] - 0.6, a["N"], a["td"]
    for i in range(2):
        m.crbox("body", f"button{i}", "button", [0, N - 2.2 - i * 2.4, -td / 2 - 0.15], [1.0, 1.0, 0.4], b=0.2)
    m.rbox("head", "skull", "skin", [-5.6, y0, -5.1], [5.6, y0 + 10.2, 5.1], b=1.6)
    m.rbox("head", "hair", "hair", [-5.8, y0 + 6.4, -1.5], [5.8, y0 + 9.4, 5.3], b=0.8)
    m.sym(m.decal, "head", "eye", [2.4, y0 + 5.6, -5.16], [3.0, 3.1], ("eye", dict(iris=(60, 120, 230), iris_r=0.3, look=0)))
    m.sym(m.cbox, "head", "brow", "hair", [2.4, y0 + 7.6, -5.15], [2.4, 0.5, 0.3], rot=[0, 0, 8])
    m.sym(m.decal, "head", "cheek", [3.7, y0 + 3.3, -5.12], [1.8, 1.1], ("oval", dict(color=(240, 140, 140), noise=2)))
    m.crbox("head", "nose", "skin", [0, y0 + 4.3, -5.45], [1.1, 1.0, 0.8], b=0.3)
    m.decal("head", "smile", [0, y0 + 2.2, -5.16], [5.0, 2.2], ("smile", {}))
    m.bone("jaw", "head", [0, y0 + 1.2, -3.0])
    m.rbox("jaw", "jaw", "skin", [-3.2, y0 - 0.2, -5.25], [3.2, y0 + 1.2, -2.0], b=0.4)
    m.rbox("head", "hat", "hat", [-5.9, y0 + 8.4, -5.4], [5.9, y0 + 11.8, 5.4], b=1.4)
    m.crbox("head", "hat_brim", "hat", [0, y0 + 8.6, -5.4], [6.4, 0.6, 1.6], b=0.2)
    m.crbox("head", "prop_button", "prop", [0, y0 + 12.1, 0], [1.4, 0.8, 1.4], b=0.3)
    m.cbox("head", "prop_stem", "prop", [0, y0 + 12.9, 0], [0.6, 1.4, 0.6])
    m.cbox("head", "prop_blade1", "prop", [0, y0 + 13.6, 0], [8.0, 0.3, 1.2], rot=[0, 30, 0])
    m.cbox("head", "prop_blade2", "prop", [0, y0 + 13.6, 0], [8.0, 0.3, 1.2], rot=[0, -60, 0])
    # balloon and sign
    ax, top, s, fore = a["hands"]["right"]
    m.cbox(fore, "string", "string", [ax - 1.75, top + 7.6, -1.6], [0.25, 17.4, 0.25], rot=[0, 0, 12])
    m.crbox(fore, "balloon_tie", "balloon", [ax - 3.5, top + 16.4, -1.6], [1.0, 0.9, 1.0], b=0.2)
    m.crbox(fore, "balloon", "balloon", [ax - 3.5, top + 20.0, -1.6], [5.6, 6.4, 5.6], b=1.6)
    ax, top, s, fore = a["hands"]["left"]
    m.cbox(fore, "sign_stick", "stick", [ax, top + 1.0, -2.4], [0.5, 9.0, 0.5])
    m.crbox(fore, "sign", "sign", [ax, top + 6.6, -2.8], [7.4, 3.8, 0.5], b=0.2,
            paint={"north": [("text", dict(text="BALLOONS!", colors=[(220, 40, 40), (40, 80, 200), (230, 170, 20)])),
                             ("frame", dict(color=(220, 40, 40)))]}, d=7)
    return m, dict(width=0.6, height=1.6, egg=(0xCE2828, 0x2C46B6))


def puppet():
    m = Model("puppet", seed=71, grime=0.1)
    common(m)
    m.mat("black", (22, 22, 26), kind="cloth", noise=4)
    m.mat("stripe", (232, 232, 232), pattern="stripes_h", rgb2=(22, 22, 26), period=0.8, noise=3)
    m.mat("mask", (242, 242, 240), noise=3, grime=0, shade=0.1)
    m.mat("button", (240, 240, 240), noise=2, grime=0)
    P = dict(leg_h=18, leg_w=2.6, hip_x=2.0, foot=1.0, torso=(7.6, 13, 5.2), arm_w=2.2, upper_arm=8.5, forearm=8.0,
             thigh_c="black", shin_c="black", foot_c="black", pelvis_c="black", chest_c="black", upper_c="black",
             fore_c="black", hand_c="black", right_hand="puppet", left_hand="puppet", neck=2.8, chest_paint={},
             chest_bevel=1.0)
    a = skeleton(m, P)
    y0, N, td = a["y0"], a["N"], a["td"]
    for side, s in (("right", -1), ("left", 1)):
        ax, top, _, fore = a["hands"][side]
        m.cbox(fore, "cuff", "stripe", [ax, top + 2.0, 0], [2.3, 3.6, 2.3])
        m.cbox(f"{side}_leg", "ankle_cuff", "stripe", [s * 2.0, 3.8, 0], [2.4, 3.6, 2.4])
    for i in range(3):
        m.crbox("body", f"button{i}", "button", [0, N - 3.2 - i * 2.8, -td / 2 - 0.15], [1.1, 1.1, 0.4], b=0.25)
    m.rbox("head", "skull", "black", [-3.5, y0, -3.3], [3.5, y0 + 8.8, 3.3], b=0.9)
    m.rbox("head", "mask", "mask", [-3.3, y0 + 0.2, -3.9], [3.3, y0 + 8.4, -2.9], b=0.5, paint={"north": ("mask", {})}, d=9)
    m.bone("jaw", "head", [0, y0 + 0.5, -2.0])
    m.rbox("jaw", "jaw", "mask", [-1.7, y0 - 0.4, -3.9], [1.7, y0 + 0.5, -2.2], b=0.3)
    return m, dict(width=0.6, height=2.7, egg=(0x16161A, 0xE8E8E8))


def endoskeleton():
    m = Model("endoskeleton", seed=81, grime=0.4)
    common(m, metal=(122, 122, 128))
    m.mat("eyeball", (236, 236, 230), noise=3, grime=0)
    P = dict(style="endo", leg_h=13, leg_w=2.2, hip_x=2.7, foot=2.4, torso=(8.6, 11, 4.6), arm_w=1.9, upper_arm=6.4,
             forearm=5.8, foot_style="endo")
    a = skeleton(m, P)
    y0, N, L, td = a["y0"], a["N"], a["L"], a["td"]
    m.cbox("body", "wire0", "wire_r", [1.6, L + 6, -td / 2 - 0.3], [0.35, 7, 0.35], rot=[0, 0, 12])
    m.cbox("body", "wire1", "wire_b", [-1.4, L + 5.5, -td / 2 - 0.3], [0.35, 6, 0.35], rot=[0, 0, -15])
    m.crbox("body", "power", "metal_dark", [0, L + 3.0, -0.3], [3.2, 2.4, 2.6], b=0.4, paint={"north": ("rivets", {})})
    m.rbox("head", "skull", "metal", [-4.3, y0 + 2.2, -3.6], [4.3, y0 + 8.2, 4.2], b=1.0, paint={"north": ("rivets", {})})
    m.rbox("head", "cranium", "metal_dark", [-3.6, y0 + 7.6, -2.6], [3.6, y0 + 9.0, 3.4], b=0.6)
    m.rbox("head", "faceplate", "metal_dark", [-3.8, y0 + 3.6, -4.3], [3.8, y0 + 7.6, -3.4], b=0.4)
    m.sym(m.crbox, "head", "eyeball", "eyeball", [2.0, y0 + 5.6, -4.5], [2.4, 2.4, 1.6], b=0.5)
    m.sym(m.decal, "head", "eye", [2.0, y0 + 5.6, -5.36], [1.9, 1.9], ("eye", dict(iris=(235, 30, 30), iris_r=0.3)))
    m.sym(m.cbox, "head", "lid", "metal", [2.0, y0 + 6.95, -4.6], [2.6, 0.6, 1.8], rot=[-10, 0, 0])
    m.box("head", "teeth_up", "teeth", [-3.0, y0 + 2.0, -5.5], [3.0, y0 + 3.1, -3.0],
          paint={"north": ("teeth", dict(n=7, color=(225, 225, 220), yellow=0.1))})
    m.box("head", "mouth", "mouth", [-2.9, y0 + 0.6, -5.0], [2.9, y0 + 2.4, -2.6])
    m.sym(m.cbox, "head", "ear_post", "metal_dark", [3.3, y0 + 9.4, 0.4], [1.0, 2.8, 1.0])
    m.sym(m.crbox, "head", "ear_disc", "metal", [3.3, y0 + 11.0, 0.4], [2.2, 2.2, 0.6], b=0.4)
    m.bone("jaw", "head", [0, y0 + 1.6, -1.0])
    m.rbox("jaw", "jaw", "metal", [-3.5, y0 - 0.1, -5.7], [3.5, y0 + 1.1, -0.4], b=0.4)
    m.box("jaw", "teeth_down", "teeth", [-3.0, y0 + 1.0, -5.5], [3.0, y0 + 2.0, -3.0],
          paint={"north": ("teeth", dict(n=7, up=False, color=(225, 225, 220), yellow=0.1))})
    m.sym(m.cbox, "jaw", "hinge", "metal_dark", [3.7, y0 + 1.5, -1.0], [0.8, 1.8, 1.8])
    m.sym(m.cbox, "jaw", "piston", "chrome", [3.4, y0 + 3.0, -2.0], [0.4, 2.6, 0.4], rot=[20, 0, 0])
    return m, dict(width=0.7, height=2.3, egg=(0x76767C, 0xEB1E1E))


CHARACTERS = [freddy, bonnie, chica, foxy, golden_freddy, springtrap, balloon_boy, puppet, endoskeleton]


# =====================================================================
# Animations (shared bone names). Values follow Blockbench keyframe
# convention as written here: negative X swings a limb forward/up (flipped below).
# =====================================================================

def animations(name):
    kf = {}

    def k(anim, bone, ch, pts):
        kf.setdefault(anim, {}).setdefault(bone, {})[ch] = pts

    swing = 18 if name != "puppet" else 10
    leg = 26 if name != "balloon_boy" else 34

    # idle: slow mechanical breathing + head twitches
    k("idle", "head", "rotation", {0: [0, 0, 0], 1.0: [2, 9, -3], 1.9: [2, 9, -3], 2.0: [0, 0, 0], 3.0: [-2, -7, 3], 4.0: [0, 0, 0]})
    k("idle", "jaw", "rotation", {0: [0, 0, 0], 2.4: [0, 0, 0], 2.5: [10, 0, 0], 2.7: [0, 0, 0], 4.0: [0, 0, 0]})
    k("idle", "body", "rotation", {0: [0, 0, 0], 2.0: [1.5, 0, 0], 4.0: [0, 0, 0]})
    k("idle", "right_arm", "rotation", {0: [0, 0, 0], 2.0: [-3, 0, 2], 4.0: [0, 0, 0]})
    k("idle", "left_arm", "rotation", {0: [0, 0, 0], 2.0: [-3, 0, -2], 4.0: [0, 0, 0]})

    # walk: stiff, heavy steps
    k("walk", "right_leg", "rotation", {0: [leg, 0, 0], 0.6: [-leg, 0, 0], 1.2: [leg, 0, 0]})
    k("walk", "left_leg", "rotation", {0: [-leg, 0, 0], 0.6: [leg, 0, 0], 1.2: [-leg, 0, 0]})
    k("walk", "right_arm", "rotation", {0: [-swing, 0, 0], 0.6: [swing, 0, 0], 1.2: [-swing, 0, 0]})
    k("walk", "left_arm", "rotation", {0: [swing, 0, 0], 0.6: [-swing, 0, 0], 1.2: [swing, 0, 0]})
    k("walk", "body", "rotation", {0: [3, 0, 2], 0.6: [3, 0, -2], 1.2: [3, 0, 2]})
    k("walk", "body", "position", {0: [0, 0, 0], 0.3: [0, 0.6, 0], 0.6: [0, 0, 0], 0.9: [0, 0.6, 0], 1.2: [0, 0, 0]})
    k("walk", "head", "rotation", {0: [0, 0, 0], 0.3: [0, 5, 2], 0.6: [0, 0, 0], 0.9: [0, -5, -2], 1.2: [0, 0, 0]})

    # attack: lunge, both arms grab, jaw snaps open
    k("attack", "right_arm", "rotation", {0: [0, 0, 0], 0.2: [-140, 0, -10], 0.45: [-70, 0, 0], 0.7: [0, 0, 0]})
    k("attack", "left_arm", "rotation", {0: [0, 0, 0], 0.25: [-140, 0, 10], 0.5: [-70, 0, 0], 0.7: [0, 0, 0]})
    k("attack", "jaw", "rotation", {0: [0, 0, 0], 0.15: [32, 0, 0], 0.5: [32, 0, 0], 0.7: [0, 0, 0]})
    k("attack", "head", "rotation", {0: [0, 0, 0], 0.2: [-12, 0, 0], 0.45: [10, 0, 0], 0.7: [0, 0, 0]})
    k("attack", "body", "rotation", {0: [0, 0, 0], 0.45: [14, 0, 0], 0.7: [0, 0, 0]})

    # Blockbench/GeckoLib preview swings limbs forward with positive X: flip the authored values
    for bones in kf.values():
        for chans in bones.values():
            if "rotation" in chans:
                chans["rotation"] = {t: [-v[0], v[1], v[2]] for t, v in chans["rotation"].items()}

    meta = {"idle": dict(loop="loop", length=4.0), "walk": dict(loop="loop", length=1.2),
            "attack": dict(loop="once", length=0.7)}
    return kf, meta
