// Offline renderer: serves the composition, renders every frame (with motion blur)
// across parallel headless Chromium pages, then muxes with the soundtrack via ffmpeg.
//
//   node render.mjs                 → out/showreel.mp4
//   node render.mjs --stills 1,3.2  → out/still-1.00.png, out/still-3.20.png
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(path.join(execFileSync('npm', ['root', '-g']).toString().trim(), 'playwright'))); }

const ROOT = path.dirname(new URL(import.meta.url).pathname);
const OUT = path.join(ROOT, 'out');
const FRAMES = path.join(OUT, 'frames');
const FPS = 60, DUR = 15, TOTAL = FPS * DUR;
const args = process.argv.slice(2);
const stillsArg = args.includes('--stills') ? args[args.indexOf('--stills') + 1] : null;
const WORKERS = Math.max(1, Math.min(os.cpus().length, 6));

const MIME = { '.html': 'text/html', '.woff2': 'font/woff2', '.wav': 'audio/wav', '.js': 'text/javascript' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404).end(); return; }
  res.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, r));
const url = `http://127.0.0.1:${server.address().port}/index.html?render`;

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
async function openPage() {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await page.goto(url);
  await page.evaluate(() => window.READY);
  return page;
}
async function grab(page, t) {
  const b64 = await page.evaluate(t => { window.renderFrame(t); return document.getElementById('c').toDataURL('image/png').slice(22); }, t);
  return Buffer.from(b64, 'base64');
}

fs.mkdirSync(OUT, { recursive: true });
if (stillsArg) {
  const page = await openPage();
  for (const t of stillsArg.split(',').map(Number)) {
    const f = path.join(OUT, `still-${t.toFixed(2)}.png`);
    fs.writeFileSync(f, await grab(page, t)); console.log(f);
  }
} else {
  fs.rmSync(FRAMES, { recursive: true, force: true }); fs.mkdirSync(FRAMES, { recursive: true });
  let next = 0, done = 0; const t0 = Date.now();
  await Promise.all(Array.from({ length: WORKERS }, async () => {
    const page = await openPage();
    while (next < TOTAL) {
      const f = next++;
      fs.writeFileSync(path.join(FRAMES, `${String(f).padStart(4, '0')}.png`), await grab(page, f / FPS));
      if (++done % 60 === 0) console.log(`${done}/${TOTAL} frames · ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }));
  const ffmpeg = process.env.FFMPEG || 'ffmpeg';
  const wav = path.join(ROOT, 'audio', 'soundtrack.wav');
  execFileSync(ffmpeg, ['-y', '-hide_banner', '-loglevel', 'error',
    '-framerate', String(FPS), '-i', path.join(FRAMES, '%04d.png'), '-i', wav,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-tune', 'film', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', path.join(OUT, 'showreel.mp4')], { stdio: 'inherit' });
  console.log('→', path.join(OUT, 'showreel.mp4'));
}
await browser.close();
server.close();
