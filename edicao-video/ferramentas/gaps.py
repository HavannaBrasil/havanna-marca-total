"""Stylistic wide gaps for orange cards, as measured in the reference: in ~55% of multi-word cards ONE gap is widened
to 3-8 spaces (115-300 px at 1080), the gap closest to x~570 px (slightly right of centre), line kept centred.
It is not tied to the hands or the mic (78% of the widened area sits on the dark shirt).
usage: gaps.py timeline.json"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
tl = json.load(open(sys.argv[1]))
UNIT = R.ORANGE['gap_unit']; KS = [4, 6, 3, 5, 7, 4, 8, 5]
n_multi = n_wide = 0
for c in tl['captions']:
    if c['tier'] != 'orange':
        continue
    words = [w['text'] for w in c['words']]
    if isinstance(c.get('gaps'), list) and len(c['gaps']) == len(words) - 1:
        continue
    gaps = [1] * (len(words) - 1)
    if len(words) >= 2:
        n_multi += 1
        if n_wide < round(0.55 * n_multi + 0.2):          # keep the running share near 55%
            rend = [R.render_text_mask(w, R.ORANGE['font'], R.ORANGE['size'], R.ORANGE['track']) for w in words]
            widths = [r - l + 1 for (_, l, r, _) in rend]
            k = KS[n_wide % len(KS)]
            best = None
            for gi in range(len(gaps)):
                for kk in range(k, 2, -1):
                    gs = [1] * len(gaps); gs[gi] = kk
                    total = sum(widths) + sum(R.ORANGE['gap_base'] + UNIT * g for g in gs)
                    if total <= R.ORANGE['max_w']:
                        break
                else:
                    continue
                left = (1080 - total) / 2 + sum(widths[:gi + 1]) + sum(R.ORANGE['gap_base'] + UNIT * g for g in gs[:gi])
                centre = left + (R.ORANGE['gap_base'] + UNIT * kk) / 2
                if best is None or abs(centre - 570) < best[0]:
                    best = (abs(centre - 570), gs)
            if best:
                gaps = best[1]; n_wide += 1
    c['gaps'] = gaps
json.dump(tl, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
print(f'wide gaps on {n_wide} of {n_multi} multi-word orange cards')
