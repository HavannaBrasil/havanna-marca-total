"""Authored edit plan (word-index based) -> EDL + caption/effect/SFX timeline, applying the reference's rules.
usage: plan_tool2.py words.json plan.json out_dir

plan.json:
{
 "src": "mezz.mov", "grade": "<ffmpeg chain>",
 "text": {"12": "Deus,"},                       # word text overrides ("" hides the word in captions)
 "keep": [[0, 40], [44, 120]],                   # inclusive word ranges, output order
 "pad_before": 0.05, "pad_after": 0.06, "max_gap": 0.12,
 "breath": {"87": 0.26},                          # keep a longer pause (s) before these words
 "framing": [{"from": 0, "zoom": 1.0}],          # optional, static framing per segment (no animation)
 "cut_at": [33, 61],                              # extra forced cuts at these word starts
 "cards": [ {"tier": "hook", "top": [0, 2], "top_text": ["QUANDO", "É QUE"], "sub": [3, 7], "top_gap": 170},
            {"tier": "white", "lines": [[8, 8], [9, 9]], "text": ["SUBESTIMANDO", "FERIDA?"], "entry": "cut", "line2_entry": "slide"},
            {"tier": "white", "lines": [[17, 17], [18, 18]], "text": ["TODO", "MUNDO"], "mode": "equal"},
            {"tier": "orange", "w": [10, 12], "text": "Quando a gente", "entry": "auto"} ],
 "bw": [16, 18],                                   # word range of the black-and-white moment (starts on a cut)
 "transitions": [{"at": 22, "pattern": "T1"}],    # incoming segment starts at word 22
 "ui": [{"type": "counter", "at": 30, "until": 36, "to": 460, ...}],
 "sfx": "auto",
 "music": {"key_shift": 0}
}
"""
import sys, json, os
words = json.load(open(sys.argv[1])); plan = json.load(open(sys.argv[2])); out = sys.argv[3]
os.makedirs(out, exist_ok=True)
FPS = 30; FR = 1.0 / FPS
snap = lambda x: round(round(x * FPS) / FPS, 5)
txt = {int(k): v for k, v in plan.get('text', {}).items()}
wt = lambda i: txt.get(i, words[i]['w'])
pb, pa, mg = plan.get('pad_before', .05), plan.get('pad_after', .06), plan.get('max_gap', .12)
breath = {int(k): v for k, v in plan.get('breath', {}).items()}

# ---------------- segments ----------------
forced = set(plan.get('cut_at', [])) | ({f['from'] for f in plan.get('framing', [])} if isinstance(plan.get('framing'), list) else set()) | {t['at'] for t in plan.get('transitions', [])}
if plan.get('bw'):
    forced.add(plan['bw'][0])
phr = []
for a, b in plan['keep']:
    cur = [a]
    for i in range(a + 1, b + 1):
        if words[i]['s'] - words[i - 1]['e'] > mg or i in forced or i in breath:
            phr.append(cur); cur = [i]
        else:
            cur.append(i)
    phr.append(cur)
segs = []
for ws in phr:
    s_in = max(0.0, words[ws[0]]['s'] - breath.get(ws[0], pb)); s_out = words[ws[-1]]['e'] + pa
    if segs and segs[-1]['words'][-1] + 1 == ws[0] and s_in < segs[-1]['out']:
        mid = (words[ws[0] - 1]['e'] + words[ws[0]]['s']) / 2
        segs[-1]['out'] = mid; s_in = mid
    segs.append({'in': s_in, 'out': s_out, 'words': ws})
for s in segs:
    s['in'], s['out'] = snap(s['in']), snap(s['out'])
segs = [s for s in segs if s['out'] - s['in'] >= FR]
t = 0.0; wmap = {}
for s in segs:
    s['t0'] = round(t, 5)
    for i in s['words']:
        wmap[i] = (t + words[i]['s'] - s['in'], t + words[i]['e'] - s['in'])
    t += s['out'] - s['in']; s['t1'] = round(t, 5)
total = t
seg_of_word = {i: k for k, s in enumerate(segs) for i in s['words']}
cut_times = [s['t0'] for s in segs[1:]]

# framing -> EDL.  'auto' = the reference's 3 static scale levels switched at every cut
if plan.get('framing') == 'auto':
    LV = {'W': 1.0, 'M': 1.17, 'T': 1.30}
    after_tr = [t['at'] for t in plan.get('transitions', [])][:2]
    cyc = ['T', 'W', 'M', 'W', 'T', 'M']; ci = 0; prev = None; auto = []
    for k, s_ in enumerate(segs):
        w0 = s_['words'][0]
        f = {'from': w0}
        if k == 0:
            lv = 'M'
        elif w0 in after_tr or k == len(segs) - 1:
            lv = 'W'
        elif k % 3 == 2 and prev in ('M', 'T'):
            lv = prev; f['cx_shift'] = 0.06 if (k // 3) % 2 else -0.06   # same size, reframed sideways
        else:
            lv = cyc[ci % len(cyc)]; ci += 1
            while lv == prev:
                lv = cyc[ci % len(cyc)]; ci += 1
        prev = lv
        f['zoom'] = LV[lv]
        auto.append(f)
    plan['framing'] = auto
fr = sorted(plan.get('framing', [{'from': 0, 'zoom': 1.0}]), key=lambda f: f['from'])
def framing_for(w0):
    cur = fr[0]
    for f in fr:
        if f['from'] <= w0:
            cur = f
    return cur
edl = {'src': plan['src'], 'grade': plan.get('grade', ''), 'segments': []}
for s in segs:
    f = framing_for(s['words'][0])
    edl['segments'].append({'in': s['in'], 'out': s['out'], 'zoom': f.get('zoom', 1.0), 'cx': f.get('cx'), 'cy': f.get('cy'), 'cx_shift': f.get('cx_shift', 0.0), '_first_word': s['words'][0]})
json.dump(edl, open(f'{out}/edl_raw.json', 'w'), indent=1)

# ---------------- captions ----------------
def on(i):  # output onset of word i
    return wmap[i][0]
def snap_to_cut(x):
    for c in cut_times:
        if -0.05 <= x - c <= 0.15:
            return c
    return x
def W(i, text=None):
    return {'text': text if text is not None else wt(i), 't': round(on(i), 4)}
cards = []
for c in plan['cards']:
    tier = c['tier']
    if tier == 'orange':
        idx = [i for i in range(c['w'][0], c['w'][1] + 1) if i in wmap and wt(i) != '']
        texts = c['text'].split(' ') if c.get('text') else [wt(i) for i in idx]
        ws = [{'text': x, 't': round(on(idx[min(k, len(idx) - 1)]), 4)} for k, x in enumerate(texts)]
        cards.append({'tier': 'orange', 'words': ws, '_first': idx[0], '_last': idx[-1], 'entry': c.get('entry', 'auto'), 'gaps': c.get('gaps', 'auto')})
    elif tier == 'white':
        lines = []
        for li, (a, b) in enumerate(c['lines']):
            idx = [i for i in range(a, b + 1) if i in wmap]
            texts = c['text'][li].split(' ') if c.get('text') else [wt(i).upper() for i in idx]
            lines.append([{'text': x, 't': round(on(idx[min(k, len(idx) - 1)]), 4)} for k, x in enumerate(texts)])
        card = {'tier': 'white', 'lines': lines, '_first': c['lines'][0][0], '_last': c['lines'][-1][1], '_l2': c['lines'][1][0] if len(c['lines']) > 1 else None,
                'entry': c.get('entry', 'cut'), 'line2_entry': c.get('line2_entry', 'cut'), 'mode': c.get('mode', 'match')}
        for k in ('block_w', 'cap_top', 'track_em', 'center_y'):
            if k in c:
                card[k] = c[k]
        cards.append(card)
    elif tier == 'hook':
        top_idx = list(range(c['top'][0], c['top'][1] + 1))
        tops = c.get('top_text') or [wt(i).upper() for i in top_idx]
        sub_idx = list(range(c['sub'][0], c['sub'][1] + 1))
        cards.append({'tier': 'hook', 'top': [{'text': x, 't': 0.0} for x in tops], 'top_gap': c.get('top_gap', 172),
                      'sub': [W(i) for i in sub_idx], 't_sub': round(max(on(sub_idx[0]) - 0.1, 0.5), 4), '_first': top_idx[0], '_last': sub_idx[-1]})
# onsets
for k, c in enumerate(cards):
    if c['tier'] == 'hook':
        c['t0'] = 0.0
    else:
        c['t0'] = snap(snap_to_cut(on(c['_first'])))
    if c['tier'] == 'white' and len(c['lines']) > 1:
        t2 = on(c['_l2']) - 0.1
        c['t_line2'] = snap(max(t2, c['t0'] + 0.35)) if c.get('mode') != 'equal' else c['t0']
# on a silhouette transition the incoming caption appears on the first full-white frame, not at the cut
NFULL = {'T1': 2, 'T2': 2, 'T3': 1, 'T4': 1}
trE = {segs[seg_of_word[tr['at']]]['t0']: NFULL.get(tr.get('pattern', 'T1'), 2) for tr in plan.get('transitions', [])}
for c in cards:
    for E, nf in trE.items():
        if abs(c['t0'] - E) < 0.02:
            c['t0'] = snap(E - nf * FR); c['_trans'] = True
# entries (orange auto rule), ends
early = plan.get('early_s', 8.0)
for k, c in enumerate(cards):
    if c['tier'] != 'orange' or c['entry'] != 'auto':
        continue
    prev = cards[k - 1] if k else None
    if c.get('_trans'):
        c['entry'] = 'cut'                                 # appears on the white frame of the transition
    elif c['t0'] < early:
        c['entry'] = 'A'                                   # the opening seconds use the dim-hold entry
    elif prev is None or prev['tier'] != 'orange':
        c['entry'] = 'cut'                                 # first orange after a white block cuts on
    else:
        c['entry'] = 'B' if c['t0'] - prev['t0'] > 0.9 else 'cut'
    if c['entry'] in ('A', 'B'):
        c['t0'] = snap(c['t0'] - FR)       # frame 0 of the slide is invisible
for k, c in enumerate(cards):
    nxt = cards[k + 1]['t0'] if k + 1 < len(cards) else total - 3 * FR
    c['t1'] = round(max(nxt, c['t0'] + FR), 5)
# ---------------- B&W moment ----------------
bw = []
if plan.get('bw'):
    a, b = plan['bw']
    bw = [[segs[seg_of_word[a]]['t0'], snap(wmap[b][1] + 0.05)]]
# ---------------- transitions ----------------
trans = [{'segment': seg_of_word[tr['at']], 'pattern': tr.get('pattern', 'T1')} for tr in plan.get('transitions', [])]
PATLEN = {'T1': 7, 'T2': 7, 'T3': 5, 'T4': 4}
# ---------------- UI ----------------
ui = []
for u in plan.get('ui', []):
    e = dict(u)
    e['t0'] = round(on(u['at']) - u.get('lead', 0.05), 3)
    e['t1'] = round(wmap[u['until']][1] + u.get('tail', 0.3), 3)
    if 'items' in u:
        e['items'] = [{**it, 't': round(on(it['at']), 3)} for it in u['items']]
    for side in ('left', 'right'):
        if f'{side}_at' in u:
            e[f'{side}_t'] = round(on(u[f'{side}_at']), 3); e.pop(f'{side}_at')
    for kk in ('at', 'until'):
        e.pop(kk, None)
    ui.append(e)
# ---------------- SFX ----------------
sfx = []
if plan.get('sfx', 'auto') == 'auto':
    lows = []
    if bw:
        lows.append({'type': 'hit', 't': bw[0][0] + FR, 'peak_db': -1.5})
    alt = ['boom', 'boom_c', 'hit']; nb = 0
    for c in cards:
        if c['tier'] != 'white':
            continue
        cand = []
        if c.get('entry') == 'slide':
            cand.append(c['t0'] - 0.12)
        if c.get('line2_entry') == 'slide' and 't_line2' in c:
            cand.append(c['t_line2'] - 0.10)
        for x in cand:
            if x < total * plan.get('sfx_until', 0.6):
                kind = alt[nb % 3]; nb += 1
                lows.append({'type': kind, 't': x if kind != 'hit' else x + 0.02, 'peak_db': {'boom': -2, 'boom_c': -4, 'hit': -1.5}[kind]})
    lows.sort(key=lambda s: s['t'])
    kept = []
    for s in lows:
        if not kept or s['t'] - kept[-1]['t'] >= plan.get('sfx_min_gap', 5.0) or s['type'] == 'hit':
            kept.append(s)
    sfx += kept
    for ti, tr in enumerate(trans):
        if ti == 0:
            continue                                   # the reference's first flash has no SFX
        E = segs[tr['segment']]['t0']; k = PATLEN.get(tr['pattern'], 7)
        sfx.append({'type': 'glitch', 't': E - k * FR + 0.05, 'peak_db': -6, 'seed': 10 + ti})
    hook = [c for c in cards if c['tier'] == 'hook']
    if hook:
        sfx.append({'type': 'glitch', 't': hook[0]['t_sub'], 'peak_db': -8, 'seed': 91})
        firstw = [c for c in cards if c['tier'] == 'white' and 't_line2' in c]
        if firstw and firstw[0]['t0'] < 4.0:
            sfx.append({'type': 'glitch', 't': firstw[0]['t_line2'] - 0.18, 'peak_db': -8, 'seed': 92})
    pops = [c for c in cards if c['tier'] == 'white' and c.get('entry', 'cut') == 'cut' and 0.62 * total <= c['t0'] <= 0.86 * total]
    for j, c in enumerate(pops):
        if j % 2 == 0:
            sfx.append({'type': 'tick2', 't': c['t0'] - 0.08, 'peak_db': -7})
else:
    for s in plan.get('sfx', []):
        e = dict(s); e['t'] = round(on(s['at']) + s.get('offset', 0), 3); e.pop('at'); sfx.append(e)
for c in cards:
    for kk in ('_first', '_last', '_l2', '_trans'):
        c.pop(kk, None)
json.dump({'captions': cards, 'ui': ui, 'sfx': sorted(sfx, key=lambda s: s['t']), 'bw': bw, 'transitions_plan': trans, 'duration': round(total, 4),
           'segments': [{'t0': s['t0'], 't1': s['t1'], 'in': s['in'], 'out': s['out'], 'first': s['words'][0], 'last': s['words'][-1]} for s in segs],
           'music_build': round(0.2 + 4 * max(1, round((total * 0.3 - 0.2) / 4)), 2)},
          open(f'{out}/timeline.json', 'w'), ensure_ascii=False, indent=1)
json.dump(trans, open(f'{out}/transitions_plan.json', 'w'))
print(f'{len(segs)} segments, {total:.2f}s, {len(cards)} cards, {len(sfx)} sfx, {len(trans)} transitions, bw {bw}')
