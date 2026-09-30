#!/bin/bash
# Download (once the network allows Drive), normalise and transcribe the Carla source.
set -e
T="$(cd "$(dirname "$0")" && pwd)"; S=${EDV_HOME:-$HOME/edicao-video-dados}; C=$S/work/carla; mkdir -p $C; cd $C
if [ ! -s carla_raw.MOV ]; then
  curl -sS -L -o carla_raw.MOV "https://drive.usercontent.google.com/download?id=1xVILqX2ZF0CcV2BXWrE4zPL6c3PPInRp&export=download&confirm=t"
fi
ls -la carla_raw.MOV
python3 $T/prep.py carla_raw.MOV mezz.mov
python3 $T/asr_parakeet.py mezz.mov words.json > transcript_parakeet.txt
python3 $T/asr_whisper.py mezz.mov whisper.json > transcript_whisper.txt
echo INTAKE_DONE
