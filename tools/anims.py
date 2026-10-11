"""Writes the animatronic animations (GeckoLib JSON) for the five FNAF 1 animatronics.

Stiff, twitchy, machine-like motion instead of a golem's arm swing: legs step with linear
interpolation, arms barely move, the head snaps between poses, and the jumpscare ("attack")
throws both arms up with the jaw wide open and the head shaking.
Convention: negative X swings a limb forward/up; positive X opens the jaw.
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "animations", "entity")


def ch(keys, lerp="linear"):
    return {f"{t:.2f}": {"vector": v, "lerp_mode": lerp} for t, v in sorted(keys.items())}


def build(name):
    fast = name == "foxy"
    anims = {}

    # idle: dead still, then a sudden head snap, a jaw twitch, a slow lean
    anims["idle"] = {"loop": True, "animation_length": 6.0, "bones": {
        "head": {"rotation": ch({0: [0, 0, 0], 1.6: [0, 0, 0], 1.68: [4, 14, -3], 3.0: [4, 14, -3], 3.08: [-2, -8, 5],
                                 4.6: [-2, -8, 5], 4.7: [0, 0, 0], 6.0: [0, 0, 0]})},
        "jaw": {"rotation": ch({0: [0, 0, 0], 4.0: [0, 0, 0], 4.06: [12, 0, 0], 4.16: [0, 0, 0], 4.24: [8, 0, 0], 4.32: [0, 0, 0],
                                6.0: [0, 0, 0]})},
        "body": {"rotation": ch({0: [0, 0, 0], 3.0: [2, 0, 1], 6.0: [0, 0, 0]}, "catmullrom")},
        "right_arm": {"rotation": ch({0: [0, 0, 0], 3.0: [-2, 0, 2], 6.0: [0, 0, 0]}, "catmullrom")},
        "left_arm": {"rotation": ch({0: [0, 0, 0], 3.0: [-2, 0, -2], 6.0: [0, 0, 0]}, "catmullrom")},
    }}

    if fast:
        L, A, T = 34, 30, 0.7
    else:
        L, A, T = 20, 6, 1.4
    h = T / 2
    anims["walk"] = {"loop": True, "animation_length": T, "bones": {
        "right_leg": {"rotation": ch({0: [L, 0, 0], h: [-L, 0, 0], T: [L, 0, 0]})},
        "left_leg": {"rotation": ch({0: [-L, 0, 0], h: [L, 0, 0], T: [-L, 0, 0]})},
        "right_arm": {"rotation": ch({0: [-A, 0, 3], h: [A, 0, 3], T: [-A, 0, 3]})},
        "left_arm": {"rotation": ch({0: [A, 0, -3], h: [-A, 0, -3], T: [A, 0, -3]})},
        "right_forearm": {"rotation": ch({0: [-10 if not fast else -35, 0, 0], T: [-10 if not fast else -35, 0, 0]})},
        "left_forearm": {"rotation": ch({0: [-10 if not fast else -35, 0, 0], T: [-10 if not fast else -35, 0, 0]})},
        "body": {"rotation": ch({0: [3 if not fast else 12, 0, 3], h: [3 if not fast else 12, 0, -3], T: [3 if not fast else 12, 0, 3]}),
                 "position": ch({0: [0, 0, 0], h / 2: [0, -0.6, 0], h: [0, 0, 0], h * 1.5: [0, -0.6, 0], T: [0, 0, 0]})},
        "head": {"rotation": ch({0: [0, 0, 0], T * 0.3: [0, 6, 2], T * 0.35: [2, -4, -2], T * 0.8: [0, 3, 0], T: [0, 0, 0]})},
    }}

    anims["attack"] = {"loop": False, "animation_length": 1.2, "bones": {
        "right_arm": {"rotation": ch({0: [0, 0, 0], 0.1: [-115, 0, -14], 1.0: [-115, 0, -14], 1.2: [0, 0, 0]})},
        "left_arm": {"rotation": ch({0: [0, 0, 0], 0.1: [-115, 0, 14], 1.0: [-115, 0, 14], 1.2: [0, 0, 0]})},
        "right_forearm": {"rotation": ch({0: [0, 0, 0], 0.1: [-30, 0, 0], 1.2: [0, 0, 0]})},
        "left_forearm": {"rotation": ch({0: [0, 0, 0], 0.1: [-30, 0, 0], 1.2: [0, 0, 0]})},
        "jaw": {"rotation": ch({0: [0, 0, 0], 0.06: [42, 0, 0], 1.0: [42, 0, 0], 1.2: [0, 0, 0]})},
        "head": {"rotation": ch({0: [0, 0, 0], 0.08: [-14, 0, 8], 0.14: [-14, 0, -8], 0.2: [-14, 0, 8], 0.26: [-14, 0, -8],
                                 0.32: [-14, 0, 8], 0.38: [-14, 0, -8], 0.44: [-14, 0, 6], 0.5: [-14, 0, -6], 1.0: [-10, 0, 0],
                                 1.2: [0, 0, 0]})},
        "body": {"rotation": ch({0: [0, 0, 0], 0.1: [12, 0, 0], 1.0: [12, 0, 0], 1.2: [0, 0, 0]})},
    }}
    return {"format_version": "1.8.0", "animations": anims, "geckolib_format_version": 2}


def main():
    for name in ("freddy", "bonnie", "chica", "foxy", "golden_freddy"):
        with open(os.path.join(OUT, f"{name}.animation.json"), "w") as f:
            json.dump(build(name), f, indent=1)
    print("ok")


if __name__ == "__main__":
    main()
