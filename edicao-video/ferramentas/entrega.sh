#!/bin/bash
# Prepara a entrega de um trabalho já renderizado.
# uso: entrega.sh <pasta do trabalho>
# Gera, a partir do final do proj.json:
#   <nome>_entrega.mp4   HEVC em dois passos, abaixo de 30 MB (limite de envio de arquivo no chat), som AAC 192k
#   mestre/<nome>.mp4.parteN   o arquivo em qualidade máxima dividido em partes de 28 MiB, para enviar pelo chat
#   qa_transicoes.png    quadros exatos em volta de cada transição (n-3, n-1, n)
# e imprime duração, loudness e pico. Para juntar as partes no Mac:
#   cd ~/Downloads && cat <nome>.mp4.parte? > ~/Desktop/<nome>.mp4
set -e
cd "$1"
OUT=$(python3 -c "import json;print(json.load(open('proj.json'))['out'])"); NOME=${OUT%.mp4}
DUR=$(ffmpeg -hide_banner -i "$OUT" 2>&1 | sed -nE 's/.*Duration: ([0-9:.]+).*/\1/p' | awk -F: '{print $1*3600+$2*60+$3}')
# 28 MB no total: (28e6*8/duração) menos 192 kb/s de áudio e 2% de folga do contêiner
VB=$(python3 -c "print(int((28e6*8/$DUR - 192e3)*0.98/1000))")
P="-c:v libx265 -preset medium -b:v ${VB}k -pix_fmt yuv420p -tag:v hvc1 -color_primaries bt709 -color_trc bt709 -colorspace bt709"
ffmpeg -v error -y -i "$OUT" $P -x265-params pass=1:stats=x265.log:log-level=error -an -f mp4 /dev/null
ffmpeg -v error -y -i "$OUT" $P -x265-params pass=2:stats=x265.log:log-level=error -c:a aac -b:a 192k -movflags +faststart "${NOME}_entrega.mp4"
rm -rf mestre; mkdir mestre
split -b 28M -d -a 1 "$OUT" "mestre/$(basename "$OUT").parte"
python3 - <<'PY'
import json, subprocess
E = [x['E'] for x in json.load(open('trans/transitions.json'))] if __import__('os').path.exists('trans/transitions.json') else []
out = json.load(open('proj.json'))['out']
sel = [k for e in E for k in (round(e * 30) - 3, round(e * 30) - 1, round(e * 30))]
if sel:
    expr = '+'.join(f'eq(n\\,{k})' for k in sel)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-vf', f"select='{expr}',scale=180:320,tile={len(sel)}x1",
                    '-vsync', '0', '-frames:v', '1', 'qa_transicoes.png'])
PY
for f in "$OUT" "${NOME}_entrega.mp4"; do
  echo "== $f ($(du -m "$f" | cut -f1) MB)"
  ffmpeg -hide_banner -i "$f" -af loudnorm=print_format=summary -f null - 2>&1 | grep -E "Input Integrated|Input True Peak"
done
ls -l mestre
echo ENTREGA_DONE
