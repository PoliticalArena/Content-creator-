"""Animated channel end card (Gamchha Patrakar) appended to the main edit.
usage: endcard.py <card.jpg> <main.mp4> <out.mp4> <workdir>"""
import math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CARD, MAIN, OUT, WORK = sys.argv[1:5]
W, H, FPS = 1080, 1920, 30
DUR = 4.5
NF = int(DUR * FPS)

clamp = lambda x: max(0.0, min(1.0, x))
def ease_out_back(x, s=2.2):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2
def ease_out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3

card = Image.open(CARD).convert("RGB").resize((W, H), Image.LANCZOS)

# buttons (in 1080x1920 space): cut them out, then fill their strip with background
BTN_BOXES = [(24, 1562, 366, 1786), (378, 1562, 702, 1786), (716, 1562, 1054, 1786)]
BTN_IN = [0.55, 0.75, 0.95]        # pop-in times
BTN_TAP = [1.7, 2.4, 3.1]          # tap/press times
def soft_cut(box):
    im = card.crop(box).convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((6, 6, im.width - 7, im.height - 7), radius=44, fill=255)
    im.putalpha(m.filter(ImageFilter.GaussianBlur(5)))
    return im
buttons = [soft_cut(b) for b in BTN_BOXES]
base = card.copy()
fill = card.crop((0, 1820, W, 1920)).transpose(Image.FLIP_TOP_BOTTOM).resize((W, 320)).filter(ImageFilter.GaussianBlur(3))
fade = Image.linear_gradient("L").resize((1, 40))
fmask = Image.new("L", fill.size, 255)
fmask.paste(fade.resize((W, 40)), (0, 0))
fmask.paste(fade.resize((W, 30)).transpose(Image.FLIP_TOP_BOTTOM), (0, fill.height - 30))
base.paste(fill, (0, 1516), fmask)


def scaled_center(canvas, im, cx, cy, s, alpha=1.0):
    if s <= 0.02:
        return
    r = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR).convert("RGBA")
    if alpha < 1:
        r.putalpha(int(255 * alpha))
    canvas.alpha_composite(r, (int(cx - r.width / 2), int(cy - r.height / 2)))


def frame(t):
    # slow push-in on the whole card, with a punchy zoom on entry
    z = 1.0 + 0.18 * (1 - ease_out_cubic(t / 0.45)) + 0.04 * (t / DUR)
    cw, ch = W / z, H / z
    x0, y0 = (W - cw) / 2, (H - ch) * 0.35
    canvas = base.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")
    if t < 0.25:   # motion blur on the entry zoom
        canvas = canvas.filter(ImageFilter.GaussianBlur(8 * (1 - t / 0.25)))

    # buttons: pop in, then each gets a press + ripple
    for i, (box, img) in enumerate(zip(BTN_BOXES, buttons)):
        bx = (box[0] + box[2]) / 2
        by = (box[1] + box[3]) / 2
        # map button centre through the same zoom
        cx = (bx - x0) * z
        cy = (by - y0) * z
        s = ease_out_back((t - BTN_IN[i]) / 0.35) * z
        dt = t - BTN_TAP[i]
        if 0 <= dt < 0.3:
            s *= 1 - 0.1 * math.sin(dt / 0.3 * math.pi)
        scaled_center(canvas, img, cx, cy, s, clamp((t - BTN_IN[i]) / 0.08))
        if 0 <= dt < 0.6:   # tap ripple
            k = dt / 0.6
            r = int(30 + 170 * ease_out_cubic(k))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse((cx - r, cy - r, cx + r, cy + r),
                                       outline=(255, 255, 255, int(230 * (1 - k))), width=8)
            canvas = Image.alpha_composite(canvas, ov)

    # diagonal light sweep across the card
    sp = (t - 1.2) / 0.9
    if 0 <= sp <= 1:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        xs = -400 + sp * (W + 800)
        ImageDraw.Draw(ov).polygon([(xs, 0), (xs + 140, 0), (xs - 500, H), (xs - 640, H)], fill=(255, 255, 255, 60))
        canvas = Image.alpha_composite(canvas, ov.filter(ImageFilter.GaussianBlur(30)))

    # white flash on the cut in
    if t < 0.18:
        canvas = Image.alpha_composite(canvas, Image.new("RGBA", (W, H), (255, 255, 255, int(220 * (1 - t / 0.18)))))
    return canvas.convert("RGB")


# ---------- SFX ----------
SR = 48000
def env(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / r)

def whoosh(dur=0.45):
    n = int(dur * SR); noise = np.random.randn(n); out = np.zeros(n); y = 0
    for i in range(n):
        y += (0.02 + 0.5 * i / n) * (noise[i] - y); out[i] = y
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2 * 1.2

def boom(dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 55 + 70 * np.exp(-t * 18)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.28) + np.random.randn(n) * env(n, 0.001, 0.03) * 0.4

def pop(freq, dur=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(freq * (1 + 1.5 * np.exp(-t * 60))) / SR) * env(n, 0.001, 0.035)

def click():
    n = int(0.06 * SR); t = np.arange(n) / SR
    return (np.random.randn(n) * env(n, 0.0005, 0.006) + np.sin(2 * np.pi * 2200 * t) * env(n, 0.0005, 0.012)) * 0.7

def chime(dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) * env(n, 0.003, 0.5) / (k + 1) for k, f in enumerate((880, 1108.7, 1318.5)))
    return s * 0.5

def build_sfx():
    np.random.seed(3)
    total = int(DUR * SR)
    mix = np.zeros(total)
    def add(sig, at, g):
        i = int(at * SR); j = min(total, i + len(sig)); mix[i:j] += sig[:j - i] * g
    add(whoosh(0.4), 0.0, 0.5)
    add(boom(), 0.02, 0.6)
    for i, ts in enumerate(BTN_IN):
        add(pop(600 + 200 * i), ts, 0.5)
    for ts in BTN_TAP:
        add(click(), ts, 0.7)
    add(chime(), BTN_TAP[0] - 0.05, 0.25)
    mix *= np.minimum(1, (DUR - np.arange(total) / SR) / 0.4)   # fade out
    mix = mix / np.max(np.abs(mix)) * 0.6
    with wave.open(f"{WORK}/end_sfx.wav", "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())


def main():
    build_sfx()
    end_mp4 = f"{WORK}/endcard.mp4"
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", f"{WORK}/end_sfx.wav",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", str(DUR), end_mp4],
        stdin=subprocess.PIPE)
    for i in range(NF):
        enc.stdin.write(frame(i / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", MAIN, "-i", end_mp4, "-filter_complex",
        "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True)
    print("done")


if __name__ == "__main__":
    if len(sys.argv) > 5:   # preview stills
        for ts in map(float, sys.argv[5].split(",")):
            frame(ts).save(f"{WORK}/end_{ts:.2f}.jpg", quality=85)
    else:
        main()
