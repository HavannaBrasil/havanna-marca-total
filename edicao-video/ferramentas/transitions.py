"""Prepare the 'silhouette flash' transitions measured in the reference.
For each transition the INCOMING shot starts k frames early as a person cut-out over the outgoing shot, flickering
through states, then 1-2 full-white frames, then the hard cut. We extract, for each transition, the k source frames
right before the incoming segment's in-point (same crop as that segment) plus a 1 s warm-up for the matting model.

usage: transitions.py edl.json timeline.json plan_transitions.json out_dir
plan_transitions.json: [{"segment": 7, "pattern": "T1"}, ...]   (segment = index of the INCOMING segment)
writes out_dir/transitions.json for render.py
"""
import sys, json, subprocess, os, re

PATTERNS = {
    'T1': ['white', 'semi', 'plain', 'hot', 'plain', 'full', 'full'],
    'T2': ['white', 'semi70', 'cool', 'hot', 'plain', 'full', 'full'],
    'T3': ['glow', 'plain', 'black', 'plain', 'full'],
    'T4': ['white', 'black', 'plain', 'full'],
}
TOOLS = os.path.dirname(os.path.abspath(__file__))

edl = json.load(open(sys.argv[1])); tl = json.load(open(sys.argv[2])); plan = json.load(open(sys.argv[3])); out = sys.argv[4]
os.makedirs(out, exist_ok=True)
src = edl['src']
probe = subprocess.run(['ffmpeg', '-hide_banner', '-i', src], capture_output=True, text=True).stderr
m = re.search(r'Video:.*?(\d{3,5})x(\d{3,5})', probe); SW, SH = int(m.group(1)), int(m.group(2))
W, H = edl.get('W', 1080), edl.get('H', 1920)
res = []
for i, tr in enumerate(plan):
    seg = edl['segments'][tr['segment']]
    pat = PATTERNS[tr.get('pattern', 'T1')] if isinstance(tr.get('pattern', 'T1'), str) else tr['pattern']
    k = len(pat)
    z = seg.get('zoom', 1.0); cx = seg.get('cx', .5); cy = seg.get('cy', .5)
    ch = SH / z; cw = ch * W / H
    if cw > SW:
        cw = SW; ch = cw * H / W
    x = min(max(cx * SW - cw / 2, 0), SW - cw); y = min(max(cy * SH - ch / 2, 0), SH - ch)
    t_end = seg['in']; t_start = max(0.0, t_end - k / 30 - 1.0)
    clip = f'{out}/tr{i}_frames.mp4'; alpha = f'{out}/tr{i}_alpha.mkv'
    vf = f"crop={cw:.1f}:{ch:.1f}:{x:.1f}:{y:.1f},scale={W}:{H}:flags=lanczos,fps=30" + ("," + edl['grade'] if edl.get('grade') else '')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t_start:.4f}', '-i', src, '-t', f'{t_end - t_start:.4f}', '-vf', vf, '-an',
                    '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', clip], check=True)
    subprocess.run(['python3', f'{TOOLS}/matte.py', clip, alpha, '720', '1280', 'mobilenetv3', '0.25'], check=True)
    E = tl['segments'][tr['segment']]['t0']
    res.append({'E': E, 'frames': clip, 'alpha': alpha, 'pattern': pat})
json.dump(res, open(f'{out}/transitions.json', 'w'), indent=1)
print('prepared', len(res), 'transitions')
