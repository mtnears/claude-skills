# Colours, Pantone codes and garments

## What to ask
- **Shirt / garment / background colour** whenever the art will go on something coloured:
  it drives which art colour gets *no ink* (the shirt shows through), the mockups, and the
  white underbase decision. Accept hex, a Pantone code, or a plain description ("heather
  gray, baseball tee with green sleeves"). Offer white and heather gray if they have no idea.
- **Ink colours** (screen print): ask whether they have actual ink colours/codes.

## If they give codes
Use them exactly (hex, RGB, Pantone, CMYK). Pass hex to `separations.py --palette` and
**include the garment colour in the palette** as the no-ink entry. Say in the spec sheet that
these are the customer's codes.

## If they don't: approximate and ask
Let `separations.py` find the inks (k-means in L*a*b*), name them in plain words
(burnt orange, olive green), and show **swatches with hex and the nearest Pantone** for
approval. Say "close match picked from the art; tell me any you want changed". Never block
the job on exact colours. Remember the ink count the person asked for (5-ink, 4-ink...).

## Pantone and printer codes
`pantone_match.py HEX,HEX,... --out inks.json --names "HEX=Name,..."` gives:
- **Pantone Solid Coated** code + the screen hex + dE00;
- **Cotton TCX** alternate (fabric/apparel) + dE00.
Needs node + `npm install pantone-cli` + `npx pantone-cli fetch-index` (once per workspace;
the index comes from GitHub). dE00 under ~3 is very close. Always add the caveat: these are
starting points, not ink formulas; the printer matches against a swatch book and mixes to
their own formulas. If the lookup is unavailable, give hex/RGB only and say so.

## Spec sheet for the printer
`spec_sheet.py SEPDIR OUTDIR --title T --width-in W --garment "..." --job-json job.json`.
`job.json` holds `inks` (from `pantone_match.py`, plus a `use` line per ink: what prints in
it), `notes`, `questions` (defaults ask about mesh/ink, trapping/halftones, size/order,
merging colours) and `mock` (path to the mockup image). Output: `films/NN_<Ink>_<HEX>.tif`
in print order, `films.json`, and `printer_spec_sheet.pdf` (size, garment, ink table with
swatches and codes, coverage, notes, questions for the printer, mockups).

## Mockups
`shirt_mockup.py SEPDIR OUTDIR --width-in W --bodies FFFFFF:white,C9CBCD:heather --sleeve HEX|same`
draws illustrative tees from the actual plates (shirt colour shows where no ink). Not a
colour proof; say so.

## Dark garments
Need a white underbase plate plus a plate for the "light" colour: more screens, tighter
registration, and heavier ink. Say that, and only build it when the person wants it
(`separations.py --underbase`).
