"""Animated explainer: Class 8 SST Ch 2 - India's Long Road to Independence.

16:9 1920x1080 @30fps, offline AI voiceover (Kokoro), burned-in captions,
1857->1947 progress timeline, synthesised tanpura drone + light SFX.

Usage:  python3 build.py            -> out/road-to-independence.mp4 (+ .srt, upload.md, thumbnail.png)
        python3 build.py --preview  -> out/preview/*.png (one still per beat)
        python3 build.py --script   -> script.md only

Edit the BEATS list to change narration / on-screen text, then re-run.
TTS clips are cached in out/tts/, so only changed lines are re-voiced.
"""
import hashlib
import math
import os
import random
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
TTS_DIR = os.path.join(OUT, "tts")
MODEL_DIR = os.path.expanduser("~/.cache/kokoro")
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_FILES = ["kokoro-v1.0.int8.onnx", "voices-v1.0.bin"]

W, H, FPS = 1920, 1080, 30
SR = 24000
VOICE, SPEED = "bm_george", 1.05
LEAD, TAIL = 0.30, 0.45            # silence around each voice line (s)
TITLE = "India's Long Road to Independence"
TAG = "CLASS 8 · SST · CHAPTER 2"

FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FONT_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
FONT_ITAL = "/usr/share/fonts/opentype/inter/InterDisplay-MediumItalic.otf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SAFFRON = (255, 153, 51)
GREEN = (70, 200, 100)
RED = (235, 70, 70)
GREY = (190, 195, 210)

# --------------------------------------------------------------------- eras
ERAS = {
    "hook":  ("", (6, 12, 36), (22, 34, 88)),
    "e1":    ("ERA 1 · 1858–1885 · THE CROWN TAKES OVER", (34, 20, 10), (82, 48, 22)),
    "e2":    ("ERA 2 · 1890–1915 · A NATION AWAKENS", (8, 26, 46), (22, 64, 98)),
    "e3":    ("ERA 3 · 1915–1922 · GANDHI ARRIVES", (8, 36, 22), (28, 88, 52)),
    "e4":    ("ERA 4 · 1927–1935 · PURNA SWARAJ", (46, 18, 8), (118, 54, 14)),
    "e5":    ("ERA 5 · 1939–1946 · WAR & QUIT INDIA", (32, 8, 14), (88, 20, 34)),
    "e6":    ("ERA 6 · 1946–1947 · FREEDOM & PARTITION", (8, 14, 44), (26, 42, 108)),
    "outro": ("", (6, 12, 36), (22, 34, 88)),
}

# kinds: stat, title, era, year, versus, quote, chips, recap, end.
# vo = narration (also the captions). points = (text, cue word in vo).
# year = position of the bottom timeline marker.
BEATS = [
    dict(era="hook", kind="stat", year=1857, n=90, fmt="{} YEARS", label="1857 → 1947", emoji="⏳",
         vo="From 1857 to 1947, it took India ninety years to win its freedom from the most powerful empire on Earth."),
    dict(era="hook", kind="title", year=1857,
         vo="Hundreds of languages, many faiths, one dream. This is India's long road to independence, Chapter 2, made simple."),

    dict(era="e1", kind="era", year=1858, num="ERA 1", name="The Crown Takes Over", emoji="👑"),
    dict(era="e1", kind="year", year=1858, emoji="👑", head="The British Crown takes direct control",
         points=[("After the 1857 Uprising", "Uprising"), ("Ruled by the Viceroy", "Victoria"), ("East India Company out", "Company")],
         vo="After the Great Uprising of 1857, Queen Victoria's Crown took direct control of India from the East India Company."),
    dict(era="e1", kind="versus", year=1858, head="The 1858 Royal Proclamation",
         left=("PROMISED", SAFFRON, ["Respect for Indian princes", "Equal care for all subjects", "No forced Christianity"]),
         right=("REALITY", RED, ["Princes closely controlled", "Treated as 'inferior races'", "Missionaries backed by officials"]),
         split="practice",
         vo="The Royal Proclamation promised to respect Indian princes, to care for Indians like all other subjects, and not to impose Christianity. In practice, none of these promises were kept."),
    dict(era="e1", kind="year", year=1878, emoji="⛓️", head="Exploitation & control",
         points=[("Heavy taxes → famines", "famines"), ("Arms Act: no weapons", "Arms"), ("Press Act: censorship", "Press")],
         vo="Heavy land taxes caused terrible famines. The Arms Act of 1878 banned Indians from keeping weapons, and the Vernacular Press Act censored Indian-language newspapers."),
    dict(era="e1", kind="year", year=1875, big="REFORM", emoji="📚", head="Reformers change society",
         points=[("Brahmo Samaj · 1828", "Brahmo"), ("Arya Samaj · 1875", "Arya"), ("Against child marriage & caste", "child")],
         vo="Meanwhile, reformers changed society from within. Raja Ram Mohan Roy founded the Brahmo Samaj in 1828, and Swami Dayananda Saraswati founded the Arya Samaj in 1875. Both fought child marriage and caste discrimination."),
    dict(era="e1", kind="quote", year=1880, who="Swami Vivekananda",
         quote="Arise, awake, and stop not till the goal is reached.",
         vo="Swami Vivekananda gave Indians courage with his famous call. Arise, awake, and stop not till the goal is reached."),
    dict(era="e1", kind="year", year=1875, emoji="🎶", head="Vande Mataram",
         points=[("Bankim Chandra Chattopadhyay", "Bankim"), ("'I bow to the Motherland'", "bow"), ("Became a battle cry", "battle")],
         vo="In 1875, Bankim Chandra Chattopadhyay composed Vande Mataram. I bow to the Motherland. It would become the battle cry of the freedom struggle."),
    dict(era="e1", kind="year", year=1885, emoji="🏛️", head="Indian National Congress is born",
         points=[("1st session in Bombay", "Bombay"), ("72 delegates", "seventy"), ("Moderates: polite requests", "Moderates")],
         vo="In 1885, the Indian National Congress held its first session in Bombay, with seventy-two delegates. Its early leaders, the Moderates, politely asked for reforms. The British mostly ignored them."),

    dict(era="e2", kind="era", year=1890, num="ERA 2", name="A Nation Awakens", emoji="🔥"),
    dict(era="e2", kind="year", year=1897, big="ANGER", emoji="✊", head="Discontent spreads",
         points=[("Kukas boycott foreign goods", "Kukas"), ("Tilak: 'Lokmanya'", "Tilak"), ("Birsa Munda's Ulgulaan", "Birsa")],
         vo="Anger kept growing. The Kukas of Punjab boycotted foreign goods. Bal Gangadhar Tilak, called Lokmanya, roused the people through his newspaper Kesari. And Birsa Munda led the great tribal uprising, the Ulgulaan."),
    dict(era="e2", kind="year", year=1905, emoji="✂️", head="Curzon splits Bengal",
         points=[("Official reason: efficiency", "official"), ("Real reason: divide & rule", "Divide")],
         vo="In 1905, Viceroy Curzon split Bengal into two. The official reason was efficiency. The real reason? Divide and rule."),
    dict(era="e2", kind="year", year=1905, big="SWADESHI", emoji="🧵", head="It backfired",
         points=[("Bonfires of foreign cloth", "burned"), ("Buy Indian-made goods", "Indian"), ("Rakhis for unity", "rakhis")],
         vo="It backfired. People burned foreign cloth, bought Indian-made goods, and tied rakhis on each other's wrists as a symbol of Hindu Muslim unity. This was the Swadeshi and Boycott movement."),
    dict(era="e2", kind="year", year=1906, emoji="📜", head="Two big turning points",
         points=[("Congress: Swaraj, Swadeshi,", "four"), ("Boycott, National Education", "Boycott"), ("Muslim League founded, Dhaka", "Muslim")],
         vo="In 1906, the Congress adopted four goals: Swaraj, Swadeshi, Boycott, and National Education. The same year, the All-India Muslim League was founded in Dhaka."),
    dict(era="e2", kind="versus", year=1907, head="1907 · The Surat Split",
         left=("MODERATES", SAFFRON, ["Gradual reform", "Dialogue with the British", "Gokhale, Naoroji"]),
         right=("NATIONALISTS", GREEN, ["Swaraj now", "Boycott & protest", "Lal, Bal, Pal"]),
         split="Nationalists",
         vo="In 1907, at Surat, the Congress split in two. The Moderates wanted gradual reform. The Nationalists, Lal, Bal and Pal, wanted Swaraj."),
    dict(era="e2", kind="year", year=1908, emoji="💣", head="The revolutionaries",
         points=[("Khudiram Bose hanged at 18", "Khudiram"), ("Alipore Bomb Trial", "Aurobindo"), ("Tilak jailed: 6 years", "Tilak")],
         vo="Some chose revolution. In 1908, eighteen-year-old Khudiram Bose was hanged for a bomb attack. Aurobindo Ghose faced the Alipore Bomb Trial, and Tilak was jailed for six years."),
    dict(era="e2", kind="year", year=1911, emoji="🏆", head="The protests worked",
         points=[("Partition of Bengal cancelled", "cancelled"), ("Capital: Calcutta → Delhi", "capital")],
         vo="The protests worked. In 1911, the partition of Bengal was cancelled, and the capital moved from Calcutta to Delhi."),
    dict(era="e2", kind="year", year=1915, big="GHADAR", emoji="⚔️", head="Revolt during World War I",
         points=[("Ghadar Party plans army mutiny", "Ghadar"), ("Bagha Jatin dies fighting · 1915", "Bagha")],
         vo="During World War One, the Ghadar Party tried to spark a mutiny in the army, and the fearless Bagha Jatin died fighting in 1915."),

    dict(era="e3", kind="era", year=1915, num="ERA 3", name="Gandhi Arrives", emoji="🕊️"),
    dict(era="e3", kind="year", year=1915, emoji="🕊️", head="Gandhi returns from South Africa",
         points=[("Weapon: satyagraha", "satyagraha"), ("Truth + nonviolence", "nonviolence")],
         vo="In 1915, Mohandas Karamchand Gandhi returned from South Africa with a new weapon: satyagraha, the force of truth and nonviolence."),
    dict(era="e3", kind="year", year=1916, emoji="🤝", head="Coming together",
         points=[("Home Rule: Tilak & Annie Besant", "Home"), ("Lucknow Pact: Congress + League", "Lucknow")],
         vo="In 1916, Tilak and Annie Besant launched the Home Rule Movement, and the Lucknow Pact brought the Congress and the Muslim League together."),
    dict(era="e3", kind="year", year=1919, emoji="🩸", head="Jallianwala Bagh",
         points=[("Rowlatt Act: jail without trial", "Rowlatt"), ("13 April · Amritsar", "April"), ("Dyer fires on unarmed crowd", "Dyer")],
         vo="Then came 1919. The Rowlatt Act allowed arrest without trial. On the thirteenth of April, at Jallianwala Bagh in Amritsar, General Dyer blocked the exit and opened fire on an unarmed crowd."),
    dict(era="e3", kind="stat", year=1919, n=1650, fmt="{:,} ROUNDS", label="in about 10 minutes", emoji="🕯️",
         vo="One thousand six hundred and fifty rounds, in about ten minutes. Over a thousand people killed, by Indian estimates. The whole nation was united in grief and anger."),
    dict(era="e3", kind="year", year=1920, emoji="🚫", head="Non-Cooperation Movement",
         points=[("Joined by the Khilafat Movement", "Khilafat"), ("Boycott British schools & courts", "schools"), ("Burn foreign cloth", "cloth")],
         vo="In 1920, Gandhi launched the Non-Cooperation Movement, joined by the Khilafat Movement. Indians boycotted British schools, courts, and cloth."),
    dict(era="e3", kind="year", year=1922, emoji="⏸️", head="Chauri Chaura",
         points=[("Police station set on fire", "fire"), ("Gandhi calls off the movement", "called")],
         vo="But in 1922, protesters at Chauri Chaura set a police station on fire. Gandhi called off the movement. He would not accept violence."),

    dict(era="e4", kind="era", year=1927, num="ERA 4", name="Purna Swaraj", emoji="🇮🇳"),
    dict(era="e4", kind="year", year=1928, emoji="🙅", head="'Simon, go back!'",
         points=[("Simon Commission: 0 Indians", "single"), ("Lala Lajpat Rai beaten", "Lala")],
         vo="In 1928, the Simon Commission arrived without a single Indian member. Simon, go back, people shouted. Lala Lajpat Rai was beaten in a lathi charge, and died soon after."),
    dict(era="e4", kind="year", year=1929, emoji="🇮🇳", head="Purna Swaraj",
         points=[("Lahore session, December", "Lahore"), ("Goal: complete independence", "complete")],
         vo="In December 1929, at the Lahore session, the Congress demanded Purna Swaraj, complete independence."),
    dict(era="e4", kind="stat", year=1930, n=380, fmt="{} KM", label="The Salt March to Dandi", emoji="🧂",
         vo="In 1930, Gandhi walked three hundred and eighty kilometres to Dandi, and made salt from seawater, breaking an unjust law. The Civil Disobedience Movement had begun."),
    dict(era="e4", kind="year", year=1931, emoji="🔥", head="Bhagat Singh, Sukhdev, Rajguru",
         points=[("Hanged in 1931", "hanged"), ("Aged just 22–23", "heroes")],
         vo="Young revolutionaries Bhagat Singh, Sukhdev and Rajguru chose a different path. In 1931 they were hanged, and became heroes for generations."),
    dict(era="e4", kind="year", year=1932, big="1931–35", emoji="📝", head="Talks and compromises",
         points=[("Gandhi–Irwin Pact · 1931", "Irwin"), ("Poona Pact · Gandhi & Ambedkar", "Poona"), ("1935 Act: provincial self-rule", "1935")],
         vo="The Gandhi Irwin Pact of 1931 opened talks. The Poona Pact of 1932 settled a dispute between Gandhi and Doctor B. R. Ambedkar over separate electorates. And the Act of 1935 gave the provinces some self-rule."),

    dict(era="e5", kind="era", year=1939, num="ERA 5", name="War & Quit India", emoji="✊"),
    dict(era="e5", kind="year", year=1940, emoji="➗", head="The idea of separate nations",
         points=[("Lahore Resolution · 1940", "1940"), ("Jinnah: separate Muslim states", "Jinnah")],
         vo="Meanwhile, the idea of separate nations was growing. In 1940, the Muslim League under Jinnah demanded separate Muslim-majority states."),
    dict(era="e5", kind="stat", year=1941, n=2500000, fmt="{:,}", label="Indian soldiers in World War II", emoji="🪖",
         vo="India was dragged into World War Two without being asked. Over two and a half million Indian soldiers fought for Britain."),
    dict(era="e5", kind="year", year=1942, big="QUIT INDIA", emoji="📣", head="'Do or Die!'",
         points=[("Launched August 1942", "August"), ("Leaders arrested", "arrested"), ("The whole country rises", "rose")],
         vo="In August 1942, Gandhi gave the call: Quit India! Do or die! The leaders were arrested, but the whole country rose up."),
    dict(era="e5", kind="year", year=1943, emoji="🎖️", head="Netaji & the INA",
         points=[("Subhas Chandra Bose", "Subhas"), ("Indian National Army", "Army"), ("Azad Hind government", "Azad")],
         vo="Abroad, Subhas Chandra Bose led the Indian National Army, and proclaimed the Azad Hind government in 1943."),
    dict(era="e5", kind="year", year=1946, emoji="⚓", head="Britain loses its grip",
         points=[("Royal Indian Navy mutiny", "Navy"), ("Britain exhausted by war", "exhausted")],
         vo="In 1946, sailors of the Royal Indian Navy mutinied. Britain, exhausted by war, knew it could no longer hold India."),

    dict(era="e6", kind="era", year=1946, num="ERA 6", name="Freedom & Partition", emoji="🇮🇳"),
    dict(era="e6", kind="year", year=1946, emoji="💔", head="Tensions explode",
         points=[("Direct Action Day · Aug 1946", "Direct"), ("Violence in Calcutta", "Calcutta")],
         vo="But Hindu Muslim tensions exploded. Jinnah's Direct Action Day, in August 1946, brought terrible violence to Calcutta."),
    dict(era="e6", kind="year", year=1947, big="15 AUG 1947", emoji="🇮🇳", head="Freedom at midnight",
         points=[("India becomes independent", "freedom"), ("Divided: India & Pakistan", "divided"), ("Millions forced to migrate", "Millions")],
         vo="At midnight on the fifteenth of August 1947, India awoke to freedom. But it was also divided into India and Pakistan. Millions were forced to leave their homes."),
    dict(era="e6", kind="stat", year=1947, n=560, fmt="{}+", label="princely states united by Sardar Patel", emoji="🧩",
         vo="Sardar Vallabhbhai Patel then united more than five hundred and sixty princely states into one India."),
    dict(era="e6", kind="chips", year=1947, head="Who won India's freedom?",
         items=[("Moderates", "Moderates"), ("Nationalists", "Nationalists"), ("Revolutionaries", "revolutionaries"),
                ("Satyagrahis", "satyagrahis"), ("Soldiers", "soldiers"), ("Millions of people", "millions")],
         final="TOGETHER.",
         vo="Freedom was not won by one person, or one method. Moderates, Nationalists, revolutionaries, satyagrahis, soldiers, and millions of ordinary people. Together, they made it happen."),

    dict(era="outro", kind="recap", year=1947,
         items=[("1857", "Uprising", "1857"), ("1885", "Congress", "1885"), ("1905", "Bengal split", "1905"),
                ("1919", "Jallianwala", "1919"), ("1930", "Salt March", "1930"), ("1942", "Quit India", "1942"),
                ("1947", "Freedom", "1947")],
         vo="Quick recap. 1857, the Uprising. 1885, the Congress. 1905, Bengal is split. 1919, Jallianwala Bagh. 1930, the Salt March. 1942, Quit India. And 1947, Independence."),
    dict(era="outro", kind="end", year=1947,
         vo="Which freedom fighter inspires you the most? Tell us in the comments, and subscribe for more chapters made simple."),
]

# Respellings used for the voice only (captions keep the real spelling).
PRON = {
    "Swaraj": "Swaraaj", "Purna": "Poorna", "satyagrahis": "satyaagrahees", "satyagraha": "satyaagraha",
    "Vande Mataram": "Vande Maataram", "Jallianwala Bagh": "Jalli-aan-waala Baagh", "Lokmanya": "Loke-maanya",
    "Kesari": "Kay-sari", "Ulgulaan": "Ulgu-laan", "Dandi": "Daandi", "Azad Hind": "Aazaad Hind",
    "Chauri Chaura": "Chowri Chowra", "Khilafat": "Khi-laafat", "Ghadar": "Ghuddar", "Khudiram": "Khoodiram",
    "Bagha Jatin": "Baagha Jateen", "Kukas": "Kookas", "lathi": "laathi", "Brahmo Samaj": "Brahmo Samaaj",
    "Arya Samaj": "Aarya Samaaj", "Chattopadhyay": "Chatto-paadhyay", "Sukhdev": "Sukh-dev",
}

ERA_SFX = {"era": "boom", "stat": "boom", "title": "chime", "end": "chime"}


# ------------------------------------------------------------------ helpers
_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, x):
    return a + (b - a) * x


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


_txt = {}


def text_img(text, size, fill=WHITE, path=FONT_BLACK, max_w=1600, stroke=0, align="center", spacing=1.12):
    """RGBA image of wrapped text (cached). Shrinks to fit max_w."""
    key = (text, size, fill, path, max_w, stroke, align)
    if key in _txt:
        return _txt[key]
    while True:
        fnt = font(path, size)
        lines = wrap(text, fnt, max_w)
        if max(fnt.getlength(l) for l in lines) <= max_w or size < 30:
            break
        size -= 4
    lh = int(size * spacing)
    w = int(max(fnt.getlength(l) for l in lines)) + stroke * 2 + 6
    h = lh * len(lines) + stroke * 2 + int(size * 0.28)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        lw = fnt.getlength(l)
        x = (w - lw) / 2 if align == "center" else stroke
        d.text((x, stroke + i * lh), l, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
    _txt[key] = img
    return img


_emo = {}


def emoji_img(chars, height):
    key = (chars, height)
    if key not in _emo:
        fnt = font(FONT_EMOJI, 109)
        tmp = Image.new("RGBA", (160 * len(chars) + 40, 180), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((20, 10), chars, font=fnt, embedded_color=True)
        bbox = tmp.getbbox() or (0, 0, 1, 1)
        tmp = tmp.crop(bbox)
        r = height / tmp.height
        _emo[key] = tmp.resize((max(1, int(tmp.width * r)), height), Image.LANCZOS)
    return _emo[key]


def put(canvas, img, xy, alpha=1.0, scale=1.0, anchor="lt"):
    """Paste img onto canvas with alpha/scale. anchor: lt (left-top) or mm (centre)."""
    if alpha <= 0.01:
        return
    if abs(scale - 1.0) > 0.01:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        img = img.copy()
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img.putalpha(a)
    x, y = xy
    if anchor == "mm":
        x, y = x - img.width // 2, y - img.height // 2
    canvas.alpha_composite(img, (int(x), int(y)))


def rounded(size, radius, fill, outline=None, width=0):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill, outline=outline, width=width)
    return img


def cue_time(b, cue):
    """Seconds into the beat where `cue` is spoken (char-proportional estimate)."""
    vo = b.get("vo", "")
    i = vo.lower().find(cue.lower()) if cue else -1
    if i < 0 or not vo:
        return LEAD
    return LEAD + b["vo_dur"] * (i / len(vo)) - 0.15


# --------------------------------------------------------------- voiceover
_kokoro = None


def tts(text):
    os.makedirs(TTS_DIR, exist_ok=True)
    spoken = text
    for k, v in PRON.items():
        spoken = spoken.replace(k, v)
    h = hashlib.sha1(f"{VOICE}|{SPEED}|{spoken}".encode()).hexdigest()[:16]
    path = os.path.join(TTS_DIR, h + ".npy")
    if os.path.exists(path):
        return np.load(path)
    global _kokoro
    if _kokoro is None:
        os.makedirs(MODEL_DIR, exist_ok=True)
        for f in MODEL_FILES:
            p = os.path.join(MODEL_DIR, f)
            if not os.path.exists(p):
                print("downloading", f)
                subprocess.run(["curl", "-sSL", "-o", p, MODEL_URL + f], check=True)
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(MODEL_DIR, MODEL_FILES[0]), os.path.join(MODEL_DIR, MODEL_FILES[1]))
    samples, sr = _kokoro.create(spoken, voice=VOICE, speed=SPEED, lang="en-gb")
    assert sr == SR
    samples = samples.astype(np.float32)
    np.save(path, samples)
    return samples


def plan():
    """Voice every beat and compute start/duration."""
    t = 0.0
    for i, b in enumerate(BEATS):
        if b.get("vo"):
            print(f"  voice {i + 1}/{len(BEATS)}", end="\r")
            b["audio"] = tts(b["vo"])
            b["vo_dur"] = len(b["audio"]) / SR
            b["dur"] = LEAD + b["vo_dur"] + TAIL
        else:
            b["audio"], b["vo_dur"], b["dur"] = None, 0.0, 1.9
        if b["kind"] in ("recap", "chips"):
            b["dur"] += 0.8
        if b["kind"] == "end":
            b["dur"] += 2.5
        b["start"] = t
        t += b["dur"]
    print()
    return t


# -------------------------------------------------------------------- audio
def synth_sfx(name):
    n = lambda s: int(SR * s)
    t = lambda s: np.arange(n(s)) / SR
    rng = np.random.default_rng(7)
    if name == "whoosh":
        x = rng.standard_normal(n(0.5))
        x = np.convolve(x, np.ones(40) / 40, "same")
        env = np.sin(np.linspace(0, math.pi, len(x))) ** 2
        return 0.35 * x * env
    if name == "boom":
        tt = t(1.4)
        return 0.55 * np.sin(2 * math.pi * (55 - 20 * tt) * tt) * np.exp(-tt * 3.2)
    if name == "pop":
        tt = t(0.12)
        return 0.18 * np.sin(2 * math.pi * 880 * tt) * np.exp(-tt * 40)
    if name == "chime":
        tt = t(2.0)
        return 0.16 * sum(np.sin(2 * math.pi * f * tt) * np.exp(-tt * d) for f, d in ((523.25, 2.5), (783.99, 3), (1046.5, 4)))
    return np.zeros(1)


def tanpura(total):
    """Pa-Sa-Sa-Sa(low) plucked drone with buzzy harmonics, looped for `total` s."""
    sa = 138.59  # C#3
    notes = [sa * 0.75, sa * 2, sa * 2, sa]
    out = np.zeros(int(SR * (total + 5)))
    pluck_len = int(SR * 4.5)
    tt = np.arange(pluck_len) / SR
    plucks = []
    for f in notes:
        sig = np.zeros(pluck_len)
        for k in range(1, 14):
            # jawari buzz: upper harmonics bloom then fade
            amp = (1 / k) * (1 + 0.8 * np.sin(math.pi * np.clip(tt / (0.6 + 0.12 * k), 0, 1)))
            sig += amp * np.sin(2 * math.pi * f * k * tt * (1 + 0.0004 * k))
        sig *= np.exp(-tt * 0.9) * np.minimum(1, tt / 0.01)
        plucks.append(sig / 6)
    step = int(SR * 1.0)
    i, pos = 0, 0
    while pos < len(out) - pluck_len:
        out[pos:pos + pluck_len] += plucks[i % 4]
        pos += step
        i += 1
    out = out[:int(SR * total)]
    fade = int(SR * 2)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def build_audio(total):
    n = int(SR * total) + SR
    vo = np.zeros(n, dtype=np.float32)
    fx = np.zeros(n, dtype=np.float32)
    for b in BEATS:
        s = int(SR * (b["start"] + LEAD))
        if b["audio"] is not None:
            a = b["audio"]
            vo[s:s + len(a)] += a[:n - s]
        sfx = ERA_SFX.get(b["kind"], "whoosh")
        clip = synth_sfx(sfx)
        s0 = int(SR * b["start"])
        fx[s0:s0 + len(clip)] += clip[:n - s0]
        for _, cue in b.get("points", []):
            c = synth_sfx("pop")
            s1 = int(SR * (b["start"] + max(0, cue_time(b, cue))))
            fx[s1:s1 + len(c)] += c[:n - s1]
    music = tanpura(total)
    music = np.pad(music, (0, n - len(music)))
    music *= 0.09 / (np.abs(music).max() + 1e-9)
    mix = vo * 0.95 + fx * 0.5 + music
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    path = os.path.join(OUT, "mix.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path


# ----------------------------------------------------------------- visuals
_bg = {}


def background(era):
    if era not in _bg:
        _, top, bot = ERAS[era]
        y = np.linspace(0, 1, H)[:, None, None]
        grad = np.array(top)[None, None, :] * (1 - y) + np.array(bot)[None, None, :] * y
        grad = np.repeat(grad, W, axis=1)
        xx, yy = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
        vig = 1 - 0.45 * np.clip(xx ** 2 * 0.6 + yy ** 2, 0, 1)[..., None]
        grain = np.random.default_rng(1).normal(0, 5, (H, W, 1))
        arr = np.clip(grad * vig + grain, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, "RGB").convert("RGBA")
        # faint ashoka-chakra watermark
        wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_chakra(ImageDraw.Draw(wm), 1600, 760, 520, 0, (255, 255, 255, 14), 10)
        img.alpha_composite(wm)
        _bg[era] = img
    return _bg[era]


def draw_chakra(d, cx, cy, r, rot, col, wdt):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=wdt)
    d.ellipse((cx - r * 0.14, cy - r * 0.14, cx + r * 0.14, cy + r * 0.14), fill=col)
    for k in range(24):
        a = rot + k * math.pi / 12
        d.line((cx + r * 0.14 * math.cos(a), cy + r * 0.14 * math.sin(a), cx + r * 0.94 * math.cos(a), cy + r * 0.94 * math.sin(a)),
               fill=col, width=max(2, wdt // 2))


PARTICLES = [(random.Random(i).uniform(0, W), random.Random(i + 99).uniform(0, H),
              random.Random(i + 7).uniform(1.5, 4.5), random.Random(i + 3).uniform(8, 30)) for i in range(70)]


def particles(canvas, t):
    d = ImageDraw.Draw(canvas)
    for x, y, r, v in PARTICLES:
        yy = (y - t * v) % H
        xx = x + 18 * math.sin(t * 0.3 + y)
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 210, 150, 55))


TL_X0, TL_X1, TL_Y = 260, 1660, 1022
TL_MARKS = [1857, 1885, 1905, 1919, 1930, 1942, 1947]


def year_x(y):
    return TL_X0 + (TL_X1 - TL_X0) * (y - 1857) / (1947 - 1857)


def timeline(canvas, year):
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((TL_X0, TL_Y - 4, TL_X1, TL_Y + 4), 4, fill=(255, 255, 255, 55))
    xm = year_x(year)
    if xm > TL_X0 + 4:
        d.rounded_rectangle((TL_X0, TL_Y - 4, xm, TL_Y + 4), 4, fill=SAFFRON + (255,))
    f = font(FONT_SEMI, 20)
    for m in TL_MARKS:
        x = year_x(m)
        done = m <= year + 0.01
        d.ellipse((x - 6, TL_Y - 6, x + 6, TL_Y + 6), fill=(SAFFRON if done else (120, 125, 145)) + (255,))
        d.text((x, TL_Y + 26), str(m), font=f, fill=(255, 255, 255, 200 if done else 110), anchor="mm")
    d.ellipse((xm - 13, TL_Y - 13, xm + 13, TL_Y + 13), fill=WHITE + (255,), outline=SAFFRON + (255,), width=5)
    d.text((xm, TL_Y - 32), str(int(round(year))), font=font(FONT_BLACK, 26), fill=WHITE + (255,), anchor="mm")


def header(canvas, era, alpha):
    tag = ERAS[era][0]
    if tag:
        f = font(FONT_SEMI, 24)
        w = int(f.getlength(tag)) + 44
        pill = rounded((w, 48), 24, SAFFRON + (235,))
        ImageDraw.Draw(pill).text((22, 24), tag, font=f, fill=(30, 15, 0), anchor="lm")
        put(canvas, pill, (70, 52), alpha)
    t = text_img(TAG, 22, (255, 255, 255, 150), FONT_SEMI)
    put(canvas, t, (W - 70 - t.width, 62), 1.0)


def caption_chunks(b):
    words = b.get("vo", "").split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) > 46 or w[-1] in ".?!":
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    total = sum(len(c) + 1 for c in chunks)
    out, acc = [], 0
    for c in chunks:
        s = LEAD + b["vo_dur"] * acc / total
        acc += len(c) + 1
        out.append((s, LEAD + b["vo_dur"] * acc / total, c))
    b["_caps"] = out
    return out


def captions(canvas, b, lt):
    for s, e, c in b.get("_caps") or caption_chunks(b):
        if s <= lt < e + 0.05:
            img = text_img(c, 38, WHITE, FONT_SEMI, max_w=1500)
            box = rounded((img.width + 44, img.height + 14), 14, (0, 0, 0, 150))
            put(canvas, box, (W // 2, 930), 1, anchor="mm")
            put(canvas, img, (W // 2, 932), 1, anchor="mm")
            return


# --- scene renderers: draw onto layer L for beat b at local time lt ---------
def sc_title(L, b, lt):
    d = ImageDraw.Draw(L)
    a = ease_out(lt / 0.8)
    draw_chakra(d, W // 2, 300, int(140 * ease_back(lt / 0.9)), lt * 0.6, (120, 150, 255, int(230 * a)), 9)
    put(L, text_img("INDIA'S LONG ROAD", 112, WHITE), (W // 2, 560 + 30 * (1 - a)), a, anchor="mm")
    a2 = ease_out((lt - 0.35) / 0.7)
    put(L, text_img("TO INDEPENDENCE", 112, SAFFRON), (W // 2, 680 + 30 * (1 - a2)), a2, anchor="mm")
    a3 = ease_out((lt - 0.9) / 0.6)
    put(L, text_img("Class 8 Social Science  ·  Chapter 2  ·  Made Simple", 36, GREY, FONT_MED), (W // 2, 790), a3, anchor="mm")


def sc_era(L, b, lt):
    a = ease_out(lt / 0.5)
    put(L, emoji_img(b["emoji"], 150), (W // 2, 300), a, ease_back(lt / 0.55), anchor="mm")
    put(L, text_img(b["num"], 54, SAFFRON, FONT_BOLD), (W // 2, 455), a, anchor="mm")
    put(L, text_img(b["name"].upper(), 130, WHITE), (W // 2 + 80 * (1 - a), 580), a, anchor="mm")
    d = ImageDraw.Draw(L)
    wbar = int(600 * ease_out((lt - 0.2) / 0.6))
    d.rounded_rectangle((W // 2 - wbar // 2, 670, W // 2 + wbar // 2, 680), 5, fill=SAFFRON + (255,))


def sc_year(L, b, lt):
    big = b.get("big", str(b["year"]))
    a = ease_out(lt / 0.55)
    size = 230 if len(big) <= 5 else (150 if len(big) <= 8 else 118)
    put(L, text_img(big, size, SAFFRON, max_w=700), (120 - 120 * (1 - a), 200), a)
    put(L, emoji_img(b["emoji"], 170), (330, 640), ease_out((lt - 0.2) / 0.4), ease_back((lt - 0.2) / 0.5), anchor="mm")
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((850, 210, 858, 780), 4, fill=(255, 255, 255, int(70 * a)))
    ah = ease_out((lt - 0.15) / 0.5)
    put(L, text_img(b["head"], 66, WHITE, FONT_BLACK, max_w=900, align="left"), (900 + 40 * (1 - ah), 210), ah)
    y = 400 if len(b["head"]) > 26 else 340
    for i, (txt, cue) in enumerate(b.get("points", [])):
        ap = ease_out((lt - cue_time(b, cue)) / 0.4)
        if ap <= 0:
            y += 120
            continue
        card = rounded((880, 96), 18, (255, 255, 255, 26))
        put(L, card, (900 + 60 * (1 - ap), y), ap)
        d = ImageDraw.Draw(L)
        cx = 900 + 60 * (1 - ap)
        d.rounded_rectangle((cx, y, cx + 10, y + 96), 5, fill=SAFFRON + (int(255 * ap),))
        put(L, text_img(txt, 42, WHITE, FONT_SEMI, max_w=820, align="left"), (cx + 38, y + 22), ap)
        y += 120


def sc_stat(L, b, lt):
    a = ease_out(lt / 0.5)
    put(L, emoji_img(b["emoji"], 140), (W // 2, 230), a, ease_back(lt / 0.6), anchor="mm")
    k = ease_out((lt - 0.2) / 1.6)
    val = int(round(b["n"] * k))
    put(L, text_img(b["fmt"].format(val), 210, SAFFRON, max_w=1700), (W // 2, 480), a, 0.9 + 0.1 * ease_back(lt / 0.6), anchor="mm")
    al = ease_out((lt - 0.8) / 0.5)
    put(L, text_img(b["label"], 60, WHITE, FONT_BOLD), (W // 2, 680 + 20 * (1 - al)), al, anchor="mm")


def sc_versus(L, b, lt):
    a = ease_out(lt / 0.5)
    put(L, text_img(b["head"], 62, WHITE), (W // 2, 180), a, anchor="mm")
    split_t = cue_time(b, b["split"])
    for side, (title, col, items) in enumerate((b["left"], b["right"])):
        x = 170 if side == 0 else 1000
        t0 = 0.3 if side == 0 else split_t
        ac = ease_out((lt - t0) / 0.5)
        if ac <= 0:
            continue
        card = rounded((750, 560), 26, (255, 255, 255, 22), outline=col + (200,), width=3)
        dy = 40 * (1 - ac)
        put(L, card, (x, 260 + dy), ac)
        band = rounded((750, 92), 26, col + (230,))
        put(L, band, (x, 260 + dy), ac)
        put(L, text_img(title, 46, (20, 10, 0) if col == SAFFRON else WHITE), (x + 375, 306 + dy), ac, anchor="mm")
        span = (b["vo_dur"] * 0.45) if side == 0 else (b["vo_dur"] + LEAD - split_t) * 0.6
        for i, it in enumerate(items):
            ai = ease_out((lt - t0 - 0.3 - i * span / 3) / 0.35)
            mark = "✓" if side == 0 and col == SAFFRON else "•"
            put(L, text_img(f"{mark}  {it}", 40, WHITE, FONT_SEMI, max_w=660, align="left"), (x + 45 + 30 * (1 - ai), 400 + i * 130 + dy), ai)
    if lt > split_t:
        av = ease_back((lt - split_t) / 0.4)
        put(L, text_img("VS", 64, WHITE, FONT_BLACK, stroke=4), (W // 2 + 10, 540), min(1, av), av, anchor="mm")


def sc_quote(L, b, lt):
    a = ease_out(lt / 0.5)
    put(L, text_img("“", 300, SAFFRON, FONT_BLACK), (200, 120), a)
    words = b["quote"].split()
    qs = cue_time(b, words[0] + " " + words[1])
    k = np.clip((lt - qs) / max(0.5, (b["vo_dur"] + LEAD - qs) * 0.85), 0, 1)
    shown = " ".join(words[:max(0, int(math.ceil(k * len(words))))])
    full = text_img(b["quote"], 88, WHITE, FONT_ITAL, max_w=1400)
    if shown:
        img = text_img(shown, 88, WHITE, FONT_ITAL, max_w=1400)
        # draw into a box the size of the full quote so lines don't jump
        box = Image.new("RGBA", full.size, (0, 0, 0, 0))
        box.alpha_composite(img, ((full.width - img.width) // 2 if img.height < full.height // 2 else 0, 0))
        put(L, box, (W // 2, 470), 1, anchor="mm")
    aw = ease_out((lt - 0.4) / 0.5)
    put(L, text_img("— " + b["who"], 50, SAFFRON, FONT_BOLD), (W // 2, 720), aw, anchor="mm")


def sc_chips(L, b, lt):
    a = ease_out(lt / 0.5)
    put(L, text_img(b["head"], 70, WHITE), (W // 2, 190), a, anchor="mm")
    cols = 3
    for i, (txt, cue) in enumerate(b["items"]):
        ap = ease_back((lt - cue_time(b, cue)) / 0.45)
        if ap <= 0:
            continue
        cx = 400 + (i % cols) * 560
        cy = 380 + (i // cols) * 170
        img = text_img(txt, 44, WHITE, FONT_BOLD)
        chip = rounded((img.width + 70, 110), 55, (255, 255, 255, 30), outline=SAFFRON + (220,), width=3)
        chip.alpha_composite(img, (35, (110 - img.height) // 2 + 4))
        put(L, chip, (cx, cy), min(1, ap), ap, anchor="mm")
    af = ease_back((lt - cue_time(b, "Together")) / 0.5)
    if af > 0:
        put(L, text_img(b["final"], 120, SAFFRON), (W // 2, 760), min(1, af), af, anchor="mm")


def sc_recap(L, b, lt):
    a = ease_out(lt / 0.5)
    put(L, text_img("QUICK RECAP", 72, WHITE), (W // 2, 190), a, anchor="mm")
    d = ImageDraw.Draw(L)
    n = len(b["items"])
    xs = [230 + i * (1460 / (n - 1)) for i in range(n)]
    times = [cue_time(b, cue) for _, _, cue in b["items"]]
    # road line grows to the latest revealed node
    reached = 0
    for i, t0 in enumerate(times):
        if lt >= t0:
            reached = i + min(1, (lt - t0) / 0.5) if i < n - 1 else i
    xr = xs[0] + (xs[-1] - xs[0]) * (reached / (n - 1)) if reached else xs[0]
    d.rounded_rectangle((xs[0], 496, xs[-1], 504), 4, fill=(255, 255, 255, 60))
    d.rounded_rectangle((xs[0], 496, xr, 504), 4, fill=SAFFRON + (255,))
    for i, (yr, label, _) in enumerate(b["items"]):
        ap = ease_back((lt - times[i]) / 0.45)
        if ap <= 0:
            continue
        r = 22 * ap
        last = i == n - 1
        col = GREEN if last else SAFFRON
        d.ellipse((xs[i] - r, 500 - r, xs[i] + r, 500 + r), fill=col + (255,), outline=WHITE + (255,), width=4)
        up = i % 2 == 0
        put(L, text_img(yr, 54, col, FONT_BLACK), (xs[i], 410 if up else 590), min(1, ap), anchor="mm")
        put(L, text_img(label, 34, WHITE, FONT_SEMI, max_w=230), (xs[i], 345 if up else 655), min(1, ap), anchor="mm")


def sc_end(L, b, lt):
    a = ease_out(lt / 0.5)
    put(L, text_img("Which freedom fighter inspires you the most?", 80, WHITE, max_w=1500), (W // 2, 300), a, anchor="mm")
    ac = ease_out((lt - cue_time(b, "comments")) / 0.5)
    put(L, emoji_img("👇", 110), (W // 2 - 260, 560), ac, anchor="mm")
    put(L, text_img("Comment below", 60, SAFFRON, FONT_BOLD), (W // 2 + 60, 560), ac, anchor="mm")
    asub = ease_back((lt - cue_time(b, "subscribe")) / 0.5)
    if asub > 0:
        pulse = 1 + 0.04 * math.sin(lt * 6)
        btn = rounded((520, 120), 60, (220, 30, 40, 255))
        ImageDraw.Draw(btn).text((260, 60), "SUBSCRIBE", font=font(FONT_BLACK, 56), fill=WHITE, anchor="mm")
        put(L, btn, (W // 2, 740), min(1, asub), asub * pulse, anchor="mm")


SCENES = dict(title=sc_title, era=sc_era, year=sc_year, stat=sc_stat, versus=sc_versus,
              quote=sc_quote, chips=sc_chips, recap=sc_recap, end=sc_end)


def beat_at(t):
    for i, b in enumerate(BEATS):
        if t < b["start"] + b["dur"]:
            return i
    return len(BEATS) - 1


def render(t):
    i = beat_at(t)
    b = BEATS[i]
    lt = t - b["start"]
    # background (crossfade between eras)
    frame = background(b["era"]).copy()
    if i > 0 and BEATS[i - 1]["era"] != b["era"] and lt < 0.6:
        frame = Image.blend(background(BEATS[i - 1]["era"]), frame, ease_out(lt / 0.6))
    particles(frame, t)
    # scene layer with fade in/out
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    SCENES[b["kind"]](L, b, lt)
    out_a = 1 - ease_out((lt - (b["dur"] - 0.25)) / 0.25) if i < len(BEATS) - 1 else 1
    if out_a < 0.99:
        L.putalpha(L.getchannel("A").point(lambda v: int(v * out_a)))
    frame.alpha_composite(L)
    header(frame, b["era"], ease_out(lt / 0.5) if i > 0 and BEATS[i - 1]["era"] != b["era"] else 1)
    if b.get("vo") and b["kind"] not in ("quote",):
        captions(frame, b, lt)
    prev_year = BEATS[i - 1]["year"] if i > 0 else b["year"]
    timeline(frame, lerp(prev_year, b["year"], ease_out(lt / 0.9)))
    return frame.convert("RGB")


def render_bytes(fi):
    return render(fi / FPS).tobytes()


# ------------------------------------------------------------------ outputs
def fmt_ts(s, srt=False):
    h, m = int(s // 3600), int(s % 3600 // 60)
    sec = s % 60
    if srt:
        return f"{h:02d}:{m:02d}:{int(sec):02d},{int((sec % 1) * 1000):03d}"
    return f"{m}:{int(sec):02d}"


def write_srt():
    lines, k = [], 1
    for b in BEATS:
        if not b.get("vo"):
            continue
        for s, e, c in caption_chunks(b):
            lines += [str(k), f"{fmt_ts(b['start'] + s, True)} --> {fmt_ts(b['start'] + e, True)}", c, ""]
            k += 1
    with open(os.path.join(OUT, "road-to-independence.srt"), "w") as f:
        f.write("\n".join(lines))


def write_script(timed):
    lines = [f"# {TITLE} — narration script", "",
             "Class 8 SST, Chapter 2 (Tapestry of the Past). Generated from `build.py` BEATS — edit there, not here.", "",
             "| # | Time | On screen | Voiceover |", "|---|---|---|---|"]
    for i, b in enumerate(BEATS):
        ts = fmt_ts(b["start"]) if timed else "–"
        if b["kind"] == "era":
            vis = f"**{b['num']}: {b['name']}** (chapter card) {b['emoji']}"
        elif b["kind"] == "year":
            vis = f"**{b.get('big', b['year'])}** {b['emoji']} — {b['head']}: " + "; ".join(p for p, _ in b["points"])
        elif b["kind"] == "stat":
            vis = f"Count-up **{b['fmt'].format(b['n'])}** — {b['label']} {b['emoji']}"
        elif b["kind"] == "versus":
            vis = f"Split card: {b['left'][0]} vs {b['right'][0]}"
        elif b["kind"] == "quote":
            vis = f"Quote card, word-by-word — {b['who']}"
        elif b["kind"] == "chips":
            vis = "Chips pop in: " + ", ".join(t for t, _ in b["items"]) + f" → **{b['final']}**"
        elif b["kind"] == "recap":
            vis = "Recap timeline: " + " · ".join(f"{y} {l}" for y, l, _ in b["items"])
        elif b["kind"] == "title":
            vis = "Title card, spinning Ashoka Chakra"
        else:
            vis = "End card: comment prompt + SUBSCRIBE"
        lines.append(f"| {i + 1} | {ts} | {vis} | {b.get('vo', '*(whoosh + boom)*')} |")
    with open(os.path.join(ROOT, "script.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def write_upload(total):
    chapters = ["0:00 Intro"]
    for b in BEATS:
        if b["kind"] == "era":
            chapters.append(f"{fmt_ts(b['start'])} {b['num'].title()}: {b['name']}")
        if b["kind"] == "recap":
            chapters.append(f"{fmt_ts(b['start'])} Quick recap")
    txt = f"""# Upload kit

**Length:** {fmt_ts(total)}  ·  **Format:** 16:9 1920x1080, YouTube long-form

## Title options
1. India's Freedom Struggle in {math.ceil(total / 60)} Minutes | Class 8 SST Chapter 2 Animated
2. India's Long Road to Independence — Class 8 History Explained (1857–1947)
3. 90 Years to Freedom: Class 8 SST Ch 2 Full Chapter Animation

## Description
India's Long Road to Independence (Class 8 Social Science, Chapter 2) explained with animation — from the 1858 Royal Proclamation to Independence and Partition in 1947. Covers reform movements, the birth of the Congress, the Partition of Bengal, Swadeshi, the revolutionaries, Gandhi's satyagraha, Jallianwala Bagh, Non-Cooperation, the Salt March, Quit India, the INA and the integration of princely states.

Chapters:
{chr(10).join(chapters)}

#Class8 #SocialScience #IndianFreedomStruggle #History #NCERT #CBSE

## Tags
class 8 sst chapter 2, india's long road to independence, class 8 history, indian freedom struggle, ncert class 8, freedom struggle animation, 1857 to 1947, cbse class 8 social science

## Files
- `road-to-independence.mp4` — upload this
- `road-to-independence.srt` — upload as English subtitles (YouTube Studio → Subtitles)
- `thumbnail.png` — 1280x720 thumbnail
"""
    with open(os.path.join(OUT, "upload.md"), "w") as f:
        f.write(txt)


def thumbnail():
    img = background("e4").copy()
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_chakra(ImageDraw.Draw(L), 1500, 540, 360, 0.2, (255, 255, 255, 60), 14)
    put(L, emoji_img("🇮🇳", 300), (1500, 540), 1, anchor="mm")
    put(L, text_img("1857 → 1947", 96, SAFFRON, FONT_BLACK, stroke=6), (90, 170))
    put(L, text_img("INDIA'S ROAD", 150, WHITE, FONT_BLACK, stroke=8), (80, 330))
    put(L, text_img("TO FREEDOM", 150, WHITE, FONT_BLACK, stroke=8), (80, 500))
    tag = rounded((720, 110), 55, SAFFRON + (255,))
    ImageDraw.Draw(tag).text((360, 55), "CLASS 8 · CH 2", font=font(FONT_BLACK, 60), fill=(30, 15, 0), anchor="mm")
    put(L, tag, (90, 720))
    img.alpha_composite(L)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(os.path.join(OUT, "thumbnail.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--script" in sys.argv:
        write_script(False)
        return
    total = plan()
    write_script(True)
    print(f"total {total:.1f}s, {len(BEATS)} beats")
    if "--preview" in sys.argv:
        pdir = os.path.join(OUT, "preview")
        os.makedirs(pdir, exist_ok=True)
        for i, b in enumerate(BEATS):
            render(b["start"] + b["dur"] * 0.8).save(os.path.join(pdir, f"{i + 1:02d}-{b['kind']}.png"))
        return
    audio = build_audio(total)
    write_srt()
    write_upload(total)
    thumbnail()
    nframes = int(total * FPS)
    out = os.path.join(OUT, "road-to-independence.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", audio, "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, fb in enumerate(pool.imap(render_bytes, range(nframes), chunksize=16)):
            ff.stdin.write(fb)
            if k % (FPS * 10) == 0:
                print(f"  frame {k}/{nframes}", end="\r")
    ff.stdin.close()
    ff.wait()
    print("\nwrote", out)


if __name__ == "__main__":
    main()
