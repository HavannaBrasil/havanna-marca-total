"""Confere, no áudio do vídeo FINAL, se alguma palavra ficou cortada nos cortes que removem áudio.
Para cada corte com salto na fonte, reconhece (Parakeet) a janela em volta do corte no arquivo final e imprime
ao lado das palavras que o plano diz que estão ali. Uma palavra truncada aparece como palavra diferente,
encurtada ou ausente (exemplo real: "ninguém" virou "ninho" e "maturidade" virou "maturi").
uso: qa_cortes.py <pasta do trabalho> [video final, padrão final do proj.json]"""
import sys, os, json, glob, subprocess
import numpy as np
EDV = os.environ.get('EDV_HOME', os.path.expanduser('~/edicao-video-dados'))
import sherpa_onnx
wd = sys.argv[1]
tl = json.load(open(f'{wd}/timeline.json')); words = json.load(open(f'{wd}/words.json'))
words = words['words'] if isinstance(words, dict) else words
plan = json.load(open(f'{wd}/plan.json'))
txt = {int(k): v for k, v in plan.get('text', {}).items()}
video = sys.argv[2] if len(sys.argv) > 2 else os.path.join(wd, json.load(open(f'{wd}/proj.json'))['out'])
P = EDV + '/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8'
rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=glob.glob(P + '/encoder*.onnx')[0], decoder=glob.glob(P + '/decoder*.onnx')[0],
                                                    joiner=glob.glob(P + '/joiner*.onnx')[0], tokens=P + '/tokens.txt',
                                                    model_type='nemo_transducer', num_threads=4)
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
segs = tl['segments']
w = lambda i: txt.get(i, words[i]['w']) or words[i]['w']
n = 0
for a, b in zip(segs, segs[1:]):
    if abs(a['out'] - b['in']) < 1e-3:
        continue                                   # corte só de imagem: o áudio continua, nada a conferir
    n += 1
    t = b['t0']
    clip = x[int(max(0, t - 1.3) * 16000):int((t + 1.0) * 16000)]
    clip = np.concatenate([np.zeros(4000, np.float32), clip, np.zeros(8000, np.float32)])
    s = rec.create_stream(); s.accept_waveform(16000, clip); rec.decode_stream(s)
    esperado = ' '.join(w(i) for i in range(max(a['first'], a['last'] - 2), a['last'] + 1)) + ' | ' + \
               ' '.join(w(i) for i in range(b['first'], min(b['last'], b['first'] + 1) + 1))
    print(f'{t:7.2f}s  plano: {esperado:<45}  ouvido: {s.result.text}')
print(f'{n} cortes com salto de áudio conferidos. Compare a última palavra antes de cada barra com o que foi ouvido.')
