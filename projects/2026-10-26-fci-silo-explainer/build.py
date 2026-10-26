#!/usr/bin/env python3
"""Assembles the FCI silo explainer Reel/Short (1080x1920).

  raw/aroll.*          your talking-head footage (IMG_5516.MOV)  -> required for the real edit
  raw/modi_clip.mp4    the Modi cutaway (screen recording)
  edit/gfx/*           rendered by graphics.py

Usage:
  python3 graphics.py            # once, or after editing on-screen copy
  python3 build.py               # final edit  -> exports/fci_silo_reel_9x16.mp4
  python3 build.py --preview     # no footage: 60s labelled stand-in A-roll -> exports/PREVIEW_*.mp4

Timing: TIMELINE positions are fractions of the A-roll length (they follow the script's
five points). Put absolute seconds in OVERRIDES once you know where each point is spoken.
"""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, "edit", "gfx")
EDIT = os.path.join(HERE, "edit")
EXPORTS = os.path.join(HERE, "exports")
W, H, FPS = 1080, 1920, 30
ENC = ["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]

# Section = chip (3s) followed by its B-roll cards, starting at this fraction of the A-roll.
TIMELINE = [
    {"pct": 0.00, "chip": "chip1", "broll": ["b1"]},        # FCI ₹20,000 cr programme
    {"pct": 0.15, "chip": "chip2", "broll": ["b2"]},        # anti-monopoly rule removed
    {"pct": 0.40, "chip": "chip3", "broll": ["b3", "b4"]},  # Phase 1: 70/80, ₹9,713 cr
    {"pct": 0.59, "chip": "chip4", "broll": ["b5"]},        # duopoly ₹16,500 cr
    {"pct": 0.76, "chip": "chip5", "broll": ["b6"]},        # critics vs FCI
]
MODI_PCT = 0.57          # Modi cutaway lands in the middle, right after the Phase-1 reveal
MODI_SRC = (1.0, 8.0)    # seconds of raw/modi_clip.mp4 to use
MODI_PUNCH = 2.0         # punch-in + boom, seconds into the cutaway (matches graphics.py)
HOOK_LEN = 3.6
OVERRIDES = {}           # e.g. {"chip2": 14.5, "modi": 33.0} in A-roll seconds


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"command failed:\n{' '.join(cmd)}\n{r.stderr[-3000:]}")
    return r


def probe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    return json.loads(r.stdout)


def duration(path):
    return float(probe(path)["format"]["duration"])


def silences(path):
    r = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=n=-32dB:d=0.25", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [(s + e) / 2 for s, e in zip(starts, ends)]


# ------------------------------------------------------------------ A-roll
def normalise_aroll(src, dst):
    info = probe(src)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = v["width"], v["height"]
    rot = 0
    for sd in v.get("side_data_list", []):
        rot = int(sd.get("rotation", rot) or 0)
    if abs(rot) == 90:
        w, h = h, w
    hdr = v.get("color_transfer") in ("arib-std-b67", "smpte2084")
    tm = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
          "zscale=t=bt709:m=bt709:r=tv,format=yuv420p," if hdr else "")
    if abs(w / h - W / H) < 0.08:  # already vertical: fill frame
        vf = f"[0:v]{tm}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v]"
    else:  # landscape/square: blurred fill behind the shot
        vf = (f"[0:v]{tm}split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"gblur=sigma=40,eq=brightness=-0.15[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2,setsar=1[v]")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src]
    if not has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-filter_complex", vf + ";[%s]aresample=48000,highpass=f=80,"
            "acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-1.5[a]"
            % ("0:a" if has_audio else "1:a"),
            "-map", "[v]", "-map", "[a]", "-shortest", *ENC, dst]
    run(cmd)
    print("A-roll:", f"{w}x{h}", "HDR->SDR" if hdr else "SDR", f"{duration(dst):.1f}s")


def preview_aroll(dst, secs=60):
    font = os.path.join(HERE, "assets", "fonts", "NotoDeva-900.ttf")
    dt = (f"drawtext=fontfile={font}:text='{{}}':fontcolor=white@0.55:fontsize={{}}:x=(w-tw)/2:y={{}}")
    vf = ",".join([
        dt.format("A-ROLL PLACEHOLDER", 64, "h*0.48"),
        dt.format("IMG_5516.MOV यहाँ आएगा", 54, "h*0.53"),
        "drawtext=fontfile=%s:text='%%{pts\\:hms}':fontcolor=white@0.5:fontsize=48:x=(w-tw)/2:y=h*0.6" % font,
    ])
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x2a3040:s={W}x{H}:r={FPS}:d={secs}",
         "-f", "lavfi", "-i", f"sine=f=180:r=48000:d={secs},volume=0.02,aformat=channel_layouts=stereo",
         "-vf", vf, "-shortest", *ENC, dst])


# ------------------------------------------------------------------ Modi cutaway
def build_modi(dst):
    a, b = MODI_SRC
    dur = b - a
    p = MODI_PUNCH
    shake = f"if(between(t,{p},{p}+0.35),18*sin(t*95),0)"
    # filters can't change frame size mid-stream, so the punch-in is a second, pre-zoomed
    # layer (right-aligned to keep both people in shot) switched on at MODI_PUNCH
    fc = (
        f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={FPS},crop=388:348:0:248,"
        "delogo=x=343:y=228:w=44:h=118,eq=contrast=1.08:saturation=1.15,split=3[s1][s2][s3];"
        f"[s1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=30,"
        "eq=brightness=-0.25:saturation=1.2[bg];"
        f"[s2]scale={W}:968:flags=lanczos,unsharp=5:5:0.8[fg];"
        f"[s3]scale={round(W * 1.18)}:{round(968 * 1.18)}:flags=lanczos,"
        f"crop={W}:968:x='iw-ow-20+{shake}':y='(ih-oh)*0.3',unsharp=5:5:0.8[zm];"
        "[bg][fg]overlay=0:476:shortest=1[b0];"
        f"[b0][zm]overlay=0:476:enable='gte(t,{p})'[base];"
        "[1:v]setpts=PTS-STARTPTS[cap];[base][cap]overlay=0:0:eof_action=pass,"
        # 2-frame white flash on the cut in
        "drawbox=c=white@1:t=fill:enable='lt(t,0.067)'[v];"
        f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,loudnorm=I=-16:TP=-1.5[ca];"
        f"[2:a]volume=0.55[w];[3:a]adelay={int(p * 1000)}|{int(p * 1000)},volume=0.9[bm];"
        "[ca][w][bm]amix=inputs=3:normalize=0:duration=first[a]"
    )
    run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(HERE, "raw", "modi_clip.mp4"),
         "-i", os.path.join(G, "modi_caption.mov"), "-i", os.path.join(G, "sfx_whoosh.wav"),
         "-i", os.path.join(G, "sfx_boom.wav"), "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-t", str(dur), *ENC, dst])


# ------------------------------------------------------------------ main pass
def plan(total):
    """Absolute A-roll times for every element; keeps sections from colliding."""
    events, cursor = [], HOOK_LEN + 0.2
    lens = {"b1": 3.6, "b2": 3.6, "b3": 4.0, "b4": 3.4, "b5": 3.6, "b6": 4.4}
    for sec in TIMELINE:
        t = OVERRIDES.get(sec["chip"], max(sec["pct"] * total, cursor))
        events.append(("chip", sec["chip"], t, 3.0))
        t += 3.1
        for b in sec["broll"]:
            t = OVERRIDES.get(b, t)
            events.append(("broll", b, t, lens[b]))
            t += lens[b]
        cursor = t + 0.6
    events.append(("cta", "cta", max(total - 4.0, cursor), 4.0))
    return events


def snap_modi(aroll, total, events):
    if "modi" in OVERRIDES:
        return OVERRIDES["modi"]
    busy = [(t, t + d) for kind, _, t, d in events if kind == "broll"]
    target = MODI_PCT * total
    for a, b in busy:  # never cut inside a B-roll card: push to just after it
        if a <= target <= b:
            target = b + 0.2
    # snap to the nearest pause in speech so the cut doesn't chop a word
    gaps = [s for s in silences(aroll) if abs(s - target) < 4 and not any(a <= s <= b for a, b in busy)]
    return min(gaps, key=lambda s: abs(s - target)) if gaps else target


def main_pass(aroll, total, events, dst):
    inputs = ["-i", aroll, "-i", os.path.join(G, "hook.mov")]
    sfx = {k: os.path.join(G, f"sfx_{k}.wav") for k in ("whoosh", "pop", "stamp")}
    # punch-in zoom on the talking head that alternates at every section
    cuts = [0.0] + [t for kind, _, t, _ in events if kind == "chip"]
    zoomed = "+".join(f"between(t,{cuts[i]:.3f},{cuts[i + 1] if i + 1 < len(cuts) else 1e9:.3f})"
                      for i in range(1, len(cuts), 2))
    fc = [f"[0:v]setsar=1,split[full][z];[z]scale={round(W * 1.12)}:{round(H * 1.12)},crop={W}:{H}[zin]",
          f"[full][zin]overlay=0:0:enable='{zoomed}'[v0]",
          "[1:v]setpts=PTS-STARTPTS[hk]", "[v0][hk]overlay=0:0:eof_action=pass[v1]"]
    last, n_in, aud = "v1", 2, ["[0:a]"]
    # B-roll first, overlays (chips/CTA) on top
    order = [e for e in events if e[0] == "broll"] + [e for e in events if e[0] != "broll"]
    for i, (kind, name, t, d) in enumerate(order):
        ext = "mp4" if kind == "broll" else "mov"
        inputs += ["-i", os.path.join(G, f"{name}.{ext}")]
        fc.append(f"[{n_in}:v]setpts=PTS-STARTPTS+{t:.3f}/TB[o{i}]")
        fc.append(f"[{last}][o{i}]overlay=0:0:eof_action=pass[v{i + 2}]")
        last, n_in = f"v{i + 2}", n_in + 1
        hits = [("whoosh" if kind == "broll" else "pop", t, 0.35 if kind == "broll" else 0.3)]
        if name == "b2":
            hits.append(("stamp", t + 1.1, 0.7))
        for s, at, vol in hits:
            inputs += ["-i", sfx[s]]
            ms = int(max(0, at - (0.15 if s == "whoosh" else 0)) * 1000)
            fc.append(f"[{n_in}:a]adelay={ms}|{ms},volume={vol}[s{n_in}]")
            aud.append(f"[s{n_in}]")
            n_in += 1
    for k, at in enumerate((0.0, 0.35, 0.9, 1.45)):  # hook word pops
        inputs += ["-i", sfx["pop"]]
        ms = int(at * 1000)
        fc.append(f"[{n_in}:a]adelay={ms}|{ms},volume=0.25[s{n_in}]")
        aud.append(f"[s{n_in}]")
        n_in += 1
    fc.append(f"{''.join(aud)}amix=inputs={len(aud)}:normalize=0:duration=first[a]")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
         "-map", f"[{last}]", "-map", "[a]", "-t", f"{total:.3f}", *ENC, dst])


def stitch(main, modi, cut, dst):
    fc = (f"[0:v]trim=0:{cut},setpts=PTS-STARTPTS[v1];[0:a]atrim=0:{cut},asetpts=PTS-STARTPTS[a1];"
          f"[0:v]trim={cut},setpts=PTS-STARTPTS[v2];[0:a]atrim={cut},asetpts=PTS-STARTPTS[a2];"
          "[1:v]setpts=PTS-STARTPTS[mv];[1:a]asetpts=PTS-STARTPTS[ma];"
          "[v1][a1][mv][ma][v2][a2]concat=n=3:v=1:a=1[v][ac];"
          "[ac]loudnorm=I=-14:TP=-1.0:LRA=9[a]")
    run(["ffmpeg", "-v", "error", "-y", "-i", main, "-i", modi, "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", *ENC, "-movflags", "+faststart", dst])


def main():
    preview = "--preview" in sys.argv
    os.makedirs(EXPORTS, exist_ok=True)
    if not os.path.exists(os.path.join(G, "hook.mov")):
        run([sys.executable, os.path.join(HERE, "graphics.py")])
    aroll = os.path.join(EDIT, "aroll_1080x1920.mp4")
    if preview:
        aroll = os.path.join(EDIT, "PREVIEW_standin_aroll.mp4")
        preview_aroll(aroll)
    else:
        src = sorted(glob.glob(os.path.join(HERE, "raw", "aroll.*")) + glob.glob(os.path.join(HERE, "raw", "IMG_5516.*")))
        if not src:
            sys.exit("Put the talking-head footage at raw/aroll.mov (or raw/IMG_5516.MOV), or run with --preview.")
        normalise_aroll(src[0], aroll)
    total = duration(aroll)
    events = plan(total)
    cut = snap_modi(aroll, total, events)
    for kind, name, t, d in events:
        print(f"  {t:6.1f}s  {kind:5s} {name}")
    print(f"  {cut:6.1f}s  MODI cutaway ({MODI_SRC[1] - MODI_SRC[0]:.0f}s)")
    modi = os.path.join(EDIT, "modi_insert.mp4")
    build_modi(modi)
    main_out = os.path.join(EDIT, "main_pass.mp4")
    main_pass(aroll, total, events, main_out)
    final = os.path.join(EXPORTS, ("PREVIEW_" if preview else "") + "fci_silo_reel_9x16.mp4")
    stitch(main_out, modi, cut, final)
    print("wrote", os.path.relpath(final, HERE), f"{duration(final):.1f}s")


if __name__ == "__main__":
    main()
