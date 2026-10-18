# Archiving finished art

Where packages go is **set by the person**, not by the skill. Read `config.json` beside
`SKILL.md`:

```json
{ "owner": "Name", "archive_root": "C:\\path\\to\\Digital Assets",
  "scripts_home": "C:\\path\\to\\Digital Assets\\_Common\\art-prep-scripts",
  "package_path": "{client}\\Artwork\\{title} {yyyy-mm}",
  "clients": ["Client A", "Project B"], "root_readme": "README.md" }
```
If it's missing, ask: "Where should finished packages go?" (and the scripts folder), offer to
save the answer in `config.json`, and carry on. If the archive root has a `README.md`,
**read it before filing**: it wins over anything here (layout, naming, versions).

## Default layout (when the root has no README of its own)
```
<archive_root>\
  _Common\                      shared: brand, fonts, templates, scripts
  <Client or Project>\
    Artwork\<Title YYYY-MM>\    art-prep packages
    Designs\<Item>\             native working files (.lds, .empf, .3mf/.stl, ...)
    Reference\                  what the client sent, scans, photos
```

## Rules
- Use the existing client/project folder when one matches; for a new one, ask, then create it
  with the same three subfolders.
- Package layout inside: `00-source` (original exactly as received, name ends `_ORIGINAL`,
  never edited), `01-master`, `02-outputs\<use>`, `03-previews`, `README.txt`.
- Never overwrite a released package (sent, approved, produced): a revision is
  `<Title> <YYYY-MM> v2`.
- The README records the source (AI prompt if any) and every change.
- Keep one client's customer details out of other clients' notes.
- Art from other people: keep their files, leave personal details (emails, phones,
  addresses) out of README and file names.
- Device project files (a Leonardo .lds, an eufyMake .empf) go in `Designs\<Item>\`, named
  `<Item>_<variant>_<device>.<ext>`.

## Doing the copy
- If the archive folder is connected (the linked computer), ask once ("File it in
  <client>\Artwork\<title>?") and copy only after a yes. Moves and deletes need their OK.
- Large files: the folder tool may reject files over ~30 MB. Send those through the chat
  file-send first, then commit them by the file id it returns; small files can go directly.
- Not connected: hand over the ZIP and give the exact folder to put it in.
- After copying, list the destination and check the file count and sizes.
