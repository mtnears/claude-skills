# Archiving finished art

Set this up once for your own storage. Claude asks before copying anything.

**Root:** `<your asset folder>`. Replace this line with your path, e.g.
`C:\Users\<you>\OneDrive\Documents\Business\Digital Assets\`. If you keep a README in that
folder describing your layout, Claude reads it first and follows it over this file.

Suggested layout (client or project first, then kind of asset):
```
Digital Assets\
  _Common\                      brand, fonts, templates, jigs: used across clients
  <Client or Project>\
    Artwork\<Title YYYY-MM>\    art-prep packages go here
    Designs\<Item>\             native working files (cutter, UV printer, 3D, laser projects)
    Reference\                  photos, scans, what the client sent
```

## Where a package goes
`<root>\<Client or Project>\Artwork\<Title> <YYYY-MM>\` holding the package layout
(`00-source`, `01-master`, `02-outputs\<use>`, `03-previews`, `README.txt`).
- Use an existing client/project folder when one matches; ask before creating a new one.
- Device project files from the job go in `Designs\<Item>\`, named `<Item>_<variant>_<device>.<ext>`.
- Never overwrite a released package (sent, approved, produced): a revision becomes
  `<Title> <YYYY-MM> v2`. Cloud version history covers working edits.
- `00-source` holds the file exactly as received; never edited.
- The README records the source (AI prompt if any) and every change.

## Doing the copy
- If the asset folder is connected to the session, ask once ("File it in
  Digital Assets\<Client>\Artwork\<Title YYYY-MM>?") and copy only after a yes.
- If it isn't connected, hand over the ZIP and give the exact folder to put it in.
- Art from other people: keep their files, but leave their personal details (emails,
  phone numbers, addresses) out of README and file names.
- If no root is set yet, ask the user where finished art should live.
