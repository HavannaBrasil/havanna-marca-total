"""Ferramentas de leitura para decidir e conferir cortes. Rode dentro da pasta do trabalho.

  inspecionar.py palavras [de] [ate]    índice, início, fim e texto de cada palavra (words.json), com as trocas de texto do plano
  inspecionar.py cortes                 cada corte que remove áudio (timeline.json), com os trechos prontos para o asr_clip.py:
                                        o que termina no corte (fim da palavra anterior) e o que começa nele (início da seguinte)
  inspecionar.py energia <t> [janela]   envelope de 10 ms em dB em volta do instante t da fonte (mezz.mov); '.' marca silêncio
                                        (abaixo de silence_db do plano, padrão -45). Um trecho de silêncio de 4 a 8 marcas dentro
                                        de uma palavra é o fechamento de uma consoante, não o fim da palavra.
"""
import sys, os, json, subprocess
import numpy as np

cmd = sys.argv[1] if len(sys.argv) > 1 else ''
words = json.load(open('words.json')); words = words['words'] if isinstance(words, dict) else words
plan = json.load(open('plan.json')) if os.path.exists('plan.json') else {}
txt = {int(k): v for k, v in plan.get('text', {}).items()}

if cmd == 'palavras':
    a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else len(words) - 1
    for i in range(a, b + 1):
        w = words[i]; extra = f'   legenda: "{txt[i]}"' if i in txt else ''
        print(f'{i:4d}  {w["s"]:7.2f}  {w["e"]:7.2f}  {w["w"]}{extra}')

elif cmd == 'cortes':
    tl = json.load(open('timeline.json')); segs = tl['segments']
    pares = []
    for a, b in zip(segs, segs[1:]):
        if abs(a['out'] - b['in']) < 1e-3:
            continue
        print(f'final {b["t0"]:7.2f}s  fonte {a["out"]:7.2f} -> {b["in"]:7.2f}  '
              f'"{words[a["last"]]["w"]}" | "{words[b["first"]]["w"]}"  (palavras {a["last"]} | {b["first"]})')
        pares += [f'{max(0, a["out"] - 0.8):.2f}:{a["out"]:.2f}', f'{b["in"]:.2f}:{b["in"] + 0.8:.2f}']
    print('\nConferência (cada par: trecho que termina no corte, trecho que começa nele):')
    print('python3 $F/asr_clip.py mezz.mov ' + ' '.join(pares))

elif cmd == 'energia':
    t = float(sys.argv[2]); jan = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
    sil = plan.get('silence_db', -45.0)
    a = max(0.0, t - jan)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a:.3f}', '-t', f'{2 * jan:.3f}', '-i', plan.get('src', 'mezz.mov'),
                          '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32); n = len(x) // 160
    env = 10 * np.log10((x[:n * 160].reshape(n, 160) ** 2).mean(1) + 1e-12)
    for k in range(0, n, 10):
        linha = ''.join('.' if v < sil else '#' for v in env[k:k + 10])
        vals = ' '.join(f'{v:4.0f}' for v in env[k:k + 10])
        print(f'{a + k / 100:7.2f}  {linha:<10}  {vals}')

else:
    print(__doc__)
