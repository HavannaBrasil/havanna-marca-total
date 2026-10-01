"""Whisper large-v3-turbo (sherpa-onnx) transcription over VAD-split chunks, used to cross-check Parakeet's text.
usage: asr_whisper.py in.wav|video out.json"""
import os as _os
EDV = _os.environ.get('EDV_HOME', _os.path.expanduser('~/edicao-video-dados'))
import sys, json, subprocess, numpy as np, sherpa_onnx
M=EDV + '/models/sherpa-onnx-whisper-turbo'
V=EDV + '/models/silero_vad.onnx'
src,out=sys.argv[1],sys.argv[2]
pcm=subprocess.run(['ffmpeg','-v','error','-i',src,'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout
x=np.frombuffer(pcm,np.int16).astype(np.float32)/32768; sr=16000
import glob
enc=glob.glob(M+'/*encoder*.onnx'); dec=glob.glob(M+'/*decoder*.onnx'); tok=glob.glob(M+'/*tokens*.txt')
enc=[e for e in enc if 'int8' in e] or enc; dec=[d for d in dec if 'int8' in d] or dec
rec=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=enc[0],decoder=dec[0],tokens=tok[0],language='pt',task='transcribe',num_threads=4)
cfg=sherpa_onnx.VadModelConfig(); cfg.silero_vad.model=V; cfg.silero_vad.min_silence_duration=0.35; cfg.silero_vad.max_speech_duration=25; cfg.sample_rate=sr
vad=sherpa_onnx.VoiceActivityDetector(cfg,buffer_size_in_seconds=120)
segs=[]; win=512
for i in range(0,len(x),win):
    vad.accept_waveform(x[i:i+win])
    while not vad.empty():
        segs.append((vad.front.start/sr, np.array(vad.front.samples))); vad.pop()
vad.flush()
while not vad.empty():
    segs.append((vad.front.start/sr, np.array(vad.front.samples))); vad.pop()
res=[]
for st,a in segs:
    s=rec.create_stream(); s.accept_waveform(sr,a); rec.decode_stream(s)
    res.append({'start':round(st,2),'end':round(st+len(a)/sr,2),'text':s.result.text.strip()})
json.dump(res,open(out,'w'),ensure_ascii=False,indent=1)
print('\n'.join(f"[{r['start']:6.2f}-{r['end']:6.2f}] {r['text']}" for r in res))
