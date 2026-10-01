#!/bin/bash
# Baixa um vídeo bruto do Drive, normaliza (HDR do iPhone para SDR, 30 quadros por segundo, 1080x1920) e transcreve.
# uso: intake.sh <id ou link do ARQUIVO no Drive> <nome do trabalho>
# O arquivo precisa estar compartilhado por link e a rede do ambiente precisa liberar drive.usercontent.google.com.
# Resultado em $EDV_HOME/work/<nome>: bruto.mov, mezz.mov, words.json, whisper.json e as duas transcrições em texto.
set -e
T="$(cd "$(dirname "$0")" && pwd)"; S=${EDV_HOME:-$HOME/edicao-video-dados}
ID=$(printf '%s' "$1" | sed -E 's#.*/file/d/([^/?]+).*#\1#; s#.*[?&]id=([^&]+).*#\1#')
C=$S/work/$2; mkdir -p "$C"; cd "$C"
if [ ! -s bruto.mov ]; then
  curl -sS -L -o bruto.mov "https://drive.usercontent.google.com/download?id=$ID&export=download&confirm=t"
fi
# uma página HTML no lugar do vídeo significa arquivo não compartilhado por link ou rede bloqueada
if head -c 512 bruto.mov | grep -qi "<html"; then echo "ERRO: o Drive devolveu uma página, não o vídeo (compartilhamento ou rede)"; rm -f bruto.mov; exit 1; fi
ls -la bruto.mov
python3 $T/prep.py bruto.mov mezz.mov
python3 $T/asr_parakeet.py mezz.mov words.json > transcript_parakeet.txt
python3 $T/asr_whisper.py mezz.mov whisper.json > transcript_whisper.txt
echo INTAKE_DONE "$C"
