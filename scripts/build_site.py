"""Assemble the deployable site in site/ from each page's source folder.

Each page keeps living where its owner works on it; this script copies the
current versions into one folder that publish_site.py uploads:

    site/index.html              landing page (hand-written, never overwritten)
    site/shock/                  shock-formation viewer   <- shock viewer/
    site/race/                   finite-volume race        <- Finite volume solver/
    site/pinn/                   live ONNX PINN page       <- web/
    site/allen-cahn/             Allen-Cahn simulator      <- allen_cahn/js/
    site/data/reference_json/    Burgers references used by the race
    site/data/allen_cahn/        equilibria and PINN guesses used by the simulator

Every copied page gets a small "back to all demos" link. Links use explicit
.../index.html paths because CloudFront only serves index.html at the site root.

Run from the repo root after changing any page, then commit site/:
    python scripts/build_site.py
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

# (source, destination inside site/)
PAGES = {
    "shock": [("shock viewer/index.html", "index.html"),
              ("shock viewer/shock_viewer.js", "shock_viewer.js")],
    "race": [("Finite volume solver/race_solver.html", "index.html"),
             ("Finite volume solver/burgers_fv.js", "burgers_fv.js")],
    "pinn": [("web/index.html", "index.html"),
             ("web/pinn.onnx", "pinn.onnx")],
    "allen-cahn": [("allen_cahn/js/simulator.html", "index.html"),
                   ("allen_cahn/js/allen_cahn.js", "allen_cahn.js")],
}
DATA = {
    "data/reference_json": "ref_nu*.json",      # the race needs only the ref_ files
    "data/allen_cahn": "*.json",
}

# A plain link in the page flow (a floating button covered page titles on phones).
BACK_LINK = (
    '<nav style="max-width:980px;margin:0 auto;padding:12px 16px 0;'
    'font:14px system-ui,sans-serif"><a href="../index.html" '
    'style="color:inherit;opacity:.7;text-decoration:none">&larr; All demos</a></nav>'
)


def add_back_link(html: str) -> str:
    i = html.find("<body")
    if i < 0:
        return html
    j = html.find(">", i) + 1
    return html[:j] + "\n" + BACK_LINK + html[j:]


def main():
    SITE.mkdir(exist_ok=True)
    if not (SITE / "index.html").exists():
        raise SystemExit("site/index.html (the landing page) is missing")

    for page, files in PAGES.items():
        out = SITE / page
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        for src, dst in files:
            src_path = ROOT / src
            if not src_path.exists():
                raise SystemExit(f"missing source for {page}: {src}")
            if dst.endswith(".html"):
                (out / dst).write_text(add_back_link(src_path.read_text(encoding="utf-8")),
                                       encoding="utf-8")
            else:
                shutil.copy2(src_path, out / dst)
            print(f"{src:45s} -> site/{page}/{dst}")

    for folder, pattern in DATA.items():
        out = SITE / folder
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        files = sorted((ROOT / folder).glob(pattern))
        if not files:
            raise SystemExit(f"no {pattern} files in {folder}")
        for f in files:
            shutil.copy2(f, out / f.name)
            print(f"{str(f.relative_to(ROOT)):45s} -> site/{folder}/{f.name}")

    total = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file())
    print(f"\nsite/ is ready: {total / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
