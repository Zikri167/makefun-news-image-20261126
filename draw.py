"""Procedural front-page renderer for news-image-20261126.

Stdlib only. Draws a 1024x1024 newspaper front page for Thursday
26 November 2026 and writes it as a deterministic PNG: fixed palette,
fixed geometry, zlib level 9, no timestamps, no randomness, so two runs
produce byte-identical output.
"""
import base64
import struct
import zlib

from fontdata import FONTS

W, H = 1024, 1024
PAPER = (247, 243, 232)
INK = (20, 20, 20)
RED = (163, 18, 18)
BLUE = (29, 78, 137)
GRAY = (110, 105, 95)
LIGHT = (233, 227, 212)
MID = (200, 192, 172)
ORANGE = (214, 110, 20)
GOLD = (232, 178, 40)


class Canvas:
    def __init__(self, w=W, h=H, bg=PAPER):
        self.w, self.h = w, h
        self.buf = bytearray(bg * (w * h))

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + (x1 - x0) * 3] = bytes(c) * (x1 - x0)

    def hline(self, x, y, w, c, t=1):
        for k in range(t):
            self.rect(x, y + k, w, 1, c)

    def vline(self, x, y, h, c, t=1):
        for k in range(t):
            self.rect(x + k, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            for a in range(t):
                for b in range(t):
                    self.px(x + a, y + b, c)
            if x == x1 and y == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            if rr <= 0:
                break
            for a in range(360):
                import math
                x = cx + int(rr * math.cos(math.radians(a)))
                y = cy + int(rr * math.sin(math.radians(a)))
                self.px(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for dy in range(-ry, ry + 1):
            dx = int(rx * (1 - (dy * dy) / (ry * ry)) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def poly(self, pts, c):
        # Scanline fill, even-odd rule.
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(int(xs[k]), y, max(1, int(xs[k + 1]) - int(xs[k])), 1, c)

    # ---- text ----
    def _glyph(self, font, ch):
        f = FONTS[font]
        g = f["chars"].get(ch)
        if g is None:
            g = f["chars"]["?"]
        return f, g

    def text_w(self, font, s):
        f = FONTS[font]
        total = 0
        for ch in s:
            g = f["chars"].get(ch, f["chars"]["?"])
            total += g[0]
        return total

    def text(self, font, x, y_baseline, s, c=INK):
        """Draw s with its baseline at y_baseline. Returns width drawn."""
        f = FONTS[font]
        cx = x
        for ch in s:
            g = f["chars"].get(ch, f["chars"]["?"])
            adv, w, h, y0, b64 = g
            if w and h:
                bits = base64.b64decode(b64)
                top = y_baseline - f["ascent"] + y0
                bi = 0
                for yy in range(h):
                    for xx in range(w):
                        byte = bits[bi >> 3]
                        if byte & (0x80 >> (bi & 7)):
                            self.px(cx + xx, top + yy, c)
                        bi += 1
            cx += adv
        return cx - x

    def text_center(self, font, cx, y_baseline, s, c=INK):
        w = self.text_w(font, s)
        return self.text(font, cx - w // 2, y_baseline, s, c)

    def wrap(self, font, s, width):
        lines, cur = [], ""
        for word in s.split(" "):
            trial = (cur + " " + word).strip()
            if self.text_w(font, trial) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, font, x, y_baseline, s, width, leading, c=INK):
        y = y_baseline
        for ln in self.wrap(font, s, width):
            self.text(font, x, y, ln, c)
            y += leading
        return y


def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def burst(cv, bx, by, r, c):
    # 16-point star burst.
    import math
    pts = []
    for k in range(16):
        ang = math.pi * k / 8
        rr = r if k % 2 == 0 else r // 3
        pts.append((bx + int(rr * math.cos(ang)), by + int(rr * math.sin(ang))))
    cv.poly(pts, c)


# ---- pictograms (flat vector shapes) ----

def draw_tanker(cv, x, y, w, h):
    # Fuel tanker on a road, engulfed in flames.
    road_y = y + int(h * 0.86)
    cv.hline(x, road_y, w, INK, 3)
    for wx in (0.05, 0.35, 0.65, 0.88):
        cv.hline(x + int(w * wx), road_y + 10, int(w * 0.08), GRAY, 2)
    # tank body: long cylinder, tilted slightly by the crash
    tank_y = road_y - 52
    cv.rect(x + 18, tank_y, 210, 44, GRAY)
    cv.ellipse(x + 18, tank_y + 22, 10, 22, MID)
    cv.ellipse(x + 228, tank_y + 22, 10, 22, MID)
    cv.rect(x + 18, tank_y, 210, 10, LIGHT)
    # hazard stripe on the tank
    for i in range(6):
        cv.rect(x + 30 + i * 32, tank_y + 16, 16, 20, RED if i % 2 == 0 else GOLD)
    # cab
    cv.rect(x + 238, tank_y + 6, 52, 38, INK)
    cv.rect(x + 246, tank_y + 12, 20, 14, BLUE)
    # wheels
    for wx in (52, 96, 196, 262):
        cv.circle(x + wx, road_y - 2, 11, INK)
        cv.circle(x + wx, road_y - 2, 4, PAPER)
    # flames rising from the tank
    burst(cv, x + 120, tank_y - 26, 34, ORANGE)
    burst(cv, x + 170, tank_y - 38, 26, RED)
    cv.poly([(x + 100, tank_y - 10), (x + 112, tank_y - 52),
             (x + 124, tank_y - 10)], GOLD)
    cv.poly([(x + 150, tank_y - 14), (x + 162, tank_y - 58),
             (x + 174, tank_y - 14)], GOLD)
    # smoke
    for dx, dy, r in ((0.30, -0.42, 9), (0.42, -0.52, 12), (0.55, -0.58, 9)):
        cv.circle(x + int(w * dx), y + int(h * (0.62 + dy)), r, GRAY)


def draw_jets(cv, x, y, w, h):
    # Runway with five fighter jets, one hit, refinery flames behind.
    base = y + h - 12
    cv.hline(x, base, w, INK, 3)
    for wx in (0.05, 0.30, 0.55, 0.80):
        cv.hline(x + int(w * wx), base + 6, int(w * 0.14), GRAY, 2)
    # refinery towers at the back
    for tx in (0.72, 0.82, 0.92):
        cv.rect(x + int(w * tx), y + 8, 14, 44, GRAY)
        burst(cv, x + int(w * tx) + 7, y + 4, 12, ORANGE)
    # five jets in a row, nose right
    for i in range(5):
        jx = x + 8 + i * 52
        jy = base - 34
        cv.poly([(jx, jy + 10), (jx + 34, jy + 10), (jx + 46, jy + 16),
                 (jx + 34, jy + 22), (jx, jy + 22)], INK)
        cv.poly([(jx + 10, jy + 10), (jx + 18, jy), (jx + 24, jy + 10)], INK)
        cv.poly([(jx + 10, jy + 22), (jx + 18, jy + 32), (jx + 24, jy + 22)], INK)
        cv.rect(jx + 4, jy + 13, 8, 6, RED if i == 2 else BLUE)
    # hit marker over the middle jet
    burst(cv, x + 122, base - 52, 18, RED)
    cv.circle(x + 122, base - 52, 5, PAPER)


def draw_rocket(cv, x, y, w, h):
    # Rocket climbing past the Tiangong station, stars around.
    for sx, sy in ((0.08, 0.12), (0.22, 0.04), (0.85, 0.10), (0.93, 0.35),
                   (0.05, 0.55), (0.90, 0.62)):
        cv.circle(x + int(w * sx), y + int(h * sy), 2, GRAY)
    # station: horizontal module with panels
    sx, sy = x + int(w * 0.58), y + int(h * 0.30)
    cv.rect(sx, sy, 74, 18, GRAY)
    cv.rect(sx - 34, sy + 4, 30, 10, BLUE)
    cv.rect(sx + 78, sy + 4, 30, 10, BLUE)
    cv.circle(sx + 37, sy + 9, 6, RED)
    # orbit ring
    cv.ring(x + int(w * 0.62), y + int(h * 0.42), 52, MID, 2)
    # rocket, nose up
    rx = x + int(w * 0.22)
    ry = y + 6
    cv.poly([(rx, ry), (rx + 12, ry + 18), (rx - 12, ry + 18)], RED)
    cv.rect(rx - 12, ry + 18, 24, 40, INK)
    cv.rect(rx - 12, ry + 30, 24, 8, BLUE)
    cv.poly([(rx - 12, ry + 58), (rx - 24, ry + 74), (rx - 12, ry + 66)], INK)
    cv.poly([(rx + 12, ry + 58), (rx + 24, ry + 74), (rx + 12, ry + 66)], INK)
    # flame
    cv.poly([(rx - 8, ry + 74), (rx, ry + 96), (rx + 8, ry + 74)], ORANGE)
    cv.poly([(rx - 4, ry + 74), (rx, ry + 88), (rx + 4, ry + 74)], GOLD)


def draw_atom_flag(cv, x, y, w, h):
    # Atom symbol (tactical nuclear weapons) + Swiss flag leaving.
    ax, ay = x + int(w * 0.28), y + int(h * 0.52)
    cv.circle(ax, ay, 7, RED)
    cv.ring(ax, ay, 34, INK, 2)
    cv.ring(ax, ay, 34, INK, 2)
    for ang in (30, 90, 150):
        import math
        a = math.radians(ang)
        cv.line(ax - int(34 * math.cos(a)), ay - int(34 * math.sin(a)),
                ax + int(34 * math.cos(a)), ay + int(34 * math.sin(a)), INK, 2)
    # Swiss flag, top right
    fx, fy = x + int(w * 0.66), y + 6
    cv.rect(fx, fy, 52, 52, RED)
    cv.rect(fx + 22, fy + 8, 8, 36, PAPER)
    cv.rect(fx + 8, fy + 22, 36, 8, PAPER)
    # exit arrow, flag pointing out to the right
    cv.line(fx + 56, fy + 26, fx + 92, fy + 26, INK, 3)
    cv.poly([(fx + 92, fy + 26), (fx + 78, fy + 16), (fx + 78, fy + 36)], INK)


def draw_mercury(cv, x, y, w, h):
    # Sun, Mercury on its orbit, and the BepiColombo probe.
    sx, sy = x + 52, y + int(h * 0.52)
    burst(cv, sx, sy, 34, GOLD)
    cv.circle(sx, sy, 24, ORANGE)
    # orbit ellipse around the sun
    cv.ring(x + 150, y + int(h * 0.52), 48, MID, 2)
    # Mercury, small grey world on the orbit
    cv.circle(x + 184, y + int(h * 0.52) - 30, 11, GRAY)
    cv.circle(x + 181, y + int(h * 0.52) - 33, 3, MID)
    # probe: box body, panel wings, dish
    px, py = x + 128, y + 18
    cv.rect(px, py, 34, 22, INK)
    cv.rect(px - 26, py + 5, 22, 12, BLUE)
    cv.rect(px + 38, py + 5, 22, 12, BLUE)
    cv.line(px + 17, py, px + 17, py - 12, INK, 2)
    cv.circle(px + 17, py - 14, 5, RED)
    cv.text("label", x + 180, y + int(h * 0.52) + 44, "MERCURY", GRAY)


# ---- layout ----

def panel_rule(cv, y):
    cv.hline(28, y, 968, INK, 2)


def render(path):
    cv = Canvas()
    # double outer frame
    cv.rect(0, 0, W, 4, INK)
    cv.rect(0, H - 4, W, 4, INK)
    cv.rect(0, 0, 4, H, INK)
    cv.rect(W - 4, 0, 4, H, INK)
    cv.rect(10, 10, W - 20, 2, INK)
    cv.rect(10, H - 12, W - 20, 2, INK)

    # ---- masthead ----
    cv.text_center("masthead", W // 2, 78, "THE WORLD IN ONE DAY", INK)
    cv.hline(28, 92, 968, INK, 2)
    cv.text_center("headline", W // 2, 122, "THURSDAY, 26 NOVEMBER 2026", RED)
    cv.text_center("label", W // 2, 146,
                   "THE DAY'S WORLD NEWS  \u2014  IN ONE IMAGE", GRAY)
    panel_rule(cv, 156)

    # ---- lead: Cairo tanker fire ----
    y = 170
    cv.text("label", 28, y + 14, "EGYPT  \u00b7  CAIRO RING ROAD", RED)
    cv.text("headline", 28, y + 62, "Tanker fire kills 31", INK)
    cv.text("headline", 28, y + 104, "on Cairo ring road", INK)
    cv.para("deck", 28, y + 140,
            "A fuel tanker crashed and caught fire on the Cairo ring "
            "road, killing at least 31 and injuring 21, Egypt said.",
            600, 26)
    draw_tanker(cv, 660, y + 6, 320, 190)
    cv.text("body", 28, y + 216, "Reuters  \u00b7  AP  \u2014  Cairo", GRAY)
    panel_rule(cv, 396)

    # ---- three panels ----
    pxs = (28, 356, 684)
    panels = [
        ("UKRAINE WAR  \u00b7  SAVASLEYKA", "Ukraine hits airbase",
         "Five warplanes damaged \u2014 3 MiG-31, 2 Su-34 \u2014 and two "
         "Samara refineries ablaze.",
         draw_jets),
        ("CHINA  \u00b7  SPACE", "Shenzhou-24 lifts off",
         "First Pakistani astronaut, Muhammad Zeeshan Ali, joins the "
         "Tiangong station.",
         draw_rocket),
        ("NORTH KOREA  \u00b7  PYONGYANG", "Swiss staff expelled",
         "Kim orders wider deployment of tactical nuclear weapons.",
         draw_atom_flag),
    ]
    for (x, (kick, head, deck, pic)) in zip(pxs, panels):
        if x > 28:
            cv.vline(x - 16, 412, 244, MID, 1)
        cv.text("label", x, 424, kick, RED)
        pic(cv, x, 436, 312, 88)
        yy = cv.para("subhead", x, 552, head, 312, 29)
        cv.para("body", x, yy + 10, deck, 312, 21)
    panel_rule(cv, 668)

    # ---- Mercury strip ----
    y = 684
    cv.text("label", 28, y + 14, "SPACE  \u00b7  MERCURY", RED)
    cv.text("subhead", 28, y + 52, "BepiColombo reaches Mercury", INK)
    cv.text("subhead", 28, y + 82, "after eight-year voyage", INK)
    cv.text("deck", 28, y + 118,
            "ESA-JAXA probe enters orbit of the Sun's innermost planet.", INK)
    draw_mercury(cv, 700, y + 8, 280, 130)
    panel_rule(cv, 812)

    # ---- IN BRIEF ----
    y = 818
    cv.text("label", 28, y + 14, "IN BRIEF", RED)
    cv.hline(120, y + 8, 876, INK, 1)
    briefs = [
        "Duran Duran guitarist Andy Taylor dies aged 65",
        "US proposes new tariffs",
        "Second judge blocks Trump's birthright citizenship order",
        "Israeli drone strike kills 3 in Gaza's Shati camp",
        "Houthis claim attack on Saudi Ras Tanura refinery",
        "Colombia police free 20 hostages after 17 hours",
        "Russia counts about 500,000 killed in Ukraine war",
    ]
    yy = y + 38
    for b in briefs:
        cv.rect(28, yy - 11, 8, 8, RED)
        cv.text("body", 46, yy, b, INK)
        yy += 18
    panel_rule(cv, 974)

    # ---- footer ----
    cv.text_center("body", W // 2, 992,
                   "Sources: Reuters  \u00b7  AP  \u00b7  BBC  \u00b7  AFP   \u2014   Early edition",
                   GRAY)
    return write_png(cv, path)


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    n = render(out)
    print(f"wrote {out} {n} bytes")
