# Laser cutting and engraving (xTool and similar)

Everything here is computed from the art's own pixels and written as SVG in real millimetres.
Script: `scripts/laser_prep.py`. Needs numpy, Pillow, OpenCV and shapely
(`pip install --break-system-packages shapely opencv-python-headless`).

Validated so far on an xTool M2 10 W diode, 3 mm black cast acrylic, xTool Studio 1.9.11
(measured kerf, fit test and scale check on a reference plate). **Not yet validated:** the logo
stencil/inlay/stack builds (built and previewed, not cut), CO2 and UV modules.

## What each module is for (ask which one; confirm against the maker's material list)
- **Diode (blue):** cuts opaque and dark material. Clear or light-coloured acrylic passes the beam.
  Wider kerf, a slanted wall on thick stock.
- **CO2:** cuts clear and coloured acrylic, wood, leather; engraves acrylic well.
- **UV:** fine marking and engraving; not a thick-cut tool.
Kerf, fit and settings belong to one **material + thickness + laser + settings** combination.
New combination = one reference plate, not a guess.

## Ask first
Machine and module, material and thickness, final size, what is cut and what is etched, whether
loose centres (A, R, O, 4...) are wanted as pieces or kept attached, and whether it is one colour
or a layered/inlaid sign. If a profile for that combination exists (`config.json` → `laser_profiles`),
use its numbers and say so. If not, offer the reference plate first.

## The reference plate (do this once per combination)
```
laser_prep.py LOGO.png OUT --mode reference --machine "xTool M2 10W diode" --material "3 mm black cast acrylic" --profile-id 01
```
(`LOGO.png` is optional: pass `-` for no engraved logo.) Writes `reference_plate.svg` (about
176 x 134 mm), a labelled guide image, `reference_plate_MEASURE.txt` and a profile template.
- Every loose piece has its **top-left corner cut off** (chamfer) and engraved numbers, so
  orientation survives when it drops. Every measuring mark has a twin on the opposite side.
- **Numbering rule (any test piece):** every piece carries its ID and numbered measuring lines
  (1-3 left-right = X, 4-6 top-bottom = Y), so the person can report "S1 line 4" exactly.
  Numbers that look the same upside down (6/9, M/W) are **underlined** by the engrave font, so
  "up" is never ambiguous. Keep this in any new test layout.
- **S1** 20 mm piece + **H1** 20 mm hole: kerf per direction (X = left-right, Y = top-bottom).
  The pieces that drop out of H1/H2 are marked too and are extra samples.
- **F1** eight 10 mm holes at offsets -0.40 to -0.05 mm per side + numbered plugs: the fit.
- **D1** 40 mm disc with the logo etched + **H2** hole; **R1/R2** rulers 100/60 mm (machine scale).
- The machine label is engraved on F1 (capital letters and digits only).
- **Engrave first, then cut**, or the loose pieces fall out unengraved. Many programs import the
  red hairline as "score": change that layer to cut (xTool Studio does).
- Same settings as the real job. Let it cool. Measure with the same calipers, closed gently.

### From the readings to numbers
- **Piece kerf** (outside jaws): `20 - mean(S1)` per direction; the plug gives `10 - plug`.
- **Hole kerf** (inside jaws): `mean(H1) - 20` per direction. Inside jaws and slanted walls make
  this read smaller than the piece kerf; on the M2 the piece lost 0.26 / 0.365 mm and the hole
  grew 0.15 / 0.21 mm (X / Y), and the fit test agreed with the hole value. Use piece and hole
  values separately: `--kerf-piece X,Y --kerf-hole X,Y`.
- **Fit:** try one plug in each hole. Clearance per side = hole offset c + the kerf effect; the
  snug hole tells you `--fit`. On the M2: snug at -20, tight at -25, loose at -15; press fit
  about +0.02 mm per side, glued inlay about +0.05.
- Check scale from R1/R2 (true on the M2). Record everything in `config.json` as a profile.

## Builds from a logo (`--mode`)
`--width-mm` sets the traced art's width; `--blank circle|rect|none`, `--blank-diam`, `--margin-mm`.
- **stencil:** the blank with the art cut out (letters pop out). Trapped centres become numbered
  loose **islands** (`--counters piece`) or stay attached by bridges (`--counters bridge
  --bridge-mm 1.2`). Also writes the plain backer disc.
- **positive:** the art as cut-out pieces + backer. **inlay:** stencil front with the fit offset
  + pieces + backer, for a second colour pressed in. **stack:** backer, outline layers grown
  `--grow 2,4` mm, and the art. **engrave:** the art as a blue fill + the blank outline.
- Kerf is applied per axis with an elliptical offset (beam spot shape), pieces grow and holes
  shrink so the true sizes land on nominal; `--fit` is the clearance per side for inlay holes.
- Reports: `*_laser_report.json` (islands and sizes, bridges, thin spots under
  `--min-feature-mm` 1.0 in orange on the preview). Islands under 2.5 mm across are fiddly:
  offer bridges or a bigger size.
- Colours in the SVG: red hairline = cut, blue fill = engrave.

## From a 3D model (STL)
`stl_to_cut.py MODEL.stl OUT --height-mm 120 [--rotate N] [--mirror]` for a flat relief or
extrusion: finds the slab plane, projects the triangles, writes one cut outline in mm with the
slits kept as holes and specks dropped. Units in STLs are unreliable, so always set the size.
A flat part has no front: show the preview, let the person pick facing, then **store the file
in its correct orientation** (they flip in the laser software if ever needed; no mirrored copies).
Report slit widths: under about 3x the kerf they are fiddly.

## Limits and gotchas
- Tracing follows the source: soft or ragged edges give wavy cuts; upscale or clean first. Photo
  art is not traced (use a one-colour version or `--ink HEX`).
- Several ink colours are one run per colour (`--ink HEX --tol N`); no automatic colour layers.
- The engrave font is capitals, digits and a few symbols only. Longer notes go in the profile.
- Do not scale SVGs in the laser software except all parts together; kerf does not scale.
- A file that "reads the wrong size" can be a stale cloud-synced copy: force a sync and re-import.
- Never a power/speed recommendation: record the settings used and the result.
