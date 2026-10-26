#!/usr/bin/env python3
"""Renders every motion-graphics element for the FCI silo explainer.

Outputs (edit/gfx/):
  hook.mov, chip1-5.mov, cta.mov, modi_caption.mov  -> 1080x1920 overlays with alpha
  b1-b6.mp4                                         -> 1080x1920 full-screen B-roll cards
  sfx_*.wav                                         -> whoosh / pop / boom / stamp

All on-screen copy lives in COPY below; edit it and re-run.
Usage: python3 graphics.py [name ...]   (no args = render everything)
"""
import math
import os
import subprocess
import sys
import wave
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "edit", "gfx")
FONT_DIR = os.path.join(HERE, "assets", "fonts")
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
W, H, FPS = 1080, 1920, 30

NAVY = (11, 16, 32)
NAVY2 = (22, 32, 64)
YELLOW = (255, 212, 0)
RED = (255, 59, 48)
ORANGE = (255, 140, 26)
GREEN = (52, 199, 89)
WHITE = (255, 255, 255)
GREY = (120, 128, 150)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------- on-screen copy
COPY = {
    "hook": ["₹20,000 करोड़ का", "अनाज प्रोजेक्ट…", "80 में से 70 ठेके", "सिर्फ़ एक कंपनी को?"],
    "chips": [
        "FCI का ₹20,000 करोड़ साइलो प्लान",
        "मई 2022: एंटी-मोनोपोली नियम हटा",
        "Phase 1: 70/80 ठेके अडानी को",
        "₹16,500 करोड़+ सिर्फ़ 2 कंपनियों को",
        "चिंताएँ बनाम FCI का जवाब",
    ],
    "source": "स्रोत: मीडिया रिपोर्ट्स",
    "cta": ["आपकी क्या राय है?", "कमेंट करें  •  फ़ॉलो करें"],
    "meme": ["MEANWHILE...", "इसी बीच मंच पर…"],
}


# ---------------------------------------------------------------- helpers
@lru_cache(None)
def font(size, weight=900):
    name = {700: "NotoDeva-700.ttf", 900: "NotoDeva-900.ttf", "anton": "Anton.ttf"}[weight]
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size, layout_engine=ImageFont.Layout.RAQM)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_in_out(x):
    return 0.5 - 0.5 * math.cos(math.pi * x)


def inr(n):
    """Indian digit grouping: 20000 -> 20,000; 1234567 -> 12,34,567."""
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


@lru_cache(512)
def text_layer(text, size, weight=900, fill=WHITE, stroke=0, stroke_fill=BLACK):
    f = font(size, weight)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = 8 + stroke
    img = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - l, pad - t), text, font=f, fill=fill,
                             stroke_width=stroke, stroke_fill=stroke_fill)
    return img


@lru_cache(64)
def emoji_layer(ch, px):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10, 10), ch, font=f, embedded_color=True)
    img = img.crop(img.getbbox())
    return img.resize((px, int(px * img.height / img.width)), Image.LANCZOS)


def paste(canvas, layer, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    """Alpha-composite `layer` centred at (cx, cy)."""
    if alpha <= 0.003 or scale <= 0.01:
        return
    lay = layer
    if abs(scale - 1) > 1e-3:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BICUBIC)
    if angle:
        lay = lay.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999:
        a = lay.getchannel("A").point(lambda v: int(v * alpha))
        lay = lay.copy()
        lay.putalpha(a)
    canvas.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


def text(canvas, s, size, cx, cy, weight=900, fill=WHITE, stroke=0, scale=1.0, alpha=1.0, angle=0.0):
    paste(canvas, text_layer(s, size, weight, fill, stroke), cx, cy, scale, alpha, angle)


def wrap(s, size, weight, max_w):
    f = font(size, weight)
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if f.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def pill(w, h, fill, radius=None, ss=2):
    radius = h // 2 if radius is None else radius
    img = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius * ss, fill=fill)
    return img.resize((w, h), Image.LANCZOS)


@lru_cache(4)
def background(seed=0):
    """Navy vertical gradient with a faint grid and vignette (B-roll base)."""
    y = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(NAVY2, float), np.array(NAVY, float)
    arr = (top * (1 - y) + bot * y) * np.ones((1, W, 1))
    arr[::90, :, :] += 7
    arr[:, ::90, :] += 7
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
    arr *= (1 - 0.55 * d ** 1.6)[:, :, None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return img


def source_tag(canvas, alpha=1.0):
    text(canvas, COPY["source"], 30, W / 2, H - 150, weight=700, fill=(190, 196, 215), alpha=alpha)


class Writer:
    def __init__(self, name, alpha):
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, name)
        codec = ["-c:v", "qtrle"] if alpha else ["-c:v", "libx264", "-crf", "16", "-preset", "medium",
                                                  "-pix_fmt", "yuv420p"]
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", *codec, path], stdin=subprocess.PIPE)
        self.path = path

    def frame(self, img):
        self.p.stdin.write(img.tobytes())

    def close(self):
        self.p.stdin.close()
        if self.p.wait():
            raise SystemExit(f"ffmpeg failed for {self.path}")
        print("wrote", os.path.relpath(self.path, HERE))


def render(name, dur, draw, alpha):
    wr = Writer(name, alpha)
    for i in range(int(round(dur * FPS))):
        t = i / FPS
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if alpha else background().copy()
        draw(img, t, dur)
        wr.frame(img)
    wr.close()


def out_fade(t, dur, d=0.25):
    return 1 - prog(t, dur - d, d)


# ---------------------------------------------------------------- overlays
def draw_hook(img, t, dur):
    fo = out_fade(t, dur)
    # top gradient so text reads over any footage
    grad = np.zeros((900, W, 4), np.uint8)
    grad[..., 3] = (np.linspace(200, 0, 900) ** 1.0)[:, None].astype(np.uint8)
    g = Image.fromarray(grad, "RGBA")
    if fo < 1:
        g.putalpha(g.getchannel("A").point(lambda v: int(v * fo)))
    img.alpha_composite(g)
    l1, l2, l3, l4 = COPY["hook"]
    lift = -60 * (1 - fo)
    # line 1 & 2: word-by-word pop
    for li, (line, y, t0) in enumerate(((l1, 330, 0.0), (l2, 450, 0.35))):
        words = line.split()
        f = font(92, 900)
        total = f.getlength(line)
        x = W / 2 - total / 2
        for wi, w in enumerate(words):
            ww = f.getlength(w)
            p = prog(t, t0 + wi * 0.11, 0.22)
            col = YELLOW if "₹" in w else WHITE
            text(img, w, 92, x + ww / 2, y + lift, fill=col, stroke=6,
                 scale=0.4 + 0.6 * ease_out_back(p), alpha=min(p * 3, 1) * fo)
            x += ww + f.getlength(" ")
    # line 3: slam on yellow box
    p = prog(t, 0.9, 0.22)
    if p > 0:
        lay = text_layer(l3, 118, 900, BLACK)
        box = pill(lay.width + 70, lay.height + 30, YELLOW, radius=26)
        box.alpha_composite(lay, (35, 15))
        sc = 1.8 - 0.8 * ease_out_cubic(p)
        shake = 10 * math.sin(t * 90) * (1 - prog(t, 1.12, 0.2)) if p >= 1 else 0
        paste(img, box, W / 2 + shake, 615 + lift, scale=sc, alpha=min(p * 2, 1) * fo, angle=-2)
    # line 4: red question
    p = prog(t, 1.45, 0.3)
    text(img, l4, 86, W / 2 - 50, 790 + lift + 40 * (1 - ease_out_cubic(p)), fill=RED, stroke=7,
         alpha=p * fo, scale=0.9 + 0.1 * ease_out_back(p))
    if p > 0:
        ex = W / 2 - 50 + font(86, 900).getlength(l4) / 2 + 70
        paste(img, emoji_layer("🤯", 100), ex, 780 + lift, scale=ease_out_back(prog(t, 1.7, 0.3)),
              alpha=fo)


def make_chip(n):
    label = COPY["chips"][n - 1]

    def draw(img, t, dur):
        pin = ease_out_cubic(prog(t, 0, 0.35))
        pout = 1 - ease_in_out(prog(t, dur - 0.3, 0.3))
        a = min(pin, pout)
        lay = text_layer(label, 52, 900, WHITE)
        bw = lay.width + 150
        body = pill(bw, 104, (11, 16, 32, 230))
        body.alpha_composite(lay, (120, (104 - lay.height) // 2))
        badge = pill(84, 84, YELLOW)
        num = text_layer(str(n), 52, 900, BLACK)
        badge.alpha_composite(num, ((84 - num.width) // 2, (84 - num.height) // 2))
        body.alpha_composite(badge, (10, 10))
        x = W / 2 - (1 - a) * (W / 2 + bw / 2)
        paste(img, body, x, 300, alpha=a)
    return draw


def draw_cta(img, t, dur):
    l1, l2 = COPY["cta"]
    p1 = prog(t, 0, 0.35)
    fo = out_fade(t, dur, 0.3)
    lay = text_layer(l1, 78, 900, BLACK)
    box = pill(lay.width + 90, lay.height + 40, (255, 255, 255, 245), radius=30)
    box.alpha_composite(lay, (45, 20))
    paste(img, box, W / 2, 1300, scale=0.5 + 0.5 * ease_out_back(p1), alpha=min(1, p1 * 2) * fo)
    p2 = prog(t, 0.35, 0.35)
    lay2 = text_layer(l2, 58, 900, BLACK)
    btn = pill(lay2.width + 80, lay2.height + 36, YELLOW)
    btn.alpha_composite(lay2, (40, 18))
    pulse = 1 + 0.04 * math.sin(max(0, t - 0.7) * 8)
    paste(img, btn, W / 2, 1440, scale=(0.5 + 0.5 * ease_out_back(p2)) * pulse, alpha=min(1, p2 * 2) * fo)
    paste(img, emoji_layer("👇", 90), W / 2, 1560 + 14 * math.sin(t * 7), alpha=p2 * fo)


def draw_modi_caption(img, t, dur):
    """Meme-style text for the Modi cutaway. Punch-in moment at 2.0s matches build.py."""
    fo = out_fade(t, dur, 0.2)
    en, hi = COPY["meme"]
    p = prog(t, 0.05, 0.25)
    text(img, en, 150, W / 2, 250, weight="anton", fill=WHITE, stroke=9,
         scale=1.4 - 0.4 * ease_out_cubic(p), alpha=p * fo)
    p = prog(t, 0.45, 0.3)
    text(img, hi, 74, W / 2, 400, fill=YELLOW, stroke=6, alpha=p * fo, scale=0.8 + 0.2 * ease_out_back(p))
    for i, (ch, x, y, t0) in enumerate((("😂", 180, 1520, 2.0), ("😂", 900, 1460, 2.15), ("👀", 540, 1600, 4.2))):
        q = prog(t, t0, 0.25)
        bob = 10 * math.sin((t - t0) * 9 + i)
        paste(img, emoji_layer(ch, 150), x, y + bob, scale=ease_out_back(q), alpha=fo, angle=(-12, 10, 0)[i])


# ---------------------------------------------------------------- B-roll cards
def draw_b1(img, t, dur):
    """FCI ₹20,000 crore counter with silos rising."""
    fo = out_fade(t, dur, 0.2)
    p = prog(t, 0, 0.3)
    text(img, "भारतीय खाद्य निगम (FCI)", 58, W / 2, 330, weight=700, fill=(200, 206, 225), alpha=p * fo)
    c = ease_out_cubic(prog(t, 0.2, 1.4))
    val = f"₹{inr(20000 * c)}"
    text(img, val, 190, W / 2, 560, fill=YELLOW, stroke=0, alpha=fo,
         scale=1 + 0.08 * math.sin(math.pi * prog(t, 1.6, 0.25)))
    text(img, "करोड़", 110, W / 2, 740, fill=WHITE, alpha=min(1, c * 3) * fo)
    p = prog(t, 1.2, 0.35)
    text(img, "अनाज भंडारण का 'साइलो' प्रोग्राम", 60, W / 2, 900, weight=700, alpha=p * fo)
    # silos
    ss = 2
    layer = Image.new("RGBA", (W * ss, 700 * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    base = 680 * ss
    for i, (cx, hgt) in enumerate(((250, 420), (430, 520), (650, 520), (830, 420))):
        g = ease_out_back(prog(t, 0.3 + i * 0.12, 0.6), 1.3)
        h = int(hgt * g * ss)
        if h <= 0:
            continue
        w2 = 80 * ss
        x0, x1 = cx * ss - w2, cx * ss + w2
        d.rectangle((x0, base - h, x1, base), fill=(196, 202, 214))
        d.rectangle((x0, base - h, x0 + 30 * ss, base), fill=(160, 166, 180))
        for k in range(1, 6):
            yy = base - h + k * h // 6
            d.line((x0, yy, x1, yy), fill=(140, 146, 160), width=3 * ss)
        d.pieslice((x0, base - h - w2, x1, base - h + w2), 180, 360, fill=(220, 225, 235))
        d.rectangle((cx * ss - 8 * ss, base - h - w2 - 30 * ss, cx * ss + 8 * ss, base - h - w2 + 4 * ss),
                    fill=(160, 166, 180))
    d.rectangle((0, base, W * ss, base + 20 * ss), fill=(245, 166, 35))
    layer = layer.resize((W, 700), Image.LANCZOS)
    if fo < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * fo)))
    img.alpha_composite(layer, (0, 1000))
    p = prog(t, 1.5, 0.3)
    text(img, "लक्ष्य: खाद्य सुरक्षा + बेहतर PDS", 48, W / 2, 1760, weight=700, fill=(255, 220, 150), alpha=p * fo)


def draw_b2(img, t, dur):
    """Anti-monopoly rule card gets stamped 'REMOVED'."""
    fo = out_fade(t, dur, 0.2)
    p = ease_out_back(prog(t, 0, 0.4), 1.4)
    card = pill(900, 640, (250, 250, 252, 255), radius=40)
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, 899, 120), 40, fill=(30, 40, 80))
    cd.rectangle((0, 60, 899, 120), fill=(30, 40, 80))
    hdr = text_layer("FCI टेंडर नियम", 52, 900, WHITE)
    card.alpha_composite(hdr, ((900 - hdr.width) // 2, (120 - hdr.height) // 2))
    ttl = text_layer("एंटी-मोनोपोली नियम", 84, 900, (20, 24, 40))
    card.alpha_composite(ttl, ((900 - ttl.width) // 2, 180))
    for k, line in enumerate(wrap("कोई एक कंपनी पूरे प्रोजेक्ट पर एकाधिकार न जमा सके", 50, 700, 780)):
        ly = text_layer(line, 50, 700, (70, 76, 95))
        card.alpha_composite(ly, ((900 - ly.width) // 2, 340 + k * 80))
    jolt = 0
    ps = prog(t, 1.1, 0.18)
    if ps >= 1:
        jolt = 14 * math.sin(t * 80) * (1 - prog(t, 1.28, 0.25))
    paste(img, card, W / 2 + jolt, 760, scale=0.6 + 0.4 * p, alpha=min(1, prog(t, 0, 0.2) * 2) * fo)
    if ps > 0:
        lay = text_layer("हटाया गया", 120, 900, RED)
        stamp = Image.new("RGBA", (lay.width + 80, lay.height + 50), (0, 0, 0, 0))
        ImageDraw.Draw(stamp).rounded_rectangle((4, 4, stamp.width - 5, stamp.height - 5), 24, outline=RED, width=12)
        stamp.alpha_composite(lay, (40, 25))
        paste(img, stamp, W / 2 + jolt, 900, scale=2.4 - 1.4 * ease_out_cubic(ps), alpha=min(1, ps * 1.5) * fo,
              angle=14)
    p = prog(t, 1.6, 0.35)
    text(img, "मई 2022 • नीति आयोग + DEA बैठक", 56, W / 2, 1230, fill=YELLOW, alpha=p * fo)
    p = prog(t, 2.0, 0.35)
    for k, line in enumerate(wrap("तर्क: “बाज़ार को स्वतंत्र रूप से काम करने दो”", 50, 700, 900)):
        text(img, line, 50, W / 2, 1340 + k * 72, weight=700, fill=(215, 220, 235), alpha=p * fo)
    source_tag(img, fo * prog(t, 0.3, 0.3))


def draw_b3(img, t, dur):
    """80-square grid: 70 go orange (AAL)."""
    fo = out_fade(t, dur, 0.2)
    text(img, "Phase 1 टेंडर • कुल 80 ठेके", 60, W / 2, 300, alpha=prog(t, 0, 0.3) * fo)
    cols, rows, sz, gap = 10, 8, 78, 12
    gw = cols * sz + (cols - 1) * gap
    x0, y0 = (W - gw) / 2, 420
    filled = int(70 * ease_in_out(prog(t, 0.5, 1.6)))
    shown = int(80 * prog(t, 0.0, 0.45))
    tile_o = pill(sz, sz, ORANGE + (255,), radius=14)
    tile_g = pill(sz, sz, (60, 70, 100, 255), radius=14)
    for i in range(shown):
        r, c = divmod(i, cols)
        tile = tile_o if i < filled else tile_g
        img.alpha_composite(tile if fo >= 1 else _fade(tile, fo),
                            (int(x0 + c * (sz + gap)), int(y0 + r * (sz + gap))))
    yb = y0 + rows * (sz + gap) + 60
    text(img, f"{filled} / 80 ठेके", 96, W / 2, yb + 40, fill=ORANGE, alpha=min(1, prog(t, 0.5, 0.2)) * fo)
    p = prog(t, 2.25, 0.3)
    text(img, "87.5%", 210, W / 2, yb + 240, fill=YELLOW, weight="anton", stroke=0,
         scale=1.6 - 0.6 * ease_out_back(p, 1.2) if p > 0 else 0, alpha=min(1, p * 2) * fo)
    p = prog(t, 2.6, 0.3)
    text(img, "अडानी एग्री लॉजिस्टिक्स लि. (AAL)", 54, W / 2, yb + 420, weight=700, alpha=p * fo)
    source_tag(img, fo * prog(t, 0.3, 0.3))


def _fade(layer, a):
    lay = layer.copy()
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    return lay


def draw_b4(img, t, dur):
    """Phase 1 money: ₹11,915 cr total vs ₹9,713 cr to Adani."""
    fo = out_fade(t, dur, 0.2)
    text(img, "Phase 1 के ठेकों की रकम", 66, W / 2, 420, alpha=prog(t, 0, 0.3) * fo)
    maxw, x0 = 860, (W - 860) // 2
    for k, (label, val, col, y, t0) in enumerate((("कुल ठेके", 11915, (90, 100, 135), 650, 0.2),
                                                  ("अडानी समूह को", 9713, ORANGE, 1000, 0.7))):
        p = ease_out_cubic(prog(t, t0, 1.0))
        text(img, label, 56, x0 + font(56, 700).getlength(label) / 2 + 4, y - 80, weight=700,
             alpha=prog(t, t0, 0.2) * fo)
        bw = int(maxw * val / 11915 * p)
        if bw > 4:
            img.alpha_composite(_fade(pill(bw, 120, col + (255,), radius=22), fo), (x0, y))
        v = text_layer(f"₹{inr(val * p)} करोड़", 64, 900, WHITE)
        paste(img, v, x0 + v.width / 2 + 24, y + 60 + 0, alpha=prog(t, t0, 0.2) * fo)
    p = prog(t, 1.9, 0.3)
    text(img, "लगभग 81.5% रकम एक ही समूह को", 70, W / 2, 1330, fill=YELLOW, stroke=0,
         scale=0.8 + 0.2 * ease_out_back(p), alpha=p * fo)
    source_tag(img, fo * prog(t, 0.3, 0.3))


def draw_b5(img, t, dur):
    """Donut: ₹16,500 cr+ of ₹20,000 cr to two companies."""
    fo = out_fade(t, dur, 0.2)
    text(img, "Phase 2 तक", 60, W / 2, 300, weight=700, fill=(200, 206, 225), alpha=prog(t, 0, 0.3) * fo)
    text(img, "दो कंपनियों का दबदबा", 84, W / 2, 400, alpha=prog(t, 0.1, 0.3) * fo)
    ss, R, th = 2, 330, 90
    lay = Image.new("RGBA", (2 * R * ss + 8, 2 * R * ss + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    box = (4, 4, 2 * R * ss + 3, 2 * R * ss + 3)
    d.arc(box, 0, 360, fill=(55, 65, 95), width=th * ss)
    p = ease_in_out(prog(t, 0.4, 1.3))
    frac = 16500 / 20000
    if p > 0:
        d.arc(box, -90, -90 + 360 * frac * p, fill=YELLOW, width=th * ss)
    lay = lay.resize((lay.width // ss, lay.height // ss), Image.LANCZOS)
    cy = 900
    paste(img, lay, W / 2, cy, alpha=fo, scale=0.85 + 0.15 * ease_out_back(prog(t, 0, 0.4)))
    text(img, f"₹{inr(16500 * p)}", 110, W / 2, cy - 30, fill=YELLOW, alpha=fo)
    text(img, "करोड़+  /  ₹20,000", 46, W / 2, cy + 70, weight=700, fill=(200, 206, 225), alpha=fo)
    p2 = prog(t, 1.7, 0.3)
    for k, (lbl, col) in enumerate((("अडानी + लीप इंडिया", YELLOW), ("बाक़ी सभी", (55, 65, 95)))):
        y = 1360 + k * 100
        img.alpha_composite(_fade(pill(56, 56, col + (255,), radius=12), p2 * fo), (230, y - 28))
        tl = text_layer(lbl, 58, 900 if k == 0 else 700, WHITE)
        paste(img, tl, 310 + tl.width / 2, y, alpha=p2 * fo)
    text(img, "DUOPOLY", 120, W / 2, 1640, weight="anton", fill=RED,
         scale=1.5 - 0.5 * ease_out_cubic(prog(t, 2.1, 0.25)), alpha=prog(t, 2.1, 0.2) * fo)
    source_tag(img, fo * prog(t, 0.3, 0.3))


def draw_b6(img, t, dur):
    """Both sides: critics vs FCI's response."""
    fo = out_fade(t, dur, 0.2)
    cards = (
        ("आलोचक / किसान संगठन (AIKS)", RED,
         "खाद्य सुरक्षा का ढांचा निजी मोनोपोली को — किसान और सरकार दोनों कॉर्पोरेट पर निर्भर होंगे", 520, -1, 0.0),
        ("FCI का जवाब", GREEN,
         "पक्षपात के आरोप ख़ारिज — टेंडर प्रक्रिया खुली और पारदर्शी थी", 1160, 1, 0.8),
    )
    for title, col, body, cy, side, t0 in cards:
        p = ease_out_cubic(prog(t, t0, 0.45))
        if p <= 0:
            continue
        lines = wrap(body, 54, 700, 840)
        card = pill(940, 190 + 84 * len(lines), (250, 250, 252, 255), radius=36)
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, 939, 110), 36, fill=col)
        cd.rectangle((0, 60, 939, 110), fill=col)
        tl = text_layer(title, 54, 900, WHITE)
        card.alpha_composite(tl, ((940 - tl.width) // 2, (110 - tl.height) // 2))
        for k, line in enumerate(lines):
            ly = text_layer(line, 54, 700, (25, 30, 45))
            card.alpha_composite(ly, ((940 - ly.width) // 2, 150 + k * 84))
        paste(img, card, W / 2 + side * (1 - p) * 1100, cy, alpha=fo)
    text(img, "VS", 110, W / 2, 840, weight="anton", fill=YELLOW, stroke=8,
         scale=ease_out_back(prog(t, 1.2, 0.3)), alpha=fo)
    source_tag(img, fo * prog(t, 0.3, 0.3))


# ---------------------------------------------------------------- sound effects
SR = 48000


def _wav(name, x):
    x = np.clip(x / (np.abs(x).max() + 1e-9) * 0.9, -1, 1)
    st = (np.stack([x, x], 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())
    print("wrote", os.path.relpath(os.path.join(OUT, name), HERE))


def make_sfx():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(7)
    # whoosh: band-swept noise with a swell
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out, lp = np.zeros(n), 0.0
    cut = 0.02 + 0.25 * np.sin(np.pi * t / t[-1]) ** 2
    for i in range(n):
        lp += cut[i] * (noise[i] - lp)
        out[i] = lp
    _wav("sfx_whoosh.wav", out * np.sin(np.pi * t / t[-1]) ** 1.5)
    # pop
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    _wav("sfx_pop.wav", np.sin(2 * np.pi * (900 - 5000 * t) * t) * np.exp(-t * 45))
    # boom (meme bass hit)
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    f = 38 + 60 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    click = rng.standard_normal(n) * np.exp(-t * 60) * 0.5
    _wav("sfx_boom.wav", np.tanh(2.2 * (body + click)))
    # stamp: thud + short noise
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    _wav("sfx_stamp.wav", np.sin(2 * np.pi * 70 * t) * np.exp(-t * 16) + rng.standard_normal(n) * np.exp(-t * 40) * 0.6)


# ---------------------------------------------------------------- registry
JOBS = {
    "hook": lambda: render("hook.mov", 3.6, draw_hook, True),
    **{f"chip{n}": (lambda n=n: render(f"chip{n}.mov", 3.0, make_chip(n), True)) for n in range(1, 6)},
    "cta": lambda: render("cta.mov", 4.0, draw_cta, True),
    "modi_caption": lambda: render("modi_caption.mov", 7.0, draw_modi_caption, True),
    "b1": lambda: render("b1.mp4", 3.6, draw_b1, False),
    "b2": lambda: render("b2.mp4", 3.6, draw_b2, False),
    "b3": lambda: render("b3.mp4", 4.0, draw_b3, False),
    "b4": lambda: render("b4.mp4", 3.4, draw_b4, False),
    "b5": lambda: render("b5.mp4", 3.6, draw_b5, False),
    "b6": lambda: render("b6.mp4", 4.4, draw_b6, False),
    "sfx": make_sfx,
}

if __name__ == "__main__":
    for name in sys.argv[1:] or JOBS:
        JOBS[name]()
