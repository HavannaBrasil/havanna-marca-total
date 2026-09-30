"""Normalize any source (iPhone MOV HDR/HLG/Dolby Vision, rotated, 24-60fps) to SDR BT.709 30fps mezzanine.
usage: prep.py in.MOV out.mp4 [max_long_side]"""
import sys, subprocess, json, re
src, out = sys.argv[1], sys.argv[2]
p = subprocess.run(['ffmpeg','-hide_banner','-i',src],capture_output=True,text=True).stderr
print(p[p.find('Input'):][:1500])
hdr = ('arib-std-b67' in p) or ('smpte2084' in p) or ('bt2020' in p)
m = re.search(r'Video:.*?(\d{3,5})x(\d{3,5})', p)
w,h = int(m.group(1)), int(m.group(2))
rot = re.search(r'rotation of (-?\d+)', p) or re.search(r'rotate\s*:\s*(-?\d+)', p)
if rot and abs(int(rot.group(1))) in (90,270): w,h = h,w
vertical = h >= w
# target: keep vertical 1080x1920 if vertical, else keep landscape at 1920x1080 (reframe later)
tw,th = (1080,1920) if vertical else (1920,1080)
vf = []
if hdr:
    vf += ['zscale=t=linear:npl=203','format=gbrpf32le','zscale=p=bt709','tonemap=tonemap=hable:desat=0:peak=4','zscale=t=bt709:m=bt709:r=tv','format=yuv420p']
vf += [f'scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos',f'crop={tw}:{th}','fps=30','format=yuv420p']
cmd=['ffmpeg','-v','error','-y','-i',src,'-vf',','.join(vf),'-c:v','libx264','-preset','medium','-crf','14','-pix_fmt','yuv420p',
     '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-c:a','pcm_s16le','-ar','48000','-ac','2',out]
print('HDR' if hdr else 'SDR', 'vertical' if vertical else 'landscape', w,h,'->',tw,th)
subprocess.run(cmd,check=True)
