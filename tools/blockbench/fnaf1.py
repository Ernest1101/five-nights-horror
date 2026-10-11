"""The five FNAF 1 animatronics, game-accurate, in clean 16x Minecraft style.

One texel per model pixel, integer-ish boxes, mottled fur and pixel-art faces, but no ragged
fur flaps: shapes follow the FNAF 1 designs (big heads with jowls and separate snout/jaw,
heavy torsos with light bellies, segmented limbs with endoskeleton joints).
Shared skeleton/helpers come from fnaf_mc; bone names match the mod's animations.
"""
from bbmodel_kit import Model
from fnaf_mc import K, W, TOOTH, base_mats, pix, fit, body, bowtie
from fnaf_mc import animations  # noqa: F401  (re-exported for build_models)

T = {"T": TOOTH}


def eyebrows(m, y, z, x=3.4, w=4.0, tilt=12, mat="black"):
    for s in (1, -1):
        m.box("head", f"eyebrow{s}", mat, [s * x - w / 2, y, z - 0.6], [s * x + w / 2, y + 1, z], rot=[0, 0, -s * tilt],
              origin=[s * x, y + 0.5, z - 0.3])


def snout_and_jaw(m, y0, mat, width=7, front=-7.5, nose=None, freckles=None, teeth=8, jaw_mat=None):
    """Upper snout with nose, upper teeth, dark mouth, and a hinged lower jaw with teeth."""
    hw = width / 2
    m.box("head", "snout", mat, [-hw, y0 + 1, front], [hw, y0 + 4, -5], paint={"north": freckles} if freckles else None)
    if nose:
        m.box("head", "nose", nose, [-1.5, y0 + 3, front - 0.6], [1.5, y0 + 4.3, front + 0.6])
    m.box("head", "mouth", "mouth", [-hw + 0.5, y0 - 0.5, front + 0.5], [hw - 0.5, y0 + 1, -5])
    m.box("head", "teeth_up", "teeth", [-hw + 0.3, y0 + 0.2, front - 0.1], [hw - 0.3, y0 + 1.1, front + 0.5],
          paint={"north": pix(["T" * teeth], T, flat="T")})
    m.bone("jaw", "head", [0, y0 + 0.5, -3])
    m.box("jaw", "jaw", jaw_mat or mat, [-hw + 0.2, y0 - 1.8, front + 0.2], [hw - 0.2, y0 + 0.2, -3])
    m.box("jaw", "teeth_dn", "teeth", [-hw + 0.6, y0 - 0.3, front + 0.1], [hw - 0.6, y0 + 0.5, front + 0.7],
          paint={"north": pix(["T" * (teeth - 1)], T, flat="T")})


# ====================================================================== Freddy / Golden Freddy

def freddy(name="freddy", golden=False):
    m = Model(name, seed=11 if not golden else 12, density=1)
    if golden:
        base_mats(m, (210, 172, 40), (224, 192, 80))
    else:
        base_mats(m, (122, 70, 32), (196, 140, 88))
    m.mat("mic", (36, 36, 40), kind="mc")
    m.mat("mic_head", (156, 156, 162), kind="mc")
    P = dict(lw=5.5, ld=5.5, hx=3.4, shin=4, thigh=5, tw=14, td=9, pelvis=3, chest=10, aw=4.5, ua=5, fa=4, belly="fur2",
             fringe=False)
    if golden:
        P.update(head_rot=[6, 0, 9])
    else:
        P.update(right_forearm_rot=[38, 0, 0])
    a = body(m, P)
    y0, L, td = a["y0"], a["L"], a["td"]
    bowtie(m, a, "black")
    lid = m.mats["fur_dk"]["rgb"]
    if golden:
        eyes = ["", "", "..LLL.LLL..", "..KKK.KKK..", "..KWK.KWK.."]
    else:
        eyes = ["", "", "..LLL.LLL..", "..WBW.WBW..", "..WWW.WWW.."]
    m.box("head", "skull", "fur", [-5.5, y0, -5], [5.5, y0 + 9, 5],
          paint={"north": pix(fit(eyes, 11, 9), {"K": K, "W": W, "B": (56, 118, 232), "L": lid}, glow="W" if golden else "B")})
    m.box("head", "jowls", "fur", [-6, y0 - 0.5, -4.5], [6, y0 + 3.5, 3])
    m.box("head", "crown", "fur", [-4.5, y0 + 9, -4], [4.5, y0 + 9.8, 4])
    eyebrows(m, y0 + 7.2, -5, x=2.9, w=3.6, tilt=10)
    dk = tuple(int(v * 0.45) for v in m.mats["fur"]["rgb"])
    snout_and_jaw(m, y0, "fur2", width=7, front=-7.5, nose="black",
                  freckles=pix([".......", "d.....d", ".d...d.", "......."], {"d": dk}, flat="d"))
    for s in (1, -1):
        m.box("head", f"ear{s}", "fur", [s * 4.6 - 1.8, y0 + 8.2, -1], [s * 4.6 + 1.8, y0 + 11.8, 1])
        m.box("head", f"ear_in{s}", "fur_dk" if golden else "fur2", [s * 4.6 - 1, y0 + 8.8, -1.4], [s * 4.6 + 1, y0 + 11, -1])
    m.box("head", "hat_brim", "black", [-3, y0 + 9.8, -3], [3, y0 + 10.6, 3])
    m.box("head", "hat_top", "black", [-2.2, y0 + 10.6, -2.2], [2.2, y0 + 14, 2.2])
    if golden:
        m.decal("body", "tear", [3.4, L + 7, -td / 2 - 0.06], [2.5, 2.5], ("hole", dict(bars=1)))
        m.decal("head", "head_tear", [-4, y0 + 2, -5.06], [1.8, 1.8], ("hole", dict(bars=0)))
    else:
        ax, top, s, fore = a["hands"]["right"]
        m.bone("mic", fore, [ax, top, 0], [-38, 0, 0])
        m.box("mic", "mic_handle", "mic", [ax - 0.6, top - 4, -3.2], [ax + 0.6, top + 1.5, -2])
        m.box("mic", "mic_ring", "endo_l", [ax - 0.9, top + 1.5, -3.5], [ax + 0.9, top + 2.1, -1.7])
        m.box("mic", "mic_head", "mic_head", [ax - 1.2, top + 2.1, -3.8], [ax + 1.2, top + 4.4, -1.4],
              paint={f: pix(["g.g", ".g.", "g.g"], {"g": (70, 70, 74)}, flat="g") for f in ("north", "south", "east", "west")})
    return m, dict(width=0.9, height=2.4, egg=(0x7A4620, 0x1A1A1A) if not golden else (0xD2AC28, 0x1E1C1E))


def golden_freddy():
    return freddy("golden_freddy", golden=True)


# ====================================================================== Bonnie

def bonnie():
    m = Model("bonnie", seed=21, density=1)
    base_mats(m, (92, 80, 186), (170, 178, 232))
    m.mat("guitar", (200, 28, 32), kind="mc")
    m.mat("neck", (40, 26, 20), kind="mc")
    P = dict(lw=5.5, ld=5.5, hx=3.4, shin=4, thigh=5, tw=14, td=9, pelvis=3, chest=10, aw=4.5, ua=5, fa=4, belly="fur2",
             fringe=False, right_forearm_rot=[55, 0, -12], left_forearm_rot=[70, 0, 20], left_arm_rot=[12, 0, 0])
    a = body(m, P)
    y0, L, td = a["y0"], a["L"], a["td"]
    bowtie(m, a, "red")
    lid = m.mats["fur_dk"]["rgb"]
    m.box("head", "skull", "fur", [-5.5, y0, -5], [5.5, y0 + 9, 5],
          paint={"north": pix(fit(["", "", "..LLL.LLL..", "..WPW.WPW..", "..WWW.WWW.."], 11, 9),
                              {"W": W, "P": (222, 40, 150), "L": lid}, glow="P")})
    m.box("head", "jowls", "fur", [-6, y0 - 0.5, -4.5], [6, y0 + 3.5, 3])
    eyebrows(m, y0 + 7.2, -5, x=2.9, w=3.6, tilt=8)
    snout_and_jaw(m, y0, "fur2", width=8, front=-7.5, nose="nose")
    m.mat("nose", (60, 36, 86), kind="mc")
    inner = m.mats["fur2"]["rgb"]
    for side, s in (("left", 1), ("right", -1)):
        bn = f"{side}_ear"
        m.bone(bn, "head", [s * 2.6, y0 + 9, 0], [-4, 0, -6 * s])
        m.box(bn, "ear_post", "endo", [s * 2.6 - 0.5, y0 + 8.5, -0.5], [s * 2.6 + 0.5, y0 + 10.5, 0.5])
        m.box(bn, "ear", "fur", [s * 2.6 - 1.8, y0 + 10.5, -0.9], [s * 2.6 + 1.8, y0 + 21, 0.9],
              paint={"north": pix(["fff"] + ["fbf"] * 8 + ["fff"], {"b": inner, "f": m.mats["fur"]["rgb"]}, flat="")})
    # red guitar held across the body
    gc = [-1.5, L + 6, -td / 2 - 2.5]
    rot = [0, 0, 36]

    def g(nm, mat, f, t, paint=None):
        m.box("body", nm, mat, [gc[0] + f[0], gc[1] + f[1], gc[2] + f[2]], [gc[0] + t[0], gc[1] + t[1], gc[2] + t[2]],
              rot=rot, origin=gc, paint=paint)

    g("g_body", "guitar", [-3, -3.5, -0.75], [3, 2.5, 0.75], paint={"north": pix(["......", "......", "..KK..", "..KK..", "......", ".WWWW."],
                                                                            {"K": K, "W": W}, flat="KW")})
    g("g_horn", "guitar", [-3.5, 0.5, -0.75], [-2.5, 3.5, 0.75])
    g("g_neck", "neck", [-0.6, 2.5, -0.6], [0.6, 15, 0.6], paint={"north": pix(["W", "K"] * 6, {"K": (40, 26, 20), "W": (220, 220, 210)}, flat="KW")})
    g("g_head", "guitar", [-1.2, 15, -0.6], [1.2, 18, 0.6])
    return m, dict(width=0.9, height=2.8, egg=(0x5C50BA, 0xC81C20))


# ====================================================================== Chica

def chica():
    m = Model("chica", seed=31, density=1)
    base_mats(m, (236, 204, 42), (248, 226, 96))
    m.mat("beak", (240, 128, 24), kind="mc")
    m.mat("leg_o", (236, 116, 26), kind="mc")
    m.mat("claw", (232, 232, 226), kind="mc")
    m.mat("bib", (242, 242, 238), kind="mc")
    m.mat("plate", (228, 236, 240), kind="mc")
    m.mat("cake", (214, 110, 50), kind="mc", pattern="stripes_v", rgb2=(240, 160, 90), period=1.0)
    m.mat("frosting", (238, 90, 150), kind="mc")
    m.mat("candle", (246, 226, 90), kind="mc")
    m.mat("flame", (255, 170, 40), kind="mc", glow=True)
    P = dict(lw=5.5, ld=5.5, hx=3.4, shin=4, thigh=5, tw=14, td=9.5, pelvis=3, chest=10, aw=4.5, ua=5, fa=4, fringe=False,
             shin_c="leg_o", foot_c="leg_o", foot_style="bird", left_forearm_rot=[78, 0, 6])
    a = body(m, P)
    y0, N, L, td = a["y0"], a["N"], a["L"], a["td"]
    m.box("head", "skull", "fur", [-5.5, y0, -5], [5.5, y0 + 10, 5],
          paint={"north": pix(fit(["", "", "", ".KKKK.KKKK.", ".KWPK.KPWK.", ".KWPK.KPWK.", "..KK...KK.."], 11, 10),
                              {"K": K, "W": W, "P": (190, 70, 210)}, glow="P")})
    m.box("head", "jowls", "fur", [-6, y0 - 0.5, -4.5], [6, y0 + 3.5, 3])
    eyebrows(m, y0 + 7.4, -5, x=3.0, w=4.2, tilt=-16)
    # beak: wide upper beak with teeth, hinged lower beak
    m.box("head", "beak", "beak", [-3.5, y0 + 1.5, -9], [3.5, y0 + 4, -5])
    m.box("head", "beak_tip", "beak", [-2.5, y0 + 2, -10], [2.5, y0 + 3.5, -9])
    m.box("head", "mouth", "mouth", [-3, y0 + 0.2, -8.5], [3, y0 + 1.6, -5])
    m.box("head", "teeth_up", "teeth", [-3.2, y0 + 0.9, -9.1], [3.2, y0 + 1.7, -8.5], paint={"north": pix(["TTTTTTT"], T, flat="T")})
    m.bone("jaw", "head", [0, y0 + 1, -3.5])
    m.box("jaw", "jaw", "beak", [-3, y0 - 1, -9], [3, y0 + 0.4, -3.5])
    m.box("jaw", "teeth_dn", "teeth", [-2.8, y0 + 0.2, -8.9], [2.8, y0 + 0.9, -8.3], paint={"north": pix(["TTTTTT"], T, flat="T")})
    for i, (x, rz, hh) in enumerate(((-1.4, 22, 3), (0, 0, 4), (1.4, -22, 3))):
        m.box("head", f"tuft{i}", "fur2", [x - 0.6, y0 + 10, -0.6], [x + 0.6, y0 + 10 + hh, 0.6], rot=[-10, 0, rz], origin=[x, y0 + 10, 0])
    m.box("body", "bib", "bib", [-5.5, L + 3.5, -td / 2 - 0.5], [5.5, N - 0.5, -td / 2], d=3,
          paint={"north": [("text", dict(text="LET'S\nEAT!!", bg=(242, 242, 238),
                                         colors=[(150, 60, 200), (240, 170, 20), (60, 170, 230), (230, 70, 150), (90, 180, 70)])),
                           ("frame", dict(color=(150, 60, 200), width=1))]})
    ax, top = a["hands"]["left"][0], a["hands"]["left"][1]
    hx, hyc = ax, top - 1.5
    m.bone("cupcake", "left_forearm", [hx, hyc, 0], [-78, 0, -6])
    m.box("cupcake", "plate", "plate", [hx - 3.5, hyc + 1.5, -3.5], [hx + 3.5, hyc + 2.2, 3.5])
    m.box("cupcake", "cake", "cake", [hx - 2.5, hyc + 2.2, -2.5], [hx + 2.5, hyc + 4.5, 2.5])
    m.box("cupcake", "frosting", "frosting", [hx - 3, hyc + 4.5, -3], [hx + 3, hyc + 7.5, 3],
          paint={"north": pix(["......", "WK..KW", "......"], {"K": K, "W": W}, flat="WK")})
    m.box("cupcake", "frosting_top", "frosting", [hx - 1.8, hyc + 7.5, -1.8], [hx + 1.8, hyc + 8.5, 1.8])
    m.box("cupcake", "candle", "candle", [hx - 0.5, hyc + 8.5, -0.5], [hx + 0.5, hyc + 10.5, 0.5])
    m.box("cupcake", "flame", "flame", [hx - 0.5, hyc + 10.5, -0.5], [hx + 0.5, hyc + 11.5, 0.5])
    return m, dict(width=0.9, height=2.4, egg=(0xECCC2A, 0xF0801A))


# ====================================================================== Foxy

def foxy():
    m = Model("foxy", seed=41, density=1, grime=0.4)
    base_mats(m, (172, 42, 32), (214, 156, 126))
    m.mat("pants", (112, 64, 32), kind="mc")
    m.mat("hook", (180, 180, 184), kind="mc")
    m.mat("inner", (96, 20, 18), kind="mc")
    torn = {f: pix(["...."] * 4 + ["  . ", " .  "], {}) for f in ("north", "south", "east", "west")}
    P = dict(lw=4.5, ld=4.5, hx=2.8, shin=5, thigh=5, tw=12, td=8, pelvis=3, chest=9, aw=3.5, ua=5, fa=4, belly="fur2",
             fringe=False, thigh_c="pants", pelvis_c="pants", thigh_paint=torn, endo_shin=True, foot_style="endo",
             right_hand="none", left_hand="endo", left_fore_endo=True, right_forearm_rot=[25, 0, 0])
    a = body(m, P)
    y0, N, L, td, tw = a["y0"], a["N"], a["L"], a["td"], a["tw"]
    lid = m.mats["fur_dk"]["rgb"]
    m.box("head", "skull", "fur", [-4.5, y0, -4.5], [4.5, y0 + 8, 4.5],
          paint={"north": pix(fit(["", "", "", "......LL.", "......WYK", "......WYK"], 9, 8),
                              {"K": K, "W": W, "Y": (250, 206, 30), "L": lid}, glow="Y")})
    m.box("head", "jowls", "fur", [-5, y0 - 0.5, -4], [5, y0 + 3, 2.5])
    m.box("head", "patch", "black", [0.8, y0 + 3.6, -5.1], [3.8, y0 + 6.4, -4.5])
    m.box("head", "patch_strap", "black", [-4.8, y0 + 5.4, -4.7], [4.8, y0 + 6.2, 4.7], rot=[0, 0, -12], origin=[0, y0 + 5.8, 0])
    eyebrows(m, y0 + 6.6, -4.5, x=2.4, w=3.2, tilt=14)
    # long fox snout: red top, tan underside, lots of teeth
    m.box("head", "snout", "fur", [-2.3, y0 + 1.3, -9.5], [2.3, y0 + 3.8, -4.5], paint={"down": pix(["tttt"], {"t": m.mats["fur2"]["rgb"]})})
    m.box("head", "nose", "black", [-1.2, y0 + 3, -10.1], [1.2, y0 + 4.2, -9.1])
    m.box("head", "mouth", "mouth", [-2, y0 + 0.2, -9], [2, y0 + 1.4, -4.5])
    m.box("head", "teeth_up", "teeth", [-2.1, y0 + 0.6, -9.6], [2.1, y0 + 1.5, -9], paint={"north": pix(["TTTTT"], T, flat="T")})
    m.box("head", "teeth_side", "teeth", [-2.2, y0 + 0.6, -9], [2.2, y0 + 1.4, -6], paint={f: pix(["TTTT"], T, flat="T") for f in ("east", "west")})
    m.bone("jaw", "head", [0, y0 + 0.4, -3.5], [-14, 0, 0])
    m.box("jaw", "jaw", "fur2", [-2.2, y0 - 1.4, -9], [2.2, y0 + 0.3, -3.5])
    m.box("jaw", "teeth_dn", "teeth", [-2, y0 - 0.1, -8.8], [2, y0 + 0.7, -8.2], paint={"north": pix(["TTTT"], T, flat="T")})
    for s in (1, -1):
        m.box("head", f"ear{s}", "fur", [s * 3.2 - 1.9, y0 + 7, -0.7], [s * 3.2 + 1.9, y0 + 11, 0.7], rot=[0, 0, -10 * s], origin=[s * 3.2, y0 + 7, 0])
        m.box("head", f"ear_tip{s}", "fur", [s * 3.7 - 0.8, y0 + 11, -0.5], [s * 3.7 + 0.8, y0 + 13, 0.5], rot=[0, 0, -10 * s],
              origin=[s * 3.2, y0 + 7, 0])
        m.box("head", f"ear_in{s}", "inner", [s * 3.2 - 1, y0 + 7.6, -1.1], [s * 3.2 + 1, y0 + 10.4, -0.7], rot=[0, 0, -10 * s],
              origin=[s * 3.2, y0 + 7, 0])
    # torn suit showing the endoskeleton
    m.decal("body", "chest_hole", [-1.5, L + 6.5, -td / 2 - 0.06], [4.5, 4], ("hole", dict(bars=2)))
    m.decal("body", "side_hole", [tw / 2 + 0.06, L + 7, 0], [2.5, 3], ("hole", dict(bars=1)), face="east")
    m.decal("right_arm", "arm_hole", [-(tw / 2 + 1.75), N - 7.5, -1.81], [1.8, 2.2], ("hole", dict(bars=1)))
    ax, top, s, fore = a["hands"]["right"]
    m.box(fore, "hook_cuff", "hook", [ax - 1.5, top - 1, -1.5], [ax + 1.5, top + 0.5, 1.5])
    m.box(fore, "hook_shaft", "hook", [ax - 0.5, top - 4.5, -0.5], [ax + 0.5, top - 1, 0.5])
    m.box(fore, "hook_bend", "hook", [ax - 0.5, top - 5.5, -2.5], [ax + 0.5, top - 4.5, 0.5])
    m.box(fore, "hook_up", "hook", [ax - 0.5, top - 5.5, -3.5], [ax + 0.5, top - 2.8, -2.5])
    m.box(fore, "hook_tip", "hook", [ax - 0.4, top - 3.2, -3.4], [ax + 0.4, top - 1.8, -2.6], rot=[-30, 0, 0], origin=[ax, top - 2.8, -3])
    return m, dict(width=0.8, height=2.4, egg=(0xAC2A20, 0xD69C7E))


CHARACTERS = [freddy, bonnie, chica, foxy, golden_freddy]
