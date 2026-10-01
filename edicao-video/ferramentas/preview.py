"""Composite captions + UI over base.mp4 at given output times (no transitions), for layout checks.
usage: preview.py timeline.json plan.json out.png t1 t2 ...
       preview.py timeline.json plan.json out.png auto
auto picks: the hook, every white card (after its second line is in), the middle of the B&W moment, each UI element
after its last state change, and a few orange cards spread over the video. Run it inside the work folder (reads base.mp4)."""
import sys, json, os, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
from PIL import Image
tl = json.load(open(sys.argv[1])); plan = json.load(open(sys.argv[2])); out = sys.argv[3]
def auto_times(tl):
    ts = []
    for c in tl['captions']:
        if c['tier'] == 'hook':
            ts.append(c.get('t_sub', 0.3) + 0.3)
        elif c['tier'] == 'white':
            ts.append(min(c['t1'] - 0.05, max(c['t0'], c.get('t_line2', c['t0'])) + 0.25))
    for a, b in tl['bw']:
        ts.append((a + b) / 2)
    for u in tl['ui']:
        last = max([u['t0']] + [it['t'] for it in u.get('items', [])] + [u.get(k) for k in ('left_t', 'right_t') if u.get(k)])
        ts.append(min(u['t1'] - 0.1, last + 0.4))
    oranges = [c for c in tl['captions'] if c['tier'] == 'orange']
    for c in oranges[::max(1, len(oranges) // 4)][:4]:
        ts.append((c['t0'] + c['t1']) / 2)
    out = []
    for t in sorted(round(t, 2) for t in ts):
        if not out or t - out[-1] > 0.4:          # drop near-duplicates (a card and a UI state at the same moment)
            out.append(t)
    return out
ts = auto_times(tl) if sys.argv[4:] == ['auto'] else [float(x) for x in sys.argv[4:]]
print('instantes:', ' '.join(f'{t:.2f}' for t in ts))
R.apply_style(plan.get('style'))
caps = R.Captions(tl['captions']); UR = R.UIRenderer(R.W, R.H)
tiles = []
for t in ts:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', 'base.mp4', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(R.H, R.W, 3).astype(np.float32) / 255
    if any(a <= t < b for a, b in tl['bw']):
        fr = R.bw_effect(fr)
    prem = np.zeros_like(fr); ta = np.zeros((R.H, R.W), np.float32); ga = np.zeros_like(ta); sa = np.zeros_like(ta)
    for m, col, op, dx, dy, glow, br in caps.layers(t):
        mm = R.shift(m, dx, dy) * op; c = np.array(col, np.float32) / 255 * br
        prem = prem * (1 - mm[..., None]) + c * mm[..., None]; ta = ta * (1 - mm) + mm
        if glow is True:
            ga = np.maximum(ga, np.clip(R.cv2.GaussianBlur(mm, (0, 0), R.WHITE['glow_sigma']) * R.WHITE['glow_k'], 0, 1))
        elif glow == 'shadow' and R.ORANGE.get('shadow_k', 0) > 0:
            sa = np.maximum(sa, np.clip(R.cv2.GaussianBlur(R.shift(mm, 0, R.ORANGE.get('shadow_dy', 3)), (0, 0), R.ORANGE.get('shadow_sigma', 6)) * R.ORANGE['shadow_k'], 0, 1))
    fr = fr * (1 - sa[..., None]); fr = fr * (1 - ga[..., None]) + ga[..., None]; fr = fr * (1 - ta[..., None]) + prem
    for e in tl['ui']:
        r = UR.frame(e, t)
        if r and r[0]:
            R.blend_sprite(fr, r[0], r[1], r[2])
    im = Image.fromarray((np.clip(fr, 0, 1) * 255 + .5).astype(np.uint8)).resize((360, 640))
    tiles.append(im)
sheet = Image.new('RGB', (360 * min(6, len(tiles)), 640 * ((len(tiles) + 5) // 6)))
for i, im in enumerate(tiles):
    sheet.paste(im, ((i % 6) * 360, (i // 6) * 640))
sheet.save(out); print('ok', out)
