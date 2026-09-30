"""Assemble the cut + reframed + graded base video from an EDL.
EDL json: {"src": mezzanine.mov, "W":1080, "H":1920, "grade": "<ffmpeg filter chain or empty>",
           "segments": [{"in": s, "out": s, "zoom": 1.0, "cx": 0.5, "cy": 0.45, "bw": false, "zoom_to": null}]}
Writes base.mp4 (video) and base.wav (audio, 48k stereo) with 6 ms fades at every cut to avoid clicks."""
import sys, json, subprocess
edl = json.load(open(sys.argv[1])); out_v, out_a = sys.argv[2], sys.argv[3]
src, W, H = edl['src'], edl.get('W',1080), edl.get('H',1920)
probe = subprocess.run(['ffmpeg','-hide_banner','-i',src],capture_output=True,text=True).stderr
import re
m = re.search(r'Video:.*?(\d{3,5})x(\d{3,5})', probe); SW, SH = int(m.group(1)), int(m.group(2))
grade = edl.get('grade','')
fc=[]; vl=[]; al=[]
for i,s in enumerate(edl['segments']):
    z=s.get('zoom',1.0); cx=s.get('cx',0.5); cy=s.get('cy',0.5)
    # crop window in source keeping 9:16 of the output
    ch = SH/z; cw = ch*W/H
    if cw > SW: cw = SW; ch = cw*H/W
    x = min(max(cx*SW-cw/2,0),SW-cw); y = min(max(cy*SH-ch/2,0),SH-ch)
    zt = s.get('zoom_to')
    dur = s['out']-s['in']
    v = f"[0:v]trim=start={s['in']:.4f}:end={s['out']:.4f},setpts=PTS-STARTPTS"
    v += f",crop={cw:.1f}:{ch:.1f}:{x:.1f}:{y:.1f}"
    v += f",scale={W}:{H}:flags=lanczos"
    v += ",setsar=1"
    if grade: v += ","+grade
    if s.get('bw'): v += ",hue=s=0,eq=brightness=-0.06:contrast=1.15"
    v += f",fps=30,format=yuv420p[v{i}]"
    fc.append(v); vl.append(f"[v{i}]")
    fd=min(0.006,dur/4)
    fc.append(f"[0:a]atrim=start={s['in']:.4f}:end={s['out']:.4f},asetpts=PTS-STARTPTS,afade=t=in:d={fd:.4f},afade=t=out:st={dur-fd:.4f}:d={fd:.4f}[a{i}]"); al.append(f"[a{i}]")
n=len(edl['segments'])
fc.append(''.join(vl)+f"concat=n={n}:v=1:a=0[vout]")
fc.append(''.join(al)+f"concat=n={n}:v=0:a=1[aout]")
open(out_v+'.filter.txt','w').write(';\n'.join(fc))
subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-filter_complex_script',out_v+'.filter.txt','-map','[vout]','-c:v','libx264','-preset','medium','-crf','15','-pix_fmt','yuv420p','-an',out_v,
                '-map','[aout]','-vn','-c:a','pcm_s16le','-ar','48000',out_a],check=True)
print('assembled', n, 'segments')
