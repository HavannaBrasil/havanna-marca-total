"""Original audio synthesized from scratch (no samples, no third-party music), calibrated on the reference study.

pad_minor(duration): ambient worship-style bed. Minor key i - VII - VI - V (Gm | F | Eb(add9) | Dsus4-D),
    one chord every 4.0 s starting at 0.2 s, G3/G4 pedal held over every chord, sparse intro (pad + a decaying
    bass note every 2 s) until `build_at`, then sustained root bass and a fuller pad (+5 dB), soft pluck notes
    at each chord change, stereo pad with mono bass, hard stop at the end (60 ms micro-fade).
boom(), hit(), boom_c(), glitch(): the four SFX families measured in the reference.
All outputs: float32 stereo arrays shaped (2, n) at 48 kHz.
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
_rng = np.random.default_rng(11)

def _f(x, kind, fc, order=2):
    wn = np.array(fc) / (SR / 2)
    return sosfilt(butter(order, wn, kind, output='sos'), x, axis=-1)

def _ir(seconds=3.0, decay=2.4, seed=3):
    r = np.random.default_rng(seed)
    n = int(seconds * SR); t = np.arange(n) / SR
    ir = r.standard_normal((2, n)) * np.exp(-t * decay)[None]
    ir = _f(ir, 'low', 5500)
    ir[:, :int(.015 * SR)] *= np.linspace(0, 1, int(.015 * SR))[None]
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))

def _hz(semi, ref=196.0):
    return ref * 2 ** (semi / 12)

def _voice(freq, tt, detune=0.0035, harmonics=6, roll=1.7, phase=0.0):
    out = np.zeros((2, len(tt)))
    for ch, dt in ((0, -detune), (1, detune)):
        lfo = 1 + 0.0010 * np.sin(2 * np.pi * (0.11 + 0.07 * ch) * tt + phase)
        for k in range(1, harmonics + 1):
            out[ch] += np.sin(2 * np.pi * freq * k * (1 + dt) * lfo * tt + phase * k) / k ** roll
    return out

CHORDS = [  # semitones relative to G3 (196 Hz); bass is the root two octaves under the chord name
    {'pad': [0, 3, 7], 'bass': -12},            # Gm
    {'pad': [-2, 2, 5], 'bass': -14},           # F
    {'pad': [-4, 0, 3, 10], 'bass': -16},       # Eb(add9)
    {'pad': [-5, 0, 2], 'pad2': [-5, -1, 2], 'bass': -17},  # Dsus4 -> D
]

def pad_minor(duration, start=0.2, chord_s=4.0, build_at=16.2, key_shift=0):
    n = int(duration * SR); t = np.arange(n) / SR
    pad = np.zeros((2, n)); bass = np.zeros((2, n)); pluck = np.zeros((2, n))
    ref = 196.0 * 2 ** (key_shift / 12)
    k = 0
    while True:
        c0 = start + k * chord_s
        if c0 >= duration:
            break
        ch = CHORDS[k % 4]
        a, b = int(c0 * SR), min(n, int((c0 + chord_s + 2.5) * SR))
        tt = t[a:b] - c0
        env = np.minimum(1, tt / 1.2) * np.clip((chord_s + 2.5 - tt) / 2.5, 0, 1)
        env = np.clip(env, 0, None) ** 1.4
        for si, semi in enumerate(ch['pad']):
            v = _voice(_hz(semi, ref), tt, phase=si * 1.3 + k)
            if 'pad2' in ch:  # sus4 resolves to the major third halfway
                v2 = _voice(_hz(ch['pad2'][si], ref), tt, phase=si * 1.3 + k)
                xf = np.clip((tt - chord_s / 2) / 0.4, 0, 1)
                v = v * (1 - xf) + v2 * xf
            pad[:, a:b] += v * env * 0.14
        # G3/G4 reinforced only on the chords that contain G (i, VI, sus4), as measured
        for semi in ((0, 12) if (k % 4) in (0, 2, 3) else ()):
            pad[:, a:b] += _voice(_hz(semi, ref), tt, detune=0.002, harmonics=4, roll=2.2, phase=0.7 + semi) * env * (0.10 if semi == 0 else 0.06)
        # bass: decaying pulses every 2 s before the build, sustained after
        fb = _hz(ch['bass'], ref)
        if c0 < build_at - 0.05:
            for p in (0.95, 2.95):
                s0 = c0 + p
                if s0 >= duration:
                    continue
                i0 = int(s0 * SR); i1 = min(n, i0 + int(2.2 * SR)); tb = t[i0:i1] - s0
                e = np.minimum(1, tb / 0.02) * np.exp(-tb * 1.6)
                wv = np.sin(2 * np.pi * fb * tb) + 0.25 * np.sin(2 * np.pi * 2 * fb * tb)
                bass[:, i0:i1] += wv * e * 0.32
        else:
            eb = np.minimum(1, tt / 0.25) * np.clip((chord_s + 0.3 - tt) / 0.3, 0, 1)
            wv = np.sin(2 * np.pi * fb * tt) + 0.2 * np.sin(2 * np.pi * 2 * fb * tt)
            bass[:, a:b] += wv * eb * 0.30
        # soft pluck (piano-like) on the chord change: top chord tone an octave up
        top = _hz(ch['pad'][-1] + 12, ref)
        i1 = min(n, a + int(2.5 * SR)); tp = t[a:i1] - c0
        e = np.minimum(1, tp / 0.006) * np.exp(-tp * 2.2)
        pl = sum(np.sin(2 * np.pi * top * h * tp) * (0.5 ** (h - 1)) for h in (1, 2, 3))
        pluck[0, a:i1] += pl * e * 0.07; pluck[1, a:i1] += pl * e * 0.05
        k += 1
    pad = _f(pad, 'low', 1600); pad = _f(pad, 'high', 140)
    build = np.clip((t - build_at) / 0.5, 0, 1)
    pad *= (0.50 + 0.50 * build)[None]          # about +6 dB after the build (intro sits lower)
    bass = _f(bass, 'low', 180)
    bass[1] = bass[0]                           # mono bass
    ir = _ir()
    wet = np.stack([fftconvolve(pad[c] + pluck[c], ir[c])[:n] for c in (0, 1)])
    mix = 0.45 * (pad + pluck) + 0.85 * wet + bass
    lead = np.clip((t - start) / 0.15, 0, 1)
    mix *= lead[None]
    tail = int(0.06 * SR); mix[:, -tail:] *= np.linspace(1, 0, tail)[None]
    return (mix / (np.max(np.abs(mix)) + 1e-9) * 0.9).astype(np.float32)

def boom(dur=0.38, f0=112):
    """Boom A: soft-attack low whump, energy 30-400 Hz, peak ~115 Hz, slight stereo."""
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.clip(t / 0.15, 0, 1) ** 1.5 * np.exp(-np.clip(t - 0.15, 0, None) * 12)
    f = f0 * (1.25 - 0.25 * np.clip(t / dur, 0, 1))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(f * 0.5) / SR)
    noise = _f(_rng.standard_normal((2, n)), 'low', 400) * 0.35
    x = body[None] * env + noise * env
    x[1] = x[1] * 0.85 + x[0] * 0.15
    x = _f(x, 'low', 420)
    return (x / (np.max(np.abs(x)) + 1e-9) * 0.95).astype(np.float32)

def hit(dur=0.22, f0=34):
    """Hit B: impact with a sub body around 34 Hz (0.18 s), a broadband 2-8 kHz attack and a faint 0.12 s pre-rise."""
    pre = int(0.12 * SR); n = int(dur * SR) + pre; t = np.arange(n) / SR
    y = np.zeros((2, n))
    tr = t[pre:] - t[pre]
    f = f0 * (1 + 3.0 * np.exp(-tr * 30))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tr * 9)
    click = _f(_rng.standard_normal(len(tr)), 'band', [2000, 8000]) * np.exp(-tr * 60) * 0.55
    sparkle = _f(_rng.standard_normal((2, len(tr))), 'band', [3000, 9000]) * np.exp(-tr * 30) * 0.12
    y[:, pre:] = (body + click)[None] + sparkle
    rise = _f(_rng.standard_normal((2, pre)), 'band', [200, 2500]) * (np.linspace(0, 1, pre) ** 3)[None] * 0.12
    y[:, :pre] += rise
    return (y / (np.max(np.abs(y)) + 1e-9) * 0.95).astype(np.float32), 0.12  # (audio, attack offset seconds)

def boom_c(dur=0.27, f0=124):
    """Boom C: wide, decorrelated low boom (~124 Hz) that pans left to right over ~0.2 s."""
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.clip(t / 0.06, 0, 1) * np.exp(-t * 11)
    l = np.sin(2 * np.pi * f0 * t) * env + 0.3 * np.sin(2 * np.pi * f0 * 1.5 * t) * env * np.exp(-t * 20)
    r = np.sin(2 * np.pi * f0 * 1.013 * t + 1.3) * env + 0.3 * np.sin(2 * np.pi * f0 * 1.52 * t + .4) * env * np.exp(-t * 20)
    pan = np.clip((t - 0.03) / 0.2, 0, 1)
    x = np.stack([l * np.cos(pan * np.pi / 2), r * np.sin(pan * np.pi / 2) + 0.25 * r])
    return (x / (np.max(np.abs(x)) + 1e-9) * 0.9).astype(np.float32)

def tick2(gap=0.087):
    """Double click (two ~3 ms ringing ticks 87 ms apart) used on some big-caption pops."""
    n = int((gap + 0.02) * SR); x = np.zeros((2, n))
    for k, g in ((0, 1.0), (int(gap * SR), 0.85)):
        L = int(0.004 * SR); tt = np.arange(L) / SR
        tk = np.sin(2 * np.pi * 3200 * tt) * np.exp(-tt * 1400) * g
        x[:, k:k + L] += tk[None]
    return (x / (np.max(np.abs(x)) + 1e-9) * 0.9).astype(np.float32)

def glitch(dur=0.15, bursts=5, seed=None):
    """Digital glitch: 4-5 wide-stereo crackle bursts (5-10 ms) over ~150 ms, 250 Hz-12 kHz, last burst strongest."""
    r = np.random.default_rng(seed if seed is not None else 5)
    n = int(dur * SR); x = np.zeros((2, n))
    starts = np.sort(r.uniform(0, dur - 0.012, bursts)); starts[-1] = dur - 0.012
    for i, s in enumerate(starts):
        L = int(r.uniform(0.005, 0.010) * SR); i0 = int(s * SR)
        g = 0.45 + 0.55 * (i + 1) / bursts
        b = r.standard_normal((2, L)) * g
        b = np.sign(b) * np.abs(b) ** 0.6                     # crunchy
        b *= np.hanning(L)[None]
        x[:, i0:i0 + L] += b[:, :max(0, min(L, n - i0))]
    x = _f(x, 'band', [250, 12000])
    return (x / (np.max(np.abs(x)) + 1e-9) * 0.95).astype(np.float32)
