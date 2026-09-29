// Generates assets/sounds/splash_intro.wav, the sound under the splash
// animation. Synthesised from scratch (no samples), timed to the splash:
//   0.0–0.9s  soft airy swell as the figure appears
//   0.5–2.0s  swirling whoosh (panning L→R) as the ribbon spirals in
//   ~2.05s    warm bell chord as the ribbon locks into the ring
//   2.6–3.4s  light sparkles as MINDCARE settles
// Run: node tool/generate_splash_sound.js
const fs = require('fs');
const path = require('path');

const SR = 44100;
const DUR = 5.0;
const N = Math.floor(SR * DUR);
const L = new Float32Array(N);
const R = new Float32Array(N);

let seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1;
const smooth = (e0, e1, x) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};
const add = (i, v, pan) => {
  // Equal-power pan, pan in [-1, 1].
  const a = ((pan + 1) * Math.PI) / 4;
  L[i] += v * Math.cos(a);
  R[i] += v * Math.sin(a);
};

// Band-pass biquad whose centre frequency can change per sample.
function bandpass() {
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  return (x, f, q) => {
    const w = (2 * Math.PI * f) / SR;
    const alpha = Math.sin(w) / (2 * q);
    const b0 = alpha, b2 = -alpha, a0 = 1 + alpha, a1 = -2 * Math.cos(w), a2 = 1 - alpha;
    const y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0;
    x2 = x1; x1 = x; y2 = y1; y1 = y;
    return y;
  };
}

// 1. Airy swell as the figure appears.
{
  const bp = bandpass();
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    if (t > 1.3) break;
    const env = smooth(0, 0.6, t) * (1 - smooth(0.6, 1.3, t));
    const f = 600 + 1400 * smooth(0, 1.0, t);
    add(i, bp(rand(), f, 0.9) * env * 0.35, -0.2);
  }
}

// 2. Ribbon whoosh: rising band-pass sweep, panning left to right.
{
  const bp = bandpass();
  const bp2 = bandpass();
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    if (t < 0.4) continue;
    if (t > 2.3) break;
    const env = smooth(0.4, 1.45, t) * (1 - smooth(1.45, 2.25, t));
    const f = 280 + 2600 * smooth(0.4, 1.9, t);
    const n = rand();
    const v = bp(n, f, 1.4) * 0.55 + bp2(n, f * 1.9, 2.2) * 0.25;
    const pan = -0.7 + 1.4 * smooth(0.5, 2.0, t);
    add(i, v * env * 0.9, pan);
  }
}

// Soft rising glide under the whoosh, for a bit of "magic".
for (let i = 0; i < N; i++) {
  const t = i / SR;
  if (t < 0.5) continue;
  if (t > 2.2) break;
  const env = smooth(0.5, 1.6, t) * (1 - smooth(1.8, 2.2, t));
  const f = 220 * Math.pow(2, smooth(0.5, 2.05, t));
  const ph = 2 * Math.PI * (220 * (t - 0.5) + (f - 220) * 0.35 * (t - 0.5));
  add(i, Math.sin(ph) * env * 0.035, 0);
}

// 3. Warm bell chord when the ring locks in (C major add 9, strummed).
function bell(t0, freq, amp, pan, decay = 1.3) {
  const start = Math.floor(t0 * SR);
  for (let i = start; i < N; i++) {
    const t = (i - start) / SR;
    const attack = smooth(0, 0.006, t);
    const body = Math.sin(2 * Math.PI * freq * t) * Math.exp(-t / decay);
    const partial = Math.sin(2 * Math.PI * freq * 2.76 * t) * Math.exp(-t / (decay * 0.25)) * 0.35;
    const shimmer = Math.sin(2 * Math.PI * freq * 5.4 * t) * Math.exp(-t / (decay * 0.1)) * 0.12;
    add(i, (body + partial + shimmer) * attack * amp, pan);
  }
}
[
  [523.25, -0.35],
  [659.25, -0.1],
  [783.99, 0.15],
  [1174.66, 0.4],
].forEach(([f, pan], k) => bell(2.05 + k * 0.035, f, 0.16, pan));

// Low pad under the chord.
for (let i = Math.floor(1.9 * SR); i < N; i++) {
  const t = i / SR;
  const env = smooth(1.9, 2.4, t) * (1 - smooth(3.4, 5.0, t));
  const v = Math.sin(2 * Math.PI * 130.81 * t) * 0.6 + Math.sin(2 * Math.PI * 196.0 * t) * 0.4;
  add(i, v * env * 0.07, 0);
}

// 4. Sparkles as the wordmark settles (C major pentatonic, high).
const sparkleNotes = [1046.5, 1174.66, 1318.51, 1567.98, 1760.0, 2093.0];
for (let k = 0; k < 8; k++) {
  const t0 = 2.55 + k * 0.1 + (rand() + 1) * 0.02;
  const f = sparkleNotes[Math.floor(((rand() + 1) / 2) * sparkleNotes.length) % sparkleNotes.length];
  bell(t0, f, 0.035, rand() * 0.8, 0.22);
}

// Simple stereo reverb (Schroeder: 4 combs + 2 all-passes per channel).
function reverb(input, offset) {
  const out = new Float32Array(N);
  const combs = [1116, 1188, 1277, 1356].map((d) => ({ d: d + offset, buf: new Float32Array(d + offset), i: 0 }));
  for (let n = 0; n < N; n++) {
    let s = 0;
    for (const c of combs) {
      const y = c.buf[c.i];
      c.buf[c.i] = input[n] + y * 0.8;
      c.i = (c.i + 1) % c.d;
      s += y;
    }
    out[n] = s / combs.length;
  }
  for (const d of [556 + offset, 441 + offset]) {
    const buf = new Float32Array(d);
    let i = 0;
    for (let n = 0; n < N; n++) {
      const b = buf[i];
      const y = -out[n] + b;
      buf[i] = out[n] + b * 0.5;
      i = (i + 1) % d;
      out[n] = y;
    }
  }
  return out;
}
const wetL = reverb(L, 0);
const wetR = reverb(R, 23);

// Mix, fade out, normalise, write 16-bit stereo WAV.
let peak = 0;
const mix = new Float32Array(N * 2);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  const fade = 1 - smooth(DUR - 0.9, DUR, t);
  mix[i * 2] = (L[i] * 0.8 + wetL[i] * 0.35) * fade;
  mix[i * 2 + 1] = (R[i] * 0.8 + wetR[i] * 0.35) * fade;
  peak = Math.max(peak, Math.abs(mix[i * 2]), Math.abs(mix[i * 2 + 1]));
}
const gain = 0.7 / peak;

const data = Buffer.alloc(N * 4);
for (let i = 0; i < N * 2; i++) {
  data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, mix[i] * gain)) * 32767), i * 2);
}
const header = Buffer.alloc(44);
header.write('RIFF', 0);
header.writeUInt32LE(36 + data.length, 4);
header.write('WAVE', 8);
header.write('fmt ', 12);
header.writeUInt32LE(16, 16);
header.writeUInt16LE(1, 20);
header.writeUInt16LE(2, 22);
header.writeUInt32LE(SR, 24);
header.writeUInt32LE(SR * 4, 28);
header.writeUInt16LE(4, 32);
header.writeUInt16LE(16, 34);
header.write('data', 36);
header.writeUInt32LE(data.length, 40);

const out = path.join(__dirname, '..', 'assets', 'sounds', 'splash_intro.wav');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, Buffer.concat([header, data]));
console.log(`wrote ${out} (${((44 + data.length) / 1024).toFixed(0)} KB)`);
