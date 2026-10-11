"""Generates Freddy Fazbear's Pizza (FNAF 1 layout) as a vanilla structure template.

Outputs (mod resources):
  data/fnaf/structures/pizzeria.nbt     blocks + block entities (signs)
  data/fnaf/pizzeria/markers.json       player spawn, animatronic spawns, paintings to hang
and a top-down preview PNG next to this script.

Coordinates: x east, y up, z south; the building's front (office) is at the south end.
"""
import gzip
import io
import json
import os
import random
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "src", "main", "resources", "data", "fnaf")
W, H, D = 66, 9, 58          # size x, y, z
CEIL = 7                      # ceiling layer; rooms are air on y 1..6
rnd = random.Random(1987)

blocks = {}                   # (x,y,z) -> (name, props)
block_nbt = {}                # (x,y,z) -> nbt dict
paintings, spawns = [], {}
rooms = {}


def put(x, y, z, name, **props):
    if 0 <= x < W and 0 <= y < H and 0 <= z < D:
        blocks[(x, y, z)] = ("minecraft:" + name if ":" not in name else name, {k: str(v).lower() for k, v in props.items()})


def fill(x0, y0, z0, x1, y1, z1, name, **props):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                put(x, y, z, name, **props)


def air(x0, y0, z0, x1, y1, z1):
    fill(x0, y0, z0, x1, y1, z1, "air")


def is_air(x, y, z):
    b = blocks.get((x, y, z))
    return b is not None and b[0] == "minecraft:air"


# ====================================================================== shell + rooms

fill(0, 0, 0, W - 1, CEIL + 1, D - 1, "fnaf:concrete_wall")


def room(name, x0, z0, x1, z1, floor, wall, top=6):
    rooms[name] = (x0, z0, x1, z1, floor, wall, top)
    air(x0, 1, z0, x1, top, z1)


room("stage", 20, 1, 45, 11, "stage", "stage")
room("dining", 12, 12, 53, 36, "dining", "dining")
room("cove", 5, 19, 11, 29, "cove", "cove")
room("backstage", 4, 1, 17, 10, "dark", "back")
room("restroom", 56, 13, 62, 25, "tile", "tile")
room("kitchen", 56, 27, 62, 37, "kitchen", "kitchen")
room("west_hall", 22, 38, 25, 54, "hall", "hall")
room("east_hall", 40, 38, 43, 54, "hall", "hall")
room("closet", 16, 40, 20, 46, "dark", "back")
room("office", 27, 46, 38, 55, "hall", "office", top=5)

# doorways (3 tall unless noted)
air(14, 1, 11, 16, 3, 11)        # backstage -> dining
air(54, 1, 16, 55, 3, 18)        # dining -> restroom
air(54, 1, 30, 55, 3, 31)        # dining -> kitchen
air(22, 1, 37, 25, 4, 37)        # dining -> west hall
air(40, 1, 37, 43, 4, 37)        # dining -> east hall
air(21, 1, 42, 21, 3, 43)        # west hall -> supply closet


# ====================================================================== surfaces

def floor_block(kind, x, z):
    if kind in ("dining", "hall"):
        return "fnaf:checker_floor"
    if kind in ("stage", "cove"):
        return "fnaf:stage_planks"
    if kind == "tile":
        return "fnaf:bath_tile"
    if kind == "kitchen":
        return "fnaf:kitchen_tile"
    return "fnaf:dark_tile"


def dirty(name, alt, p=0.12):
    return alt if rnd.random() < p else name


def wall_block(kind, x, y, z):
    """FNAF 1 walls: dark baseboard, black/white checkered tile band, red stripe, grimy plaster above."""
    if kind in ("dining", "hall", "office"):
        if y == 1:
            return "fnaf:wall_base"
        if y in (2, 3):
            return "fnaf:wall_checker"
        if y == 4:
            return "fnaf:wall_red"
        return "fnaf:wall_plaster"
    if kind == "stage":
        return "fnaf:star_curtain"
    if kind == "cove":
        return "fnaf:cove_curtain"
    if kind in ("tile", "kitchen"):
        return "fnaf:wall_checker" if y == 1 else "fnaf:bath_tile"
    return "fnaf:concrete_wall"


for name, (x0, z0, x1, z1, fkind, wkind, top) in rooms.items():
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            put(x, 0, z, floor_block(fkind, x, z))
            put(x, top + 1, z, "fnaf:ceiling_tile")
    # paint walls that face into this room
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            if x0 <= x <= x1 and z0 <= z <= z1:
                continue
            for y in range(1, top + 1):
                b = blocks.get((x, y, z))
                if b and b[0] == "fnaf:concrete_wall":
                    put(x, y, z, wall_block(wkind, x, y, z))
# doorway floors
for (x, z) in [(x, 11) for x in range(14, 17)] + [(x, z) for x in (54, 55) for z in (16, 17, 18, 30, 31)] + \
        [(x, 37) for x in list(range(22, 26)) + list(range(40, 44))] + [(21, 42), (21, 43)]:
    put(x, 0, z, "fnaf:checker_floor")



def lights(name, spacing=6, flicker=0.0, only=None):
    """Fluorescent panels in the ceiling of a room on a regular grid (powered by the generator)."""
    x0, z0, x1, z1, _, _, top = rooms[name]
    xs = only[0] if only else range(x0 + (x1 - x0) % spacing // 2 + 1, x1, spacing)
    zs = only[1] if only else range(z0 + (z1 - z0) % spacing // 2 + 1, z1, spacing)
    for x in xs:
        for z in zs:
            put(x, top + 1, z, "fnaf:ceiling_light", powered="true", lit="true", flicker=str(rnd.random() < flicker).lower())


def litter(name, p):
    """Confetti, napkins and soda stains on the empty floor."""
    x0, z0, x1, z1 = rooms[name][:4]
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if is_air(x, 1, z) and rnd.random() < p:
                put(x, 1, z, "fnaf:confetti")


# ====================================================================== show stage

fill(20, 1, 1, 45, 1, 7, "fnaf:stage_planks")
for x in range(20, 46):
    put(x, 1, 8, "fnaf:stage_step", type="bottom", waterlogged="false")
    put(x, 1, 7, "fnaf:stage_planks")
# star backdrop on the back wall, red valance on top
for x in range(20, 46):
    for y in range(2, 7):
        put(x, y, 0, "fnaf:star_curtain")
    put(x, 6, 1, "fnaf:red_curtain")
for z in range(1, 9):
    for y in range(2, 7):
        put(20, y, z, "fnaf:red_curtain")
        put(45, y, z, "fnaf:red_curtain")
for x in (21, 44):
    for y in range(3, 7):
        put(x, y, 1, "fnaf:red_curtain")
# speakers + stage lights
for x in (23, 42):
    fill(x, 2, 2, x + 1, 4, 3, "fnaf:speaker", facing="south")
lights("stage", only=([25, 32, 39], [5]))
spawns["bonnie"] = [26.5, 2, 4.5, 0]
spawns["freddy"] = [32.5, 2, 4.5, 0]
spawns["chica"] = [39.5, 2, 4.5, 0]
# "Celebrate!" banner-poster above the stage edge on the backdrop
paintings.append(dict(variant="fnaf:celebrate", pos=[33, 4, 1], facing="south"))


# ====================================================================== dining area

for cx in (19, 32, 45):
    for z in range(16, 33):
        for dx in (0, 1):
            put(cx + dx, 1, z, "fnaf:party_table")
            r = rnd.random()
            if r < 0.3:
                put(cx + dx, 2, z, "fnaf:party_hat")
            elif r < 0.6:
                put(cx + dx, 2, z, "fnaf:plate")
            elif r < 0.72:
                put(cx + dx, 2, z, "fnaf:soda_cup")
        if z % 2 == 0:
            put(cx - 1, 1, z, "fnaf:chair", facing="east")
            put(cx + 2, 1, z, "fnaf:chair", facing="west")
    # balloons tied at the table ends
    for z in (16, 32):
        put(cx, 2, z, "fnaf:balloon")
        put(cx + 1, 2, z, "fnaf:balloon")
# confetti-coloured streamers along the ceiling
for x in range(12, 54):
    if x % 3 == 0:
        for z in (14, 24, 34):
            put(x, 6, z, "fnaf:streamer")
lights("dining", 7)
# arcade cabinets along the east wall
for z in range(25, 29):
    put(53, 1, z, "fnaf:arcade", facing="west")
# party posters on the side walls
paintings += [dict(variant="fnaf:celebrate", pos=[12, 3, 18], facing="east"),
              dict(variant="fnaf:celebrate", pos=[53, 3, 22], facing="west"),
              dict(variant="fnaf:freddy_poster", pos=[53, 3, 33], facing="west"),
              dict(variant="fnaf:rules", pos=[12, 3, 33], facing="east")]
# garbage + a tipped chair
put(13, 1, 35, "fnaf:trash_can")
put(52, 1, 13, "fnaf:chair", facing="north")
litter("dining", 0.10)


# ====================================================================== pirate cove

fill(5, 1, 19, 10, 1, 29, "fnaf:stage_planks")
for z in range(19, 30):
    for y in range(1, 7):
        if z == 24 and y < 5:
            continue                                           # Foxy peeks through the gap
        put(11, y, z, "fnaf:cove_curtain")
for z in range(19, 30):
    put(11, 6, z, "fnaf:red_curtain")
put(12, 2, 21, "fnaf:out_of_order_sign", facing="east")
lights("cove", only=([8], [24]), flicker=1.0)
spawns["foxy"] = [7.5, 2, 24.5, 90]


# ====================================================================== backstage

for x in range(5, 17):
    put(x, 1, 1, "fnaf:metal_shelf", facing="south")
    put(x, 2, 1, "fnaf:metal_shelf", facing="south")
for i, x in enumerate(range(5, 17, 2)):
    put(x, 3, 1, "fnaf:spare_head", facing="south", kind=i % 4)
fill(8, 1, 5, 12, 1, 6, "fnaf:workbench", facing="south")
put(9, 2, 5, "fnaf:spare_head", facing="south", kind=1)
put(11, 2, 6, "fnaf:spare_head", facing="east", kind=0)
put(10, 2, 5, "fnaf:papers", facing="south")
put(4, 1, 9, "fnaf:workbench", facing="north")
put(5, 1, 9, "fnaf:workbench", facing="north")
put(16, 1, 3, "fnaf:cardboard_box")
put(16, 2, 3, "fnaf:cardboard_box")
put(16, 1, 4, "fnaf:cardboard_box")
for p in ((4, 6, 1), (17, 6, 10), (4, 6, 10)):
    put(*p, "fnaf:cobweb")
lights("backstage", only=([10], [5]), flicker=1.0)


# ====================================================================== restrooms

for z in (16, 20):
    fill(59, 1, z, 62, 3, z, "fnaf:stall_wall")
fill(59, 1, 14, 59, 3, 14, "fnaf:stall_wall")
for z in (14, 18, 22):
    put(59, 1, z, "fnaf:stall_door", facing="east", half="lower", hinge="left", open="false", powered="false")
    put(59, 2, z, "fnaf:stall_door", facing="east", half="upper", hinge="left", open="false", powered="false")
for z in (15, 19, 23):
    put(62, 1, z, "fnaf:toilet", facing="west")
for z in range(14, 25, 3):
    put(56, 1, z, "fnaf:sink", facing="east")
    put(56, 3, z, "fnaf:mirror", facing="east")
lights("restroom", only=([57], [15, 21]), flicker=0.5)


# ====================================================================== kitchen (lights are broken)

for z in range(27, 38):
    if z % 3 == 0:
        put(62, 1, z, "fnaf:oven", facing="west")
    else:
        put(62, 1, z, "fnaf:counter")
for z in range(28, 37, 2):
    put(62, 2, z, "fnaf:cooking_pot")
fill(58, 1, 30, 60, 1, 33, "fnaf:counter")
put(59, 2, 31, "fnaf:cooking_pot")
put(58, 2, 32, "fnaf:plate")
put(60, 2, 30, "fnaf:soda_cup")
put(56, 1, 36, "fnaf:cardboard_box")
put(57, 1, 36, "fnaf:cardboard_box")
put(56, 2, 36, "fnaf:cardboard_box")
put(56, 1, 27, "fnaf:fridge", facing="east")
put(56, 1, 29, "fnaf:trash_can")


# ====================================================================== supply closet

for z in range(40, 47):
    put(16, 1, z, "fnaf:metal_shelf", facing="east")
    if z % 2:
        put(16, 2, z, "fnaf:cardboard_box")
put(20, 1, 46, "fnaf:mop_bucket")
put(18, 1, 40, "fnaf:metal_shelf", facing="south")
put(19, 1, 40, "fnaf:metal_shelf", facing="south")
put(18, 6, 41, "fnaf:cobweb")
put(18, 1, 43, "fnaf:generator", facing="east", running="true")
lights("closet", only=([18], [44]), flicker=1.0)


# ====================================================================== halls

lights("west_hall", only=([23], [40, 46, 52]), flicker=0.6)
lights("east_hall", only=([42], [40, 46, 52]), flicker=0.6)
litter("west_hall", 0.04)
litter("east_hall", 0.04)
for p in ((22, 6, 38), (25, 6, 54), (43, 6, 38), (40, 6, 54), (22, 1, 54)):
    put(*p, "fnaf:cobweb")
paintings += [dict(variant="fnaf:rules", pos=[22, 3, 46], facing="east"),
              dict(variant="fnaf:celebrate", pos=[43, 3, 41], facing="west"),
              dict(variant="fnaf:golden_poster", pos=[22, 3, 52], facing="east")]
for i, z in enumerate((41, 43, 45, 47)):
    paintings.append(dict(variant=f"fnaf:drawing{i + 1}", pos=[40, 4, z], facing="east"))
spawns["golden_freddy"] = [23.5, 1, 53.5, 180]


# ====================================================================== security office

# doors (iron doors held open by levers) + light buttons wired to lamps in the halls
for wx, side, hall_x, inner_x in ((26, "west", 25, 27), (39, "east", 40, 38)):
    face = "east" if side == "west" else "west"
    air(wx, 1, 50, wx, 2, 50)
    put(wx, 1, 50, "fnaf:security_door", facing=face, half="lower", hinge="left", open="true", powered="true")
    put(wx, 2, 50, "fnaf:security_door", facing=face, half="upper", hinge="left", open="true", powered="true")
    put(inner_x, 2, 49, "fnaf:door_button", face="wall", facing=face, powered="true")
    put(inner_x, 3, 51, "fnaf:light_button", face="wall", facing=face, powered="false")
    put(hall_x, 3, 51, "fnaf:door_light", lit="false")
    put(wx, 3, 50, "air")
# desk with monitors, fan, cupcake and a lamp
fill(29, 1, 47, 36, 1, 48, "fnaf:office_desk", facing="south")
for x in (30, 31, 35):
    put(x, 2, 47, "fnaf:crt_monitor", facing="south")
put(31, 3, 47, "fnaf:crt_monitor", facing="south")
put(33, 2, 47, "fnaf:desk_fan", facing="south")
put(35, 2, 48, "fnaf:cupcake", facing="south")
put(36, 2, 48, "fnaf:soda_cup")
put(29, 2, 48, "fnaf:party_hat")
# windows next to the doors, looking into the halls
for wx in (26, 39):
    for y in (2, 3):
        for z in (52, 53):
            put(wx, y, z, "fnaf:office_window", facing="east")
put(32, 2, 48, "fnaf:papers", facing="south")
put(30, 2, 48, "fnaf:papers", facing="east")
put(32, 1, 50, "fnaf:office_chair", facing="north")
put(37, 1, 54, "fnaf:trash_can")
put(28, 1, 54, "fnaf:cardboard_box")
lights("office", only=([30, 35], [50]))
paintings += [dict(variant="fnaf:celebrate", pos=[33, 3, 46], facing="south"),
              dict(variant="fnaf:drawing1", pos=[27, 3, 47], facing="east"),
              dict(variant="fnaf:drawing2", pos=[27, 4, 53], facing="east"),
              dict(variant="fnaf:drawing3", pos=[38, 3, 47], facing="west"),
              dict(variant="fnaf:drawing4", pos=[38, 4, 53], facing="west")]
player = [32.5, 1, 52.5, 180]


put(56, 2, 27, "air")

# ====================================================================== write the structure

def nbt_payload(tag, value):
    """Minimal NBT encoder; tag = 'byte'|'int'|'string'|'list:<inner>'|'compound'|'double' ..."""
    out = io.BytesIO()
    write_value(out, tag, value)
    return out.getvalue()


TAGS = {"end": 0, "byte": 1, "short": 2, "int": 3, "long": 4, "float": 5, "double": 6, "string": 8, "list": 9, "compound": 10}


def guess(v):
    if isinstance(v, bool):
        return "byte"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "double"
    if isinstance(v, str):
        return "string"
    if isinstance(v, dict):
        return "compound"
    if isinstance(v, list):
        return "list"
    raise TypeError(v)


def write_string(out, s):
    b = s.encode("utf-8")
    out.write(struct.pack(">H", len(b)))
    out.write(b)


def write_value(out, tag, v, inner=None):
    if tag == "byte":
        out.write(struct.pack(">b", int(v)))
    elif tag == "int":
        out.write(struct.pack(">i", v))
    elif tag == "double":
        out.write(struct.pack(">d", v))
    elif tag == "string":
        write_string(out, v)
    elif tag == "list":
        it = inner or (guess(v[0]) if v else "end")
        out.write(struct.pack(">bi", TAGS[it], len(v)))
        for x in v:
            write_value(out, it, x)
    elif tag == "compound":
        for k, x in v.items():
            t = "byte" if k in ("has_glowing_text", "is_waxed") else guess(x)
            out.write(struct.pack(">b", TAGS[t]))
            write_string(out, k)
            write_value(out, t, x)
        out.write(b"\x00")


def main():
    palette, index = [], {}
    entries = []
    for pos, (name, props) in sorted(blocks.items()):
        if name == "minecraft:air" and not any(x0 - 1 <= pos[0] <= x1 + 1 and z0 - 1 <= pos[2] <= z1 + 1
                                                for (x0, z0, x1, z1, *_r) in rooms.values()):
            continue                     # interior air is kept so a rebuild clears old furniture
        key = (name, tuple(sorted(props.items())))
        if key not in index:
            index[key] = len(palette)
            e = {"Name": name}
            if props:
                e["Properties"] = dict(props)
            palette.append(e)
        b = {"pos": list(pos), "state": index[key]}
        if pos in block_nbt:
            b["nbt"] = block_nbt[pos]
        entries.append(b)
    root = {"DataVersion": 3465, "size": [W, H, D], "palette": palette, "blocks": entries, "entities": []}
    raw = io.BytesIO()
    raw.write(struct.pack(">b", 10))
    write_string(raw, "")
    write_value(raw, "compound", root)
    os.makedirs(os.path.join(DATA, "structures"), exist_ok=True)
    with gzip.open(os.path.join(DATA, "structures", "pizzeria.nbt"), "wb") as f:
        f.write(raw.getvalue())
    os.makedirs(os.path.join(DATA, "pizzeria"), exist_ok=True)
    with open(os.path.join(DATA, "pizzeria", "markers.json"), "w") as f:
        json.dump({"size": [W, H, D], "player": player, "animatronics": spawns, "paintings": paintings}, f, indent=1)
    with open(os.path.join(HERE, "pizzeria_blocks.json"), "w") as f:
        json.dump([[*p, n] for p, (n, _) in blocks.items() if n != "minecraft:air"], f)
    print(f"{len(entries)} blocks, {len(palette)} states, {len(paintings)} paintings")


if __name__ == "__main__":
    main()
