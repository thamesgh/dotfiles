#!/usr/bin/env python3
"""Keyboard URL hints for Rex.

Started by the `url_hints` action in init.lua inside a floating pane laid over
the pane being searched. It redraws that pane's screen exactly, fades the text
back while each URL becomes a blue bubble with a letter hint, and opens
the chosen URL in the default browser. Leaving fades back to the original
screen before the pane closes, so the overlay never visibly pops.

Usage: url-hints.py SCREEN_FILE COLUMNS ROWS [BLOCK]
  SCREEN_FILE  the pane's screen as VT sequences (deleted after reading)
  COLUMNS      the pane's width
  ROWS         the pane's height
  BLOCK        the pane's block ID, focused again when the overlay closes

Keys: type a hint to open its URL, backspace to undo a letter, escape or
ctrl+c to cancel.
"""

import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import termios
import time
import tty
import unicodedata

ALPHABET = "asdfjklghqweruiopzxcvnmbty"

# Colors for light and dark themes: the URL bubble, the URL text, the tag
# holding the hint, and the hint letter.
LIGHT = dict(body=(0xDC, 0xE9, 0xFF), text=(0x0A, 0x4E, 0xB8),
             tag=(0x1D, 0x6F, 0xF2), ink=(0xFF, 0xFF, 0xFF),
             pressed=(0xB4, 0xD0, 0xFF))
DARK = dict(body=(0x1A, 0x35, 0x5E), text=(0xC7, 0xDD, 0xFF),
            tag=(0x3B, 0x82, 0xF6), ink=(0xFF, 0xFF, 0xFF),
            pressed=(0x27, 0x4E, 0x8A))
DIM_AMOUNT = 0.6               # how far the text fades toward the background
SWAP_AT = 0.4                  # fade point where letters and caps replace text

FADE_IN = 0.16
FADE_OUT = 0.14
FLASH = 0.07
FRAME = 1 / 60

CAP_LEFT, CAP_RIGHT = "\ue0b6", "\ue0b4"  # rounded powerline caps

THEMES = ("/Applications/Rex.app/Contents/Resources/"
          "SuperUI_SuperDesignTokens.bundle/Contents/Resources/themes.json")
DEFAULT_FG, DEFAULT_BG = (0xC5, 0xC8, 0xC6), (0x1D, 0x1F, 0x21)

URL_RE = re.compile(r"(?:https?|ftp|file)://[^\s<>\"'`]+")
TRAILING = ".,;:!?'\"*"
PAIRS = {")": "(", "]": "[", "}": "{", ">": "<"}


# --- Colors -----------------------------------------------------------------

def hex_rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def xterm_color(n):
    if n < 16:
        base = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238),
                (205, 0, 205), (0, 205, 205), (229, 229, 229), (127, 127, 127),
                (255, 0, 0), (0, 255, 0), (255, 255, 0), (92, 92, 255),
                (255, 0, 255), (0, 255, 255), (255, 255, 255)]
        return base[n]
    if n < 232:
        n -= 16
        steps = [0, 95, 135, 175, 215, 255]
        return (steps[n // 36], steps[n // 6 % 6], steps[n % 6])
    v = 8 + (n - 232) * 10
    return (v, v, v)


def mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class Colors:
    def __init__(self, palette):
        self.palette = palette
        self.fg, self.bg = DEFAULT_FG, DEFAULT_BG
        # Rex doesn't report the default colors, so find the Rex theme whose
        # ANSI colors match the pane's palette and take its colors from there.
        ansi = [palette.get(i) for i in range(16)]
        try:
            with open(THEMES) as f:
                themes = json.load(f)
            for theme in themes:
                src = theme.get("source", {})
                if [hex_rgb(c) for c in src.get("ansi", [])] == ansi:
                    self.fg, self.bg = hex_rgb(src["foreground"]), hex_rgb(src["background"])
                    break
        except (OSError, ValueError, KeyError):
            pass

    def rgb(self, spec, default):
        if spec is None:
            return default
        if spec[0] == "i":
            return self.palette.get(spec[1]) or xterm_color(spec[1])
        return spec[1:]


# --- Parsing the pane's VT dump ---------------------------------------------

TOKEN_RE = re.compile(
    r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"   # OSC
    r"|\x1b\[[0-?]*[ -/]*[@-~]"           # CSI
    r"|\x1b[()*+-./].|\x1b."               # charset and other escapes
    r"|\r\n|\r|\n"
    r"|[^\x1b\r\n]+")

PLAIN = (None, None, False, False, False, False, False, False)
# style: (fg, bg, bold, faint, italic, underline, inverse, strike)


def parse_color(params, i):
    """Read an extended color at params[i] (after 38/48). Returns (spec, next)."""
    p = params[i] if i < len(params) else ""
    if ":" in p:
        parts = p.split(":")
        if parts[0] in ("38", "48", "58"):
            parts = parts[1:]
        try:
            if parts[0] == "5":
                return ("i", int(parts[1])), i + 1
            if parts[0] == "2":
                rgb = [int(x or 0) for x in parts[-3:]]
                return ("c",) + tuple(rgb), i + 1
        except (ValueError, IndexError):
            return None, i + 1
        return None, i + 1
    try:
        if p == "5":
            return ("i", int(params[i + 1])), i + 2
        if p == "2":
            return ("c", int(params[i + 1]), int(params[i + 2]), int(params[i + 3])), i + 4
    except (ValueError, IndexError):
        pass
    return None, len(params)


def apply_sgr(style, body):
    fg, bg, bold, faint, italic, under, inverse, strike = style
    params = body.split(";") if body else ["0"]
    i = 0
    while i < len(params):
        p = params[i]
        head = p.split(":")[0]
        code = int(head) if head.isdigit() else 0
        if head in ("38", "48") and ":" in p:
            spec, _ = parse_color([p], 0)
            if head == "38":
                fg = spec
            else:
                bg = spec
            i += 1
            continue
        if code in (38, 48):
            spec, i = parse_color(params, i + 1)
            if code == 38:
                fg = spec
            else:
                bg = spec
            continue
        if code == 58:  # underline color: skip
            _, i = parse_color(params, i + 1)
            continue
        if code == 0:
            fg, bg, bold, faint, italic, under, inverse, strike = PLAIN
        elif code == 1:
            bold = True
        elif code == 2:
            faint = True
        elif code == 3:
            italic = True
        elif code == 4:
            under = not p.endswith(":0")
        elif code == 7:
            inverse = True
        elif code == 9:
            strike = True
        elif code == 21:
            under = True
        elif code == 22:
            bold = faint = False
        elif code == 23:
            italic = False
        elif code == 24:
            under = False
        elif code == 27:
            inverse = False
        elif code == 29:
            strike = False
        elif 30 <= code <= 37:
            fg = ("i", code - 30)
        elif code == 39:
            fg = None
        elif 40 <= code <= 47:
            bg = ("i", code - 40)
        elif code == 49:
            bg = None
        elif 90 <= code <= 97:
            fg = ("i", code - 90 + 8)
        elif 100 <= code <= 107:
            bg = ("i", code - 100 + 8)
        i += 1
    return (fg, bg, bold, faint, italic, under, inverse, strike)


def char_width(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def parse_vt(data, columns):
    """Return (rows, palette). Each row is a list of cells [char, style], where
    char is "" for the right half of a wide character."""
    palette = {}
    lines, line, style = [], [], PLAIN
    for m in TOKEN_RE.finditer(data):
        tok = m.group(0)
        if tok.startswith("\x1b]4;"):
            body = tok[2:].rstrip("\x07").replace("\x1b\\", "")
            parts = body.split(";")
            for k in range(1, len(parts) - 1, 2):
                rgb = re.match(r"rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)", parts[k + 1])
                if rgb and parts[k].isdigit():
                    palette[int(parts[k])] = tuple(int(x[:2], 16) for x in rgb.groups())
        elif tok.startswith("\x1b["):
            if tok.endswith("m"):
                style = apply_sgr(style, tok[2:-1])
        elif tok.startswith("\x1b"):
            pass
        elif tok in ("\r\n", "\n"):
            lines.append(line)
            line = []
        elif tok == "\r":
            pass
        else:
            for ch in tok:
                if ch < " ":
                    continue
                w = char_width(ch)
                if w == 0:
                    if line:
                        line[-1][0] += ch
                    continue
                line.append([ch, style])
                if w == 2:
                    line.append(["", style])
    lines.append(line)

    rows = []
    for line in lines:
        if not line:
            rows.append([])
        while line:
            cut = columns
            if cut < len(line) and line[cut][0] == "":
                cut -= 1  # keep a wide character together
            rows.append(line[:cut])
            line = line[cut:]
    return rows, palette


# --- Finding URLs -----------------------------------------------------------

def clean_url(url):
    """Strip punctuation that trails a URL in prose, keeping balanced brackets."""
    while url:
        last = url[-1]
        if last in TRAILING:
            url = url[:-1]
        elif last in PAIRS and url.count(last) > url.count(PAIRS[last]):
            url = url[:-1]
        else:
            break
    return url


def find_urls(rows, columns):
    """Return [(url, [(row, start_col, end_col), ...])] in screen order.

    Rows as wide as the pane are treated as soft-wrapped, so a URL that runs
    past the right edge is joined with its continuation on the next row.
    """
    found = []
    text, where = "", []  # where[i] = (row, col) of text[i]

    def flush():
        for m in URL_RE.finditer(text):
            url = clean_url(m.group(0))
            if url.endswith("://"):
                continue
            spans = []
            for i in range(m.start(), m.start() + len(url)):
                row, col = where[i]
                if spans and spans[-1][0] == row:
                    spans[-1][2] = col + 1
                else:
                    spans.append([row, col, col + 1])
            found.append((url, [tuple(s) for s in spans]))

    for r, row in enumerate(rows):
        for c, (ch, _) in enumerate(row):
            if ch:
                text += ch[0]
                where.append((r, c))
        if len(row) < columns:
            flush()
            text, where = "", []
    flush()
    return found


def make_hints(count):
    if count <= len(ALPHABET):
        return list(ALPHABET[:count])
    return [a + b for a in ALPHABET for b in ALPHABET][:count]


# --- Animation ----------------------------------------------------------------

def ease(t):
    return 1 - (1 - t) ** 3


class Anim:
    def __init__(self, value=0.0):
        self.a = self.b = value
        self.t0, self.dur = 0.0, 0.0

    def get(self, now):
        if self.dur <= 0 or now >= self.t0 + self.dur:
            return self.b
        if now <= self.t0:
            return self.a
        return self.a + (self.b - self.a) * ease((now - self.t0) / self.dur)

    def to(self, target, dur, now, delay=0.0):
        self.a, self.b = self.get(now), target
        self.t0, self.dur = now + delay, dur

    def done(self, now):
        return self.dur <= 0 or now >= self.t0 + self.dur


class Bubble:
    """A URL drawn as a rounded bubble with its hint in a rounded tag at the
    left end.

    spans are the URL's cells, [(row, start_col, end_col)], one per screen row
    it covers. label replaces the text in the bubble (for messages)."""

    def __init__(self, spans, hint, url=None, label=None):
        self.spans, self.hint, self.url, self.label = spans, hint, url, label
        self.alpha = Anim()
        self.pressed = False

    @property
    def row(self):
        return self.spans[0][0]

    def cells(self, width):
        """[(row, col, kind, index)] with kind cap_left, tag, tag_right, body
        or cap_right.

        The tag is a fully rounded pill at the bubble's left end; its right
        end sits on the bubble's color. The tag goes in front of the URL, so
        the URL stays whole, unless the URL starts too close to the left edge."""
        k = len(self.hint)
        row, lo, _ = self.spans[0]
        tag_width = k + 1 if k else 0  # letters and the tag's right end
        left = max(0, lo - tag_width - 1)
        out = [(row, left, "cap_left", 0)]
        out += [(row, left + 1 + i, "tag", i) for i in range(k)]
        if k:
            out.append((row, left + 1 + k, "tag_right", 0))
        n = 0
        for i, (r, a, b) in enumerate(self.spans):
            start = left + 1 + tag_width if i == 0 else a
            for c in range(start, b):
                out.append((r, c, "body", n))
                n += 1
        last, _, end = self.spans[-1]
        if end < width:
            out.append((last, end, "cap_right", 0))
        return [cell for cell in out if cell[1] < width]


# --- Drawing ----------------------------------------------------------------

def sgr(fg, bg, attrs):
    """fg/bg are ("i", n), ("c", r, g, b), ("rgb", (r, g, b)) or None."""
    out = ["0"]
    bold, faint, italic, under, inverse, strike = attrs
    for on, code in ((bold, "1"), (faint, "2"), (italic, "3"), (under, "4"),
                     (inverse, "7"), (strike, "9")):
        if on:
            out.append(code)
    for spec, base in ((fg, 38), (bg, 48)):
        if spec is None:
            continue
        if spec[0] == "i":
            out.append("%d;5;%d" % (base, spec[1]))
        elif spec[0] == "c":
            out.append("%d;2;%d;%d;%d" % ((base,) + tuple(spec[1:])))
        else:
            out.append("%d;2;%d;%d;%d" % ((base,) + tuple(spec[1])))
    return "\x1b[" + ";".join(out) + "m"


class Screen:
    def __init__(self, rows, colors, bubbles):
        self.rows, self.colors, self.pills = rows, colors, bubbles
        self.theme = DARK if sum(colors.bg) < 3 * 128 else LIGHT
        self.dim = Anim()

    def cell(self, row, col, d):
        """The pane's own cell at (row, col), faded by d: (char, sgr)."""
        line = self.rows[row]
        if col >= len(line):
            return " ", None
        ch, (fg, bg, bold, faint, italic, under, inverse, strike) = line[col]
        attrs = [bold, faint, italic, under, inverse, strike]
        if d <= 0:
            return ch, sgr(fg, bg, attrs)
        attrs[4] = False
        return ch, sgr(("rgb", self.fg_rgb(row, col, d)), self.bg_rgb(row, col)[0], attrs)

    def bg_rgb(self, row, col):
        line = self.rows[row]
        if col >= len(line):
            return None, self.colors.bg
        _, (fg, bg, _, _, _, _, inverse, _) = line[col]
        spec = fg if inverse else bg
        return spec, self.colors.rgb(spec, self.colors.fg if inverse else self.colors.bg)

    def fg_rgb(self, row, col, d):
        """The color the pane's character at (row, col) is drawn in, faded by d."""
        line = self.rows[row]
        if col >= len(line):
            return self.colors.bg
        _, (fg, bg, _, _, _, _, inverse, _) = line[col]
        c = self.colors
        efg = bg if inverse else fg
        fg_rgb = c.rgb(efg, c.bg if inverse else c.fg)
        return mix(fg_rgb, self.bg_rgb(row, col)[1], DIM_AMOUNT * d)

    @staticmethod
    def put(row, c, cell):
        row[c] = cell
        # Never leave half of a wide character behind.
        if c + 1 < len(row) and row[c + 1][0] == "":
            row[c + 1] = (" ", row[c + 1][1])
        if row[c][0] == "" and c > 0:
            row[c - 1] = (" ", row[c - 1][1])

    def draw_bubble(self, grid, bubble, a, typed):
        if a <= 0.001:
            return
        theme = self.theme
        e = ease(a)
        swap = a >= SWAP_AT
        t = (a - SWAP_AT) / (1 - SWAP_AT) if swap else a / SWAP_AT
        plain = [False] * 6
        body_color = theme["pressed"] if bubble.pressed else theme["body"]
        width = len(next(g for g in grid if g is not None))
        for r, c, kind, i in bubble.cells(width):
            if r >= len(grid) or grid[r] is None:
                continue
            row = grid[r]
            spec, base = self.bg_rgb(r, c)
            line = self.rows[r]
            orig = line[c][0] if c < len(line) and line[c][0] else " "
            orig_fg = self.fg_rgb(r, c, 1.0)
            if kind == "body":
                bg = mix(base, body_color, e)
                ch = bubble.label[i] if bubble.label and i < len(bubble.label) else orig
                fg = mix(orig_fg if not bubble.label else bg, theme["text"], e)
                self.put(row, c, (ch, sgr(("rgb", fg), ("rgb", bg), plain)))
            elif kind == "tag":
                bg = mix(base, theme["tag"], e)
                if not swap:
                    # The character underneath sinks into the tag first.
                    self.put(row, c, (orig, sgr(("rgb", mix(orig_fg, bg, t)), ("rgb", bg), plain)))
                    continue
                strength = 0.45 if i < len(typed) else 1.0
                ink = mix(bg, theme["ink"], t * strength)
                self.put(row, c, (bubble.hint[i], sgr(("rgb", ink), ("rgb", bg), [True] + plain[1:])))
            elif kind == "tag_right":
                # The tag's rounded right end, on the bubble's color.
                bg = mix(base, body_color, e)
                color = mix(base, theme["tag"], e)
                if not swap:
                    self.put(row, c, (orig, sgr(("rgb", mix(orig_fg, bg, t)), ("rgb", bg), plain)))
                    continue
                self.put(row, c, (CAP_RIGHT, sgr(("rgb", color), ("rgb", bg), plain)))
            else:
                left = kind == "cap_left"
                color = theme["tag"] if left and bubble.hint else body_color
                color = mix(base, color, e)
                if not swap:
                    self.put(row, c, (orig, sgr(("rgb", mix(orig_fg, base, t)), spec, plain)))
                    continue
                self.put(row, c, (CAP_LEFT if left else CAP_RIGHT, sgr(("rgb", color), spec, plain)))

    def render(self, now, typed="", prefix=""):
        width, height = shutil.get_terminal_size((80, 24))
        first = max(0, len(self.rows) - height)
        d = self.dim.get(now)
        grid = []
        for r in range(len(self.rows)):
            if r < first:
                grid.append(None)
                continue
            grid.append([self.cell(r, c, d) for c in range(width)])
        for bubble in self.pills:
            self.draw_bubble(grid, bubble, bubble.alpha.get(now), typed if bubble.url else "")
        out = ["\x1b[?2026h" + prefix + "\x1b[H"]
        for screen_row, r in enumerate(range(first, len(self.rows))):
            out.append("\x1b[%d;1H" % (screen_row + 1))
            current = None
            for ch, style in grid[r]:
                if ch == "":
                    continue
                if style != current:
                    out.append(style or "\x1b[0m")
                    current = style
                out.append(ch)
            out.append("\x1b[0m\x1b[K")
        out.append("\x1b[0m\x1b[J\x1b[?2026l")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def animating(self, now):
        return not self.dim.done(now) or any(not p.alpha.done(now) for p in self.pills)


# --- Main -------------------------------------------------------------------

def refocus(block_id):
    """Give focus back to the pane the overlay covers. When a floating pane
    closes, Rex focuses whichever pane it picks, which isn't always this one;
    doing it as the fade-out starts means the overlay never hands focus away."""
    rex = os.path.join(os.environ.get("REX_BIN_DIR", ""), "rex")
    session = os.environ.get("REX_SESSION")
    if not block_id or not session or not os.access(rex, os.X_OK):
        return False
    try:
        return subprocess.Popen([rex, "focus", "-s", session, block_id],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False


def main():
    path, columns, height = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    origin = sys.argv[4] if len(sys.argv) > 4 else None
    with open(path, encoding="utf-8", errors="replace") as f:
        data = f.read()
    try:
        os.unlink(path)
    except OSError:
        pass

    rows, palette = parse_vt(data, columns)
    rows = rows[-height:]
    rows += [[] for _ in range(height - len(rows))]
    colors = Colors(palette)

    found = find_urls(rows, columns)
    by_url = {}
    for url, spans in found:
        by_url.setdefault(url, []).append(spans)
    hints = dict(zip(by_url, make_hints(len(by_url))))

    pills = [Bubble(spans, hints[url], url) for url, spans in found]
    if not pills:
        msg = " No URLs on screen "
        col = max(1, (columns - len(msg)) // 2)
        pills.append(Bubble([(height // 2, col, col + len(msg))], "", label=msg))

    screen = Screen(rows, colors, pills)

    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    signal.signal(signal.SIGWINCH, lambda *_: None)
    opener = focuser = None
    try:
        tty.setraw(fd)
        # The pane starts at a default size and takes the size it is shown at
        # a moment later. Draw nothing until then, so no frame is laid out
        # for the wrong size.
        deadline = time.monotonic() + 0.3
        while (shutil.get_terminal_size((0, 0)) != (columns, height)
               and time.monotonic() < deadline):
            time.sleep(0.005)
        now = time.monotonic()
        # An exact copy of the pane first, in one synchronized update with the
        # switch to the alternate screen, so it lands as a single frame.
        screen.render(now, prefix="\x1b[?1049h\x1b[?25l")
        screen.dim.to(1.0, FADE_IN, now)
        for i, pill in enumerate(pills):
            pill.alpha.to(1.0, FADE_IN, now, delay=min(i * 0.008, 0.06))

        typed, closing = "", False
        # With no URLs, show the message for a moment, then leave by itself.
        auto_close = now + FADE_IN + 0.6 if not hints else None

        while True:
            now = time.monotonic()
            if closing and focuser is None:
                focuser = refocus(origin)
            if auto_close and now >= auto_close and not closing:
                closing = True
                screen.dim.to(0.0, FADE_OUT, now)
                pills[0].alpha.to(0.0, FADE_OUT, now)
            screen.render(now, typed)
            busy = screen.animating(now)
            if closing and not busy:
                break
            timeout = None
            if busy:
                timeout = FRAME
            elif auto_close and not closing:
                timeout = max(0.0, auto_close - now)
            try:
                ready, _, _ = select.select([fd], [], [], timeout)
            except InterruptedError:
                continue
            if not ready:
                continue
            key = os.read(fd, 32).decode("utf-8", "replace")
            if closing:
                continue
            now = time.monotonic()
            if key.startswith(("\x1b", "\x03", "\x07")):
                closing = True
            elif key in ("\x7f", "\x08"):
                typed = typed[:-1]
            else:
                for ch in key.lower():
                    if any(h.startswith(typed + ch) for h in hints.values()):
                        typed += ch
            chosen = next((u for u, h in hints.items() if h == typed), None)
            if chosen:
                closing = True
                opener = subprocess.Popen(["/usr/bin/open", chosen])
                for pill in pills:
                    if pill.url == chosen:
                        pill.pressed = True
                        pill.alpha.to(1.0, 0, now)
            if closing:
                hold = FLASH if chosen else 0.0
                screen.dim.to(0.0, FADE_OUT, now, delay=hold)
                for pill in pills:
                    pill.alpha.to(0.0, FADE_OUT, now, delay=hold if pill.pressed else 0.0)
            else:
                for pill in pills:
                    pill.alpha.to(1.0 if pill.hint.startswith(typed) else 0.0, 0.1, now)
    finally:
        # Leave the last frame, an exact copy of the pane, on screen while the
        # pane closes. Restoring the main screen or the cursor here would show
        # a blank frame or a stray cursor before it goes.
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        for proc in (opener, focuser):
            if proc:
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass


if __name__ == "__main__":
    main()
