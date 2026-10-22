# Output menu, help text and feasibility

Use this for "what can you do?", for the intake question when the output isn't stated, and
to judge outputs that aren't listed.

## Menu (offer these, always with "other: tell me")
| Output | What I need from you | What you get |
|---|---|---|
| **UV print, flat** (eufyMake) | print width, DPI wanted | cleaned hard-edge PNG (4x if needed) + white-layer check |
| **UV print, raised** | the above + the look (coin, patch, leather, wood, your own tier list) and texture | colour PNG + custom **depth map** (black low, white tall) + the masks/config to change it later |
| **Print-and-cut sticker** (Leonardo) | width, border colour | print PNG + exact cut-line SVG |
| **Die-cut on the art edge** | width; solid outline needed | cut path with bleed |
| **Screen print, spot colours** | shirt/garment colour, ink count, width; hex/Pantone if you have them | one film per ink, Pantone + Cotton TCX codes, printer spec sheet, shirt mockups |
| **Laser cut / etch** (xTool, diode / CO2 / UV) | machine + module, material + thickness, size, what is cut vs etched, loose centres or bridges | SVG in real mm (red = cut, blue = engrave): stencil, pieces, inlay with fit, stacked layers, engrave fill; a reference plate to measure kerf and fit; a profile record |
| **DTF / DTG shirt** | width, shirt colour | 4x clean PNG, previews on light and dark |
| **Web / social / email** | max pixel width | optimised PNG |
| **Upscale / clean only** | target size | 4x master, nothing else |
| **Other** | describe the process or device | feasibility check, a one-off build, then I ask if you want it added |

Not supported (say so): halftones/simulated-process separations for photos, vectorising
photographic art, laser power/speed recommendations (record what was used instead), redrawing or "improving" the art, printer ink formulas, trapping and
registration marks (the printer adds those).

## Feasibility check for an unlisted output
Answer these in a few plain sentences, then proceed or stop:
1. **What does the process or device consume?** (a PNG with transparency, a greyscale height
   map, an SVG path, one film per ink, a PDF...)
2. **Can that be computed from the art's own pixels?** If yes it fits this skill. If it needs
   invented detail (new drawing, a 3D model from a flat picture), say what can and can't be
   promised and offer the nearest honest version.
3. **What needs the person's input?** (sizes, colours, tier choices, material)
4. **What can't be verified here?** (colour accuracy, machine behaviour: ask for a test print
   and a short report back.)
Build it as a one-off with the same draft → approve → package loop. Afterwards ask: "Want
this added to the skill?" If yes, draft a short entry for this file (output, inputs needed,
the commands used, the gotchas) for the person to approve and commit.

## Relief / material looks that are already worked out
See `relief.md` (coin, patch, leather, embroidery, wood, carved stone, paper-cut layers).
