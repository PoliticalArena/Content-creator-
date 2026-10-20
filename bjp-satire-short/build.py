"""Render the "Achhe Din Kahan Atak Gaye?" satire Short (1080x1920, 30fps).

Usage:  python3 build.py            -> out/achhe-din-short.mp4
        python3 build.py --preview  -> out/preview-*.png (one still per beat)

Optional: drop real, free-license clips into footage/<section>.mp4
(notebandi, jumla, naukri, kisan, mehengai, bonds) and they are used as the
background for that section instead of the animated pattern.
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
MUSIC = os.path.join(ROOT, "assets", "music.wav")
FOOTAGE = os.path.join(ROOT, "footage")

W, H, FPS = 1080, 1920, 30
SR = 44100
HANDLE = "@PoliticalArena"
TITLE = "ACHHE DIN KAHAN ATAK GAYE?"

FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

YELLOW = (255, 212, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (230, 32, 45)

# ---------------------------------------------------------------- timeline
# Each section: key, label, two background colours.
SECTIONS = {
    "hook": ("", (40, 10, 70), (120, 20, 90)),
    "notebandi": ("#1 NOTEBANDI", (10, 60, 40), (20, 120, 70)),
    "jumla": ("#2 15 LAKH", (90, 50, 0), (170, 100, 0)),
    "naukri": ("#3 NAUKRI", (10, 30, 90), (30, 80, 170)),
    "kisan": ("#4 KISAN", (70, 40, 10), (140, 90, 20)),
    "mehengai": ("#5 MEHENGAI", (110, 10, 20), (190, 30, 40)),
    "bonds": ("#6 ELECTORAL BONDS", (20, 20, 30), (60, 60, 90)),
    "outro": ("", (40, 10, 70), (120, 20, 90)),
}

# kind: "say" (kicker + big line + emoji), "fact" (fact card), "counter",
# "recap", "loading".  sfx: list of (name, offset_seconds).
BEATS = [
    dict(sec="hook", dur=2.8, kind="say", kicker="2014", main="Achhe din aane wale hain!", emoji="🎉", sfx=[("pop", 0)]),
    dict(sec="hook", dur=3.0, kind="say", kicker="2026", main="Bhai... kahan atak gaye?", emoji="🤔", sfx=[("boom", 0)], punch=True, shake=True),

    dict(sec="notebandi", dur=3.3, kind="say", kicker="8 NOV 2016", main="Kala dhan khatam!", emoji="💪", sfx=[("whoosh", 0)]),
    dict(sec="notebandi", dur=3.3, kind="say", kicker="POORA DESH", main="ATM ki line mein", emoji="🧍🧍🧍🧍", sfx=[("tick", 0)]),
    dict(sec="notebandi", dur=5.2, kind="fact", head="RBI REPORT", main="99.3% purane note wapas bank mein aa gaye", src="RBI Annual Report 2017-18", sfx=[("scratch", 0)]),
    dict(sec="notebandi", dur=4.2, kind="say", kicker="KALA DHAN", main="Main toh yahin hoon", emoji="😎", sfx=[("boom", 0)], punch=True),

    dict(sec="jumla", dur=3.6, kind="say", kicker="VAADA", main="Har khaate mein 15 lakh?", emoji="🤑", sfx=[("whoosh", 0), ("kaching", 0.4)]),
    dict(sec="jumla", dur=3.3, kind="say", kicker="PASSBOOK BALANCE", main="₹0.00", emoji="👀", sfx=[("boing", 0.2)], shake=True),
    dict(sec="jumla", dur=5.2, kind="fact", head="BJP PRESIDENT, 2015", main="\"Woh chunavi jumla tha\"", src="Amit Shah, TV interview, Feb 2015", sfx=[("scratch", 0)]),
    dict(sec="jumla", dur=3.0, kind="say", kicker="RESULT", main="Jumla > Khazana", emoji="🎭", sfx=[("trombone", 0)]),

    dict(sec="naukri", dur=3.3, kind="say", kicker="VAADA", main="Har saal 2 crore naukri", emoji="💼", sfx=[("whoosh", 0)]),
    dict(sec="naukri", dur=5.6, kind="fact", head="NSSO / PLFS 2017-18", main="Berozgari 6.1% — 45 saal mein sabse zyada", src="Periodic Labour Force Survey", sfx=[("scratch", 0)]),
    dict(sec="naukri", dur=5.4, kind="say", kicker="SOLUTION (2018)", main="Pakode bechna bhi rozgar hai", emoji="🍤", sfx=[("boing", 0.3)], shake=True),

    dict(sec="kisan", dur=3.3, kind="say", kicker="SEP 2020", main="3 farm laws pass", emoji="📜", sfx=[("whoosh", 0)]),
    dict(sec="kisan", dur=4.4, kind="counter", kicker="KISAN DELHI BORDER PE", fmt="MAHINA {}", a=1, b=12, emoji="🚜", sfx=[("tick", 0), ("tick", 1.4), ("tick", 2.8)]),
    dict(sec="kisan", dur=5.6, kind="fact", head="19 NOV 2021", main="Kanoon wapas + PM ne desh se kshama maangi", src="PM's address to the nation", sfx=[("gavel", 0)]),
    dict(sec="kisan", dur=3.2, kind="say", kicker="TOH", main="Pehle hi sun lete?", emoji="🙃", sfx=[("boom", 0)], punch=True),

    dict(sec="mehengai", dur=3.8, kind="counter", kicker="PETROL / LITRE", fmt="₹{}", a=71, b=100, emoji="⛽", note="Kai shehron mein ₹100 paar (2021)", sfx=[("whoosh", 0), ("kaching", 2.6)]),
    dict(sec="mehengai", dur=3.6, kind="counter", kicker="LPG CYLINDER", fmt="₹{}", a=414, b=1003, emoji="🔥", note="2014 → 2022 (Delhi)", sfx=[("kaching", 2.6)]),
    dict(sec="mehengai", dur=3.4, kind="say", kicker="SALARY", main="Wahi ki wahi", emoji="🐢", sfx=[("boing", 0.2)], shake=True),
    dict(sec="mehengai", dur=3.4, kind="say", kicker="ACHHE DIN?", main="Ya mehenge din?", emoji="💸", sfx=[("boom", 0)], punch=True),

    dict(sec="bonds", dur=3.8, kind="say", kicker="ELECTORAL BONDS", main="Chanda kisne diya? SECRET!", emoji="🤫", sfx=[("whoosh", 0)]),
    dict(sec="bonds", dur=5.6, kind="fact", head="15 FEB 2024", main="Supreme Court: scheme unconstitutional", src="SC Constitution Bench verdict", sfx=[("gavel", 0)]),
    dict(sec="bonds", dur=4.6, kind="loading", kicker="TRANSPARENCY", sfx=[("glitch", 2.2)]),

    dict(sec="outro", dur=6.9, kind="recap", items=["Notebandi", "15 lakh", "2 crore naukri", "Farm laws", "Mehengai", "Electoral bonds"], sfx=[("whoosh", 0)]),
    dict(sec="outro", dur=5.0, kind="say", kicker="TOH", main="ACHHE DIN kab aayenge?", emoji="🤷", sfx=[("boom", 0)], punch=True),
    dict(sec="outro", dur=4.6, kind="say", kicker="AAPKA JAWAB", main="Comment karo", emoji="👇", sfx=[("pop", 0)], sub="Follow for Part 2"),
    dict(sec="outro", dur=3.0, kind="end", sfx=[]),
]

t = 0.0
for b in BEATS:
    b["start"] = t
    t += b["dur"]
TOTAL = t

# ---------------------------------------------------------------- helpers
_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if fnt.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(text, size, fill=WHITE, stroke=10, max_w=960, path=FONT_BLACK, spacing=1.08, upper=False):
    """Centered multi-line text with a thick stroke, auto-shrunk to fit."""
    text = text.upper() if upper else text
    while True:
        fnt = font(path, size)
        lines = wrap(text, fnt, max_w)
        if max(fnt.getlength(l) for l in lines) <= max_w or size < 40:
            break
        size -= 6
    lh = int(size * spacing)
    w = int(max(fnt.getlength(l) for l in lines)) + stroke * 2 + 8
    h = lh * len(lines) + stroke * 2 + int(size * 0.3)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        lw = fnt.getlength(l)
        d.text(((w - lw) / 2, stroke + i * lh), l, font=fnt, fill=fill,
               stroke_width=stroke, stroke_fill=BLACK)
    return img


def emoji_img(chars, height):
    fnt = font(FONT_EMOJI, 109)
    tmp = Image.new("RGBA", (140 * len(chars) + 40, 160), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((20, 10), chars, font=fnt, embedded_color=True)
    tmp = tmp.crop(tmp.getbbox())
    r = height / tmp.height
    return tmp.resize((max(1, int(tmp.width * r)), height), Image.LANCZOS)


def pill(text, size, bg, fg=BLACK, pad=(34, 16)):
    fnt = font(FONT_BLACK, size)
    tw = fnt.getlength(text)
    asc, desc = fnt.getmetrics()
    w, h = int(tw + pad[0] * 2), asc + desc + pad[1] * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg)
    d.text((pad[0], pad[1]), text, font=fnt, fill=fg)
    return img


def shadow(img, radius=18, alpha=150):
    a = img.split()[-1].point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(a)
    pad = radius * 2
    big = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    big.paste(sh, (pad, pad + 12), sh)
    big = big.filter(ImageFilter.GaussianBlur(radius))
    big.alpha_composite(img, (pad, pad))
    return big


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    return 1 - (1 - x) ** 3


def place(frame, img, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if alpha < 1.0:
        img = img.copy()
        img.putalpha(img.split()[-1].point(lambda v: int(v * alpha)))
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


# ---------------------------------------------------------------- backgrounds
def make_background(c1, c2):
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    g = np.clip(y * 0.75 + x * 0.25, 0, 1)[..., None]
    arr = (np.array(c1) * (1 - g) + np.array(c2) * g).astype(np.uint8)
    arr = np.broadcast_to(arr, (H, W, 3)).copy()
    # radial vignette for readability
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
    arr = (arr * np.clip(1.15 - d * 0.9, 0.45, 1)[..., None]).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")


STRIPE_P = 160


def make_stripes():
    size = W + H + STRIPE_P * 2
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(-size, size * 2, STRIPE_P):
        d.polygon([(i, 0), (i + STRIPE_P // 2, 0), (i + STRIPE_P // 2 - size, size), (i - size, size)],
                  fill=(255, 255, 255, 16))
    return img


class FootageReader:
    """Streams frames of a clip scaled/cropped to 1080x1920, looping."""

    def __init__(self, path):
        self.path = path
        self.proc = None
        self._open()

    def _open(self):
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},eq=brightness=-0.14:saturation=1.05"
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", self.path, "-vf", vf, "-an",
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def frame(self):
        raw = self.proc.stdout.read(W * H * 3)
        if len(raw) < W * H * 3:
            self.proc.wait()
            self._open()
            raw = self.proc.stdout.read(W * H * 3)
        return Image.frombytes("RGB", (W, H), raw).convert("RGBA")


# ---------------------------------------------------------------- beat layers
def prepare(b):
    k = b["kind"]
    if k in ("say", "counter", "loading"):
        b["kicker_img"] = pill(b["kicker"], 54, YELLOW)
    if k == "say":
        b["main_img"] = shadow(text_block(b["main"], 132))
        if b.get("sub"):
            b["sub_img"] = pill(b["sub"], 56, WHITE)
    if b.get("emoji"):
        b["emoji_img"] = emoji_img(b["emoji"], 300 if len(b["emoji"]) == 1 else 190)
    if k == "counter" and b.get("note"):
        b["note_img"] = text_block(b["note"], 58, fill=YELLOW, stroke=6)
    if k == "fact":
        b["card"] = shadow(fact_card(b["head"], b["main"], b["src"]), radius=24, alpha=170)
    if k == "recap":
        b["title_img"] = text_block("VAADE vs HAQEEQAT", 92, fill=YELLOW)
        b["item_imgs"] = [pill(f"✗  {it}", 64, WHITE, pad=(40, 18)) for it in b["items"]]
    if k == "end":
        b["end_imgs"] = [text_block("SATIRE", 120, fill=YELLOW),
                         text_block("Har fact ka source description mein", 60, stroke=6),
                         pill(HANDLE, 64, YELLOW)]


def fact_card(head, main, src):
    cw = 940
    body = text_block(main, 92, fill=(20, 20, 20), stroke=0, max_w=cw - 100)
    srcimg = text_block("Source: " + src, 40, fill=(90, 90, 90), stroke=0, max_w=cw - 100, path=FONT_BOLD)
    headimg = pill("✓ FACT  •  " + head, 46, RED, fg=WHITE)
    ch = 60 + headimg.height + 40 + body.height + 30 + srcimg.height + 60
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=44, fill=(255, 255, 255, 250))
    d.rounded_rectangle((0, 0, 22, ch - 1), radius=11, fill=RED)
    y = 60
    card.alpha_composite(headimg, ((cw - headimg.width) // 2, y))
    y += headimg.height + 40
    card.alpha_composite(body, ((cw - body.width) // 2, y))
    y += body.height + 30
    card.alpha_composite(srcimg, ((cw - srcimg.width) // 2, y))
    return card


# ---------------------------------------------------------------- frame render
def render_beat(frame, b, tl):
    k = b["kind"]
    pop = ease_out_back(min(1, tl / 0.28))
    fade = min(1, tl / 0.12)
    cy = H * 0.52

    if k == "say":
        # stack kicker / main / emoji / sub vertically around the centre
        parts = [b["kicker_img"], b["main_img"]] + ([b["emoji_img"]] if "emoji_img" in b else []) + \
                ([b["sub_img"]] if "sub_img" in b else [])
        gap = 10
        total = sum(p.height for p in parts) + gap * (len(parts) - 1)
        y = cy - total / 2 + 40
        ys = []
        for p in parts:
            ys.append(y + p.height / 2)
            y += p.height + gap
        place(frame, b["kicker_img"], W / 2, ys[0], scale=0.7 + 0.3 * pop, alpha=fade)
        mt = max(0, tl - 0.12)
        mpop = ease_out_back(min(1, mt / 0.3))
        place(frame, b["main_img"], W / 2, ys[1], scale=0.55 + 0.45 * mpop, alpha=min(1, mt / 0.1))
        i = 2
        if "emoji_img" in b:
            et = max(0, tl - 0.3)
            bounce = math.sin(et * 7) * 14
            place(frame, b["emoji_img"], W / 2, ys[i] + bounce, scale=0.3 + 0.7 * ease_out_back(min(1, et / 0.35)),
                  alpha=min(1, et / 0.1))
            i += 1
        if "sub_img" in b:
            st = max(0, tl - 0.8)
            place(frame, b["sub_img"], W / 2, ys[i] + 40, scale=0.6 + 0.4 * ease_out_back(min(1, st / 0.3)), alpha=min(1, st / 0.1))

    if k in ("counter", "loading"):
        place(frame, b["kicker_img"], W / 2, cy - 330, scale=0.7 + 0.3 * pop, alpha=fade)

    if k == "counter":
        p = ease_out(min(1, tl / (b["dur"] * 0.6)))
        val = round(b["a"] + (b["b"] - b["a"]) * p)
        num = shadow(text_block(b["fmt"].format(val), 150, max_w=1040, fill=WHITE if p < 1 else YELLOW))
        jitter = (random.uniform(-4, 4) if p < 1 else 0)
        place(frame, num, W / 2 + jitter, cy - 60, scale=1.0 + (0.12 * max(0, 1 - (tl - b["dur"] * 0.6) / 0.3) if p >= 1 else 0))
        place(frame, b["emoji_img"], W / 2, cy + 260 + math.sin(tl * 7) * 12, scale=0.3 + 0.7 * ease_out_back(min(1, tl / 0.35)))
        if "note_img" in b and p >= 1:
            place(frame, b["note_img"], W / 2, cy + 520, alpha=min(1, (tl - b["dur"] * 0.6) / 0.2))

    elif k == "fact":
        slide = ease_out(min(1, tl / 0.35))
        place(frame, b["card"], W / 2, cy + 40 + (1 - slide) * 600, alpha=slide)

    elif k == "loading":
        bar_w, bar_h = 820, 90
        x0, y0 = (W - bar_w) / 2, cy - 80
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle((x0 - 8, y0 - 8, x0 + bar_w + 8, y0 + bar_h + 8), radius=54, fill=(0, 0, 0, 200))
        fill = min(0.03, tl / 1.5 * 0.03)
        d.rounded_rectangle((x0, y0, x0 + max(bar_h, bar_w * fill), y0 + bar_h), radius=45, fill=YELLOW)
        label = text_block("LOADING... 0%" if tl < 2.2 else "ERROR 404", 96)
        place(frame, label, W / 2, y0 + 280)
        if tl >= 2.2:
            err = text_block("Data not found", 64, fill=YELLOW, stroke=6)
            place(frame, err, W / 2, y0 + 430)

    elif k == "recap":
        place(frame, b["title_img"], W / 2, cy - 520, scale=0.7 + 0.3 * pop, alpha=fade)
        step = (b["dur"] - 1.2) / len(b["item_imgs"])
        for i, im in enumerate(b["item_imgs"]):
            it = tl - 0.4 - i * step
            if it <= 0:
                continue
            place(frame, im, W / 2, cy - 330 + i * 150, scale=0.6 + 0.4 * ease_out_back(min(1, it / 0.25)), alpha=min(1, it / 0.08))

    elif k == "end":
        for i, im in enumerate(b["end_imgs"]):
            it = tl - i * 0.25
            if it > 0:
                place(frame, im, W / 2, cy - 200 + i * 190, scale=0.6 + 0.4 * ease_out_back(min(1, it / 0.3)), alpha=min(1, it / 0.1))


def glitch(frame, strength):
    arr = np.array(frame)
    for _ in range(int(6 * strength)):
        y = random.randint(0, H - 60)
        h = random.randint(10, 60)
        arr[y:y + h] = np.roll(arr[y:y + h], random.randint(-80, 80), axis=1)
    arr[..., 0] = np.roll(arr[..., 0], int(10 * strength), axis=1)
    return Image.fromarray(arr)


def build_chrome():
    top = Image.new("RGBA", (W, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(top)
    d.rectangle((0, 0, W, 230), fill=(0, 0, 0, 170))
    title = text_block(TITLE, 54, fill=YELLOW, stroke=0, max_w=940)
    em = emoji_img("🤔", 80)
    total_w = title.width + 20 + em.width
    x = (W - total_w) // 2
    top.alpha_composite(title, (x, 115 - title.height // 2))
    top.alpha_composite(em, (x + title.width + 20, 115 - em.height // 2))
    labels = {k: pill(v[0], 46, RED, fg=WHITE) for k, v in SECTIONS.items() if v[0]}
    handle = text_block(HANDLE, 44, fill=(255, 255, 255), stroke=4)
    return top, labels, handle


def render(preview=False):
    os.makedirs(OUT, exist_ok=True)
    random.seed(7)
    for b in BEATS:
        prepare(b)
    bgs = {k: make_background(v[1], v[2]) for k, v in SECTIONS.items()}
    stripes = make_stripes()
    top, labels, handle = build_chrome()
    footage = {k: FootageReader(os.path.join(FOOTAGE, k + ".mp4"))
               for k in SECTIONS if os.path.exists(os.path.join(FOOTAGE, k + ".mp4"))}

    def frame_at(tg):
        b = next(x for x in BEATS if x["start"] <= tg < x["start"] + x["dur"] + 1e-9)
        tl = tg - b["start"]
        sec = b["sec"]
        if sec in footage:
            frame = footage[sec].frame()
        else:
            frame = bgs[sec].copy()
            off = int((tg * 90) % STRIPE_P)
            frame.alpha_composite(stripes.crop((off, off, off + W, off + H)))
        render_beat(frame, b, tl)
        frame.alpha_composite(top, (0, 0))
        if sec in labels:
            lab = labels[sec]
            frame.alpha_composite(lab, ((W - lab.width) // 2, 260))
        frame.alpha_composite(handle, ((W - handle.width) // 2, H - 190))
        d = ImageDraw.Draw(frame)
        d.rectangle((0, H - 18, W, H), fill=(0, 0, 0, 160))
        d.rectangle((0, H - 18, int(W * tg / TOTAL), H), fill=YELLOW)
        # camera moves: punch-in zoom + shake on punchlines
        z = 1.0
        if b.get("punch") and tl < 0.35:
            z = 1.0 + 0.10 * (1 - tl / 0.35)
        dx = dy = 0
        if b.get("shake") and tl < 0.45:
            amp = 18 * (1 - tl / 0.45)
            dx, dy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        if z != 1.0 or dx or dy:
            zw, zh = int(W * z), int(H * z)
            big = frame.resize((zw, zh), Image.BILINEAR)
            x0, y0 = (zw - W) // 2 + int(dx), (zh - H) // 2 + int(dy)
            big = big.crop((x0, y0, x0 + W, y0 + H))
            frame = big
        # glitch on section changes and the 404 gag
        if tl < 0.1 and b is not BEATS[0] and BEATS[BEATS.index(b) - 1]["sec"] != sec:
            frame = glitch(frame.convert("RGB"), 1.5)
        if b["kind"] == "loading" and 2.2 <= tl < 2.6:
            frame = glitch(frame.convert("RGB"), 2.5)
        return frame.convert("RGB")

    if preview:
        for i, b in enumerate(BEATS):
            frame_at(b["start"] + min(b["dur"] - 0.05, 1.6)).save(os.path.join(OUT, f"preview-{i:02d}.png"))
        return

    silent = os.path.join(OUT, "video-silent.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", silent],
                            stdin=subprocess.PIPE)
    n = int(round(TOTAL * FPS))
    for i in range(n):
        proc.stdin.write(frame_at(i / FPS).tobytes())
        if i % 300 == 0:
            print(f"frame {i}/{n}", flush=True)
    proc.stdin.close()
    proc.wait()

    audio = os.path.join(OUT, "mix.wav")
    write_audio(audio)
    final = os.path.join(OUT, "achhe-din-short.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", audio, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(silent)
    os.remove(audio)
    print("wrote", final)


# ---------------------------------------------------------------- audio
def env(n, attack=0.005, decay=0.3):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def sfx(name):
    rng = np.random.default_rng(1)
    if name == "boom":
        n = int(SR * 1.4)
        t = np.arange(n) / SR
        f = 55 + 70 * np.exp(-t * 9)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.45)
        s += rng.normal(0, 1, n) * env(n, 0.001, 0.02) * 0.6
        return np.tanh(s * 2.5) * 0.9
    if name == "pop":
        n = int(SR * 0.12)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * (900 - 3000 * t) * t) * env(n, 0.001, 0.03) * 0.5
    if name == "whoosh":
        n = int(SR * 0.45)
        noise = rng.normal(0, 1, n)
        k = np.ones(40) / 40
        s = np.convolve(noise, k, "same")
        shape = np.sin(np.pi * np.arange(n) / n) ** 2
        return s * shape * 1.4
    if name == "tick":
        out = np.zeros(int(SR * 1.2))
        for i in range(4):
            n = int(SR * 0.03)
            st = int(i * 0.3 * SR)
            out[st:st + n] += np.sin(2 * np.pi * 2400 * np.arange(n) / SR) * env(n, 0.0005, 0.006) * 0.6
        return out
    if name == "scratch":
        n = int(SR * 0.5)
        t = np.arange(n) / SR
        noise = rng.normal(0, 1, n)
        mod = np.abs(np.sin(2 * np.pi * 7 * t))
        tone = np.sin(2 * np.pi * np.cumsum(300 + 900 * mod) / SR)
        return (noise * 0.35 + tone * 0.5) * mod * np.exp(-t * 3) * 0.8
    if name == "kaching":
        n = int(SR * 0.9)
        t = np.arange(n) / SR
        s = np.zeros(n)
        for f, st in ((2093, 0.0), (2637, 0.08), (3136, 0.08)):
            i0 = int(st * SR)
            tt = t[: n - i0]
            s[i0:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 5)
        s[: int(SR * 0.06)] += rng.normal(0, 1, int(SR * 0.06)) * 0.4
        return s * 0.35
    if name == "boing":
        n = int(SR * 0.7)
        t = np.arange(n) / SR
        f = 180 + 220 * (1 - np.exp(-t * 6)) + 60 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 4)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.25) * 0.7
    if name == "trombone":
        out = []
        for i, (f, d) in enumerate(((233.1, 0.42), (220.0, 0.42), (207.7, 0.42), (196.0, 1.3))):
            n = int(SR * d)
            t = np.arange(n) / SR
            vib = 1 + (0.012 * np.sin(2 * np.pi * 6 * t) if i == 3 else 0)
            ph = 2 * np.pi * np.cumsum(f * vib) / SR
            tone = sum(np.sin(ph * h) / h for h in range(1, 7))
            a = np.minimum(1, t / 0.04) * np.minimum(1, (d - t) / 0.08)
            out.append(tone * a * 0.35)
        return np.concatenate(out)
    if name == "gavel":
        out = np.zeros(int(SR * 0.8))
        for st in (0.0, 0.28):
            n = int(SR * 0.25)
            t = np.arange(n) / SR
            s = np.sin(2 * np.pi * 140 * t) * env(n, 0.001, 0.06) + rng.normal(0, 1, n) * env(n, 0.0005, 0.01) * 0.8
            i0 = int(st * SR)
            out[i0:i0 + n] += s * 0.9
        return out
    if name == "glitch":
        n = int(SR * 0.4)
        sq = np.sign(np.sin(2 * np.pi * 180 * np.arange(n) / SR))
        gate = (rng.random(n // 800 + 1) > 0.4).repeat(800)[:n]
        return sq * gate * 0.25
    raise ValueError(name)


def load_music():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", MUSIC, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def write_audio(path):
    n = int(TOTAL * SR)
    music = np.zeros((n, 2))
    m = load_music()[:n]
    music[: len(m)] = m * 0.55
    fade = int(SR * 2.5)
    music[n - fade:] *= np.linspace(1, 0, fade)[:, None]
    effects = np.zeros(n)
    duck = np.ones(n)
    for b in BEATS:
        for name, off in b["sfx"]:
            s = sfx(name)
            i0 = int((b["start"] + off) * SR)
            i1 = min(n, i0 + len(s))
            effects[i0:i1] += s[: i1 - i0] * 0.8
            if name in ("boom", "trombone", "scratch", "gavel"):
                duck[i0:i1] = np.minimum(duck[i0:i1], 0.45)
    k = int(SR * 0.05)
    duck = np.convolve(duck, np.ones(k) / k, "same")
    mix = music * duck[:, None] + effects[:, None]
    peak = np.max(np.abs(mix))
    mix = np.tanh(mix / max(peak, 1e-9) * 1.2) * 0.95
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    render(preview="--preview" in sys.argv)
