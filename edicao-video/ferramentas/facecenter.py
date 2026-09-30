"""Fill crop centres of an EDL from face positions (OpenCV Haar, sampled per segment).
usage: facecenter.py edl_raw.json edl.json [target_face_y=0.33]
Zoomed segments put the face at target_face_y of the output frame height and centre it horizontally
(with a small offset toward the side the speaker faces is not attempted: keep it simple and stable)."""
import os as _os
EDV = _os.environ.get('EDV_HOME', _os.path.expanduser('~/edicao-video-dados'))
import sys, os
sys.path.insert(0, EDV + "/pylibs")
import json, subprocess, numpy as np, cv2

edl = json.load(open(sys.argv[1])); ty = float(sys.argv[3]) if len(sys.argv) > 3 else 0.33
src = edl['src']
casc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
prof = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')

def frame_at(t, w=540):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', src, '-frames:v', '1', '-vf', f'scale={w}:-2', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
    h = len(raw) // w
    return np.frombuffer(raw, np.uint8).reshape(h, w) if h else None

def face(t):
    g = frame_at(t)
    if g is None:
        return None
    H, W = g.shape
    best = None
    for c in (casc, prof):
        for flip in (False, True):
            img = cv2.flip(g, 1) if flip else g
            fs = c.detectMultiScale(img, 1.1, 5, minSize=(W // 14, W // 14))
            for (x, y, w, h) in fs:
                if flip:
                    x = W - x - w
                if best is None or w * h > best[2] * best[3]:
                    best = (x, y, w, h)
        if best is not None:
            break
    if best is None:
        return None
    x, y, w, h = best
    return ((x + w / 2) / W, (y + h / 2) / H, h / H)

prev = (0.5, 0.3, 0.1)
for s in edl['segments']:
    ts = np.linspace(s['in'] + 0.05, max(s['in'] + 0.06, s['out'] - 0.05), 3)
    fs = [f for f in (face(t) for t in ts) if f]
    if fs:
        fx = float(np.median([f[0] for f in fs])); fy = float(np.median([f[1] for f in fs])); fh = float(np.median([f[2] for f in fs]))
        prev = (fx, fy, fh)
    else:
        fx, fy, fh = prev
    z = s.get('zoom', 1.0)
    if s.get('cx') is None:
        s['cx'] = round(fx + s.get('cx_shift', 0.0) / z, 4)
    if s.get('cy') is None:
        s['cy'] = round(fy + (0.5 - ty) / z, 4)
    s['_face'] = [round(fx, 3), round(fy, 3), round(fh, 3)]
json.dump(edl, open(sys.argv[2], 'w'), indent=1)
print('faces filled for', len(edl['segments']), 'segments')
