"""Audio finishing calibrated on the reference: processed voice at -14 LUFS, static music bed ~15 dB under
the voice (no ducking), SFX placed on the output timeline, two-pass loudness normalisation, true peak -1 dBTP.
usage: mix.py audio_plan.json
{"voice": "base.wav", "out": "mix.wav", "duration": 57.3,
 "voice_chain": "<ffmpeg filter chain>",
 "music": {"key_shift": 0, "build_at": 16.2, "lufs": -29, "start": 0.2} | null,
 "sfx": [{"type": "boom|hit|boom_c|glitch", "t": 3.53, "peak_db": -2}],
 "target_lufs": -14}
Each sfx 't' is where the sound STARTS (for 'hit' it is the attack time; the pre-rise is placed before it).
"""
import sys, json, subprocess, os
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
import synth

FEMALE_CHAIN = ("highpass=f=120:poles=2,equalizer=f=300:t=q:w=1.2:g=-3,equalizer=f=3500:t=q:w=1:g=3,"
                "treble=g=4:f=6500,deesser=i=0.3:m=0.5:f=0.5,"
                "acompressor=threshold=-24dB:ratio=4:attack=5:release=60:makeup=8dB,"
                "dynaudnorm=f=250:g=11:m=8:p=0.9,alimiter=limit=0.891:attack=3:release=50:level=0")

def lufs(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return json.loads(r[r.rfind('{'):r.rfind('}') + 1])

P = json.load(open(sys.argv[1]))
out = P['out']; tmp = out + '.voice.wav'
chain = P.get('voice_chain', FEMALE_CHAIN)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', P['voice'], '-af', 'pan=mono|c0=0.5*c0+0.5*c1,' + chain, '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s32le', tmp], check=True)
v, sr = sf.read(tmp, dtype='float32', always_2d=True); v = v.T
n = v.shape[1]
# voice to -14 LUFS first so the music offset is exact
vl = float(lufs(tmp)['input_i'])
tl = P.get('target_lufs', -14)
v *= 10 ** ((tl - vl) / 20)
bus = v.copy()
m = P.get('music')
if m:
    bed = synth.pad_minor(n / sr, start=m.get('start', 0.2), build_at=m.get('build_at', 16.2), key_shift=m.get('key_shift', 0))[:, :n]
    sf.write(out + '.music.wav', bed.T, sr, subtype='FLOAT')
    ml = float(lufs(out + '.music.wav')['input_i'])
    bed *= 10 ** ((m.get('lufs', -29) - ml) / 20)
    bus[:, :bed.shape[1]] += bed
for s in P.get('sfx', []):
    kind = s['type']
    if kind == 'hit':
        x, pre = synth.hit()
        i0 = int((s['t'] - pre) * sr)
    else:
        x = getattr(synth, kind)(seed=s.get('seed')) if kind == 'glitch' else getattr(synth, kind)()
        i0 = int(s['t'] * sr)
    x = x * 10 ** (s.get('peak_db', -2) / 20) / (np.max(np.abs(x)) + 1e-9)
    # SFX are mixed relative to full scale of the -14 LUFS voice bus
    i0 = max(0, i0); i1 = min(n, i0 + x.shape[1])
    bus[:, i0:i1] += x[:, :i1 - i0]
sf.write(out + '.pre.wav', bus.T, sr, subtype='FLOAT')
js = lufs(out + '.pre.wav')
af = (f"loudnorm=I={tl}:TP=-1.0:LRA=7:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
      f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out + '.pre.wav', '-af', af + ',alimiter=limit=0.891:attack=2:release=40:level=0', '-ar', '48000', '-c:a', 'pcm_s16le', out], check=True)
fin = lufs(out)
print(f"mix ok -> {out}: voice in {vl:.1f} LUFS, final I {fin['input_i']} LUFS, TP {fin['input_tp']} dBTP, LRA {fin['input_lra']}")
