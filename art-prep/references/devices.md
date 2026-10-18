# Devices and what they need

Settings below come from the owner's own equipment (Oct 2026). When a device or its
software changes, update this file.

## eufyMake UV printer (eufyMake Studio)
- **Imports:** JPEG, PNG, JPG, WEBP, SVG, PSD, AI, PDF, EMPF, GIF. Send **PNG** with
  transparency: lossless, keeps the alpha channel the white layer is built from.
- **How white is made:** Ink Mode "White > CMYK" (white layers ×3, then CMYK ×1, max 12
  layers) builds the white underbase **from the image's transparency**. Every non-clear
  pixel gets white. That's why ghost pixels and specks print as stray white dots and
  soft edges print a white rim. Clean with `--speck-px 25 --hard 128` before export.
- **White Underbase Choke:** set in the software (default 0.2 mm). Don't choke again in
  `white_layer.py` (use `--choke-mm 0`); its outputs are a **check** of where white will
  go, plus a ready separate white layer if the software ever takes one.
- **Auto-detect Contours / Snapshot:** contours also come from transparency, so a clean
  hard edge gives a clean contour.
- **Craft modes:** Flat, Flat Raised, Pattern/Relief/Brushstroke texture. Raised modes
  stack white for height, so stray pixels become bumps. Clean even more strictly
  (`--speck-px 50`).
- **Custom depth map** (3D texture / relief): import a greyscale map the same shape as the
  art: black = lowest, white = tallest, outside the art pure black. Rules from eufyMake's
  guide: taper the outer rim (Edge Darken), no flat pure-white tops (bevel, cap ~245),
  smooth gradients, no isolated specks. Build it with `depthmap.py` (see `relief.md`);
  total height in mm is set in Studio. Validated Oct 2026: 4 in medallion at 2.5 mm,
  built from a tier map, printed clean beside Studio's own texture mapping, which gives
  fewer controls and no reusable file.
- Studio import limits that matter when filing: keep each file under ~30 MB for the
  chat-to-folder copy (not a Studio limit).
- **Built-in tools** (Remove BG, Cutout, Upscale, Offset, Convert to Contour, Vectorize):
  fine for quick jobs. Its Upscale/Remove BG may regenerate or guess edges; for art that
  must stay exact, do those steps here and import the result.
- Separate CMYK layers are not used today. If needed later: `white_layer.py` gives the
  white layer and the cleaned PNG is the colour layer.

## Siser Leonardo (print-and-cut)
- **Imports:** SVG, PNG, TIF, JPG. **No PDF.**
- **Print image:** `NAME_print.png`. Lossless with transparency, DPI set. Avoid JPG
  (no transparency, compression edges); TIF only if a shop asks.
- **Cut line:** `NAME_cut.svg`. A red hairline path sized in mm, exact, no tracing.
  Both files share the same canvas (including padding), so placed at the same origin
  they line up.
- First time on a new setup: import both, check the size reads correctly (SVG states mm;
  the PNG relies on its DPI tag) and do one test cut before a run.
- Alternative: Leonardo can trace `NAME_cutmask.png` itself; use that if SVG import
  ever misbehaves.
- **Border vs edge:** a border offset (1-2 mm, white or clear) cuts cleanly around any
  art. Cutting on the art edge (`--offset-mm 0`) needs a solid outline plus bleed.

## Screen printing
- Presses differ: ask the person how many colours/screens their press (or their printer's)
  takes. Spot-colour jobs usually run 4-7 inks.
- Films: one black-on-white TIF per ink at print size (`plate_NN_<hex>.tif`), LZW,
  DPI tagged. Underbase plate for dark garments, choked 0.3 mm by default.
- Print order in `separations.json`: underbase, then inks light to dark.
- `--garment HEX`: art colour matching the shirt gets no ink (the shirt shows through).
- `--palette` when the inks are already chosen (match their actual ink colours).
- Pantone Solid Coated + Cotton TCX codes and a printer spec sheet come from
  `pantone_match.py` + `spec_sheet.py` (see `colour.md`). Plates: LZW TIFF, black = ink,
  one canvas for all films, no trapping/registration marks.
- A flat-colour logo on a light shirt works well as 4-5 inks with the panel colour left
  as the shirt (validated on a five-colour logo: reconstructed print vs art mean dE76
  about 3, no ink outside the art). Dark shirts add a white underbase and a light-colour
  plate (more screens).
- Not done here: halftones / simulated process for gradients. For photographic art say
  so and suggest DTF/DTG or a separation program. Test new plates with the shop or press
  before a production run; settings will be adjusted after the first real test.

## Shirts by DTF/DTG, decals, web
- DTF/DTG print full colour from a PNG: send the 4x master (300 dpi at print size) with
  clean edges. Soft edges are fine here; ghost pixels still aren't.
- Check the art on a dark shirt: black or dark elements on transparency disappear (e.g.
  a black date line). Fix in the draft step: a backing shape, or a white variant.
- Email: attach the native PNG; share anything over ~20 MB by link.
