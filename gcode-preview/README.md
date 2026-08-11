# G-code Live Preview (VS Code)

Edit a `.gcode` file in VS Code and see a live 3D preview in a side panel. Extrusion
moves are colored by fan state so you can see where cooling is on/off:

- **blue** = fan on (`M106 S255`)
- **red** = fan off (`M107`)
- **dim gray** = travel moves

Handles `G0/G1`, `G90/G91` (abs/rel), `M82/M83` (extruder abs/rel), `G92`,
`M106/M107`, `T0`–`T3` (AMS slot) and `M400 U1` (pause). Works with continuous
spiral (vase mode) g-code since it just plots the extrusion path.

A move that extrudes **without going anywhere** — a prime, a purge, an AMS load —
is skipped rather than plotted. It deposits nothing at a place, and counting it as
toolpath is actively wrong: an AMS filament change parks at the cutter (X267, off
the right edge of the bed) and pushes 24 mm through there, which stretched the
bounding box to X267 and, downstream in the 3mf packer, put that into the `G29 A1`
adaptive bed-mesh region and mis-measured the layer height by 24 % (0.499 mm
reported for a 0.403 mm print).

The preview also has a **timelapse scrub bar** (play/pause + move slider, spacebar
to toggle) and a **vertical layer slider** on the right, both synced — drag layers
for coarse control, moves for fine.

**Overhang heat map:** the **Color: Fan / Overhang** button (top-right) recolors
the print by local overhang angle. For each extrusion it looks one layer height
below for supporting wall and measures the perpendicular gap → angle from vertical:
green (0–30°, safe) → yellow (~45°) → orange (~55°) → red (65°+, likely fails). The
HUD shows the worst angle. Works on any g-code, and correctly handles vase-mode
spirals (layers are detected by real Z / revolutions, not by "Z went up").

**Filament changes:** the same button cycles on to **Color: Filament**, which paints
the path by which filament was loaded and draws a ring around the model at the
height of every change.

- `T0`–`T3` are the four AMS slots, shown as **A1**–**A4** (the labels on the unit)
  and given a stable colour each, so returning to A1 late in the print is visibly
  the same filament. `T1000` and `T255` — the A1's "no tool" sentinels — are not
  slots and are ignored.
- `M400 U1` (Bambu's pause; M600 does not exist on these machines) is a colour
  change too, but the g-code cannot say what got loaded — a human swapped the
  spool. Those bands get a separate, desaturated palette and are labelled
  *filament unknown*, so a guess never looks like a known slot.
- The colours are **identifiers, not the real filament colours**. G-code does not
  carry those; they live in the `.3mf`'s `project_settings`. A wrong "white" band
  would read as the print rather than as a legend entry.
- The ring is drawn at the height where printing **resumes**, not where `T` executed
  — the change block itself runs off the bed, so that position means nothing.

The legend lists only the slots the file actually uses, plus each change and its Z.
The HUD counts them, split into AMS and manual.

**Relief:** the last mode in the cycle colours each extrusion by how far its radius
sits from the mean radius of its own layer — orange bulges out, cyan cuts in, grey
is flat wall. This is the mode for looking at a **surface pattern**, and without it
such a pattern is invisible: the path is drawn with flat vertex colours and no
lighting, so a one-colour band renders as a flat silhouette and a 0.6 mm zigzag on
a 45 mm radius is under two pixels. (The overhang map shows one only by accident,
because bulging also changes the local overhang angle.)

Getting this to work is entirely about measuring the centre well enough. The relief
is 0.6 mm on a 45 mm radius, so an error `e` in the centre injects a fake
`e·cos(angle)` — a full-circle sinusoid that renders as vertical stripes. Measured
on a part whose smooth wall is provably round (44.999–44.999 mm):

| centre estimator | error left on the smooth wall |
|---|---|
| median over the whole part (`extrusionCentre`) | 0.53 mm — drew stripes instead of the pattern |
| centroid of the layer | 0.19 mm — pattern washed out |
| median of the layer | 0.41 mm |
| **least-squares circle fit per layer** | **0.006 mm** |

The averages fail because a drawing is not distributed symmetrically around the
axis — two different faces at 0° and 180° do not cancel. The fit does not care
where the points sit, only that they lie on a circle. Solid layers (a bowl floor is
a spiral sweeping the whole disc) are not circles and the fit runs away, so it is
discarded whenever it lands more than 5 mm from the centroid.

The colour scale is the p75 **across layers** of each layer's peak deviation. Both
halves matter: a percentile over all segments at once is set by the solid base, and
a percentile *inside* a layer underestimates a line drawing, which is sparse — the
faces cover 5.7 % of their own bounding box, so a p98 within the layer read 0.30 mm
for a 0.60 mm pattern.

## Vase-mode slicer (STL → G-code)

There's a built-in **spiralize / vase-mode slicer**: it takes an `.stl` with a
single closed contour per layer (vase, cup, cone, twisted tube…) and emits one
continuous helical extrusion path.

1. Right-click an `.stl` in the Explorer (or open one) → **"STL → Vase G-code"**.
   A `<name>.vase.gcode` is written next to it and opens in the preview.
2. Generate a test model any time with `node tools/make-vase-stl.js` → `vase.stl`.

Defaults live in `src/vase.ts` (`DEFAULT_OPTIONS`): 0.3 mm layers, 0.45 mm line,
1.75 mm filament, 210/60 °C, centered on a 110×110 bed. The floor is left open
(pure vase); a solid base would need scanline infill — see next steps.

## Overhang clamp (STL → printable STL)

**"STL → Clamp Overhangs"** reshapes a vase-like model so no wall leans past a
target angle from vertical (setting `gcodePreview.clampAngle`, default 45°). It
slices into aligned contours, then walks bottom→top pulling any point that sits
more than `layerHeight · tan(angle)` from the wall below back toward its support
— shaving bulges and over-aggressive twists into a printable shape. Writes
`<name>.fixed.stl`. It matches the preview's overhang metric, so it targets
exactly the red zones. (Single-contour models only; changes the design.)

## Orca CLI + full pipeline

- **"STL → Slice with OrcaSlicer"** shells out to the real Orca CLI headlessly,
  extracts the plain g-code from the `.gcode.3mf` archive, and previews it.
  Configure `gcodePreview.orcaBinary` and the machine/process/filament JSON paths
  (export those from OrcaSlicer) in Settings.
- **"STL → Pipeline"** chains it all: clamp overhangs → Orca slice → preview the
  overhang heat map, in one command.
- **"G-code: Watch File for Changes"** watches a file on disk (e.g. one Orca keeps
  re-exporting) and auto-refreshes the preview — no reopen/save needed.
- **"G-code: Watch Folder (preview newest)"** watches a whole directory and always
  previews the newest g-code in it (also on the right-click menu of any folder).

## Live loop with a g-code generator

Watching a folder turns the preview into the viewer for any tool that writes
g-code — in particular the FullControl lamp generators in `../vacante-g-code`,
which write a new `output/<nombre>.gcode` per run:

1. Right-click `fullcontrol-lamparas/output/` → **"G-code: Watch Folder"**
   (the folder can still be empty).
2. `python -m lamparas.bowls celosia --altura 70` → the preview picks it up.
3. Change parameters, re-run. Each run replaces the view; the layer slider and
   the overhang heat map come along for free.

An eye icon in the status bar shows what's being watched; click it to stop.

Two details that make this reliable, both load-bearing:

- **The watcher watches the directory, not the file.** `fs.watch` on a path
  follows the inode, so a generator that writes a temp file and renames it over
  the target goes completely undetected (measured on macOS: zero events, from
  the first rename on). Directory watching also lets you arm the watcher before
  the file exists, which is the normal case for a gitignored `output/`.
- **It waits for the write to settle.** A multi-MB export fires its first change
  event long before it is done, so the watcher polls until the file size stops
  moving before parsing. On the generator side `guardar_gcode()` writes
  `.gcode.tmp` and renames, so a reader sees either the old file or the whole
  new one — never half of either.

## Printing it — no SD card

The A1 will not start a plain `.gcode`: Bambu Studio and the firmware only accept
a `.gcode.3mf` container. And the OrcaSlicer CLI cannot send one — checked
against 2.4.2, there is no `--send`, `--upload` or `--print-host`; "Upload &
Print" exists only in the GUI. So we build the container ourselves.

**"G-code → Bambu 3mf (printable over LAN)"** (also on the right-click menu of
any `.gcode`) wraps a toolpath in a real `.gcode.3mf`. Open the result in Bambu
Studio and press Print.

It needs a **template** the first time: a `.gcode.3mf` you exported from
OrcaSlicer for *your* printer and nozzle (slice anything — a cube is ideal — and
"Export plate sliced file"). The command asks for it once and remembers it in
`gcodePreview.bambuTemplate`. The template is what makes the output
machine-correct: its machine start/end g-code, its bed levelling, its filament
settings are all reused verbatim. We never synthesise Bambu start g-code.

What gets rebuilt around your toolpath:

- The **md5** in `Metadata/plate_1.gcode.md5`. The firmware checks it; leaving
  the template's would get the job rejected.
- The **adaptive bed mesh** (`G29 A1 X… Y… I… J…`), re-aimed at your model's
  real first-layer footprint. The template's numbers probe the *old* object's
  area — a 29.6 mm cube's mesh levels nothing under a 150 mm lamp.
- **Progress**: `M73` percent/time and layer markers, spread across the body.
  Without this the display jumps to 47 % before the first extrusion (the cube's
  start g-code alone climbs that high), sits there all print, then snaps to 98 %.
- **Layer markers** — `; CHANGE_LAYER` / `; Z_HEIGHT:` / `; LAYER_HEIGHT:` per
  layer, against real Z. These are not decoration: a slicer's viewer builds its
  layer slider from them and takes `; Z_HEIGHT:` as authoritative over the Z in
  the moves. Emitting one at the top of the graft rendered a 58 mm bowl as a flat
  pancake. `; LAYER_HEIGHT:` is the *bead* height (derived from the flow), not
  the spiral pitch — viewers draw width as volume / (length · that), so the pitch
  drew 0.277 mm beads for a 0.800 mm bead and the whole model looked full of
  holes.
- **The five preview PNGs**, rendered from the toolpath in the filament colour.
- Header layer count / max Z, the plate bbox, and the weight and time estimates.

Your g-code's own start/end block is stripped. It recognises the FullControl
lamps' `;===== FIN DEL START GCODE =====` markers, an existing Orca export, or
falls back to dropping `G28`/`G29`/`M104`/`M109`/`M140`/`M190`/`M84`. The
positioning and extrusion mode (`G90`/`G91`, `M82`/`M83`) is carried across the
cut and re-declared — FullControl puts its `M83` in the header, above the
marker, so a body read as absolute decodes to nonsense.

From the terminal instead:

```bash
node tools/make-3mf.js path/to/file.gcode --template ref.gcode.3mf
```

Two things to know:

- **The thumbnails are rendered from the toolpath**, not from a mesh — the 3mf
  has no geometry. For spiralised and openwork pieces that is exactly right, the
  object *is* its toolpath. A densely infilled solid would read as a scribble;
  slice those normally instead. (`src/thumbnail.ts` + `src/png.ts`, no deps.)
- **The nozzle must match.** The template records a nozzle diameter and the
  printer refuses the job if it differs from the one installed. Temperatures come
  from the template too, not from your generator's start g-code.

Test fixtures: `node tools/make-vase-stl.js` (twisted vase) and `cone.stl` (a
steep 62° flare — good for seeing the clamp work). Report any g-code's overhangs
from the terminal with `node tools/overhang-report.js <file.gcode>`.

## Install it (normal use)

```bash
npm install
npm run reinstall    # packages a .vsix and installs it into VS Code
```

Reload the window afterwards (`Developer: Reload Window`). The commands are then
available in **every** VS Code window — no F5, no Extension Development Host, no
special workspace needed. Re-run `npm run reinstall` after changing the source.

## Developing without reinstalling

`npm run reinstall` builds a `.vsix` and installs it, and VS Code then wants a
window reload to pick it up. That is the right loop for *shipping* a version, and
the wrong one for iterating — you do not need it at all while developing.

Press **F5** instead: it opens a second window ("Extension Development Host")
running the extension straight from this folder, with no packaging and no install,
and it leaves your main window alone. From there the reload you need depends on
which half you touched:

| you changed | what to do | cost |
|---|---|---|
| `media/main.js`, or the HTML/CSS in `getHtml()` | **Developer: Reload Webviews** from the Command Palette — or just close the preview panel and reopen it | instant, nothing restarts |
| `src/*.ts` (extension host) | **Ctrl+R** / **Cmd+R** in the Extension Development Host window | ~1 s, only that window |

Closing the preview panel is enough for the webview because the panel is a
singleton that disposes on close, so reopening rebuilds its HTML and re-reads
`media/main.js` from disk. Most of the visual work — the colour modes, the
legends, the overhang map — lives in `media/main.js`, so most edits cost nothing
but a panel reopen.

`F5` runs `npm: watch` as its pre-launch task (`tsc -watch`), so TypeScript is
already recompiled by the time you hit Ctrl+R. The task is marked
`isBackground` with the `$tsc-watch` problem matcher — without that pair VS Code
waits forever for a process that never exits.

### Run it instead (development host)

Only needed when you want breakpoints in the extension itself.

```bash
npm install
npm run watch        # recompiles on change; F5 starts this for you
```

Then in VS Code:

1. Open **this folder** in VS Code — not a parent folder, since `launch.json`
   resolves the extension path from `${workspaceFolder}`.
2. Press **F5** (Run > Start Debugging). A second VS Code window opens
   ("Extension Development Host").
3. In that window, open a `.gcode` file (there's `sample.gcode` here).
4. Command Palette (Cmd+Shift+P) -> **"G-code: Open Live Preview"**, or click the
   preview icon in the editor title bar.
5. Edit the g-code and **save** (or just type — it live-updates after 300 ms).

## How the live preview works

- `extension.ts` opens a Webview panel beside the editor and sends the document
  text to it. It re-sends on save (`onDidSaveTextDocument`) and, debounced, on every
  edit (`onDidChangeTextDocument`). That's the whole hot-reload loop.
- `media/main.js` parses the text and draws it with three.js, coloring each
  extrusion segment by the current fan value.

## Notes / next steps

- three.js is loaded from cdnjs (needs internet). To go fully offline, download
  `three.min.js` + `OrbitControls.js` into `media/` and point the `<script>` tags in
  `extension.ts` (`getHtml`) at local `webview.asWebviewUri(...)` paths, and drop the
  cdn entry from the CSP.
- For your use case (turning the fan on/off over the pico bands), you can extend the
  parser to also draw a Z ruler or highlight specific Z ranges.
- Big files: this draws every segment as a line. If you throw a huge print at it and
  it gets slow, the usual fix is to decimate travel moves or use a single merged
  geometry per color.
