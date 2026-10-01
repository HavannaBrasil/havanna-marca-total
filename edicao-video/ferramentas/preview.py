"""Composite captions + UI over base.mp4 at given output times (no transitions), for layout checks.
usage: preview.py timeline.json plan.json out.png t1 t2 ..."""
import sys, json, os, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
from PIL import Image
tl = json.load(open(sys.argv[1])); plan = json.load(open(sys.argv[2])); out = sys.argv[3]; ts = [float(x) for x in sys.argv[4:]]
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
