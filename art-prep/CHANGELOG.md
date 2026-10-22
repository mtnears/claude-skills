# art-prep changelog

## v2.2 (2026-10-21)
- New: `scripts/stl_to_cut.py` turns a flat STL (relief/extrusion) into a cut SVG in mm.
  Cut on an xTool M2 10 W diode: fine.
- Engrave font underlines 6/9/M/W so "which way is up" is unambiguous on test pieces; the
  numbering rule for test pieces is written down in `references/laser.md`.

## v2.1 (2026-10-20)
- New: laser cut/etch output (`scripts/laser_prep.py`, `references/laser.md`): traces the art's
  own pixels to SVG in mm. Modes: stencil (pop-out letters, loose centres or bridges), positive
  pieces, inlay with fit, stacked layers, engrave fill, kerf-test coupon, and a reference plate
  (kerf per direction for pieces and holes, fit holes and plugs, disc, rulers, orientation marks,
  engraved logo and machine label) to measure once per material, thickness and laser.
- Per-direction kerf (elliptical offset) with separate piece and hole values; per-combination
  laser profiles in `config.json`.
- Validated: the reference plate on an xTool M2 10 W diode, 3 mm black cast acrylic (kerf, fit,
  scale). Logo builds were generated and previewed but not yet cut. CO2/UV not yet validated.

## v2 (2026-10-18)
- Intake now asks for output type, colours (shirt/ink hex or approximate-and-approve) and, for
  relief, the look and texture; write-ins allowed. Unlisted outputs: feasibility, one-off,
  then ask to add. Help mode ("what can you do?").
- New: custom depth maps for raised UV/relief (`make_masks.py`, `depthmap.py`, `grid_zoom.py`,
  texture styles, `references/relief.md`, worked example).
- New: screen-print package with Pantone/Cotton TCX codes (`pantone_match.py`), printer spec
  sheet (`spec_sheet.py`), shirt mockups on given garment colours (`shirt_mockup.py`).
- Settings moved to `config.json` (archive root, scripts folder, clients): nothing
  person-specific is hard-coded in the instructions.
- Gotchas recorded (palette must include the garment colour, location-based dark-ink split,
  truncated-file check after AI upscale, 30 MB file-copy limit, others).
- Validated on: a UV + depth-map job (printed at 2.5 mm) and a 5-ink screen-print job (printer feedback pending).
