#!/usr/bin/env python3
"""Write the README for an approved art package and zip it.

Usage:
  package.py PKGDIR manifest.json [--zip OUT.zip]

PKGDIR already holds the files, laid out per the archive structure
(00-source/, 01-master/, 02-outputs/<use>/, 03-previews/).
manifest.json (written by Claude for this job):
{
  "title": "Club event logo",
  "client": "Car Club",             "project": "2027 Spring Meet",
  "date": "2026-10-16",
  "source": "ChatGPT image, prompt: ...  (or: sent by <role>, original file name ...)",
  "changes": ["ghost pixels cleared (alpha < 16)", "letter holes cleared", ...],
  "files": {"01-master/x.png": "what it is and what to use it for", ...},
  "notes": ["Print at up to 20 in wide at 300 dpi", ...]
}
The README states that nothing was redrawn (every file is computed from the source
pixels), lists each change, and says what each file is for.
"""
import argparse, json, os, zipfile
from PIL import Image


def dims(p):
    try:
        with Image.open(p) as im:
            dpi = im.info.get("dpi")
            return f"{im.width}x{im.height}" + (f" @ {round(dpi[0])} dpi" if dpi else "")
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pkgdir"); ap.add_argument("manifest")
    ap.add_argument("--zip", default=None)
    a_ = ap.parse_args()
    m = json.load(open(a_.manifest))
    L = [f"{m.get('title', 'Artwork')}", "=" * len(m.get("title", "Artwork")), "",
         f"Client: {m.get('client', '')}    Project: {m.get('project', '')}    Date: {m.get('date', '')}", "",
         "Source", "------", m.get("source", ""), "",
         "Nothing was redrawn: every file is computed from the source pixels.", "",
         "Changes", "-------"] + [f"- {c}" for c in m.get("changes", [])] + ["", "Files", "-----"]
    for rel, what in m.get("files", {}).items():
        p = os.path.join(a_.pkgdir, rel)
        L.append(f"- {rel}  [{dims(p)}]" if os.path.exists(p) else f"- {rel}  [MISSING]")
        L.append(f"    {what}")
    if m.get("notes"):
        L += ["", "Notes", "-----"] + [f"- {n}" for n in m["notes"]]
    open(os.path.join(a_.pkgdir, "README.txt"), "w").write("\n".join(L) + "\n")
    missing = [r for r in m.get("files", {}) if not os.path.exists(os.path.join(a_.pkgdir, r))]
    if a_.zip:
        with zipfile.ZipFile(a_.zip, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(a_.pkgdir):
                for f in files:
                    full = os.path.join(root, f)
                    z.write(full, os.path.relpath(full, a_.pkgdir))
        print("zip", a_.zip, os.path.getsize(a_.zip) // 1024, "KB")
    print("README written;", "missing:", missing or "none")


if __name__ == "__main__":
    main()
