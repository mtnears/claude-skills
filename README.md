# Claude skills

Skills for [Claude](https://claude.ai) that I built for my own print shop.
Skills follow the open [Agent Skills](https://agentskills.io) format: a folder with a
`SKILL.md` plus scripts, which Claude loads when a task calls for it.

## art-prep: production-ready files from AI art, without redrawing it

Ask an image generator for "high-res" and it draws a *new* picture: lettering drifts,
details change. `art-prep` works from the pixels you already have:

- **Inspects** for the things that ruin prints and cuts: ghost pixels (nearly invisible
  pixels that UV printers put white ink under and cutters trace), soft halo edges left by
  background removal, specks, and white trapped inside letters (A, P, R, 0…) that
  background removal missed. Candidates are shown as numbered close-ups; you pick.
- **Cleans** transparency (hard edges for UV and cutting, defringed soft edges for shirts and web).
- **Upscales** 4x with Real-ESRGAN (optional) or plain resampling, and shows them side by side.
- **Builds outputs** per use:
  - UV printing: clean PNG + a white-underbase check (written around eufyMake Studio)
  - Print-and-cut stickers: print PNG with bleed + SVG cut line in mm (written around Siser Leonardo)
  - Screen printing: spot-colour film plates + choked underbase, with an honest
    warning when the art is too photographic for spot colours
  - DTF/DTG shirts and web/social versions
- **Shows a draft for your approval** before it builds the package, then packages
  everything with a README of what was changed and offers to file it.

### Install
**Claude (web/desktop):** download
[art-prep.zip](https://github.com/mtnears/claude-skills/releases/latest/download/art-prep.zip)
(not the "Source code" zip), then in Claude go to

**Claude Code / other Agent Skills tools:** copy the `art-prep` folder into your skills
directory (for Claude Code: `~/.claude/skills/art-prep`).

Then just ask, e.g. *"Prep this logo for a 3 inch die-cut sticker"* or
*"Clean this ChatGPT image up for my UV printer"*.

### Before first use
- Edit `art-prep/references/devices.md` to match your machines (choke settings,
  file formats, max screen colours).
- Edit `art-prep/references/archive.md` with where finished art should be filed.
- Do one test print or cut before a production run: device software can read sizes differently.

### Requirements
Python 3 with numpy, Pillow and OpenCV (Claude's sandbox has these or installs them).
The AI upscale also needs PyTorch + spandrel and the Real-ESRGAN weights; the script header
explains the one-time setup, and a no-AI fallback is always available.

## A note on safety
Skills can run code. Read a skill (it's short) before installing it, this one included.

## License
MIT. Use it, change it, share it. Issues and suggestions welcome.
