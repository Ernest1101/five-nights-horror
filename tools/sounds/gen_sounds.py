"""Synthesizes the animatronic sounds (original, procedurally generated) and writes them as OGG
into the mod resources together with sounds.json. Needs numpy + ffmpeg on PATH.

    python tools/sounds/gen_sounds.py
"""
import json
import os
import subprocess
import tempfile
import wave

import numpy as np

SR = 44100
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "sounds", "animatronic")
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, attack=0.005, decay=0.3):
    x = np.arange(n) / SR
    a = np.clip(x / max(attack, 1e-4), 0, 1)
    return a * np.exp(-x / decay)


def noise(n):
    return rng.uniform(-1, 1, n)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def bandpass(x, lo, hi):
    return lowpass(x, hi) - lowpass(x, lo)


def metal(n, freqs, decay):
    x = np.arange(n) / SR
    out = np.zeros(n)
    for i, f in enumerate(freqs):
        out += np.sin(2 * np.pi * f * x + rng.uniform(0, 6)) * np.exp(-x / (decay / (1 + i * 0.35))) / (1 + i * 0.5)
    return out


def norm(x, peak=0.9):
    return x / (np.abs(x).max() + 1e-9) * peak


def step(variant):
    n = int(SR * 0.45)
    thud = np.sin(2 * np.pi * (55 + 10 * variant) * t(0.45)) * env(n, 0.002, 0.08)
    click = lowpass(noise(n), 2500) * env(n, 0.001, 0.02)
    ring = metal(n, [410 + 30 * variant, 1130, 1870, 2650], 0.12)
    servo = np.sin(2 * np.pi * (300 + 40 * variant) * t(0.45) + 3 * np.sin(2 * np.pi * 31 * t(0.45))) * env(n, 0.03, 0.08) * 0.15
    return norm(1.0 * thud + 0.6 * click + 0.25 * ring + servo, 0.85)


def servo(variant):
    d = 0.7 + 0.15 * variant
    x = t(d)
    f = np.linspace(170 + 20 * variant, 270 + 30 * variant, len(x)) * (1 + 0.05 * np.sin(2 * np.pi * 9 * x))
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    buzz = bandpass(noise(len(x)), 400, 2600) * 0.25
    e = np.minimum(1, np.minimum(x / 0.06, (d - x) / 0.12))
    return norm(lowpass(saw, 1800) * e + buzz * e, 0.5)


def hurt():
    n = int(SR * 0.6)
    return norm(metal(n, [380, 990, 1720, 2580, 3420], 0.18) + 0.8 * lowpass(noise(n), 4000) * env(n, 0.001, 0.03), 0.9)


def death():
    d = 2.0
    x = t(d)
    f = 240 * np.exp(-x * 1.6) + 30
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sign(np.sin(ph)) * 0.4 + np.sin(ph * 2) * 0.3
    crackle = noise(len(x)) * (rng.random(len(x)) < 0.004) * 1.5
    e = np.exp(-x * 0.9)
    return norm(lowpass(tone, 1500) * e + crackle * e + 0.6 * metal(len(x), [520, 1300], 0.25), 0.8)


def ambient(variant):
    d = 3.0
    x = t(d)
    hum = 0.5 * np.sin(2 * np.pi * 50 * x) + 0.25 * np.sin(2 * np.pi * 100 * x) + 0.15 * np.sin(2 * np.pi * 150 * x)
    buzz = bandpass(noise(len(x)), 800, 3000) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.7 + variant) * x)) * 0.25
    crackle = noise(len(x)) * (rng.random(len(x)) < 0.002) * 1.2
    breath = lowpass(noise(len(x)), 600) * (0.5 - 0.5 * np.cos(2 * np.pi * x / d)) * 0.8
    e = np.minimum(1, np.minimum(x / 0.4, (d - x) / 0.6))
    return norm((hum * 0.4 + buzz + crackle + breath * (variant == 1)) * e, 0.45)


def static():
    d = 1.2
    x = t(d)
    e = np.minimum(1, np.minimum(x / 0.02, (d - x) / 0.3))
    return norm(bandpass(noise(len(x)), 300, 7000) * e * (0.6 + 0.4 * (rng.random(len(x)) < 0.3)), 0.55)


def jumpscare():
    d = 1.7
    x = t(d)
    out = np.zeros(len(x))
    for base, wob in ((620, 37), (890, 53), (1270, 29), (430, 61)):
        f = base * (1 + 0.25 * np.sin(2 * np.pi * wob * x)) * (1 + 0.6 * x)
        ph = 2 * np.pi * np.cumsum(f) / SR
        out += 2 * ((ph / (2 * np.pi)) % 1) - 1
    out += 2.5 * bandpass(noise(len(x)), 900, 6000)
    out = np.tanh(out * 1.8)
    e = np.minimum(1, np.minimum(x / 0.01, (d - x) / 0.35))
    return norm(out * e, 0.98)


def engine(d, rpm_from, rpm_to, rough=0.3):
    """Small 4-stroke engine: firing pulses at rpm/120 Hz with exhaust noise and rattling sheet metal."""
    x = t(d)
    f = np.linspace(rpm_from, rpm_to, len(x)) / 120.0
    f *= 1 + rough * 0.15 * np.sin(2 * np.pi * 1.3 * x) + 0.05 * (rng.random(len(x)) - 0.5)
    ph = np.cumsum(f) / SR
    pulse = np.exp(-((ph % 1.0) * 9.0)) * (0.7 + 0.3 * rng.random(len(x)))
    exhaust = lowpass(noise(len(x)) * pulse, 900) * 3
    body = lowpass(pulse, 220) * 2
    rattle = bandpass(noise(len(x)), 1500, 4000) * pulse * 0.25
    return exhaust + body + rattle


def gen_run():
    d = 2.0
    out = engine(d, 3300, 3300)
    # seamless loop: crossfade the tail into the head
    n = int(SR * 0.15)
    fade = np.linspace(0, 1, n)
    out[:n] = out[:n] * fade + out[-n:] * (1 - fade)
    return norm(out[:-n], 0.6)


def gen_pull(success):
    d = 1.6 if not success else 2.2
    x = t(d)
    zip_n = int(SR * 0.45)
    zipf = np.linspace(900, 300, zip_n)
    rope = bandpass(noise(zip_n), 300, 3000) * (0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(zipf / 40) / SR * 40))
    out = np.zeros(len(x))
    out[:zip_n] += rope * np.linspace(1, 0.3, zip_n)
    eng = engine(d - 0.35, 600, 3300 if success else 200, rough=1.0)
    e = np.ones(len(eng))
    if not success:
        e = np.exp(-np.arange(len(eng)) / SR / 0.35)
    else:
        e = np.minimum(1, np.arange(len(eng)) / SR / 0.3)
    out[int(SR * 0.35):int(SR * 0.35) + len(eng)] += eng * e * 0.8
    return norm(out, 0.8)


def gen_stop():
    d = 2.2
    out = engine(d, 3300, 120, rough=0.8) * np.exp(-t(d) / 0.7)
    return norm(out, 0.7)


def power_down():
    d = 4.0
    x = t(d)
    f = 120 * np.exp(-x * 1.4) + 18
    ph = 2 * np.pi * np.cumsum(f) / SR
    hum = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sign(np.sin(3 * ph))) * np.exp(-x / 1.6)
    clunk = (metal(len(x), [90, 210, 470], 0.35) + lowpass(noise(len(x)), 300) * env(len(x), 0.001, 0.12) * 2)
    return norm(lowpass(hum, 1200) * 0.8 + clunk * 0.9, 0.95)


def click():
    n = int(SR * 0.08)
    return norm(lowpass(noise(n), 6000) * env(n, 0.0005, 0.006) + metal(n, [3200, 5100], 0.01) * 0.4, 0.7)


def write(name, data, out_dir=None):
    out_dir = out_dir or OUT
    os.makedirs(out_dir, exist_ok=True)
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, name + ".wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5",
                        os.path.join(out_dir, name + ".ogg")], check=True)


def main():
    sounds = {
        "step": [step(i) for i in range(3)],
        "servo": [servo(i) for i in range(2)],
        "hurt": [hurt()],
        "death": [death()],
        "ambient": [ambient(i) for i in range(2)],
        "static": [static()],
        "jumpscare": [jumpscare()],
    }
    spec = {}
    for name, variants in sounds.items():
        files = []
        for i, data in enumerate(variants):
            fname = f"{name}{i + 1}"
            write(fname, data)
            files.append(f"fnaf:animatronic/{fname}")
        spec[f"animatronic.{name}"] = {"subtitle": f"subtitles.fnaf.animatronic.{name}", "sounds": files}
    props = {
        "generator.run": [gen_run()],
        "generator.pull": [gen_pull(False), gen_pull(False)],
        "generator.start": [gen_pull(True)],
        "generator.stop": [gen_stop()],
        "power.down": [power_down()],
        "flashlight.click": [click()],
    }
    prop_dir = os.path.join(os.path.dirname(OUT), "prop")
    for name, variants in props.items():
        files = []
        for i, data in enumerate(variants):
            fname = f"{name.replace('.', '_')}{i + 1}"
            write(fname, data, prop_dir)
            files.append(f"fnaf:prop/{fname}")
        spec[name] = {"subtitle": f"subtitles.fnaf.{name}", "sounds": files}
    with open(os.path.join(ROOT, "src", "main", "resources", "assets", "fnaf", "sounds.json"), "w") as f:
        json.dump(spec, f, indent=2)
    print("wrote", sum(len(v) for v in sounds.values()), "sounds")


if __name__ == "__main__":
    main()
