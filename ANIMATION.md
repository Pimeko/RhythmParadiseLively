# Guy animation: notes for picking the work back up

The wallpaper currently uses three static images (`img/guy_idle_crop.png`, `img/guy_half_scream_crop.png`,
`img/guy_scream_crop.png`). An animated version using the game's frames was fully integrated and then removed,
because no upscaling method gave satisfying results. This document keeps everything needed to resume.

## Where to find the animated version

The animation player is still in the git history:

| Commit | Content |
|---|---|
| `b0edf6b` | First integration of the player and frames |
| `62643eb` | Faster idle <-> scream transition (`PASS_THROUGH_SPEED`) |
| `2b86fae` | Frames cropped without borders |
| `53c1a95` | Last animated version, with the upscaled image folders |

To get it back: `git show 53c1a95:index.html > index_anim.html`, then diff it against the current `index.html`.
The player lives in a single `<script>` block (`GUY_*` variables, `SEQ`, `guyAnim`); `scream()`, `halfScream()`
and `idle()` called `guyAnim.setTarget("scream" | "half" | "idle")` instead of changing `guy.src`.

## Frame source

1. ROM dumped from a personally owned cartridge, opened with **Tinke**.
2. Folder `grapharc/chorus/ver4/`: `chorus.NCLR` (palette), `chorus.NCBR_LZ` (tiles, LZ77-compressed, decompress
   it in Tinke), `chorus.NCER` (cell layout), `chorus.NANR` (animations).
   The main `chorus/` folder probably holds the base version of the minigame; not tested.
3. Open in **NitroPaint** in this order: NCLR -> NCBR (rename to `.NCGR` if rejected) -> NCER -> NANR,
   then *Export All* from the Cell Editor (`Cell_0000.PNG`...).
4. Each cell is exported on a 512x256 canvas with the sprite origin at (256, 128),
   so all cells are already aligned with each other.
5. Common crop `(230, 48, 286, 140)` -> 56x92 px, centered on the idle guy, saved as `img/chorus/cell_XX.png`.

## Sequences in `chorus.NANR`

Notation `cell x duration`, duration in DS ticks (1 tick = 1/60 s).

| Seq | Frames |
|---|---|
| 1 | 6x4 7x4 6x4 7x4 6x4 7x4 8x4 9x4 10x4 19x4 (blink) |
| 6 | 6x5 7x5 6x5 7x5 (idle breathing) |
| 11 | 25x2 24x2 23x2 (opening into half scream) |
| 12 | 20x6 21x6 22x4 (half scream loop) |
| 13 | 11x6 12x6 13x6 14x4 15x4 16x4 20x6 21x6 22x4 (scream closing back into half scream) |

The other 13 sequences in the file (0, 2, 3, 4, 5, 7, 8, 9, 10, 14, 15, 16, 17) were not used.
The easiest way to re-read sequences is NitroPaint's Animation Editor (*Frames* button).

## Frames for each state

Cells used: 6, 7, 8, 9, 10, 19, 20, 21, 22, 23, 24, 25, 11, 12, 13, 14, 15, 16.

| State | Behavior |
|---|---|
| **Idle** | Seq 6 played `IDLE_REPEAT` times (10), then seq 1 once, looping |
| **Idle -> half scream** | Seq 11 forward (25 -> 24 -> 23) |
| **Half scream** | Seq 12 looping (20, 21, 22) |
| **Half scream -> idle** | Seq 11 reversed (23 -> 24 -> 25) |
| **Half scream -> scream** | Seq 13 reversed (22 -> 21 -> 20 -> 16 ... -> 11), speed x`SCREAM_TRANSITION_SPEED` (5) |
| **Scream** | Loops on the last `SCREAM_LOOP_FRAMES` (3) frames of the ramp-up, in seq 13 order: 11, 12, 13 |
| **Scream -> half scream** | Seq 13 forward (11 -> ... -> 22), speed x5 |
| **Direct idle <-> scream** | The half scream is crossed `PASS_THROUGH_SPEED` (45) times faster |

The player models a track `idle | seq 11 | half scream | reversed seq 13 | scream` and walks it toward the
target state: if the mouse changes its mind mid-transition, it plays backward from the current frame, with no jump.
Display: `GUY_SCALE = 6` (56x92 sprite -> 336x552 px). The old `eye.png` overlay was disabled during the
half scream, since the frames already have their own eyes.

## Upscaling methods tried

| # | Method | Where | Principle | Why it didn't work out |
|---|---|---|---|---|
| 1 | Raw sprites | `img/chorus/` | Nearest-neighbor scaling (`image-rendering: pixelated`) | Faithful but pixelated, clashes with the wallpaper's smooth style |
| 2 | Local Real-ESRGAN | `img/chorus_hd/`, `tools/upscaler/upscale.py` | `realesrgan-x4plus-anime` model, color and alpha upscaled separately | Smooth outlines but an "AI" look: artifacts, thinner white border |
| 3 | Faithful fal.ai upscalers | `img/chorus_topaz/`, `img/chorus_recraft/`, `upscale.py --backend fal` | Topaz Precision, Recraft Crisp | Same limits: they refine but don't recreate a crisp line |
| 4 | Manual redraw | `img/chorus_hd2/` | Frames redrawn by hand | Inconsistent sizes and positions between frames |
| 5 | Automatic realignment | `img/chorus_hd2_fixed/`, `tools/normalize_frames.py` | Scale and feet aligned on the DS sprites | Positions fixed, final look still not satisfying |
| 6 | vtracer vectorization | `img/chorus_vec/`, `tools/vectorize.py` | Curve tracing per color, 3 variants (blurred colors, 3 levels, 2 levels) | Gray halos, then dotted outlines, then an oversimplified result |
| 7 | Pure SDF | — | Signed distance field, rebuilt outlines, light antialiasing | Not conclusive |
| 8 | Cascaded EPX / Scale2x | — | Fixed pixel-art rules, clean output with no grays | Still pixel art, stair-stepped diagonals |
| 9 | EPX + SDF hybrid | — | Diagonals interpreted by EPX, then smoothed by SDF | Not conclusive |
| 10 | Custom contour vectorization | — | Opaque / black areas -> OpenCV contours -> controlled smoothing -> supersampled rendering -> downscale | Not conclusive |
| 11 | Skeleton + ink strokes | — | Black reduced to its skeleton, then redrawn as strokes of controlled width | Not conclusive |

Tools prepared but never fully used (folder `../frame-restyler/`):
`restyle_frames.py` (redraw guided by reference images, OpenAI GPT Image 2.5) and `interpolate.py`
(in-between frames from keyframes, Kling O1 on fal.ai).

## Why nothing really worked

- **The source is too small.** 56x92 px: line thickness, curves and small details (teeth, bow tie) fit in
  1 or 2 pixels. The information of a high-resolution drawing simply isn't in the file.
- **The outline is one pixel wide and alternates black and dark gray** (antialiasing). Any thresholding breaks it
  up or thickens it unevenly; skeletonization helps but can't recover the original thickness variations.
- **Faithful or invented: you have to pick one.** Faithful methods (scaling, vectorization, SDF, EPX, ESRGAN) can only
  guess what's missing: blur, artifacts or a simplified look. Generative methods invent what's missing, and the
  style drifts from one frame to the next.
- **Animation needs consistency between frames.** A flaw that's fine on a still image turns into visible
  jitter when 18 frames play in sequence.

## If picking this back up

1. **Redraw the frames by hand**, using the DS sprites as pose guides and the current static images as the style
   reference, then run `python tools/normalize_frames.py` to realign them. It's the only path that gives a crisp,
   consistent line.
2. **Inkscape -> Trace Bitmap -> Pixel art tab** (Kopf-Lischinski algorithm), with manual curve cleanup.
3. **Embrace pixel art**: `img/chorus/` with `pixelated`, possibly displayed smaller.
4. **Only redraw the loops** (6/7, 20/21/22, 11/12/13): transitions last a few hundredths of a second,
   so a rougher version goes unnoticed there.

The images extracted from the game (`img/chorus*`) are not meant to be published: keep them out of the public repo.
