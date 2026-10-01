import os as _os
EDV = _os.environ.get('EDV_HOME', _os.path.expanduser('~/edicao-video-dados'))
import sys, json, subprocess, numpy as np, sherpa_onnx
M=EDV + '/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8'
src, out = sys.argv[1], sys.argv[2]
pcm = subprocess.run(['ffmpeg','-v','error','-i',src,'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout
x = np.frombuffer(pcm, np.int16).astype(np.float32)/32768
rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f'{M}/encoder.int8.onnx', decoder=f'{M}/decoder.int8.onnx', joiner=f'{M}/joiner.int8.onnx', tokens=f'{M}/tokens.txt', model_type='nemo_transducer', num_threads=4)
# chunk into <=25s windows with VAD-free fixed windows overlapped at silences is complex; use 20s windows with 0 overlap split at lowest-energy point
sr=16000; win=20*sr; pos=0; words=[]
def lowest_energy(a,b):
    seg=x[a:b]; f=int(0.02*sr); n=len(seg)//f
    e=[np.mean(seg[i*f:(i+1)*f]**2) for i in range(n)]
    return a+int(np.argmin(e))*f+f//2
while pos < len(x):
    end = len(x) if len(x)-pos <= win+5*sr else lowest_energy(pos+win-4*sr, pos+win+4*sr)
    s = rec.create_stream(); s.accept_waveform(sr, x[pos:end]); rec.decode_stream(s)
    r = s.result
    toks, ts = r.tokens, r.timestamps
    # merge sentencepiece tokens into words
    cur=None
    for t,tt in zip(toks,ts):
        t0=pos/sr+tt
        if t.startswith('▁') or t.startswith(' ') or cur is None:
            if cur: words.append(cur)
            cur={'w':t.lstrip('▁ '),'s':round(t0,3)}
        else:
            cur['w']+=t
        cur['e']=round(t0+0.08,3)
    if cur: words.append(cur)
    pos=end
# fix word ends: end = next start if gap small
for i in range(len(words)-1):
    words[i]['e']=round(min(words[i+1]['s'], max(words[i]['e'], words[i]['s']+0.12)),3)
json.dump(words, open(out,'w'), ensure_ascii=False, indent=0)
print(' '.join(w['w'] for w in words))
