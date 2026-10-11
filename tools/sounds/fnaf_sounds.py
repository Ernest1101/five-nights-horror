"""Builds the mod's FNAF-style sounds from CC0 recordings on freesound.org (+ a synthesized music box).

    python tools/sounds/fnaf_sounds.py

Original FNAF audio is copyrighted, so nothing is ripped from the games: every recording below is
CC0 (public domain) and is downloaded once into tools/sounds/raw/. The music box plays Bizet's
"Toreador Song" (public domain), like Freddy does when the power goes out. Writes OGG files to
assets/fnaf/sounds/{animatronic,prop,pizzeria}/ and regenerates sounds.json together with the
procedurally generated sounds from gen_sounds.py.
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import freesound  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SOUNDS = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "sounds")
SR = 44100
rng = np.random.default_rng(5)


def load(sid):
    """Mono float32 samples of a CC0 freesound recording (cached in tools/sounds/raw)."""
    path = os.path.join(HERE, "raw", f"{sid}.mp3")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(freesound.fetch(freesound.preview_url(sid)))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def cut(a, start, length=None):
    s = int(start * SR)
    return a[s:s + int(length * SR)] if length else a[s:]


def fade(a, fin=0.005, fout=0.05):
    a = a.copy()
    n_in, n_out = int(fin * SR), int(fout * SR)
    if n_in:
        a[:n_in] *= np.linspace(0, 1, n_in)
    if n_out:
        a[-n_out:] *= np.linspace(1, 0, n_out)
    return a


def onset(a, thresh=0.25):
    """Index of the first sample louder than thresh * peak (for trimming silence before a hit)."""
    env = np.abs(a)
    return max(0, int(np.argmax(env > thresh * env.max())) - int(0.01 * SR))


def resample(a, factor):
    """Pitch/speed change by resampling (factor < 1 = lower and slower)."""
    idx = np.arange(0, len(a) - 1, factor)
    return np.interp(idx, np.arange(len(a)), a)


def loop(a, xfade=0.3):
    """Seamless loop: crossfade the tail into the head."""
    n = int(xfade * SR)
    out = a[:-n].copy()
    out[:n] = out[:n] * np.linspace(0, 1, n) + a[-n:] * np.linspace(1, 0, n)
    return out


def mix(*parts):
    """mix((samples, offset_seconds, gain), ...)"""
    n = max(int(o * SR) + len(p) for p, o, g in parts)
    out = np.zeros(n)
    for p, o, g in parts:
        s = int(o * SR)
        out[s:s + len(p)] += p * g
    return out


def norm(a, peak=0.9):
    return a / (np.abs(a).max() + 1e-9) * peak


def lowpass(x, cutoff):
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    from scipy.signal import lfilter
    return lfilter([alpha], [1, alpha - 1], x)


def write(rel, a, peak=0.9):
    a = norm(a, peak)
    path = os.path.join(SOUNDS, rel + ".ogg")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "x.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5", path], check=True)
    return "fnaf:" + rel.replace("\\", "/")


# ---------------------------------------------------------------- music box (Bizet, public domain)

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "Bb": 10, "B": 11}


def freq(n):
    name, octave = n[:-1], int(n[-1])
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave + 1) - 69) / 12)


def music_box():
    p1 = [("C5", .75), ("D5", .25), ("C5", .5), ("A4", .5), ("A4", .5), ("A4", .5), ("G4", .5), ("A4", .5), ("Bb4", .5), ("A4", 1.5)]
    p2 = [("Bb4", .75), ("G4", .25), ("C5", .5), ("A4", .5), ("F4", .5), ("D4", .5), ("G4", .5), ("C4", 1.5)]
    end = [("Bb4", .75), ("G4", .25), ("C5", .5), ("A4", .5), ("F4", .5), ("G4", .5), ("F4", 2.5)]
    tune = p1 + p2 + p1 + end
    beat = 60 / 96
    total = sum(d for _, d in tune) * beat + 3
    out = np.zeros(int(total * SR))
    t0 = 0.0
    for i, (n, d) in enumerate(tune):
        f = freq(n) * 2          # music boxes play high
        ln = int(2.2 * SR)
        x = np.arange(ln) / SR
        tine = (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(2 * np.pi * f * 2.0 * x) * np.exp(-x * 6)
                + 0.18 * np.sin(2 * np.pi * f * 3.02 * x) * np.exp(-x * 9) + 0.1 * np.sin(2 * np.pi * f * 5.4 * x) * np.exp(-x * 20))
        note = tine * np.exp(-x * 2.2) * np.minimum(1, x / 0.002)
        s = int(t0 * SR)
        out[s:s + ln] += note[:len(out) - s]
        # the mechanism slows down a little towards the end
        slow = 1 + 0.25 * (i / len(tune)) ** 3
        t0 += d * beat * slow
    # small room + slight warble
    rev = out.copy()
    for delay, g in ((0.031, 0.35), (0.047, 0.25), (0.083, 0.18), (0.131, 0.12)):
        k = int(delay * SR)
        rev[k:] += out[:-k] * g
    x = np.arange(len(rev)) / SR
    rev *= 1 + 0.03 * np.sin(2 * np.pi * 0.7 * x)
    return rev


def whoosh(up=True):
    d = 0.35
    x = np.arange(int(d * SR)) / SR
    n = rng.uniform(-1, 1, len(x))
    env = np.sin(np.pi * x / d) ** 2
    cut = np.linspace(600, 3000, len(x)) if up else np.linspace(3000, 600, len(x))
    out = np.zeros(len(x))
    acc = 0.0
    for i in range(len(x)):
        a = 1 - np.exp(-2 * np.pi * cut[i] / SR)
        acc += a * (n[i] - acc)
        out[i] = acc
    click = np.zeros(len(x))
    k = int((0.3 if up else 0.02) * SR)
    click[k:k + 200] = rng.uniform(-1, 1, 200) * np.exp(-np.arange(200) / 30)
    return out * env + click * 0.8


def blip():
    d = 0.16
    n = int(d * SR)
    x = np.arange(n) / SR
    return rng.uniform(-1, 1, n) * np.exp(-x / 0.06) + 0.3 * np.sign(np.sin(2 * np.pi * 1800 * x)) * np.exp(-x / 0.02)


def menu_music():
    """Slow, detuned drone with a few distant music-box notes (original, not the game's theme)."""
    d = 32.0
    x = np.arange(int(d * SR)) / SR
    drone = np.zeros(len(x))
    for f, a in ((55.0, 1.0), (55.4, 0.8), (82.4, 0.5), (110.3, 0.3)):
        ph = 2 * np.pi * f * x + 0.8 * np.sin(2 * np.pi * 0.07 * x)
        drone += a * (2 * ((ph / (2 * np.pi)) % 1) - 1)
    drone = lowpass(drone, 300) * (0.6 + 0.4 * np.sin(2 * np.pi * x / d) ** 2)
    notes = np.zeros(len(x))
    seq = [("E5", 1.0), ("G5", 3.5), ("B4", 6.0), ("E5", 9.5), ("D5", 13.0), ("C5", 16.5), ("B4", 20.0), ("A4", 24.0), ("E5", 28.0)]
    for n, t0 in seq:
        f = freq(n)
        ln = int(3.0 * SR)
        y = np.arange(ln) / SR
        tone = (np.sin(2 * np.pi * f * y) + 0.3 * np.sin(2 * np.pi * f * 2 * y) * np.exp(-y * 5)) * np.exp(-y * 1.6)
        s0 = int(t0 * SR)
        notes[s0:s0 + ln] += tone[:len(notes) - s0]
    rev = notes.copy()
    for delay, g in ((0.11, 0.5), (0.23, 0.35), (0.37, 0.25), (0.53, 0.15)):
        k = int(delay * SR)
        rev[k:] += notes[:-k] * g
    hiss = lowpass(rng.uniform(-1, 1, len(x)), 2500) * 0.03
    return loop(drone * 0.5 + rev * 0.35 + hiss, 1.5)


# ---------------------------------------------------------------- the sound set

def build():
    spec = {}

    def add(event, files, subtitle=True, stream=False):
        entry = {"sounds": [{"name": f, "stream": True} if stream else f for f in files]}
        if subtitle:
            entry["subtitle"] = f"subtitles.fnaf.{event}"
        spec[event] = entry

    # animatronics
    steps = []
    for i, sid in enumerate((813056, 815039, 813053, 813055)):
        a = load(sid)
        a = cut(a, onset(a) / SR, 0.9)
        steps.append(write(f"animatronic/step{i + 1}", fade(a, 0.002, 0.25), 0.85))
    add("animatronic.step", steps)
    servo = load(322021)
    add("animatronic.servo", [write(f"animatronic/servo{i + 1}", fade(cut(servo, s, 0.9), 0.06, 0.2), 0.5)
                              for i, s in enumerate((1.0, 4.3))])
    scream = load(161404)
    mutant = load(396797)
    js = mix((cut(scream, 0.15, 2.6), 0.0, 1.0), (resample(cut(mutant, 0.05, 1.4), 0.8), 0.0, 0.9),
             (resample(cut(scream, 0.15, 2.6), 1.35), 0.02, 0.5))
    js = np.tanh(norm(js) * 2.5)
    add("animatronic.jumpscare", [write("animatronic/jumpscare1", fade(js, 0.002, 0.3), 0.98)])
    static = load(35291)
    add("animatronic.static", [write("animatronic/static1", fade(cut(static, 0.5, 1.4), 0.01, 0.3), 0.55)])
    laugh = load(350679)
    add("animatronic.laugh", [write("animatronic/laugh1", fade(resample(cut(laugh, 0.05), 0.82), 0.01, 0.3), 0.8)])
    run = load(361072)
    add("foxy.run", [write("animatronic/foxy_run1", fade(cut(run, 3.4, 3.0), 0.05, 0.3), 0.8)])
    bang = load(362633)
    add("foxy.bang", [write("animatronic/foxy_bang1", fade(bang, 0.002, 0.2), 0.95)])
    pots = load(209002)
    add("kitchen.pots", [write("pizzeria/pots1", fade(cut(pots, 1.2, 2.4), 0.01, 0.3), 0.8),
                         write("pizzeria/pots2", fade(cut(pots, 0.0, 1.3), 0.01, 0.2), 0.8)])

    # pizzeria / props
    add("music_box", [write("pizzeria/music_box1", music_box(), 0.8)], stream=True)
    add("pizzeria.ambience", [write("pizzeria/ambience1", loop(cut(load(371277), 0.5, 30.0), 1.0), 0.35)], stream=True)
    fan = load(553745)
    add("fan.loop", [write("prop/fan_loop1", loop(cut(fan, 10.0, 8.3), 0.3), 0.5)])
    door = load(406197)
    door_hit = cut(door, onset(door) / SR, 2.2)
    add("door.close", [write("prop/door_close1", fade(door_hit, 0.002, 0.4), 0.95)])
    add("door.open", [write("prop/door_open1", fade(resample(door_hit, 1.25) * np.linspace(0.7, 1, len(resample(door_hit, 1.25))), 0.002, 0.4), 0.7)])
    add("door_light.buzz", [write("prop/light_buzz1", loop(cut(load(474312), 0.1, 3.5), 0.2), 0.5)])
    add("button.click", [write("prop/button_click1", fade(load(348225), 0.001, 0.05), 0.8)])
    add("flashlight.click", [write("prop/flashlight_click1", fade(cut(load(187335), 0.0, 0.5), 0.001, 0.05), 0.8)])
    gen = load(182329)
    gen_loop = loop(gen, 0.25)
    add("generator.run", [write("prop/generator_run1", gen_loop, 0.6)])
    recoil = load(222809)
    pulls = [cut(recoil, 6.85, 1.3), cut(recoil, 9.8, 1.3)]
    add("generator.pull", [write(f"prop/generator_pull{i + 1}", fade(p, 0.005, 0.3), 0.8) for i, p in enumerate(pulls)])
    start = mix((pulls[0], 0, 1.0), (gen_loop[:int(2.5 * SR)] * np.minimum(1, np.arange(int(2.5 * SR)) / SR / 0.6), 0.55, 0.9))
    add("generator.start", [write("prop/generator_start1", fade(start, 0.005, 0.2), 0.85)])
    stop = resample(gen_loop[:int(2.4 * SR)], 0.7)
    stop *= np.exp(-np.arange(len(stop)) / SR / 1.1)
    add("generator.stop", [write("prop/generator_stop1", fade(stop, 0.005, 0.3), 0.75)])
    add("power.down", [write("prop/power_down1", fade(load(169994), 0.002, 0.4), 0.95)])

    # nights
    add("night.chimes", [write("pizzeria/chimes1", fade(cut(load(234268), 7.0, 11.5), 0.01, 1.5), 0.9)], stream=True)
    add("night.cheer", [write("pizzeria/cheer1", fade(cut(load(736924), 0.3, 5.0), 0.3, 1.2), 0.7)])
    add("cam.open", [write("prop/cam_open1", whoosh(True), 0.6)], subtitle=False)
    add("cam.close", [write("prop/cam_close1", whoosh(False), 0.6)], subtitle=False)
    add("cam.switch", [write("prop/cam_switch1", blip(), 0.5)], subtitle=False)
    add("menu.music", [write("pizzeria/menu_music1", menu_music(), 0.6)], subtitle=False, stream=True)

    # blackout refuelling (petrol cans + generator minigame)
    pour, glug = load(432350), load(568471)
    add("fuel.pour", [write("prop/fuel_pour1", fade(cut(pour, 5.2, 1.0), 0.08, 0.25), 0.7),
                      write("prop/fuel_pour2", fade(cut(glug, 2.0, 1.0), 0.08, 0.25), 0.7)])
    splash = load(207781)
    add("fuel.spill", [write("prop/fuel_spill1", fade(cut(splash, 0.0, 0.7), 0.01, 0.25), 0.8),
                       write("prop/fuel_spill2", fade(resample(cut(splash, 0.9, 0.7), 1.15), 0.01, 0.25), 0.8)])
    can = load(624489)
    can = cut(can, 8.7, 1.1)
    add("fuel.pickup", [write("prop/fuel_pickup1", fade(cut(can, onset(can) / SR), 0.002, 0.08), 0.85)])
    return spec


def main():
    import importlib.util
    spec = build()
    # keep the procedural animatronic sounds that have no recorded replacement (hurt, death, ambient)
    gs_spec = importlib.util.spec_from_file_location("gen_sounds", os.path.join(HERE, "gen_sounds.py"))
    gs = importlib.util.module_from_spec(gs_spec)
    gs_spec.loader.exec_module(gs)
    for name, data in (("hurt", [gs.hurt()]), ("death", [gs.death()]), ("ambient", [gs.ambient(i) for i in range(2)])):
        files = []
        for i, d in enumerate(data):
            gs.write(f"{name}{i + 1}", d)
            files.append(f"fnaf:animatronic/{name}{i + 1}")
        spec[f"animatronic.{name}"] = {"subtitle": f"subtitles.fnaf.animatronic.{name}", "sounds": files}
    with open(os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "sounds.json"), "w") as f:
        json.dump(spec, f, indent=2)
    print(len(spec), "sound events")


if __name__ == "__main__":
    main()
