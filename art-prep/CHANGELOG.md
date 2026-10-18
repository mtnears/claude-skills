# art-prep changelog

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
- Validated on: a 4 in medallion (UV + depth map, printed at 2.5 mm) and a flat-colour
  logo (5-ink screen-print package, printer feedback pending).
