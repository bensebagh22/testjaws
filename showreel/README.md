# Motion Reel '26

A 15-second, 1920×1080 / 60 fps motion-design showreel. Every frame and every sound is generated in code: there are no keyframes, footage, samples, or stock assets.

**Watch:** [`out/showreel.mp4`](out/showreel.mp4), or open `index.html` through any static server and hit play to watch it live in the browser.

## The cut (120 BPM, cuts land on the beat)

| Time | Scene | Techniques |
|---|---|---|
| 0–2 s | **Intro** | Crosshair with ruler ticks, heartbeat ripples, a staggered starburst, orbiting satellites, a typewriter line, and an iris-out to red |
| 2–4 s | **Kinetic type** | One word per beat: a masked rise (*I MAKE*), about 1,000 particles assembling into *PIXELS*, squash-and-stretch serif (*feel*), and an echo tunnel on *ALIVE.* The camera then flies through the full stop |
| 4–6 s | **Grid systems** | 144 cells and four spring-driven waves, each from a new origin: square → ring → cross → solid tile |
| 6–8 s | **3D particles** | 1,800 points with perspective projection and depth sorting, morphing sphere → torus → helix → lattice, then a warp jump into the next scene |
| 8–10 s | **GLSL shaders** | Domain-warped fBm in WebGL2 with brand-palette mapping and topographic bands. Organic serif *liquid* cuts to rigid *logic.* with design-tool selection boxes, then a liquid wipe |
| 10–12 s | **Data design** | Swiss 12-column grid, slot-machine odometer (900 = the frame count of this reel), spring bar chart, self-drawing line chart and donut, then a venetian slice-out |
| 12–13.5 s | **Edit / rhythm** | Quarter-note recap montage built from live re-renders of earlier scenes, with glitch bands and RGB plates, ending in a CRT power-off |
| 13.5–15 s | **Identity** | Shockwave and shards, then a spring-assembled mark, a tracking-in wordmark, a blur-in subtitle, and an availability pill |

Finishing on every frame: 6-sample motion blur (180° shutter) that never smears across a cut, camera shake and radial chromatic aberration driven by the same hit list as the audio, film grain, vignette, and a `difference`-blended HUD with a live timecode.

## Sound

`audio/soundtrack.py` synthesises the track with numpy: kick, clap, hats, supersaw pads (Am → F → C → G → Am → F → E → Am9), sidechained bass, and plucked arps. The sound design is placed on the picture timeline: typewriter ticks per character, tick cascades per grid wave, decelerating odometer clicks, bit-crushed montage hits, a falling CRT whine, silence before the drop, and a sub-boom on the logo.

## Build

```bash
python3 audio/soundtrack.py          # → audio/soundtrack.wav (needs numpy)
node render.mjs                      # → out/showreel.mp4 (needs playwright + ffmpeg; FFMPEG=/path/to/ffmpeg to override)
node render.mjs --stills 3.8,9.3     # debug stills
```

`render.mjs` serves the page and renders frames in parallel headless Chromium pages. Each frame is a pure function `renderFrame(t)`, so workers can render any frame in any order. It then muxes the frames with ffmpeg (x264 CRF 17, AAC 256k).
