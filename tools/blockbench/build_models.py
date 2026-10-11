"""Builds every animatronic inside a running Blockbench through the Blockbench MCP plugin.

Usage (Blockbench must be open with the MCP plugin enabled, default http://localhost:3000/bb-mcp):
    python build_models.py                # all models
    python build_models.py freddy foxy    # only some

For each model this creates a GeckoLib project in Blockbench, builds bones/cubes/texture/animations,
then exports through the GeckoLib plugin into the mod resources and saves a .bbmodel next to it.
"""
import base64
import json
import os
import sys

import bbmcp
import fnaf1 as fm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSETS = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf")
BBMODELS = os.path.join(ROOT, "blockbench")
PREVIEWS = os.path.join(BBMODELS, "previews")

BUILD_JS = r"""
(function(){
const D = JSON.parse(%s.replace(/~/g, String.fromCharCode(47)));
Project.box_uv = false;
Project.texture_width = D.tex; Project.texture_height = D.tex;
const tex = new Texture({name: D.name + '.png'}).fromDataURL(D.png).add(false);
const groups = {};
for (const b of D.bones) {
  const g = new Group({name: b.name, origin: b.pivot, rotation: b.rot});
  g.addTo(b.parent ? groups[b.parent] : undefined).init();
  groups[b.name] = g;
  for (const c of b.cubes) {
    const faces = {};
    for (const f in c.uv) faces[f] = c.uv[f] ? {uv: c.uv[f], texture: tex.uuid} : {uv: [0, 0, 0, 0], texture: null};
    new Cube({name: c.name, from: c.frm, to: c.to, origin: c.origin || b.pivot, rotation: c.rot,
              inflate: c.inflate, box_uv: false, faces: faces}).addTo(g).init();
  }
}
for (const an in D.anims) {
  const meta = D.meta[an];
  const a = new Animation({name: an, loop: meta.loop, length: meta.length, snapping: 20}).add(false);
  for (const bn in D.anims[an]) {
    if (!groups[bn]) continue;
    const ba = a.getBoneAnimator(groups[bn]);
    for (const ch in D.anims[an][bn]) {
      const pts = D.anims[an][bn][ch];
      for (const t in pts) {
        const v = pts[t];
        ba.addKeyframe({channel: ch, time: parseFloat(t), interpolation: 'catmullrom',
                        data_points: [{x: v[0], y: v[1], z: v[2]}]});
      }
    }
  }
}
Canvas.updateAll();
return {groups: Object.keys(groups).length, cubes: Cube.all.length, animations: Animation.all.length};
})()
"""


def image_from(result, path):
    for c in result.get("content", []):
        if c.get("type") == "image":
            with open(path, "wb") as f:
                f.write(base64.b64decode(c["data"]))
            return True
    return False


def text_of(result):
    return "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")


def build(factory, previews=True):
    model, info = factory()
    name = model.name
    png = model.texture_png()
    glow = model.texture_png(glow_only=True)
    kf, meta = fm.animations(name)

    os.makedirs(os.path.join(ASSETS, "textures", "entity"), exist_ok=True)
    with open(os.path.join(ASSETS, "textures", "entity", f"{name}.png"), "wb") as f:
        f.write(png)
    with open(os.path.join(ASSETS, "textures", "entity", f"{name}_glowmask.png"), "wb") as f:
        f.write(glow)

    bbmcp.call("risky_eval", {"code": "(function(){ for (const p of ModelProject.all.filter(p => p.name === '%s')) "
                                      "{ p.saved = true; p.close(true); } return true; })()" % name})
    bbmcp.call("create_project", {"name": name, "format": "geckolib_model"})
    bbmcp.call("geckolib_set_project_settings", {"modid": "fnaf", "model_type": "Entity", "model_identifier": name})
    data = dict(name=name, tex=model.tex_size, png="data:image/png;base64," + base64.b64encode(png).decode(),
                bones=[dict(name=b['name'], parent=b['parent'], pivot=b['pivot'], rot=b['rot'],
                           cubes=[dict(name=c['name'], frm=c['frm'], to=c['to'], inflate=c['inflate'], rot=c['rot'],
                                       origin=c['origin'], uv=c['uv']) for c in b['cubes']]) for b in model.bones],
                anims=kf, meta=meta)
    payload = json.dumps(json.dumps(data).replace("/", "~"))
    res = bbmcp.call("risky_eval", {"code": BUILD_JS % payload})
    print(name, text_of(res))

    geo = os.path.join(ASSETS, "geo", "entity", f"{name}.geo.json")
    ani = os.path.join(ASSETS, "animations", "entity", f"{name}.animation.json")
    os.makedirs(os.path.dirname(geo), exist_ok=True)
    os.makedirs(os.path.dirname(ani), exist_ok=True)
    bbmcp.call("geckolib_export_model", {"path": geo.replace("\\", "/"), "overwrite": True, "max_content_length": 0})
    bbmcp.call("geckolib_export_animations", {"path": ani.replace("\\", "/"), "overwrite": True, "max_content_length": 0})

    src = bbmcp.call("risky_eval", {"code": "(function(){ Project.saved = true; return Codecs.project.compile({raw: false}); })()"})
    os.makedirs(BBMODELS, exist_ok=True)
    with open(os.path.join(BBMODELS, f"{name}.bbmodel"), "w", encoding="utf-8") as f:
        f.write(json.loads(text_of(src)) if text_of(src).startswith('"') else text_of(src))

    if previews:
        os.makedirs(PREVIEWS, exist_ok=True)
        h = model.height()
        view = "preview"
        try:
            bbmcp.call("create_offscreen_view", {"id": view, "width": 640, "height": 760, "copy_view": "none"})
        except RuntimeError as e:
            if "already exists" not in str(e):
                raise
        for suffix, pos in (("", [-38, h * 0.75, -52]), ("_back", [36, h * 0.7, 50])):
            r = bbmcp.call("set_camera_angle", {"view": view, "position": pos, "target": [0, h / 2, 0],
                                                 "projection": "perspective", "fov": 45})
            image_from(r, os.path.join(PREVIEWS, f"{name}{suffix}.png"))
    return name, info, model.height()


def main():
    wanted = set(sys.argv[1:])
    out = []
    for factory in fm.CHARACTERS:
        if wanted and factory.__name__ not in wanted:
            continue
        out.append(build(factory))
    for name, info, h in out:
        print(f"{name}: model height {h:.1f}px ({h / 16:.2f} blocks), hitbox {info['width']}x{info['height']}")


if __name__ == "__main__":
    main()
