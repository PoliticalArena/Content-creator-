"""Vertical short edit: blurred-fill background, punch-in cuts, animated text,
motion-graphic b-roll inserts and synthesized SFX. Source watermarks are kept."""
import math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT, WORK = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS = 1080, 1920, 30
SW, SH = 884, 1920                       # source frame
VX, VY, VW, VH = 0, 712, 884, 494        # active picture inside source letterbox
DUR = 31.6           # source ends in phone UI at 31.7s
NF = int(DUR * FPS)
FG_W = W
FG_H = round(VH * W / VW)                # 618
FG_Y = (H - FG_H) // 2 - 40              # nudge up, leave room for bottom text

INTER_B = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
font = lambda p, s: ImageFont.truetype(p, s)

SAFFRON, WHITE, GREEN = (255, 153, 51), (255, 255, 255), (19, 136, 8)
RED, YELLOW, INK = (230, 30, 45), (255, 214, 0), (12, 12, 14)

# ---------- easing ----------
clamp = lambda x: max(0.0, min(1.0, x))
def ease_out_back(x, s=1.70158):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2
def ease_out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3
def ease_in_cubic(x):
    return clamp(x) ** 3

# ---------- edit decisions ----------
# punch-in cuts (time, zoom); zoom anchored top-right so the ANI credit stays in frame
ZOOMS = [(0.0, 1.0), (4.6, 1.14), (7.8, 1.0), (13.2, 1.12), (17.6, 1.0),
         (21.4, 1.15), (25.4, 1.0), (28.0, 1.10)]
BROLL = [(10.3, 11.7, "army"), (25.0, 26.4, "brief")]   # placed on speech pauses
NAME = (3.0, 8.4)
CALLOUTS = [(12.0, 16.0, "WATCH TILL THE END"), (18.5, 23.5, "EVERY WORD MATTERS")]
CTA = (28.4, DUR)
HOOK = ["ARMY", "OFFICER", "SPEAKS"]


def zoom_at(t):
    z = 1.0
    for ts, zz in ZOOMS:
        if t >= ts:
            z, start = zz, ts
    # tiny ease into each new zoom for a "snap" feel
    prev = 1.0
    for i, (ts, zz) in enumerate(ZOOMS):
        if ts == start and i:
            prev = ZOOMS[i - 1][1]
    k = ease_out_cubic((t - start) / 0.12)
    return prev + (z - prev) * k


def shake_at(t):
    hits = [ts for ts, _ in ZOOMS[1:]] + [b[0] for b in BROLL] + [b[1] for b in BROLL] + [0.05]
    for h in hits:
        d = t - h
        if 0 <= d < 0.25:
            a = 10 * (1 - d / 0.25)
            return a * math.sin(d * 90), a * math.cos(d * 70)
    return 0, 0


# ---------- text helpers ----------
def text_layer(txt, fnt, fill, stroke=0, stroke_fill=INK, shadow=True):
    l, t, r, b = fnt.getbbox(txt, stroke_width=stroke)
    pad = 30
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 6, pad - t + 8), txt, font=fnt, fill=(0, 0, 0, 170),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
        d = ImageDraw.Draw(im)
    d.text((pad - l, pad - t), txt, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def paste_scaled(canvas, layer, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    lw, lh = layer.size
    im = layer.resize((max(1, int(lw * scale)), max(1, int(lh * scale))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BILINEAR)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def pill(txt, fnt, bg, fg, padx=28, pady=14, dot=False):
    l, t, r, b = fnt.getbbox(txt)
    tw, th = r - l, b - t
    extra = 34 if dot else 0
    im = Image.new("RGBA", (tw + padx * 2 + extra, th + pady * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=im.height // 2, fill=bg)
    if dot:
        cy = im.height // 2
        d.ellipse((padx - 4, cy - 9, padx + 14, cy + 9), fill=fg)
    d.text((padx + extra - l, pady - t), txt, font=fnt, fill=fg)
    return im


# pre-render static text
F_HOOK = font(INTER_B, 128)
hook_layers = [text_layer(w, F_HOOK, YELLOW if i == 2 else WHITE, stroke=6) for i, w in enumerate(HOOK)]
kicker = pill("PRESS BRIEFING", font(INTER_XB, 40), RED, WHITE, dot=True)
header = text_layer("INDIAN ARMY", font(INTER_B, 96), WHITE, stroke=4)
name_main = text_layer("GIRISH KALIA", font(INTER_B, 64), INK, shadow=False)
name_sub = text_layer("INDIAN ARMY", font(INTER_XB, 34), WHITE, shadow=False)
callout_layers = {c[2]: text_layer(c[2], font(INTER_B, 78), WHITE, stroke=5) for c in CALLOUTS}
cta_top = text_layer("FOLLOW", font(INTER_B, 120), YELLOW, stroke=6)
cta_bot = text_layer("FOR MORE UPDATES", font(INTER_XB, 62), WHITE, stroke=4)
credit = text_layer("Video: ANI", font(INTER_SB, 30), (255, 255, 255, 190), shadow=False)
broll_txt = {
    "army": (text_layer("INDIAN", font(INTER_B, 120), WHITE, stroke=7),
             text_layer("ARMY", font(INTER_B, 140), WHITE, stroke=7)),
    "brief": (text_layer("OFFICIAL", font(INTER_B, 120), WHITE, stroke=5),
              text_layer("STATEMENT", font(INTER_B, 130), YELLOW, stroke=6)),
}


# ---------- b-roll motion graphics (drawn over the picture area) ----------
def draw_broll(canvas, kind, p):
    """p in [0,1] across the insert."""
    x0, y0, x1, y1 = 0, FG_Y, W, FG_Y + FG_H
    g = Image.new("RGBA", (W, FG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    # base: deep navy with moving grid
    d.rectangle((0, 0, W, FG_H), fill=(10, 18, 32, 255))
    off = int(p * 120)
    for gx in range(-120, W + 120, 60):
        d.line((gx + off, 0, gx + off, FG_H), fill=(40, 70, 110, 90), width=1)
    for gy in range(0, FG_H, 60):
        d.line((0, gy, W, gy), fill=(40, 70, 110, 90), width=1)
    cx, cy = W // 2, FG_H // 2
    if kind == "army":
        # tricolor bands sweeping in from the left
        for i, col in enumerate((SAFFRON, WHITE, GREEN)):
            k = ease_out_cubic((p - i * 0.06) / 0.35)
            bh = FG_H // 3
            d.rectangle((0, i * bh, int(W * k), (i + 1) * bh), fill=col + (215,))
        # ashoka-style ring
        k = ease_out_back((p - 0.15) / 0.4)
        r = int(62 * k)
        if r > 2:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(0, 0, 128, 255), width=8)
            for s in range(24):
                a = s / 24 * 2 * math.pi + p * 2
                d.line((cx, cy, cx + r * math.cos(a), cy + r * math.sin(a)), fill=(0, 0, 128, 255), width=3)
        g = g.filter(ImageFilter.GaussianBlur(0))
        top, bot = broll_txt["army"]
        ty = ease_out_back((p - 0.2) / 0.35)
        ga = Image.new("RGBA", g.size, (0, 0, 0, 0))
        paste_scaled(ga, top, cx, cy - 200, 0.6 + 0.4 * ty, clamp(ty))
        paste_scaled(ga, bot, cx, cy + 195, 0.6 + 0.4 * ease_out_back((p - 0.3) / 0.35), clamp((p - 0.3) / 0.2))
        g = Image.alpha_composite(g, ga)
    else:
        # radar pulse rings + scanning line
        for i in range(4):
            rp = (p * 1.6 + i / 4) % 1
            r = int(40 + rp * 520)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(0, 230, 160, int(200 * (1 - rp))), width=4)
        ang = p * 4 * math.pi
        d.line((cx, cy, cx + 900 * math.cos(ang), cy + 900 * math.sin(ang)), fill=(0, 230, 160, 160), width=5)
        # red alert bars top/bottom
        bar = int(46 * ease_out_cubic(p / 0.2))
        d.rectangle((0, 0, W, bar), fill=RED + (230,))
        d.rectangle((0, FG_H - bar, W, FG_H), fill=RED + (230,))
        top, bot = broll_txt["brief"]
        ga = Image.new("RGBA", g.size, (0, 0, 0, 0))
        k1, k2 = ease_out_back((p - 0.1) / 0.3), ease_out_back((p - 0.22) / 0.3)
        paste_scaled(ga, top, cx - (1 - clamp(k1)) * 600, cy - 90, 1.0, clamp(k1))
        paste_scaled(ga, bot, cx + (1 - clamp(k2)) * 600, cy + 80, 1.0, clamp(k2))
        g = Image.alpha_composite(g, ga)
    # in/out: white flash + slide
    a_in, a_out = clamp(p / 0.08), clamp((1 - p) / 0.08)
    alpha = min(a_in, a_out)
    if alpha < 1:
        g.putalpha(g.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(g, (0, y0))
    flash = max(1 - p / 0.06, 1 - (1 - p) / 0.06, 0)
    if flash > 0:
        fl = Image.new("RGBA", (W, FG_H), (255, 255, 255, int(200 * flash)))
        canvas.alpha_composite(fl, (0, y0))


# ---------- per-frame composition ----------
LOGO_MASK = Image.new("L", (150, 48), 0)
ImageDraw.Draw(LOGO_MASK).rounded_rectangle((8, 6, 142, 42), radius=10, fill=255)
LOGO_MASK = LOGO_MASK.filter(ImageFilter.GaussianBlur(4))

def compose(src, t):
    pic = src.crop((VX, VY, VX + VW, VY + VH))
    # remove CapCut app mark (top-left, whole clip): heal from the strip just below it
    patch = pic.crop((150, 4, 300, 52)).filter(ImageFilter.GaussianBlur(2))
    pic.paste(patch, (2, 4), LOGO_MASK)

    # background: blurred, darkened fill
    small = pic.resize((54, 31), Image.BILINEAR)
    bg_h = H
    bg_w = int(bg_h * VW / VH)
    bg = small.filter(ImageFilter.GaussianBlur(2)).resize((bg_w, bg_h), Image.BICUBIC)
    bg = bg.crop(((bg_w - W) // 2, 0, (bg_w - W) // 2 + W, H))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.55)
    canvas = bg.convert("RGBA")

    # foreground with top-right anchored punch-in
    z = zoom_at(t)
    cw, ch = VW / z, VH / z
    fg = pic.resize((FG_W, FG_H), Image.BICUBIC, box=(VW - cw, 0, VW, ch))
    sx, sy = shake_at(t)
    canvas.paste(fg, (int(sx), FG_Y + int(sy)))
    d = ImageDraw.Draw(canvas)
    # thin accent lines framing the picture
    d.rectangle((0, FG_Y - 6, W, FG_Y - 1), fill=SAFFRON)
    d.rectangle((0, FG_Y + FG_H, W, FG_Y + FG_H + 5), fill=GREEN)

    top_cy = FG_Y // 2 + 20
    # ---- hook (0 - 2.6s): word-by-word pop
    if t < 2.9:
        out = clamp((2.9 - t) / 0.3)
        for i, layer in enumerate(hook_layers):
            ts = 0.1 + i * 0.32
            k = ease_out_back((t - ts) / 0.28, 2.4)
            paste_scaled(canvas, layer, W / 2, top_cy - 170 + i * 150, k, clamp((t - ts) / 0.1) * out)
    # ---- persistent header after hook
    if t >= 2.6:
        k = ease_out_back((t - 2.6) / 0.4)
        paste_scaled(canvas, kicker, W / 2, top_cy - 90, k, clamp((t - 2.6) / 0.15))
        k2 = ease_out_cubic((t - 2.75) / 0.4)
        paste_scaled(canvas, header, W / 2, top_cy + 40 + (1 - k2) * 60, 1.0, k2)
        # underline sweep
        uw = int(520 * ease_out_cubic((t - 3.0) / 0.5))
        if uw > 0:
            uy = top_cy + 115
            d.rounded_rectangle((W / 2 - uw / 2, uy, W / 2 + uw / 2, uy + 10), radius=5, fill=YELLOW)

    # ---- lower-third name card (on the picture)
    if NAME[0] <= t <= NAME[1]:
        k_in = ease_out_cubic((t - NAME[0]) / 0.45)
        k_out = ease_in_cubic((t - (NAME[1] - 0.4)) / 0.4)
        slide = (1 - k_in) * -720 + k_out * -720
        by = FG_Y + FG_H - 190
        card = Image.new("RGBA", (W, 170), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rectangle((40, 10, 40 + 12, 150), fill=SAFFRON)
        cd.rectangle((52, 10, 52 + 560, 95), fill=(255, 255, 255, 245))
        cd.rectangle((52, 95, 52 + 330, 150), fill=GREEN + (245,))
        card.alpha_composite(name_main, (52 + 4, 10 - 12))
        card.alpha_composite(name_sub, (52 - 6, 95 - 22))
        canvas.alpha_composite(card, (int(slide), by))

    # ---- b-roll inserts
    for b0, b1, kind in BROLL:
        if b0 <= t <= b1:
            draw_broll(canvas, kind, (t - b0) / (b1 - b0))

    bot_cy = FG_Y + FG_H + (H - FG_Y - FG_H) // 2 - 40
    # ---- callouts (bottom zone)
    for c0, c1, txt in CALLOUTS:
        if c0 <= t <= c1:
            k = ease_out_back((t - c0) / 0.35, 2.2)
            out = clamp((c1 - t) / 0.25)
            wob = math.sin((t - c0) * 6) * 1.5
            paste_scaled(canvas, callout_layers[txt], W / 2, bot_cy, k * (1 + 0.02 * math.sin((t - c0) * 8)), out, wob)

    # ---- CTA
    if t >= CTA[0]:
        k = ease_out_back((t - CTA[0]) / 0.4, 2.6)
        pulse = 1 + 0.05 * math.sin((t - CTA[0]) * 9)
        paste_scaled(canvas, cta_top, W / 2, bot_cy - 50, k * pulse, clamp((t - CTA[0]) / 0.1))
        k2 = ease_out_cubic((t - CTA[0] - 0.25) / 0.35)
        paste_scaled(canvas, cta_bot, W / 2, bot_cy + 70 + (1 - k2) * 50, 1.0, k2)

    # ---- source credit + retention progress bar
    canvas.alpha_composite(credit, (W - credit.width - 20, FG_Y + FG_H + 12))
    pw = int(W * t / DUR)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, H - 14, W, H), fill=(255, 255, 255, 40))
    d.rectangle((0, H - 14, pw, H), fill=YELLOW)
    return canvas.convert("RGB")


# ---------- SFX ----------
SR = 48000
def env(n, a=0.005, r=0.3):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / r)

def whoosh(dur=0.45, up=True):
    n = int(dur * SR)
    noise = np.random.randn(n)
    out = np.zeros(n)
    # sweeping one-pole lowpass
    y = 0
    for i in range(n):
        f = i / n if up else 1 - i / n
        a = 0.02 + 0.5 * f
        y += a * (noise[i] - y)
        out[i] = y
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    return out * shape * 1.2

def boom(dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 55 + 70 * np.exp(-t * 18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.28)
    s += np.random.randn(n) * env(n, 0.001, 0.03) * 0.4
    return s

def pop(freq=900, dur=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    f = freq * (1 + 1.5 * np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.035)

def ding(dur=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1320 * t) + 0.5 * np.sin(2 * np.pi * 2640 * t)) * env(n, 0.002, 0.25) * 0.5

def tick():
    n = int(0.05 * SR)
    return np.random.randn(n) * env(n, 0.0005, 0.008) * 0.6

def riser(dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 200 + 900 * (t / dur) ** 2
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + whoosh(dur, True)[:n] * 0.6
    return s * (t / dur) ** 1.5

def build_sfx():
    total = int((DUR + 1) * SR)
    mix = np.zeros(total)
    def add(sig, at, gain):
        i = int(at * SR)
        j = min(total, i + len(sig))
        mix[i:j] += sig[: j - i] * gain
    np.random.seed(7)
    add(boom(), 0.05, 0.55)
    add(whoosh(0.35), 0.0, 0.35)
    for i in range(len(HOOK)):
        add(pop(700 + i * 180), 0.1 + i * 0.32, 0.45)
    add(pop(1200), 2.6, 0.3)
    add(whoosh(0.45), NAME[0] - 0.05, 0.35)
    add(whoosh(0.4, False), NAME[1] - 0.4, 0.25)
    for ts, _ in ZOOMS[1:]:
        add(tick(), ts, 0.5)
    for b0, b1, _ in BROLL:
        add(whoosh(0.4), b0 - 0.25, 0.45)
        add(boom(0.6), b0 + 0.05, 0.35)
        add(whoosh(0.35, False), b1 - 0.1, 0.35)
    for c0, _, _ in CALLOUTS:
        add(ding(), c0, 0.3)
    add(riser(1.2), CTA[0] - 1.2, 0.35)
    add(boom(), CTA[0], 0.45)
    add(pop(1000), CTA[0] + 0.25, 0.4)
    peak = np.max(np.abs(mix))
    mix = mix / peak * 0.5
    wf = wave.open(f"{WORK}/sfx.wav", "wb")
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((mix * 32767).astype(np.int16).tobytes())
    wf.close()


def main():
    build_sfx()
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={FPS}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", SRC, "-i", f"{WORK}/sfx.wav",
        "-filter_complex",
        f"[1:a]aresample=48000,highpass=f=80,acompressor=threshold=-20dB:ratio=3:makeup=3,"
        "loudnorm=I=-15:TP=-1.5:LRA=9[v];"
        f"[2:a]aresample=48000,volume=0.9[s];"
        f"[v][s]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95,apad,afade=t=out:st={DUR-0.35}:d=0.35[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(NF / FPS), OUT],
        stdin=subprocess.PIPE)
    fsize = SW * SH * 3
    i = 0
    while i < NF:
        buf = dec.stdout.read(fsize)
        if len(buf) < fsize:
            break
        src = Image.frombuffer("RGB", (SW, SH), buf)
        enc.stdin.write(compose(src.copy(), i / FPS).tobytes())
        i += 1
        if i % 150 == 0:
            print("frame", i, flush=True)
    enc.stdin.close(); enc.wait(); dec.kill()
    print("done", i, "frames")


if __name__ == "__main__":
    if len(sys.argv) > 4:   # preview mode: render stills at given times
        cap = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={FPS}", "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        fsize = SW * SH * 3
        for ts in map(float, sys.argv[4].split(",")):
            fi = int(ts * FPS)
            src = Image.frombuffer("RGB", (SW, SH), cap[fi * fsize:(fi + 1) * fsize]).copy()
            compose(src, ts).save(f"{WORK}/prev_{ts:.1f}.jpg", quality=85)
    else:
        main()
