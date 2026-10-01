#!/bin/bash
# usage: run_chain.sh <workdir> [preset] [previa]
# Runs plan -> framing -> assembly -> wide gaps -> transitions -> mix -> render, logging to <workdir>/chain.log style output.
# If the cut list, transition plan and LUT did not change since the last successful assembly, the
# framing, the 4-minute assembly and the transition mattes are reused, so a caption/UI-only change only re-mixes and re-renders.
# With 'previa' it stops after the assembly and writes previa.png (captions and UI over the graded base at the moments
# that matter) instead of mixing and rendering; it prints PREVIA_DONE.
# Prints CHAIN_DONE at the end, or CHAIN_FAILED with the failing step.
set -e -o pipefail
S="$(cd "$(dirname "$0")" && pwd)"
cd "$1"; PRESET=${2:-slow}; MODE=${3:-}
trap 'echo "CHAIN_FAILED na etapa: $STEP"' ERR
STEP=plano; python3 $S/plan_tool2.py words.json plan.json .
# what the assembly depends on: the cut list, the transition plan and the LUT files
{ cat edl_raw.json transitions_plan.json; md5sum *.cube 2>/dev/null || true; } > .chave_montagem.nova
if [ -s base.mp4 ] && [ -s base.wav ] && [ -s trans/transitions.json ] && cmp -s .chave_montagem.nova .chave_montagem; then
  echo "cortes, transições e LUT iguais aos da última montagem: reaproveitando base.mp4, base.wav e as transições"
else
  STEP=enquadramento; python3 $S/facecenter.py edl_raw.json edl.json
  STEP=montagem; python3 $S/assemble.py edl.json base.mp4 base.wav
  # captions are a plain top layer: no full-video matte needed (transitions matte their own pre-rolls)
  STEP=transicoes; rm -rf trans; python3 $S/transitions.py edl.json timeline.json transitions_plan.json trans
  cp .chave_montagem.nova .chave_montagem
fi
STEP=vaos; python3 $S/gaps.py timeline.json
if [ "$MODE" = previa ]; then
  STEP=previa; python3 $S/preview.py timeline.json plan.json previa.png auto
  echo PREVIA_DONE; exit 0
fi
STEP=projeto; python3 $S/proj.py . "$PRESET"
STEP=mixagem; python3 $S/mix.py mix.json
STEP=render; python3 $S/render.py proj.json
echo CHAIN_DONE
