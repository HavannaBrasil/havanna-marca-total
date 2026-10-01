"""Recognise short source ranges with Whisper and Parakeet to settle exact cut points.
usage: asr_clip.py src a1:b1 a2:b2 ..."""
import sys, glob, subprocess, numpy as np, sherpa_onnx
import os as _os
EDV = _os.environ.get('EDV_HOME', _os.path.expanduser('~/edicao-video-dados'))
D=EDV + '/models/'
M=D+'sherpa-onnx-whisper-turbo'
enc=[e for e in glob.glob(M+'/*encoder*.onnx') if 'int8' in e]; dec=[d for d in glob.glob(M+'/*decoder*.onnx') if 'int8' in d]; tok=glob.glob(M+'/*tokens*.txt')
wr=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=enc[0],decoder=dec[0],tokens=tok[0],language='pt',task='transcribe',num_threads=4)
P=D+'sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8'
pr=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=glob.glob(P+'/encoder*.onnx')[0],decoder=glob.glob(P+'/decoder*.onnx')[0],joiner=glob.glob(P+'/joiner*.onnx')[0],tokens=P+'/tokens.txt',model_type='nemo_transducer',num_threads=4)
pcm=subprocess.run(['ffmpeg','-v','error','-i',sys.argv[1],'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout
x=np.frombuffer(pcm,np.int16).astype(np.float32)/32768
for r in sys.argv[2:]:
    a,b=map(float,r.split(':')); seg=np.concatenate([np.zeros(4000,np.float32),x[int(a*16000):int(b*16000)],np.zeros(8000,np.float32)])
    out=[]
    for rec in (wr,pr):
        s=rec.create_stream(); s.accept_waveform(16000,seg); rec.decode_stream(s); out.append(s.result.text.strip())
    print(f'{a:.2f}-{b:.2f} | whisper: {out[0]} | parakeet: {out[1]}')
