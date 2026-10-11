"""Find and fetch CC0 sounds from freesound.org (public HQ previews, no API key needed).

    python tools/sounds/freesound.py search "metal door slam" [min_dur] [max_dur]
    python tools/sounds/freesound.py get <id> <out.ogg> [start] [length] [gain_db] [extra ffmpeg filters]

Only CC0 ("Creative Commons 0") results are listed, so no attribution or licence restrictions apply.
Minecraft needs mono sounds for positional audio: get always converts to mono 44.1 kHz Vorbis.
"""
import html
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (fnaf-horror mod sound picker)"}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def search(query, min_dur=0.0, max_dur=1e9, pages=1):
    out = []
    for page in range(1, pages + 1):
        q = urllib.parse.urlencode({"q": query, "f": 'license:"Creative Commons 0"', "page": page})
        s = fetch("https://freesound.org/search/?" + q).decode("utf-8", "replace")
        for m in re.finditer(r'data-sound-id="(\d+)"\s+data-username="([^"]*)".*?data-mp3="([^"]+)".*?data-title="([^"]*)"\s+'
                             r'data-duration="([\d.]+)".*?data-num-downloads="(\d+)"', s, re.S):
            sid, user, mp3, title, dur, dl = m.groups()
            dur = float(dur)
            if min_dur <= dur <= max_dur:
                out.append(dict(id=sid, user=user, title=html.unescape(title), dur=dur, downloads=int(dl),
                                ogg=mp3.replace("-lq.mp3", "-hq.ogg")))
    return out


def preview_url(sid):
    s = fetch(f"https://freesound.org/s/{sid}/").decode("utf-8", "replace")
    m = re.search(r'https://cdn\.freesound\.org/previews/\d+/\d+_\d+-hq\.ogg', s) or \
        re.search(r'https://cdn\.freesound\.org/previews/\d+/\d+_\d+-lq\.mp3', s)
    if not m:
        raise SystemExit(f"no preview for {sid}")
    lic = re.search(r'Creative Commons 0|creativecommons\.org/publicdomain/zero', s)
    if not lic:
        raise SystemExit(f"sound {sid} is not CC0")
    return m.group(0).replace("-lq.mp3", "-hq.mp3")


def get(sid, out, start=0.0, length=None, gain_db=0.0, extra=""):
    data = fetch(preview_url(sid))
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src")
        with open(src, "wb") as f:
            f.write(data)
        filters = [f"atrim=start={start}" + (f":duration={length}" if length else ""), "asetpts=PTS-STARTPTS"]
        if extra:
            filters.append(extra)
        filters += ["loudnorm=I=-16:TP=-1.5", f"volume={gain_db}dB",
                    "afade=t=in:d=0.005", f"afade=t=out:st={max(0.0, (length or 9999) - 0.05)}:d=0.05" if length else "anull"]
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", ",".join(filters), "-ac", "1", "-ar", "44100",
                        "-c:a", "libvorbis", "-q:a", "5", out], check=True)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "search":
        lo = float(sys.argv[3]) if len(sys.argv) > 3 else 0
        hi = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
        for r in sorted(search(sys.argv[2], lo, hi, 2), key=lambda r: -r["downloads"])[:15]:
            print(f'{r["id"]:>7} {r["dur"]:6.1f}s {r["downloads"]:>6}dl  {r["title"][:60]}  ({r["user"]})')
    elif sys.argv[1] == "get":
        a = sys.argv[2:]
        get(a[0], a[1], float(a[2]) if len(a) > 2 else 0.0, float(a[3]) if len(a) > 3 and a[3] != "-" else None,
            float(a[4]) if len(a) > 4 else 0.0, a[5] if len(a) > 5 else "")
        print("ok", a[1])
