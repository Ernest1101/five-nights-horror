"""Gameplay placements inside the downloaded FNAF 1 map (map block coordinates, see map_top.png written
by build_map.py): player/animatronic spawns and the generator. Positions are nudged to the nearest cell
that has no map geometry so nothing spawns inside a table or wall.

placements(cells) -> (extra blocks {(x, y, z): (name, props)}, markers dict)
"""

PLAYER = (25.5, 41.5, 180)                       # security office, facing the halls
# on the stage / in the cove they are dropped from above onto the raised floor
ANIMATRONICS = {"freddy": (25.5, 11.5, 0), "bonnie": (22.5, 11.5, 0), "chica": (28.5, 11.5, 0),
                "foxy": (12.5, 27.5, -90), "golden_freddy": (18.5, 40.5, 0)}
DROPPED = {"freddy": 2.6, "bonnie": 2.6, "chica": 2.6, "foxy": 2.6}
GENERATOR = (8, 18, "east")


def free(cells, x, z, y0=1, h=3):
    return all((x, y, z) not in cells for y in range(y0, y0 + h))


def floor_y(cells, x, z):
    """First empty cell above the highest geometry at the bottom of this column (stage floors etc.)."""
    y = 1
    while (x, y, z) in cells and y < 4:
        y += 1
    return y


def nearest_free(cells, x, z, h=3):
    """Nearest column with floor below and nothing at all in the h cells above it."""
    for r in range(0, 10):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                cx, cz = int(x) + dx, int(z) + dz
                if (cx, 0, cz) in cells and free(cells, cx, cz, 1, h):
                    return cx, 1, cz
    for r in range(0, 6):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                cx, cz = int(x) + dx, int(z) + dz
                y = floor_y(cells, cx, cz)
                if free(cells, cx, cz, y, h):
                    return cx, y, cz
    return int(x), 1, int(z)


def walkable(cells, col):
    """Cells (x, z) on the ground floor a 2-block-tall walker can stand in, flood-filled from the office."""
    def blocked(x, y, z):
        # only boxes covering the middle of the cell count (thin walls at the edges leave room to pass)
        return any(b[4] > (8 if y == 1 else 0) and b[0] < 11 and b[3] > 5 and b[2] < 11 and b[5] > 5
                   for b in col.get((x, y, z), []))

    def ok(x, z):
        return (x, 0, z) in cells and not blocked(x, 1, z) and not blocked(x, 2, z)

    start = (int(PLAYER[0]), int(PLAYER[1]))
    seen, todo = {start}, [start]
    while todo:
        x, z = todo.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n not in seen and ok(*n):
                seen.add(n)
                todo.append(n)
    return seen


def placements(cells, col):
    reach = walkable(cells, col)
    print(len(reach), "reachable floor cells")
    xs = [x for x, z in reach]
    zs = [z for x, z in reach]
    w, h = max(xs) + 2, max(zs) + 2
    for z in range(h):
        print("".join("#" if (x, z) in reach else ("." if (x, 0, z) in cells else " ") for x in range(w)))
    def spot(x, z, yaw, h=3):
        cx, y, cz = nearest_free(cells, x, z, h)
        return [cx + 0.5, y, cz + 0.5, yaw]

    markers = {"player": spot(*PLAYER[:2], PLAYER[2], 2),
               "animatronics": {k: [x, DROPPED[k], z, yaw] if k in DROPPED else spot(x, z, yaw)
                                for k, (x, z, yaw) in ANIMATRONICS.items()},
               "paintings": []}
    # generator: reachable cell with nothing in it, closest to the wanted spot
    gx, gz = min((c for c in reach if free(cells, c[0], c[1], 1, 2)),
                 key=lambda c: (c[0] - GENERATOR[0]) ** 2 + (c[1] - GENERATOR[1]) ** 2)
    gy = 1
    extra = {}          # power is handled by the night system now, no generator in the map
    markers["generator"] = [gx, gy, gz]
    print("markers", markers)
    return extra, markers
