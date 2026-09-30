#!/bin/bash
# usage: run_chain.sh <workdir> [preset]
set -e
S="$(cd "$(dirname "$0")" && pwd)"
cd "$1"; PRESET=${2:-slow}
python3 $S/plan_tool2.py words.json plan.json .
python3 $S/facecenter.py edl_raw.json edl.json
python3 $S/assemble.py edl.json base.mp4 base.wav
# captions are a plain top layer: no full-video matte needed (transitions matte their own pre-rolls)
python3 $S/gaps.py timeline.json
python3 $S/transitions.py edl.json timeline.json transitions_plan.json trans
python3 - <<PY
import json
t=json.load(open('timeline.json')); p=json.load(open('plan.json'))
music=dict(p.get('music',{})); music.setdefault('build_at', t['music_build']); music.setdefault('lufs',-29)
json.dump({'voice':'base.wav','out':'mix.wav','music':music,'sfx':t['sfx'],'target_lufs':-14, **({'voice_chain':p['voice_chain']} if 'voice_chain' in p else {})},open('mix.json','w'))
proj={'base':'base.mp4','audio':'mix.wav','out':p.get('out','final.mp4'),'preset':'$PRESET','crf':p.get('crf',16),
      'captions':t['captions'],'ui':t['ui'],'bw':t['bw'],'transitions':json.load(open('trans/transitions.json')),'duration':t['duration']}
json.dump(proj,open('proj.json','w'),ensure_ascii=False)
PY
python3 $S/mix.py mix.json
python3 $S/render.py proj.json
echo CHAIN_DONE
