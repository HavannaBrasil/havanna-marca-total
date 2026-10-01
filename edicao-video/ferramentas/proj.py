"""Writes mix.json and proj.json for a work folder from timeline.json, plan.json and trans/transitions.json.
usage: proj.py <workdir> [preset]"""
import sys, json, os
wd = sys.argv[1]; preset = sys.argv[2] if len(sys.argv) > 2 else 'slow'
os.chdir(wd)
t = json.load(open('timeline.json')); p = json.load(open('plan.json'))
music = dict(p.get('music', {})); music.setdefault('build_at', t['music_build']); music.setdefault('lufs', -29)
mix = {'voice': 'base.wav', 'out': 'mix.wav', 'music': music, 'sfx': t['sfx'], 'target_lufs': -14}
if 'voice_chain' in p:
    mix['voice_chain'] = p['voice_chain']
json.dump(mix, open('mix.json', 'w'))
trans = json.load(open('trans/transitions.json')) if os.path.exists('trans/transitions.json') else []
proj = {'base': 'base.mp4', 'audio': 'mix.wav', 'out': p.get('out', 'final.mp4'), 'preset': preset, 'crf': p.get('crf', 16),
        'captions': t['captions'], 'ui': t['ui'], 'bw': t['bw'], 'transitions': trans, 'duration': t['duration'], 'style': p.get('style')}
json.dump(proj, open('proj.json', 'w'), ensure_ascii=False)
print('mix.json e proj.json gravados')
