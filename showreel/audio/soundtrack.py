"""Synthesises the reel's soundtrack from scratch — no samples.

120 BPM, 15 s, 48 kHz stereo. Every hit is placed on the same timeline as the
picture in ../index.html (cuts, typewriter ticks, odometer rolls, the CRT
power-off, the logo impact).

    python3 soundtrack.py   → soundtrack.wav
"""
import os
import wave

import numpy as np

SR = 48000
DUR = 15.0
N = int(SR * DUR)
BEAT = 0.5
rng = np.random.default_rng(26)
t_all = np.arange(N) / SR


def buf():
    return np.zeros((N, 2))


def place(bus, sig, t0, gain=1.0, pan=0.0):
    """Mix a mono or stereo signal into bus at time t0 (s), equal-power pan."""
    i0 = int(round(t0 * SR))
    if i0 >= N:
        return
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4
        sig = np.stack([sig * np.cos(a), sig * np.sin(a)], 1) * np.sqrt(2)
    n = min(len(sig), N - i0)
    if i0 < 0:
        sig, n, i0 = sig[-i0:], min(len(sig) + i0, N), 0
    bus[i0:i0 + n] += sig[:n] * gain


def env_exp(n, k):
    return np.exp(-np.arange(n) / SR * k)


def onepole_lp(x, fc):
    """Time-varying one-pole low-pass. fc: scalar or per-sample array (Hz)."""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape[:1])
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    s = np.zeros(x.shape[1:]) if x.ndim > 1 else 0.0
    for i in range(len(x)):
        s = s + a[i] * (x[i] - s)
        y[i] = s
    return y


def hp(x, fc):
    return x - onepole_lp(x, fc)


def noise(sec):
    return rng.standard_normal(int(sec * SR))


# ── instruments ──────────────────────────────────────────────────────────────
def kick(sec=0.5, f0=48, f1=160, punch=30):
    n = int(sec * SR); t = np.arange(n) / SR
    f = f0 + f1 * np.exp(-t * punch)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 6.5)
    click = np.exp(-t * 900) * 0.6
    return np.tanh((body + click) * 1.6)


def clap(sec=0.35):
    n = int(sec * SR); t = np.arange(n) / SR
    nz = hp(noise(sec), 900)
    e = np.zeros(n)
    for d in (0, 0.011, 0.022):
        e += np.where(t >= d, np.exp(-(t - d) * 90), 0)
    e += np.exp(-t * 16) * 0.5
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30) * 0.5
    return norm(norm(nz * e) * 0.8 + tone)


def hat(open_=False):
    sec = 0.25 if open_ else 0.06
    t = np.arange(int(sec * SR)) / SR
    return norm(hp(hp(noise(sec), 6000), 6000) * np.exp(-t * (14 if open_ else 70)))


def tick(freq=3200, sec=0.03):
    t = np.arange(int(sec * SR)) / SR
    return norm(np.sin(2 * np.pi * freq * t) * np.exp(-t * 180) + norm(hp(noise(sec), 4000)) * np.exp(-t * 300) * 0.4)


def bell(freq, sec=2.0, idx=2.2):
    t = np.arange(int(sec * SR)) / SR
    mod = np.sin(2 * np.pi * freq * 1.4 * t) * idx * np.exp(-t * 3)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * 2.2)


def pluck(freq, sec=0.35, bright=4000):
    t = np.arange(int(sec * SR)) / SR
    saw = 2 * ((t * freq) % 1) - 1
    sq = np.sign(np.sin(2 * np.pi * freq * 1.003 * t))
    x = (saw * 0.6 + sq * 0.4) * np.exp(-t * 11)
    return norm(onepole_lp(x, bright * np.exp(-t * 9) + 300))


def supersaw(freq, sec, voices=7, detune=0.012):
    t = np.arange(int(sec * SR)) / SR
    out = np.zeros((len(t), 2))
    for v in range(voices):
        d = 1 + detune * (v - (voices - 1) / 2) / ((voices - 1) / 2)
        ph = rng.random()
        s = 2 * ((t * freq * d + ph) % 1) - 1
        p = (v / (voices - 1)) * 2 - 1
        out[:, 0] += s * (1 - p) / 2
        out[:, 1] += s * (1 + p) / 2
    return out / voices


def boom(sec=2.5, f0=34, f1=90):
    t = np.arange(int(sec * SR)) / SR
    f = f0 + f1 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    crack = norm(onepole_lp(noise(sec), 2500)) * np.exp(-t * 7) * 0.8
    return np.tanh((sub + crack) * 1.4)


def riser(sec, f0=200, f1=3000, tone=True):
    n = int(sec * SR); t = np.arange(n) / SR; x = t / sec
    nz = noise(sec)
    y = norm(onepole_lp(nz, 300 + (x ** 2) * 9000)) * (x ** 2.2)
    if tone:
        f = f0 * (f1 / f0) ** (x ** 1.5)
        y += np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 * x ** 2
    return norm(y)


def whoosh(sec=0.45):
    n = int(sec * SR); t = np.arange(n) / SR; x = t / sec
    e = np.sin(np.pi * x) ** 2
    return norm(onepole_lp(noise(sec), 400 + 6000 * e) * e)


def norm(x, peak=1.0):
    return x * (peak / (np.max(np.abs(x)) + 1e-9))


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


# ── arrangement ──────────────────────────────────────────────────────────────
drums, bass, pads, keys, fx = buf(), buf(), buf(), buf(), buf()

KICKS = [0.0, 0.5, 1.0, 1.5] + [2 + i * BEAT for i in range(12)] + [8.0, 9.0] \
    + [10 + i * BEAT for i in range(4)] + [12.0, 12.25, 12.5, 12.75, 13.0]
KICKS = sorted(set(KICKS))
for k in KICKS:
    soft = k < 2
    place(drums, kick(f1=110 if soft else 160) * (0.55 if soft else 1.0), k)

for b in (2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5):
    place(drums, clap(), b, 0.55, pan=0.05)
for i in range(64):                          # hats 2–10 s and 10–12 s
    t = 2 + i * 0.125
    if 8 <= t < 10 and i % 2:                 # half-time section
        continue
    open_ = (i % 4 == 2)
    place(drums, hat(open_), t, (0.16 if open_ else 0.11) * (1.2 if i % 2 == 0 else 0.8), pan=0.35 * (1 if i % 2 else -1))
for i in range(16):
    place(drums, hat(i % 4 == 2), 10 + i * 0.125, 0.13, pan=0.3 * (1 if i % 2 else -1))

# chords (root midi, voicing)
PROG = [(0, [57, 60, 64, 71]),   # Am(add9-ish)
        (2, [53, 57, 60, 64]),   # Fmaj7
        (4, [48, 55, 60, 64]),   # C
        (6, [55, 59, 62, 67]),   # G
        (8, [57, 60, 64, 67]),   # Am7
        (10, [53, 57, 60, 65]),  # F
        (12, [52, 56, 59, 64]),  # E (dominant — tension into the logo)
        (13.5, [45, 57, 60, 64, 71, 76])]  # Am9 — resolve
ROOTS = {0: 33, 2: 29, 4: 36, 6: 31, 8: 33, 10: 29, 12: 28, 13.5: 33}

for i, (t0, notes) in enumerate(PROG):
    t1 = PROG[i + 1][0] if i + 1 < len(PROG) else DUR
    sec = t1 - t0 + (1.6 if t0 < 13.5 else 0)
    pad = sum(supersaw(midi(m), sec) for m in notes) / len(notes)
    n = len(pad); tt = np.arange(n) / SR
    fade = np.minimum(1, tt / 0.08) * np.minimum(1, np.maximum(0, (sec - tt) / 1.4))
    cut = 900 + 1800 * (0.5 + 0.5 * np.sin(tt * 1.3)) if t0 < 13.5 else 600 + 5000 * np.exp(-tt * 1.5)
    pad = norm(onepole_lp(pad, cut)) * fade[:, None]
    gain = 0.2 if t0 >= 2 else 0.16
    if t0 == 0:
        pad *= np.minimum(1, tt / 1.8)[:, None]
    place(pads, pad, t0, gain if t0 < 13.5 else 0.34)

for t0, root in ROOTS.items():               # bass: rolling 8ths, sub + grit
    if t0 < 2:
        continue
    t1 = min(DUR, t0 + 2) if t0 < 13.5 else DUR
    step = 0.25
    k = 0
    while t0 + k * step < t1 - 1e-6 and t0 + k * step < 13.25:
        ts = t0 + k * step
        if 8 <= ts < 10 and k % 2:
            k += 1; continue
        m = root + (12 if k % 4 == 3 else 0)
        f = midi(m); sec = 0.24; tt = np.arange(int(sec * SR)) / SR
        s = np.sin(2 * np.pi * f * tt) + 0.35 * np.tanh(3 * np.sin(2 * np.pi * f * 2 * tt))
        place(bass, s * np.exp(-tt * 5) * np.minimum(1, tt / 0.004), ts, 0.42)
        k += 1
tt = np.arange(int(1.5 * SR)) / SR           # final sub on the resolve
place(bass, np.sin(2 * np.pi * midi(33) * tt) * np.exp(-tt * 1.4), 13.5, 0.55)

# arps (scene B/C and F): 16ths over chord tones
for t0, notes in PROG[1:3] + PROG[5:6]:
    for i in range(16):
        m = notes[[0, 1, 2, 3, 2, 1][i % 6]] + 12 * (i % 3 == 0)
        place(keys, pluck(midi(m + 12), bright=2500 + 2500 * (i % 4 == 0)), t0 + i * 0.125, 0.13, pan=0.5 * np.sin(i * 1.3))
for i, m in enumerate([69, 72, 76, 79, 81, 84, 88]):      # sparkle arp scene D
    place(keys, pluck(midi(m), sec=0.6, bright=6000), 6.0 + i * 0.25, 0.1, pan=-0.6 + i * 0.2)

# ── sound design, locked to picture ──────────────────────────────────────────
msg_len = len('HELLO. THIS IS A SHOWREEL.')
for i in range(msg_len):                     # typewriter in (0.12–0.70) and delete (1.20–1.45)
    place(fx, tick(2600 + 400 * (i % 3), 0.025), 0.12 + (i + 1) / msg_len * 0.58, 0.18, pan=-0.3 + 0.6 * i / msg_len)
for i in range(msg_len):
    place(fx, tick(1800, 0.02), 1.2 + i / msg_len * 0.25, 0.12)
place(fx, bell(midi(81), 2.0), 0.5, 0.18, pan=-0.2)          # heartbeat ping
place(fx, bell(midi(88), 1.6, 3.5), 1.0, 0.16, pan=0.25)     # starburst
place(fx, riser(0.9, 150, 1800), 1.1, 0.5)
place(fx, whoosh(0.5), 1.5, 0.5)
for b in (2.0, 2.5, 3.0, 3.5):
    place(fx, whoosh(0.25), b - 0.02, 0.35, pan=0.4 * np.sin(b * 7))
place(fx, riser(0.28, 400, 5000), 3.74, 0.6)                 # zoom through the period
for w in (4.0, 4.5, 5.0, 5.5):                               # grid waves: tick cascades
    for j in range(8):
        place(fx, tick(1600 + j * 220, 0.02), w + j * 0.035, 0.12 * (1 - j / 10), pan=-0.7 + j * 0.2)
place(fx, riser(0.4, 300, 4000), 7.6, 0.7)                   # warp
place(fx, boom(2.5), 8.0, 0.8)
for i in range(6):                                           # "logic." boxes snapping
    place(fx, tick(2200 + i * 150, 0.03), 9.0 + i * 0.045 + 0.08, 0.2, pan=-0.5 + i * 0.2)
place(fx, clap(), 9.0, 0.7)
place(fx, whoosh(0.55), 9.5, 0.7)                             # liquid wipe
for i in range(40):                                          # odometer: decelerating ticks
    x = i / 40
    place(fx, tick(3000, 0.015), 10.05 + (1 - (1 - x) ** 3) * 1.25, 0.09, pan=-0.4)
place(fx, riser(0.35, 500, 6000), 11.65, 0.6)
place(fx, whoosh(0.35), 11.72, 0.8)                            # slice-out
for c in (12.0, 12.25, 12.5, 12.75, 13.0):                   # montage cuts: crushed hits
    hit = boom(0.24, 50, 140) * 0.6 + norm(hp(noise(0.24), 2000)) * np.exp(-np.arange(int(0.24 * SR)) / SR * 25) * 0.4
    hit = np.round(hit * 12) / 12                              # bitcrush
    place(fx, hit, c, 0.55, pan=0.3 * np.sin(c * 11))
place(fx, riser(1.25, 120, 2400), 12.0, 0.55)
t = np.arange(int(0.25 * SR)) / SR                           # CRT power-off: falling whine
f = 3000 * (40 / 3000) ** (t / 0.25)
place(fx, np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - t / 0.25) * 0.5, 13.25, 0.5)
place(fx, boom(3.5, 30, 110), 13.5, 1.1)                      # logo impact
place(fx, whoosh(0.6), 13.45, 0.6)
for i in range(18):                                          # shards glitter
    place(fx, bell(midi(84 + [0, 3, 7, 10, 12][i % 5]), 0.9, 1.5), 13.5 + rng.random() * 0.9, 0.035, pan=rng.uniform(-0.9, 0.9))
place(fx, bell(midi(69), 3.0, 1.2), 13.95, 0.2)               # "motion designer"
for i in range(len('SHOWREEL 2026 · 900 FRAMES · 0 KEYFRAMES · 100% CODE')):
    if i % 2 == 0:
        place(fx, tick(3400, 0.012), 14.12 + i / 51 * 0.43, 0.06)

# ── mix ──────────────────────────────────────────────────────────────────────
sc = np.ones(N)                               # sidechain from kicks
for k in KICKS:
    if k < 2:
        continue
    i0 = int(k * SR); n = min(N - i0, int(0.4 * SR)); tt = np.arange(n) / SR
    sc[i0:i0 + n] = np.minimum(sc[i0:i0 + n], 1 - 0.7 * np.exp(-tt * 9))
bass *= sc[:, None]
pads *= (0.35 + 0.65 * sc)[:, None]

# duck everything in the breath before the logo impact
gap = np.ones(N)
i0, i1 = int(13.32 * SR), int(13.5 * SR)
gap[i0:i1] = np.linspace(1, 0.05, i1 - i0)

for _n, _b in (("drums", drums), ("bass", bass), ("pads", pads), ("keys", keys), ("fx", fx)):
    if os.environ.get("DEBUG"): print(_n, "rms %.3f peak %.3f" % (np.sqrt(np.mean(_b ** 2)), np.max(np.abs(_b))))
dry = drums * 0.62 + bass * 0.9 + pads * 1.8 + keys * 1.5 + fx * 0.7
dry *= gap[:, None]
dry[int(13.5 * SR):] = (bass * 0.9 + pads * 1.8 + keys * 1.5 + fx * 0.7)[int(13.5 * SR):]

# plate reverb via FFT convolution (stereo-decorrelated exponential noise IR)
ir_len = int(2.2 * SR); ti = np.arange(ir_len) / SR
ir = rng.standard_normal((ir_len, 2)) * np.exp(-ti * 3.1)[:, None]
ir = onepole_lp(ir, 5000)
send = keys * 0.8 + fx * 0.5 + pads * 0.3 + drums * 0.08
L = 1 << int(np.ceil(np.log2(N + ir_len)))
wet = np.stack([np.fft.irfft(np.fft.rfft(send[:, c], L) * np.fft.rfft(ir[:, c], L), L)[:N] for c in range(2)], 1)
wet /= np.max(np.abs(wet)) + 1e-9
mix = dry + wet * 0.22

tail = np.minimum(1, (DUR - t_all) / 0.6)     # fade the last 0.6 s
mix *= tail[:, None]
mix /= np.max(np.abs(mix)) / 1.6
mix = np.tanh(mix)                            # gentle soft-clip master
mix /= np.max(np.abs(mix)) / 0.89

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundtrack.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('→', out)
