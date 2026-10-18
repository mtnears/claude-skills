# Claude skills

Skills for Claude that I built for my own print shop. Skills follow the open [Agent Skills](https://agentskills.io) format: a folder with a `SKILL.md` plus scripts, which Claude loads when a task calls for it.

## art-prep: production-ready files from AI art, without redrawing it

Ask an image generator for "high-res" and it draws a *new* picture: lettering drifts, details change. art-prep works from the pixels you already have:

- **Asks first** for what changes the result: the output type (UV flat or raised, screen print, sticker, DTF/DTG, web, or your own write-in), size, shirt or ink colours (hex/Pantone if you have them, otherwise it approximates and asks you to approve), and for relief work the look and texture.
- **Inspects** for the things that ruin prints and cuts: ghost pixels (nearly invisible pixels that UV printers put white ink under and cutters trace), soft halo edges left by background removal, specks, and white trapped inside letters (A, P, R, 0...) that background removal missed. Candidates are shown as numbered close-ups; you pick.
- **Cleans** transparency (hard edges for UV and cutting, defringed soft edges for shirts and web).
- **Upscales** 4x with Real-ESRGAN (optional) or plain resampling, and shows them side by side.
- **Builds outputs per use:**
  - **UV printing:** clean PNG + a white-underbase check (written around eufyMake Studio)
  - **Raised UV / relief:** a custom **depth map** (black low, white tall) designed from what each part of the art *is*: coin, patch, leather, embroidery, wood or your own tier list, with optional texture. Masks and settings are kept so it can be changed and rebuilt.
  - **Print-and-cut stickers:** print PNG with bleed + SVG cut line in mm (written around Siser Leonardo)
  - **Screen printing:** spot-colour film plates, nearest Pantone / Cotton TCX codes, a printer spec sheet (PDF), and shirt mockups on your garment colour; honest warning when the art is too photographic for spot colours
  - **DTF/DTG shirts** and **web/social** versions
  - Something else? It checks whether it can be done from the pixels, builds it as a one-off, then asks whether to add it to the skill.
- **Shows a draft for your approval** before it builds the package, then packages everything with a README of what was changed and offers to file it.
- Ask it **"what can you do?"** for the menu.

### Install

**Claude (web/desktop):** download `art-prep.zip` from the [latest release](../../releases/latest) (not the "Source code" zip), then in Claude go to **Customize → Skills → upload** and choose the ZIP. Skills are per account on Free/Pro/Max plans; each person uploads their own.

**Claude Code / other Agent Skills tools:** copy the `art-prep` folder into your skills directory (for Claude Code: `~/.claude/skills/art-prep`).

Then just ask, e.g. *"Prep this logo for a 3 inch die-cut sticker"*, *"Make a raised UV depth map for this medallion"*, or *"Separate this logo for a 5-ink screen print on a heather gray tee."*

### Before first use
1. Copy `config.example.json` to `config.json` inside the skill and fill in where finished art should be filed (`archive_root`) and, optionally, a shared scripts folder (`scripts_home`). If you skip this, Claude asks the first time. Your `config.json` stays on your machine; don't commit it.
2. Tell Claude about your machines the first time (UV printer white choke, cutter file formats, max screen colours), or edit `references/devices.md` before uploading.
3. Do **one test print or cut** before a production run: device software can read sizes differently. Depth maps especially: print a small version first and tune the tier heights.

### Requirements
Python 3 with numpy, Pillow and OpenCV (Claude's sandbox has these or installs them); `reportlab` for the printer spec sheet. The AI upscale also needs PyTorch + spandrel and the Real-ESRGAN weights; the script header explains the one-time setup, and a no-AI fallback is always available. Pantone lookups use the offline `pantone-cli` npm package (needs Node; matches are approximate and the printer confirms them against a swatch book).

### A note on safety
Skills can run code. Read a skill (it's short) before installing it, this one included.

## Support
If this saves you a reprint or two, you can [sponsor me on GitHub](https://github.com/sponsors/mtnears). Totally optional; the skill is free either way.

## License
MIT. Use it, change it, share it. Issues and suggestions welcome.
