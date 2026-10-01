"""Final compositor calibrated on the reference study (all numbers at 1080x1920, 30 fps).

Layers, bottom to top:
  base video (graded)  ->  B&W moment (optional ranges)  ->  silhouette/flash transitions
  ->  captions (orange tier + white tier)  ->  skin occluder (hands/arms pass in front of the text)
  ->  UI elements (in front of everything)

usage: render.py project.json
project.json keys: base, alpha, audio, out, captions, ui, bw, transitions, preset, crf
caption card:
  {"tier":"orange","words":[{"text":..,"t":..},..],"t0":..,"t1":..,"entry":"cut|B|A","gaps":[1,5,1],"hook":false}
  {"tier":"white","lines":[[{"text":..,"t":..}],[..]],"t0":..,"t1":..,"entry":"cut|slide","line2_entry":"cut|slide","t_line2":..,"mode":"match|equal"}
  {"tier":"hook","top":[{"text":"QUANDO","t":0},{"text":"É QUE","t":0}],"top_gap":170,"sub":[..words..],"t_sub":0.87,"t0":0,"t1":1.97}
bw: [[t0,t1],..]    transitions: [{"E":cut_time,"frames":"preroll.mp4","alpha":"preroll_alpha.mkv","pattern":["white","semi",..]}]
"""
import sys, json, subprocess, os
import os as _os
EDV = _os.environ.get('EDV_HOME', _os.path.expanduser('~/edicao-video-dados'))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

FONTS = EDV + '/fonts/'
W, H, FPS = 1080, 1920, 30
SS = 3  # supersampling for glyph rendering

ORANGE = dict(font='InstrumentSans-Bold.ttf', size=83.85, track=-4.38, gap_unit=37.7, gap_base=1.6,
              baseline=991, color=(252, 125, 1), hook_color=(247, 100, 5), max_w=1000)
WHITE = dict(font='BebasNeue-Regular.ttf', cap_ratio=0.70, single_cap=225, single_captop=816, single_max_w=1041,
             block_w=890, block_min=735, block_max=970, max_cap=330, min_cap=80, gap=16, gap_accent=50,
             block_cy=1000, equal_cy=915, fill=(250, 250, 250), glow_sigma=8.0, glow_k=0.45, equal_cap=318)
HOOK = dict(cap=150, captop=814, xscale=1.0, track_em=-0.048, sub_baseline=1020, gap=172)

_fc = {}
def font(name, size):
    k = (name, round(size * 4) / 4)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONTS + name, max(1, int(round(k[1]))))
    return _fc[k]

# ---------------------------------------------------------------- glyph rendering helpers
def render_text_mask(text, fname, size, track=0.0, xscale=1.0):
    """Returns (mask float32 HxW in 0..1, ink_left, ink_right, baseline_y) rendered with per-pair advances + tracking,
    supersampled. Coordinates in output pixels."""
    f = font(fname, size * SS)
    xs = []; x = 0.0
    for i, ch in enumerate(text):
        xs.append(x)
        if i + 1 < len(text):
            x += f.getlength(text[i:i + 2]) - f.getlength(text[i + 1]) + track * SS
    width = int(x + f.getlength(text[-1]) + 60 * SS) if text else 10
    h = int(size * SS * 1.6) + 20 * SS
    base = int(size * SS * 1.15) + 10 * SS
    img = Image.new('L', (width, h), 0); d = ImageDraw.Draw(img)
    for ch, xx in zip(text, xs):
        d.text((20 * SS + xx, base), ch, font=f, fill=255, anchor='ls')
    a = np.asarray(img, np.float32) / 255.0
    if xscale != 1.0:
        a = cv2.resize(a, (max(1, int(a.shape[1] * xscale)), a.shape[0]), interpolation=cv2.INTER_AREA)
    a = cv2.resize(a, (max(1, a.shape[1] // SS), max(1, a.shape[0] // SS)), interpolation=cv2.INTER_AREA)
    cols = np.nonzero((a > 0.35).any(0))[0]
    if len(cols) == 0:
        return a, 0, 0, base / SS
    return a, int(cols.min()), int(cols.max()), base / SS

def cap_px(fname, size):
    return size * WHITE['cap_ratio'] if 'Bebas' in fname else size * 0.7

def paste_max(canvas, a, x, y):
    """max-composite mask a into canvas at top-left (x,y)."""
    h, w = a.shape; x, y = int(round(x)), int(round(y))
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(canvas.shape[1], x + w), min(canvas.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1], a[y0 - y:y1 - y, x0 - x:x1 - x])

# ---------------------------------------------------------------- orange tier
def orange_line_mask(words, gaps, color_key='color', size=None):
    """words: list[str]; gaps: list[int] (k spaces between word i-1 and i, len = n-1). Returns full-frame mask."""
    size = size or ORANGE['size']
    rend = [render_text_mask(w, ORANGE['font'], size, ORANGE['track'] * size / ORANGE['size']) for w in words]
    unit = ORANGE['gap_unit'] * size / ORANGE['size']
    def total(gs):
        return sum(r[2] - r[1] + 1 for r in rend) + sum(ORANGE['gap_base'] + unit * k for k in gs)
    gs = list(gaps)
    while total(gs) > ORANGE['max_w'] and any(k > 1 for k in gs):
        i = int(np.argmax(gs)); gs[i] -= 1
    if total(gs) > ORANGE['max_w']:
        return orange_line_mask(words, gs, color_key, size * ORANGE['max_w'] / total(gs) * 0.99)
    canvas = np.zeros((H, W), np.float32)
    per_word = []
    x = (W - total(gs)) / 2
    for i, (a, l, r, base) in enumerate(rend):
        if i > 0:
            x += ORANGE['gap_base'] + unit * gs[i - 1]
        wmask = np.zeros((H, W), np.float32)
        paste_max(wmask, a, x - l, ORANGE['baseline'] - base)
        per_word.append(wmask)
        canvas = np.maximum(canvas, wmask)
        x += r - l + 1
    orange_line_mask.last_words = per_word
    return canvas

# ---------------------------------------------------------------- white tier
ACCENT_CAPS = set('ÁÉÍÓÚÂÊÔÃÕÀÇ')
def white_block_layout(lines_text, mode='match', block_w=None, cap_top=None, track_em=0.0, center_y=None):
    """Returns list of dicts per line: mask(local), x, y(top of mask), cap_top."""
    fn = WHITE['font']
    out = []
    if len(lines_text) == 1 and mode != 'equal':
        t = lines_text[0]
        size = WHITE['single_cap'] / WHITE['cap_ratio']
        a, l, r, base = render_text_mask(t, fn, size)
        if r - l + 1 > WHITE['single_max_w']:
            size *= WHITE['single_max_w'] / (r - l + 1)
            a, l, r, base = render_text_mask(t, fn, size)
        cap = cap_px(fn, size)
        # keep the baseline at 1040 (cap top 816 at full size)
        baseline = WHITE['single_captop'] + WHITE['single_cap']
        out.append(dict(a=a, x=(W - (r - l + 1)) / 2 - l, y=baseline - base, cap_top=baseline - cap, cap=cap, size=size))
        return out
    sizes = []
    if mode == 'equal':
        for t in lines_text:
            size = WHITE['equal_cap'] / WHITE['cap_ratio']
            a, l, r, base = render_text_mask(t, fn, size)
            if r - l + 1 > 1000:
                size *= 1000 / (r - l + 1)
            sizes.append(size)
    else:
        bw = block_w or WHITE['block_w']
        # unit-size ink widths
        inks = []
        for t in lines_text:
            a, l, r, base = render_text_mask(t, fn, 100, track_em * 100)
            inks.append(r - l + 1)
        # clamp block width so every line keeps a sane cap height
        caps = [bw / iw * 100 * WHITE['cap_ratio'] for iw in inks]
        if max(caps) > WHITE['max_cap']:
            bw *= WHITE['max_cap'] / max(caps)
        caps = [bw / iw * 100 * WHITE['cap_ratio'] for iw in inks]
        if min(caps) < WHITE['min_cap']:
            bw = min(WHITE['block_max'], bw * WHITE['min_cap'] / min(caps))
        bw = max(min(bw, WHITE['block_max']), min(WHITE['block_min'], bw))
        sizes = [100 * bw / iw for iw in inks]
    rendered = [render_text_mask(t, fn, s, track_em * s) for t, s in zip(lines_text, sizes)]
    caps = [cap_px(fn, s) for s in sizes]
    def _gap(t):
        if set(t) & set('ÃÕ'):
            return 53
        if set(t) & set('ÁÉÍÓÚÂÊÔÀ'):
            return 35
        return 18
    gaps = [_gap(lines_text[i + 1]) for i in range(len(lines_text) - 1)]
    total_h = sum(caps) + sum(gaps)
    cy = center_y if center_y is not None else (WHITE['equal_cy'] if mode == 'equal' else WHITE['block_cy'])
    y = cap_top if cap_top is not None else cy - total_h / 2
    for i, ((a, l, r, base), cap, s) in enumerate(zip(rendered, caps, sizes)):
        cap_top = y
        baseline = cap_top + cap
        out.append(dict(a=a, x=(W - (r - l + 1)) / 2 - l, y=baseline - base, cap_top=cap_top, cap=cap, size=s))
        y = baseline + (gaps[i] if i < len(gaps) else 0)
    return out

def hook_layout(top_words, top_gap, sub_words):
    fn = WHITE['font']
    size = HOOK['cap'] / WHITE['cap_ratio']
    track = HOOK['track_em'] * size
    parts = [render_text_mask(t, fn, size, track, HOOK['xscale']) for t in top_words]
    widths = [r - l + 1 for (_, l, r, _) in parts]
    total = sum(widths) + top_gap * (len(parts) - 1)
    max_w = HOOK.get('max_w', 1000)
    if total > max_w:
        top_gap = max(HOOK.get('min_gap', 60), top_gap - (total - max_w))
        total = sum(widths) + top_gap * (len(parts) - 1)
    if total > max_w:
        size *= (max_w - top_gap * (len(parts) - 1)) / sum(widths); track = HOOK['track_em'] * size
        parts = [render_text_mask(t, fn, size, track, HOOK['xscale']) for t in top_words]
        widths = [r - l + 1 for (_, l, r, _) in parts]
        total = sum(widths) + top_gap * (len(parts) - 1)
        hook_layout.cap = size * WHITE['cap_ratio']
    else:
        hook_layout.cap = HOOK['cap']
    x = (W - total) / 2
    baseline = HOOK['captop'] + HOOK['cap']   # baseline stays put when the line has to shrink
    tops = []
    for (a, l, r, base), w_ in zip(parts, widths):
        tops.append(dict(a=a, x=x - l, y=baseline - base, x0=x, x1=x + w_))
        x += w_ + top_gap
    # orange sub line width-matched to the white line
    sub_text = sub_words
    return tops, (W - total) / 2, (W + total) / 2

class Captions:
    def __init__(self, cards):
        self.cards = cards
        self.cache = {}

    def mask_orange(self, c):
        key = ('o', id(c))
        if key not in self.cache:
            words = [w['text'] for w in c['words']]
            gaps = c.get('gaps')
            if not isinstance(gaps, list) or len(gaps) != len(words) - 1:
                gaps = [1] * (len(words) - 1)
            self.cache[key] = orange_line_mask(words, gaps)
            self.cache[('ow', id(c))] = orange_line_mask.last_words
        return self.cache[key]

    def white_lines(self, c):
        key = ('w', id(c))
        if key not in self.cache:
            texts = [' '.join(w['text'] for w in ln) for ln in c['lines']]
            self.cache[key] = white_block_layout(texts, c.get('mode', 'match'), c.get('block_w'), c.get('cap_top'), c.get('track_em', 0.0), c.get('center_y'))
        return self.cache[key]

    def hook(self, c):
        key = ('h', id(c))
        if key not in self.cache:
            tops, xl, xr = hook_layout([w['text'] for w in c['top']], c.get('top_gap', HOOK['gap']), None)
            # sub line: orange font, natural gaps, stretched gaps so its width matches the white line
            words = [w['text'] for w in c['sub']]
            rend = [render_text_mask(w, ORANGE['font'], ORANGE['size'], ORANGE['track']) for w in words]
            ink = sum(r - l + 1 for (_, l, r, _) in rend)
            gap = max(ORANGE['gap_unit'], ((xr - xl) - ink) / max(1, len(words) - 1))
            sub = np.zeros((H, W), np.float32); x = xl
            for i, (a, l, r, base) in enumerate(rend):
                paste_max(sub, a, x - l, HOOK['sub_baseline'] - base); x += r - l + 1 + gap
            self.cache[key] = (tops, sub)
        return self.cache[key]

    # ---------------------------------------------------------- per-frame layers
    def layers(self, t):
        """returns list of (mask HxW float, rgb tuple, opacity, dx, dy, glow:bool, brightness)"""
        out = []
        n = int(round(t * FPS))
        for c in self.cards:
            if not (c['t0'] - 1e-6 <= t < c['t1'] - 1e-6):
                continue
            f = n - int(round(c['t0'] * FPS))  # frame index inside the card
            if c['tier'] == 'orange':
                op, dy, br = 1.0, 0.0, 1.0
                e = c.get('entry', 'cut')
                col = ORANGE['hook_color'] if c.get('hook') else ORANGE['color']
                full = self.mask_orange(c)
                if e == 'B':   # easeOutQuad slide-up from +150 px, first frame already faint
                    seq = [(110, .3), (72, .5), (42, .7), (20, .87), (6, .96)]
                    if f < len(seq):
                        dy, op = seq[f]
                    out.append((full, col, op, 0, dy, 'shadow', br))
                elif e == 'A':  # word-by-word stagger left to right, dim hold at 81%, then hard step to 100%
                    br = 0.81 if f < 8 else 1.0
                    seqw = [(33, .3), (15, .6), (4, .8)]
                    for wi, wm in enumerate(self.cache[('ow', id(c))]):
                        fw = f - int(round(wi * 0.75))
                        if fw < 0:
                            continue
                        dyw, opw = seqw[fw] if fw < len(seqw) else (0, 1.0)
                        out.append((wm, col, opw, 0, dyw, 'shadow', br))
                else:
                    out.append((full, col, op, 0, dy, 'shadow', br))
            elif c['tier'] == 'white':
                lines = self.white_lines(c)
                for li, L in enumerate(lines):
                    t_on = c['t0'] if li == 0 else c.get('t_line2', c['lines'][li][0]['t'])
                    if t < t_on - 1e-6:
                        continue
                    fl = n - int(round(t_on * FPS))
                    e = c.get('entry', 'cut') if li == 0 else c.get('line2_entry', 'cut')
                    dx, op = 0.0, 1.0
                    if e == 'slide':   # easeOutQuad from off-screen right, first frame ~74% opacity
                        seq = [(560, .74), (230, .9), (60, 1.0), (5, 1.0)]
                        if fl < len(seq):
                            dx, op = seq[fl]
                    m = self.cache.setdefault(('wl', id(c), li), self._line_canvas(L))
                    out.append((m, WHITE['fill'], op, dx, 0, True, 1.0))
            elif c['tier'] == 'hook':
                tops, sub = self.hook(c)
                m = self.cache.setdefault(('ht', id(c)), self._hook_canvas(tops))
                out.append((m, WHITE['fill'], 1.0, 0, 0, True, 1.0))
                ts = c.get('t_sub', c['sub'][0]['t'])
                if t >= ts:
                    f2 = n - int(round(ts * FPS))
                    seq = [(30, 0.0), (15, .3), (4.5, .6)]
                    dy, op = seq[f2] if f2 < len(seq) else (0, 1.0)
                    br = 0.81 if f2 < 8 else 1.0
                    out.append((sub, ORANGE['hook_color'], op, 0, dy, 'shadow', br))
        return out

    def _line_canvas(self, L):
        canvas = np.zeros((H, W), np.float32)
        paste_max(canvas, L['a'], L['x'], L['y'])
        return canvas

    def _hook_canvas(self, tops):
        canvas = np.zeros((H, W), np.float32)
        for T in tops:
            paste_max(canvas, T['a'], T['x'], T['y'])
        return canvas

# ---------------------------------------------------------------- compositing helpers
def shift(m, dx, dy):
    if dx == 0 and dy == 0:
        return m
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)

def skin_occluder(rgb_u8, person):
    """person alpha (0..1) x skin probability -> occluder alpha (hands, arms, neck)."""
    ycc = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2YCrCb)
    Y, Cr, Cb = ycc[..., 0].astype(np.int16), ycc[..., 1].astype(np.int16), ycc[..., 2].astype(np.int16)
    s = ((Cr >= 136) & (Cr <= 180) & (Cb >= 78) & (Cb <= 130) & (Y > 50)).astype(np.float32)
    s = cv2.morphologyEx(s, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    s = cv2.dilate(s, np.ones((5, 5), np.uint8))
    s = cv2.GaussianBlur(s, (0, 0), 1.6)
    occ = s * np.clip(person * 1.3, 0, 1) if person is not None else s * 0
    return occ

BW_CURVE = np.interp(np.arange(256) / 255.0, [0, .11, .3, .55, .8, 1], [0, .026, .14, .405, .68, .84])
def bw_effect(fr):
    y = 0.2126 * fr[..., 0] + 0.7152 * fr[..., 1] + 0.0722 * fr[..., 2]
    y = np.interp(y, np.arange(256) / 255.0, BW_CURVE).astype(np.float32)
    return np.repeat(y[..., None], 3, axis=2)

def transition_frame(state, out_fr, in_fr, m):
    """out_fr/in_fr float RGB 0..1, m = incoming person matte 0..1."""
    mm = m[..., None]
    white = np.ones_like(out_fr)
    if state == 'full':
        return white.copy()
    if state == 'white':
        return out_fr * (1 - mm) + white * mm
    if state.startswith('semi'):
        a = 0.91 if state == 'semi' else 0.70
        cut = in_fr * (1 - a) + white * a
        return out_fr * (1 - mm) + cut * mm
    if state == 'plain':
        return out_fr * (1 - mm) + in_fr * mm
    if state == 'black':
        return out_fr * (1 - mm)
    if state in ('hot', 'cool'):
        gain = np.array([1.40, 1.70, 1.70] if state == 'hot' else [0.83, 1.0, 1.12], np.float32)
        cut = np.clip(in_fr * gain, 0, 1)
        mb = (m > 0.5).astype(np.uint8)
        ring = (cv2.dilate(mb, np.ones((9, 9), np.uint8)) - mb).astype(np.float32)
        glow = cv2.GaussianBlur(ring, (0, 0), 12) * 0.4
        cyan = np.array([160, 232, 240], np.float32) / 255
        base = out_fr * (1 - mm) + cut * mm
        base = base * (1 - glow[..., None]) + cyan * glow[..., None]
        r = (ring * 0.7)[..., None]
        return base * (1 - r) + cyan * r
    if state == 'glow':
        g = np.clip(cv2.GaussianBlur(m, (0, 0), 28) * 0.8, 0, 1)[..., None]
        base = out_fr * (1 - g) + white * g
        return base * (1 - mm) + white * mm
    return out_fr

# ---------------------------------------------------------------- UI (in front of everything)
sys.path.insert(0, os.path.dirname(__file__))
try:
    from ui_elements import UIRenderer
except Exception:
    UIRenderer = None

def blend_sprite(dst, spr, op=1.0, dy=0):
    (x0, y0, x1, y1), a = spr
    y0 += int(dy); y1 += int(dy)
    if y0 >= H or y1 <= 0:
        return
    sy0 = max(0, -y0); sy1 = a.shape[0] - max(0, y1 - H)
    y0c, y1c = max(0, y0), min(H, y1)
    rgb = a[sy0:sy1, :, :3]; al = a[sy0:sy1, :, 3:4] * op
    region = dst[y0c:y1c, x0:x1]
    region *= (1 - al); region += rgb * op  # sprite rgb is premultiplied

# ---------------------------------------------------------------- main loop
def apply_style(st):
    """Per-video layout overrides, e.g. {"dy": 267, "WHITE": {"max_cap": 210}}. dy moves every caption tier down."""
    if not st:
        return
    dy = st.get('dy', 0)
    ORANGE['baseline'] += dy
    WHITE['single_captop'] += dy; WHITE['block_cy'] += dy; WHITE['equal_cy'] += dy
    HOOK['captop'] += dy; HOOK['sub_baseline'] += dy
    for name, d in (('ORANGE', ORANGE), ('WHITE', WHITE), ('HOOK', HOOK)):
        d.update(st.get(name, {}))

def main():
    P = json.load(open(sys.argv[1]))
    apply_style(P.get('style'))
    caps = Captions(P['captions'])
    ui = P.get('ui', [])
    UR = UIRenderer(W, H) if (UIRenderer and ui) else None
    bw = P.get('bw', [])
    trans = P.get('transitions', [])
    # preload transition pre-roll frames + mattes
    for tr in trans:
        k = len(tr['pattern'])
        fr = subprocess.run(['ffmpeg', '-v', 'error', '-i', tr['frames'], '-vf', f'scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        al = subprocess.run(['ffmpeg', '-v', 'error', '-i', tr['alpha'], '-vf', f'scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
        F = np.frombuffer(fr, np.uint8).reshape(-1, H, W, 3); A = np.frombuffer(al, np.uint8).reshape(-1, H, W)
        tr['_F'] = F[-k:].astype(np.float32) / 255.0; tr['_A'] = A[-k:].astype(np.float32) / 255.0
        tr['_n0'] = int(round(tr['E'] * FPS)) - k
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', P['base'], '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    adec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', P['alpha'], '-vf', f'scale={W}:{H}:flags=bicubic', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE) if (P.get('alpha') and P.get('occlude', False)) else None
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-i', P['audio'], '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', P.get('preset', 'slow'), '-crf', str(P.get('crf', 16)),
                            '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                            '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', P['out']], stdin=subprocess.PIPE)
    fs = W * H * 3; n = 0
    end_t = P.get('duration', 1e9)
    while True:
        buf = dec.stdout.read(fs)
        if len(buf) < fs:
            break
        t = n / FPS
        pa = None
        if adec:
            ab = adec.stdout.read(W * H)
            if len(ab) == W * H:
                pa = np.frombuffer(ab, np.uint8).reshape(H, W).astype(np.float32) / 255.0
        u8 = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        fr = u8.astype(np.float32) / 255.0
        occ = skin_occluder(u8, pa) if P.get('occlude', False) else np.zeros((H, W), np.float32)
        if any(a <= t < b for a, b in bw):
            fr = bw_effect(fr)
            occ = occ * 0.0 + occ  # skin mask came from the colour frame, keep it
        for tr in trans:
            i = n - tr['_n0']
            if 0 <= i < len(tr['pattern']):
                fr = transition_frame(tr['pattern'][i], fr, tr['_F'][i], tr['_A'][i])
                occ = occ * 0  # no occlusion during the flash
        # captions
        prem = np.zeros_like(fr); text_a = np.zeros((H, W), np.float32); glow_a = np.zeros((H, W), np.float32)
        shad_a = np.zeros((H, W), np.float32)
        if t < end_t - 3 / FPS:
            for m, col, op, dx, dy, glow, br in caps.layers(t):
                mm = shift(m, dx, dy) * op
                c = np.array(col, np.float32) / 255 * br
                prem = prem * (1 - mm[..., None]) + c * mm[..., None]      # premultiplied "over"
                text_a = text_a * (1 - mm) + mm
                if glow is True:
                    glow_a = np.maximum(glow_a, np.clip(cv2.GaussianBlur(mm, (0, 0), WHITE['glow_sigma']) * WHITE['glow_k'], 0, 1))
                elif glow == 'shadow' and ORANGE.get('shadow_k', 0) > 0:
                    sh = cv2.GaussianBlur(shift(mm, 0, ORANGE.get('shadow_dy', 3)), (0, 0), ORANGE.get('shadow_sigma', 6))
                    shad_a = np.maximum(shad_a, np.clip(sh * ORANGE['shadow_k'], 0, 1))
        if text_a.any():
            vis = (1 - occ)[..., None]
            fr = fr * (1 - shad_a[..., None] * vis)
            g = glow_a[..., None] * vis
            fr = fr * (1 - g) + 1.0 * g
            fr = fr * (1 - text_a[..., None] * vis) + prem * vis
        if UR:
            for e in ui:
                r = UR.frame(e, t)
                if r and r[0]:
                    blend_sprite(fr, r[0], r[1], r[2])
        enc.stdin.write((np.clip(fr, 0, 1) * 255 + .5).astype(np.uint8).tobytes())
        n += 1
        if n % 150 == 0:
            print('frame', n, flush=True)
    enc.stdin.close(); enc.wait()
    print('rendered', n, 'frames ->', P['out'])


if __name__ == '__main__':
    main()
