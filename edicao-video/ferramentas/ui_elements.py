"""Contextual UI elements drawn in front of the video, in the reference's visual language
(orange #FC7D01, Instrument Sans Bold for labels, Bebas Neue for numbers, dark translucent panels).
Kept in the safe band 23%-69% of the height so nothing collides with the Reels interface.

element types (times in seconds on the output timeline):
  card      {title, subtitle?, icon, y}
  checklist {items:[{text, t, icon?}], y}
  counter   {to, from?, prefix?, suffix?, label?, y, count_dur?}
  versus    {left:{title, sub?, icon?}, right:{...}, left_t?, right_t?, y}
  cta       {text, icon, y}
  chip      {text, x?, y}
"""
import os as _os
EDV = _os.environ.get('EDV_HOME', _os.path.expanduser('~/edicao-video-dados'))
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = EDV + '/fonts/'
ACCENT = (252, 125, 1)
PANEL = (10, 18, 22, 222)
TEXT = (250, 250, 250)
MUTED = (176, 188, 194)
_f = {}
def font(n, s):
    k = (n, int(s))
    if k not in _f:
        _f[k] = ImageFont.truetype(FONTS + n, int(s))
    return _f[k]
BOLD = 'InstrumentSans-Bold.ttf'
REG = 'Inter-Medium.ttf'
NUM = 'BebasNeue-Regular.ttf'

def cap_h(f):
    b = f.getbbox('H'); return b[3] - b[1]

def text_at(d, x, top, s, f, fill):
    b = f.getbbox('H'); d.text((x, top - b[1]), s, font=f, fill=fill)

def icon(d, kind, cx, cy, r, color):
    c = tuple(color); w = max(3, int(r * 0.2))
    if kind == 'check':
        d.line([(cx - r * .5, cy + r * .02), (cx - r * .12, cy + r * .4), (cx + r * .55, cy - r * .4)], fill=c, width=w, joint='curve')
    elif kind == 'x':
        d.line([(cx - r * .4, cy - r * .4), (cx + r * .4, cy + r * .4)], fill=c, width=w)
        d.line([(cx - r * .4, cy + r * .4), (cx + r * .4, cy - r * .4)], fill=c, width=w)
    elif kind == 'alert':
        d.polygon([(cx, cy - r * .62), (cx + r * .66, cy + r * .5), (cx - r * .66, cy + r * .5)], outline=c, width=w)
        d.line([(cx, cy - r * .18), (cx, cy + r * .16)], fill=c, width=w)
        d.ellipse([cx - w * .6, cy + r * .27, cx + w * .6, cy + r * .27 + w * 1.2], fill=c)
    elif kind == 'bookmark':
        d.polygon([(cx - r * .38, cy - r * .55), (cx + r * .38, cy - r * .55), (cx + r * .38, cy + r * .58), (cx, cy + r * .28), (cx - r * .38, cy + r * .58)], fill=c)
    elif kind == 'send':
        d.polygon([(cx - r * .55, cy - r * .48), (cx + r * .6, cy), (cx - r * .55, cy + r * .48), (cx - r * .32, cy)], fill=c)
    elif kind == 'clock':
        d.ellipse([cx - r * .58, cy - r * .58, cx + r * .58, cy + r * .58], outline=c, width=w)
        d.line([(cx, cy), (cx, cy - r * .34)], fill=c, width=w); d.line([(cx, cy), (cx + r * .28, cy + r * .1)], fill=c, width=w)
    elif kind == 'chart':
        bw = r * .26
        for k, hh in enumerate((.42, .75, 1.1)):
            x = cx - r * .5 + k * (bw + r * .1)
            d.rectangle([x, cy + r * .5 - hh * r * .85, x + bw, cy + r * .5], fill=c)
    elif kind == 'people':
        d.ellipse([cx - r * .2, cy - r * .58, cx + r * .2, cy - r * .18], fill=c)
        d.pieslice([cx - r * .5, cy - r * .08, cx + r * .5, cy + r * .92], 180, 360, fill=c)
    elif kind == 'gear':
        d.ellipse([cx - r * .5, cy - r * .5, cx + r * .5, cy + r * .5], outline=c, width=w)
        d.ellipse([cx - r * .16, cy - r * .16, cx + r * .16, cy + r * .16], fill=c)
        for a in range(0, 360, 45):
            ang = np.deg2rad(a); d.line([(cx + np.cos(ang) * r * .5, cy + np.sin(ang) * r * .5), (cx + np.cos(ang) * r * .7, cy + np.sin(ang) * r * .7)], fill=c, width=w)
    elif kind == 'shield':
        d.polygon([(cx, cy - r * .6), (cx + r * .5, cy - r * .38), (cx + r * .42, cy + r * .25), (cx, cy + r * .62), (cx - r * .42, cy + r * .25), (cx - r * .5, cy - r * .38)], outline=c, width=w)
    elif kind == 'arrow':
        d.line([(cx - r * .5, cy), (cx + r * .4, cy)], fill=c, width=w)
        d.polygon([(cx + r * .6, cy), (cx + r * .15, cy - r * .36), (cx + r * .15, cy + r * .36)], fill=c)
    else:
        d.ellipse([cx - r * .22, cy - r * .22, cx + r * .22, cy + r * .22], fill=c)

class UIRenderer:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.cache = {}

    def sprite(self, el, state):
        key = (id(el), state)
        if key in self.cache:
            return self.cache[key]
        W, H = self.W, self.H
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        t = el['type']
        if t == 'card':
            fT = font(BOLD, el.get('title_size', 50)); fS = font(REG, el.get('sub_size', 36))
            pad, ir = 36, 44
            tw = max(d.textlength(el['title'], font=fT), d.textlength(el.get('subtitle', ''), font=fS))
            bw = int(min(W * .9, tw + pad * 3 + ir * 2)); bh = int(pad * 2 + cap_h(fT) + (cap_h(fS) + 28 if el.get('subtitle') else 0) + 6)
            x0 = (W - bw) // 2; y0 = int(el.get('y', .64) * H)
            d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 34, fill=PANEL, outline=(255, 255, 255, 46), width=2)
            d.ellipse([x0 + pad, y0 + bh / 2 - ir, x0 + pad + 2 * ir, y0 + bh / 2 + ir], fill=ACCENT)
            icon(d, el.get('icon', 'check'), x0 + pad + ir, y0 + bh / 2, ir, TEXT)
            tx = x0 + pad * 2 + 2 * ir
            text_at(d, tx, y0 + pad, el['title'], fT, TEXT)
            if el.get('subtitle'):
                text_at(d, tx, y0 + pad + cap_h(fT) + 28, el['subtitle'], fS, MUTED)
        elif t == 'checklist':
            items = el['items']; k = state
            fI = font(BOLD, el.get('size', 48)); ch = cap_h(fI); row = int(ch * 2.4); pad = 36; r = ch * .95
            tw = max(d.textlength(it['text'], font=fI) for it in items)
            bw = int(min(W * .9, tw + pad * 2 + 2 * r + 28)); bh = pad * 2 + row * (len(items) - 1) + int(2 * r)
            x0 = (W - bw) // 2; y0 = int(el.get('y', .62) * H)
            d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 34, fill=PANEL, outline=(255, 255, 255, 46), width=2)
            for i, it in enumerate(items):
                cy = y0 + pad + r + i * row; cx = x0 + pad + r; on = i < k
                if on:
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT); icon(d, it.get('icon', 'check'), cx, cy, r, TEXT)
                else:
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=MUTED, width=3)
                text_at(d, cx + r + 28, cy - ch / 2, it['text'], fI, TEXT if on else MUTED + (150,))
        elif t == 'counter':
            fN = font(NUM, el.get('size', 250)); fL = font(BOLD, el.get('label_size', 44))
            s = f"{el.get('prefix', '')}{state}{el.get('suffix', '')}"
            tw = d.textlength(s, font=fN); y0 = int(el.get('y', .26) * H)
            text_at(d, (W - tw) / 2, y0, s, fN, TEXT)
            if el.get('label'):
                lw = d.textlength(el['label'], font=fL)
                text_at(d, (W - lw) / 2, y0 + cap_h(fN) + 34, el['label'], fL, ACCENT)
        elif t == 'versus':
            fL = font(BOLD, el.get('size', 44)); fS = font(REG, el.get('sub_size', 30))
            colw = int(W * .42); gap = int(W * .03); bh = int(el.get('h', 200)); y0 = int(el.get('y', .62) * H)
            xs = [(W - 2 * colw - gap) // 2, (W - 2 * colw - gap) // 2 + colw + gap]
            for k, side in enumerate(('left', 'right')):
                it = el[side]; lit = state == k + 1
                d.rounded_rectangle([xs[k], y0, xs[k] + colw, y0 + bh], 30, fill=(ACCENT + (240,)) if lit else PANEL, outline=None if lit else (255, 255, 255, 46), width=2)
                icon(d, it.get('icon', 'x' if k == 0 else 'check'), xs[k] + 56, y0 + bh / 2, 36, TEXT)
                tx = xs[k] + 108
                text_at(d, tx, y0 + bh / 2 - cap_h(fL) - (6 if it.get('sub') else -cap_h(fL) / 2), it['title'], fL, TEXT)
                if it.get('sub'):
                    text_at(d, tx, y0 + bh / 2 + 14, it['sub'], fS, TEXT if lit else MUTED)
        elif t == 'cta':
            fT = font(BOLD, el.get('size', 46)); ch = cap_h(fT)
            bh = ch + 64; tw = d.textlength(el['text'], font=fT); bw = int(tw + 70 + bh)
            x0 = (W - bw) // 2; y0 = int(el.get('y', .64) * H)
            d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], bh // 2, fill=(250, 250, 250, 245))
            d.ellipse([x0 + 10, y0 + 10, x0 + bh - 10, y0 + bh - 10], fill=ACCENT)
            icon(d, el.get('icon', 'send'), x0 + bh / 2, y0 + bh / 2, (bh - 20) / 2, TEXT)
            text_at(d, x0 + bh + 22, y0 + 32, el['text'], fT, (18, 22, 26))
        elif t == 'chip':
            fC = font(BOLD, el.get('size', 42)); ch = cap_h(fC)
            tw = d.textlength(el['text'], font=fC); bw = int(tw + 64); bh = ch + 46
            x0 = int(el.get('x', .5) * W - bw / 2); y0 = int(el.get('y', .30) * H)
            d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], bh // 2, fill=ACCENT)
            text_at(d, x0 + 32, y0 + 23, el['text'], fC, TEXT)
        bbox = img.getbbox()
        if bbox and bbox[3] > int(0.68 * H):            # never below 68% (Reels interface zone)
            dy_ = bbox[3] - int(0.68 * H)
            img = img.transform(img.size, Image.AFFINE, (1, 0, 0, 0, 1, dy_)); bbox = img.getbbox()
        out = (bbox, np.asarray(img.crop(bbox), dtype=np.float32) / 255.0) if bbox else None
        if out is not None:
            a = out[1]; a[..., :3] *= a[..., 3:4]  # premultiply
            out = (bbox, a)
        self.cache[key] = out
        return out

    def frame(self, el, t):
        t0, t1 = el['t0'], el['t1']
        if t < t0 or t >= t1:
            return None
        ain, aout = el.get('in', .2), el.get('out', .15)
        p_in = min(1, (t - t0) / ain) if ain else 1
        p_out = min(1, (t1 - t) / aout) if aout else 1
        e = 1 - (1 - p_in) ** 3
        op = min(e, p_out); dy = (1 - e) * 60
        if el['type'] == 'checklist':
            state = sum(1 for it in el['items'] if t >= it['t'])
        elif el['type'] == 'counter':
            dur = el.get('count_dur', .9); p = min(1, max(0, (t - t0) / dur)); p = 1 - (1 - p) ** 3
            state = int(round(el.get('from', 0) + (el['to'] - el.get('from', 0)) * p))
        elif el['type'] == 'versus':
            state = 0
            if 'left_t' in el and t >= el['left_t']: state = 1
            if 'right_t' in el and t >= el['right_t']: state = 2
        else:
            state = 0
        return self.sprite(el, state), op, dy
