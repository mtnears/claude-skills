# Relief and depth maps (raised UV, embossing, patches)

A depth map is a greyscale image the same shape as the art: **black = lowest, white =
tallest**, everything outside the art pure black. eufyMake's guide
(https://www.eufymake.com/blogs/printing-guides/how-to-custom-3d-texture-depth-map) gives
the device rules; this file is how to decide the heights and build the map.

**Heights follow what things ARE, not what colour they are.** A white cloud isn't taller
than a dark rock because it is lighter. So the map is designed, shown as a draft, and
refined with the person, exactly like the colour work. Proven on a 4 in
medallion (printed at 2.5 mm relief: precise and as described).

## Ask first: look and feel
Offer these (plus "write your own"). Each is a starting tier list; the person can reorder.

| Look | Tiers, low → high | Texture |
|---|---|---|
| **Challenge coin** | field (flat) < scenery/background detail < borders + lettering + stars (all one level) < feature objects (a few levels) | none, or fine stipple on the field |
| **Embossed patch** | base < fill areas < raised border/stitch line < lettering | optional weave |
| **Faux leather** | background pebbled & low < debossed-looking field < raised logo | leather (pebbled cells) on the field only |
| **Embroidery** | fabric base < satin fill < thread-line detail < lettering | weave (fine) on fills |
| **Carved wood** | field with grain < raised shapes | wood (long wavy grain) on the field |
| **Stone / relief** | background low, foreground high, smooth blends | none or stipple |
| **Layered paper-cut** | 3-5 flat plateaus, hard steps | none |
| **Custom** | the person's own tier list: which parts at which relative height | their choice |

Also ask: **how tall in mm** the tallest part will print (eufyMake builds height from the
map, so this is set in Studio, not baked in), and whether the outer edge should taper.

## Tiers: how to choose
1. List the parts of the picture (background, rings/borders, lettering, scenery, hero objects).
2. Order them low → high by importance and by what feels physical (foreground over
   background; hero object highest).
3. Parts the person wants "the same height" (e.g. every border and its lettering) share one
   level exactly.
4. Keep background detail **below** the border tier so the frame still reads.
5. Levels used on the worked-example medallion (`examples/medallion-depth-map`): field 10 · scenery up to ~100 · borders, lettering and
   stars 150 · flag and 250 numerals 196 · Jeep 234. Max 245: flat pure-white tops print
   badly, so every top is bevelled (rounded over ~3.5 px) and the outer rim tapers over ~9 px.

## Procedure
1. **Regions.** Read coordinates with `grid_zoom.py` (gridded crop in the art's pixel
   coordinates). Write `regions.json` and run
   `make_masks.py ART.png regions.json OUT/masks`. Polygons are tightened by GrabCut or a
   colour rule, so edges follow the art.
   Show `masks_overlay.png` and **get the regions approved or corrected** before any heights.
   Hard parts: digits and letters with counters (the hole in 0, 4, A): trace each glyph as its
   own polygon and intersect with a colour rule. Do not use a big close/fill that welds
   neighbouring shapes or fills counters. Re-view after each change.
2. **Heights.** Write `config.json` (format in `depthmap.py`) and run
   `depthmap.py ART.png OUT/masks/masks.npz config.json OUT/depth`. Look at
   `depth_preview.png` (art | depth | shaded relief). Check: tier medians printed match
   intent; no pits inside letters; no seams; clean flat field; the outside is pure black.
3. **Refine** with the person, one change at a time (raise a tier, soften a hill, add
   grain). Heights are parameters, so each change is a re-run, not a redraw.
4. **Build for each size.** The same masks and config work on the native art and the 4x
   master (they rescale): build the depth map at each print scale, same DPI tag as the art.
5. Package `depth/` (maps) and `depth-build/` (masks.npz, regions.json, config.json, the
   commands) so the map can be changed and rebuilt later.

## Textures (`texture` in the config)
`leather` pebbled cells · `wood` long wavy grain · `weave` fine fabric check · `stipple`
fine random dots · `brushed` horizontal streaks. Set `amp` (levels, 4-10 is subtle) and
`scale`; switch it on per tier with `"texture": true` so the frame stays smooth and only
the intended areas are textured. Textures should stay small next to the tier steps.

## Gotchas
- Speck cleanup needs to be stricter for raised modes (`--speck-px 50`): every stray pixel
  becomes a bump.
- Don't derive heights from the colour classes; ring/lettering/star colours do identify
  *which things are borders*, but the level assigned is a design choice.
- A "seam" in the preview can be a preview-rendering artifact: check the numbers
  (`depth` values) before chasing it.
- eufyMake's built-in texture mapping is fine for quick jobs, but its height controls are
  limited and the result isn't a reusable file. The map here is reusable and rescalable.
- Test print: the person prints a small version next to eufyMake's own mapping and reports
  back; tune tier levels from that.
