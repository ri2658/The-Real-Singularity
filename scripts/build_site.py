"""Assemble the deployable site in site/ from each page's source folder.

Each page keeps living where its owner works on it; this script copies the
current versions into one folder that publish_site.py uploads:

    site/index.html              landing page (hand-written, never overwritten)
    site/beat1/, site/beat2/     story page of each beat   <- story/beat1.html, story/beat2.html
    site/shock/                  shock-formation viewer   <- shock viewer/
    site/race/                   finite-volume race        <- Finite volume solver/
    site/pinn/                   live ONNX PINN page       <- web/
    site/loss-vs-truth/          training loss vs. error   <- burgers/js/loss_truth.html
    site/allen-cahn/             Allen-Cahn simulator      <- allen_cahn/js/
    site/viscosity/              PINN vs. exact, three nu  <- burgers/js/viscosity.html
    site/hilltop/                hilltop escape experiment <- allen_cahn/js/hilltop.html
    site/correction/             PINN guesses corrected    <- allen_cahn/js/correction.html
    site/data/reference_json/    Burgers references used by the race
    site/data/allen_cahn/        equilibria and PINN guesses used by the simulator
    site/data/loss_truth/        training histories for the loss-vs-truth page
    site/data/viscosity/         PINN predictions for the viscosity page
    site/data/race_pinn/         one PINN per viscosity for the race (ONNX)

Every copied page gets the site-wide navigation bar (home, Beat 1, Beat 2;
see BEATS), and each demo page also gets a previous / next bar at the bottom
that walks through its beat in story order. The landing page's bar is
refreshed between its <!-- NAV --> markers. Every copied page also loads the
site font, Inter (see FONT), the colour palette (see PALETTE) and KaTeX (see MATH): write math in the page sources as \\( ... \\) inline or \\[ ... \\] for
a display line; text that JavaScript writes later is rendered too. Links use explicit
.../index.html paths because CloudFront only serves index.html at the site root.

Run from the repo root after changing any page, then commit site/:
    python scripts/build_site.py
"""

import hashlib
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

# (source, destination inside site/)
PAGES = {
    "beat1": [("story/beat1.html", "index.html")],
    "beat2": [("story/beat2.html", "index.html")],
    "shock": [("shock viewer/index.html", "index.html"),
              ("shock viewer/shock_viewer.js", "shock_viewer.js")],
    "race": [("Finite volume solver/race_solver.html", "index.html"),
             ("Finite volume solver/burgers_fv.js", "burgers_fv.js")],
    "pinn": [("web/index.html", "index.html"),
             ("web/pinn.onnx", "pinn.onnx")],
    "allen-cahn": [("allen_cahn/js/simulator.html", "index.html"),
                   ("allen_cahn/js/allen_cahn.js", "allen_cahn.js")],
    "loss-vs-truth": [("burgers/js/loss_truth.html", "index.html")],
    "viscosity": [("burgers/js/viscosity.html", "index.html")],
    "correction": [("allen_cahn/js/correction.html", "index.html"),
                   ("allen_cahn/js/allen_cahn.js", "allen_cahn.js")],
    "hilltop": [("allen_cahn/js/hilltop.html", "index.html"),
                ("allen_cahn/js/allen_cahn.js", "allen_cahn.js"),
                ("allen_cahn/js/hilltop.js", "hilltop.js")],
}
DATA = {
    "data/reference_json": "ref_nu*.json",      # the race needs only the ref_ files
    "data/allen_cahn": "*.json",
    "data/loss_truth": "runs.json",             # from scripts/export_loss_truth.py
    "data/viscosity": "*.json",                 # from scripts/export_viscosity.py
    "data/race_pinn": "*",                      # from scripts/export_race_onnx.py (.onnx + index.json)
}

# Site-wide navigation. The top bar shows only home and the beats; each beat's
# story page links to its demos, and the demos are chained in story order.
BEATS = [
    ("beat1", "Beat 1", "The wall of brake lights", [
        ("shock", "How the wall forms"), ("pinn", "Our PINN, live"), ("viscosity", "The breaking point"),
        ("loss-vs-truth", "The score that lies"), ("race", "The race")]),
    ("beat2", "Beat 2", "Balls in bowls", [
        ("allen-cahn", "The step-by-step simulator"), ("hilltop", "Falling off a hilltop"),
        ("correction", "Fixing the PINN's guesses")]),
]
NAV_STYLE = """<style>
.rs-nav{position:sticky;top:0;z-index:50;background:var(--bg,#fbfaf7);border-bottom:1px solid rgba(127,127,127,.25);
  font:14px/1.4 Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif}
.rs-nav,.rs-nav *,.rs-pager{box-sizing:border-box}
.rs-nav .rs-in{max-width:900px;margin:0 auto;padding:8px 16px;display:flex;align-items:center;gap:6px 18px;flex-wrap:wrap}
.rs-nav a{color:inherit;text-decoration:none;opacity:.72;padding:3px 10px;border-radius:999px;white-space:nowrap}
.rs-nav a:hover,.rs-nav a:focus-visible{opacity:1;outline:none;background:rgba(127,127,127,.14)}
.rs-nav a.on{opacity:1;font-weight:600;background:rgba(127,127,127,.18)}
.rs-nav .rs-home{font:700 15px Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;opacity:1;padding-left:0}
.rs-nav .rs-links{display:flex;align-items:center;gap:4px}
.rs-nav button.rs-theme{all:unset;box-sizing:border-box;margin-left:auto;flex:0 0 34px;display:grid;place-items:center;
  width:34px;height:34px;border-radius:999px;border:1px solid rgba(127,127,127,.35);color:inherit;cursor:pointer}
.rs-nav button.rs-theme:hover,.rs-nav button.rs-theme:focus-visible{background:rgba(127,127,127,.14);outline:none}
.rs-nav button.rs-theme svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
@media (max-width:420px){.rs-nav .rs-in{gap:6px 8px}.rs-nav a{padding:3px 7px}}
@media (min-width:1060px){.rs-nav button.rs-theme{position:absolute;right:16px;top:50%;transform:translateY(-50%)}}
:root[data-theme="dark"]{color-scheme:dark}:root[data-theme="light"]{color-scheme:light}
</style>"""
PAGER_STYLE = """<style>
.rs-pager{max-width:900px;margin:24px auto 0;padding:14px 16px 28px;border-top:1px solid rgba(127,127,127,.25);
  display:flex;flex-wrap:wrap;gap:8px 16px;justify-content:space-between;align-items:baseline;
  font:14px/1.4 Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif}
.rs-pager a{color:inherit;text-decoration:none;opacity:.8}
.rs-pager a:hover,.rs-pager a:focus-visible{opacity:1;text-decoration:underline}
.rs-pager .rs-up{opacity:.6}
.rs-pager .rs-next{font-weight:600;margin-left:auto}
</style>"""


# KaTeX from cdnjs, pinned. Only \( \) and \[ \] count as math, so dollar amounts
# stay plain text. A MutationObserver renders math in status text that the page's
# own script writes after load. <option> labels and canvas text cannot hold math.
KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"
MATH = f"""<link rel="stylesheet" href="{KATEX}/katex.min.css">
<script defer src="{KATEX}/katex.min.js"></script>
<script defer src="{KATEX}/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {{
  if (!window.renderMathInElement) return;
  var opts = {{ delimiters: [{{ left: "\\\\[", right: "\\\\]", display: true }},
                            {{ left: "\\\\(", right: "\\\\)", display: false }}],
               ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option"],
               throwOnError: false }};
  renderMathInElement(document.body, opts);
  new MutationObserver(function (muts) {{
    muts.forEach(function (m) {{
      var el = m.target.nodeType === 1 ? m.target : m.target.parentElement;
      if (el && el.isConnected && el.textContent.indexOf("\\\\(") >= 0) renderMathInElement(el, opts);
    }});
  }}).observe(document.body, {{ childList: true, subtree: true, characterData: true }});
}});
</script>"""


# One colour palette for the whole site. Every page names its colours with its own
# tokens (--bg, --pinn, --curve, ...) and points them at these, so the same thing has
# the same colour everywhere: the PINN is orange, a traditional solver or simulator is
# blue, the exact answer is neutral grey, and the three viscosities are a blue ramp
# from thick (light) to thin (dark).
PALETTE = """<style>
:root{--c-bg:#fbfaf7;--c-card:#ffffff;--c-fg:#1c2330;--c-mut:#5d6675;--c-line:#e2e1dc;--c-accent:#c2410c;
  --c-pinn:#c2410c;--c-pinn-fill:rgba(194,65,12,.16);--c-solver:#2a78d6;--c-exact:#4b5563;--c-ghost:#a9a79f;
  --c-good:#15803d;--c-bad:#b91c1c;--c-nu1:#8fbbe6;--c-nu2:#2a78d6;--c-nu3:#173f6e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--c-bg:#10151d;--c-card:#161d27;--c-fg:#e6e9ef;
  --c-mut:#98a2b3;--c-line:#2b3442;--c-accent:#fb923c;--c-pinn:#fb923c;--c-pinn-fill:rgba(251,146,60,.22);
  --c-solver:#5b9bea;--c-exact:#c3cad5;--c-ghost:#6b7380;--c-good:#4ade80;--c-bad:#f87171;
  --c-nu1:#2f5f99;--c-nu2:#5b9bea;--c-nu3:#c2dcf7}}
:root[data-theme="dark"]{--c-bg:#10151d;--c-card:#161d27;--c-fg:#e6e9ef;--c-mut:#98a2b3;--c-line:#2b3442;
  --c-accent:#fb923c;--c-pinn:#fb923c;--c-pinn-fill:rgba(251,146,60,.22);--c-solver:#5b9bea;--c-exact:#c3cad5;
  --c-ghost:#6b7380;--c-good:#4ade80;--c-bad:#f87171;--c-nu1:#2f5f99;--c-nu2:#5b9bea;--c-nu3:#c2dcf7}
</style>"""


# One font for the whole site, text and charts alike. Pages name it in their CSS and
# canvas code as "Inter, system-ui, ..."; this loads it, then asks every page to
# redraw its charts once it has arrived (each page redraws on resize).
FONT = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<script>
if (document.fonts) document.fonts.ready.then(function () { window.dispatchEvent(new Event("resize")); });
</script>"""
# Light / dark switch (button in the top bar). Without a saved choice the page
# follows the system setting; a click sets data-theme on <html>, which every
# page's CSS honours, remembers it for the other pages, and asks the charts to
# redraw. This runs in <head>, so a saved choice applies before the first paint.
THEME = """<meta name="color-scheme" content="light dark">
<style>:root{color-scheme:light dark}</style>
<script>
(function () {
  var KEY = "rs-theme", root = document.documentElement, mq = matchMedia("(prefers-color-scheme: dark)");
  // Where the choice is kept: localStorage normally. If the browser blocks site storage,
  // the choice rides along in the address instead (?theme=light), so it still carries
  // from page to page.
  var stored = (function () {
    try { localStorage.setItem(KEY + "-test", "1"); localStorage.removeItem(KEY + "-test"); return true; }
    catch (e) { return false; }
  })();
  function fromUrl() {
    var m = /[?&]theme=(light|dark)\\b/.exec(location.search);
    return m ? m[1] : null;
  }
  function load() {
    var saved = fromUrl();
    if (stored) {
      if (saved) localStorage.setItem(KEY, saved); else saved = localStorage.getItem(KEY);
    }
    if (saved === "light" || saved === "dark") root.dataset.theme = saved; else delete root.dataset.theme;
  }
  load();
  var SUN = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  var MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11z"/></svg>';
  function isDark() { return root.dataset.theme ? root.dataset.theme === "dark" : mq.matches; }
  function paint() {
    var b = document.querySelector(".rs-theme"); if (!b) return;
    var d = isDark(), label = d ? "Switch to light theme" : "Switch to dark theme";
    b.innerHTML = d ? SUN : MOON; b.setAttribute("aria-label", label); b.title = label;
  }
  window.rsToggleTheme = function () {
    var next = isDark() ? "light" : "dark";
    root.dataset.theme = next;
    if (stored) localStorage.setItem(KEY, next);
    else history.replaceState(null, "", location.pathname + "?theme=" + next + location.hash);
    paint();
    window.dispatchEvent(new Event("resize"));
  };
  document.addEventListener("DOMContentLoaded", paint);
  mq.addEventListener("change", paint);
  // A page restored by the Back / Forward buttons, or open in another tab, keeps the
  // theme it had then; re-read the saved choice so every page agrees.
  function sync() {
    var before = root.dataset.theme;
    load(); paint();
    if (root.dataset.theme !== before) window.dispatchEvent(new Event("resize"));
  }
  window.addEventListener("pageshow", function (e) { if (e.persisted) sync(); });
  // Without storage, add the choice to links to the site's other pages as they are followed.
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    if (stored || !a || !root.dataset.theme || /^[a-z]+:|^#/i.test(a.getAttribute("href"))) return;
    var h = a.getAttribute("href").split("#");
    a.setAttribute("href", h[0].replace(/[?].*$/, "") + "?theme=" + root.dataset.theme + (h[1] ? "#" + h[1] : ""));
  }, true);
  window.addEventListener("storage", function (e) { if (e.key === KEY) sync(); });
})();
</script>"""
HEAD = THEME + "\n" + PALETTE + "\n" + FONT + "\n" + MATH


def add_math(html: str) -> str:
    """Add the font and KaTeX to <head>."""
    i = html.find("</head>")
    return html if i < 0 else html[:i] + HEAD + "\n" + html[i:]


# Every page shares one content width, 900px, so the top bar, text, charts and cards
# line up from page to page. The demo pages each set their own widths, so this
# block (added after their own styles) brings them to the same edges.
WIDTH = """<style>
main{max-width:900px !important;margin-left:auto !important;margin-right:auto !important;
  padding-left:16px !important;padding-right:16px !important;box-sizing:border-box}
main :is(p,ul,ol,h1,h2,h3,figcaption,.lede,.try,.notice,.takeaways,.key,section){max-width:none !important}
/* the same four-step layout on every demo: 1 the question, 2 try it, 3 why, 4 key takeaways */
h2.step{font:700 1.15rem/1.3 Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;margin:34px 0 10px;color:var(--c-fg)}
h2.step .n{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:var(--c-accent);
  color:var(--c-bg);font:700 13px Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;margin-right:10px;vertical-align:2px}
main>h1+h2.step{margin-top:14px}
.try,.takeaways{border:0;border-top:1px solid var(--c-fg);border-bottom:1px solid var(--c-line);border-radius:0;
  background:none;padding:10px 0 12px;margin:12px 0 18px;color:var(--c-fg);font-size:15px}
.try::before{content:"Try this";display:block;font:600 11px Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  letter-spacing:.08em;text-transform:uppercase;color:var(--c-accent);margin-bottom:4px}
.takeaways ul{margin:0;padding-left:1.2em}.takeaways li{margin:0 0 8px}.takeaways li:last-child{margin-bottom:0}
.takeaways .weak{color:var(--c-accent);font-weight:600}
</style>"""


def beat_of(page):
    for key, label, title, pages in BEATS:
        if page == key or page in dict(pages):
            return key
    return None


def nav_html(current, prefix="../"):
    """Top bar; `current` is a page key (its beat is highlighted), `prefix` the path back to the site root."""
    on_beat = beat_of(current)
    links = []
    for key, label, title, pages in BEATS:
        on = ' class="on" aria-current="page"' if key == on_beat else ""
        links.append(f'<a href="{prefix}{key}/index.html"{on}>{label}</a>')
    return (f'{NAV_STYLE}\n<nav class="rs-nav" aria-label="Site"><div class="rs-in">'
            f'<a class="rs-home" href="{prefix}index.html">The Real Singularity</a>'
            f'<div class="rs-links">{"".join(links)}</div>'
            f'<button class="rs-theme" type="button" onclick="rsToggleTheme()" aria-label="Switch theme"></button>'
            f'</div></nav>')


def pager_html(page):
    """Previous / back to the beat / next, for a demo page; empty for pages outside the beats."""
    for b, (key, label, title, pages) in enumerate(BEATS):
        keys = [k for k, _ in pages]
        if page not in keys:
            continue
        i = keys.index(page)
        prev = (f'<a href="../{keys[i - 1]}/index.html">&larr; {pages[i - 1][1]}</a>' if i
                else f'<a href="../{key}/index.html">&larr; {label}: {title}</a>')
        up = f'<a class="rs-up" href="../{key}/index.html">Back to {label}</a>' if i else ""
        if i + 1 < len(keys):
            nxt = f'<a class="rs-next" href="../{keys[i + 1]}/index.html">Next: {pages[i + 1][1]} &rarr;</a>'
        elif b + 1 < len(BEATS):
            nk, nl, nt, _ = BEATS[b + 1]
            nxt = f'<a class="rs-next" href="../{nk}/index.html">Next: {nl}, {nt} &rarr;</a>'
        else:
            nxt = '<a class="rs-next" href="../index.html">Back to the start &rarr;</a>'
        return f'{PAGER_STYLE}\n<nav class="rs-pager" aria-label="{label} pages">{prev}{up}{nxt}</nav>'
    return ""


def add_nav(html: str, current: str) -> str:
    i = html.find("<body")
    if i < 0:
        return html
    j = html.find(">", i) + 1
    html = html[:j] + "\n" + nav_html(current) + html[j:]
    pager = pager_html(current)
    if pager:                      # a demo page: bring it to the shared width
        i = html.find("</head>")
        if i >= 0:
            html = html[:i] + WIDTH + "\n" + html[i:]
    k = html.rfind("</body>")
    if pager and k >= 0:
        html = html[:k] + pager + "\n" + html[k:]
    return html


def refresh_landing_nav():
    """The landing page is hand-written; only the parts between the NAV and HEAD markers are regenerated."""
    landing = SITE / "index.html"
    html = landing.read_text(encoding="utf-8")
    for (a, b), fill in ((("<!-- NAV -->", "<!-- /NAV -->"), nav_html(None, prefix="")),
                         (("<!-- HEAD -->", "<!-- /HEAD -->"), HEAD)):
        if a in html and b in html:
            start, end = html.index(a) + len(a), html.index(b)
            html = html[:start] + "\n" + fill + "\n" + html[end:]
    landing.write_text(html, encoding="utf-8")


VERSION_RE = re.compile(r'(href="(?![a-z]+:|#)[^"]*?index\.html)(\?v=[0-9a-f]+)?(?=["#])')


def version_links():
    """Add ?v=<content hash> to every link between the site's pages.

    Browsers can keep an old copy of a page and show it again without asking. Changing
    the address whenever the content changes means a reader always gets the new page.
    The hash covers the pages themselves, so it only changes when something did.
    """
    pages = sorted(SITE.rglob("*.html"))
    texts = {p: VERSION_RE.sub(r"\1", p.read_text(encoding="utf-8")) for p in pages}
    digest = hashlib.sha1("".join(texts[p] for p in pages).encode("utf-8")).hexdigest()[:8]
    for p in pages:
        p.write_text(VERSION_RE.sub(lambda m: f"{m.group(1)}?v={digest}", texts[p]), encoding="utf-8")
    print(f"page links versioned: ?v={digest}")


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
                (out / dst).write_text(add_math(add_nav(src_path.read_text(encoding="utf-8"), page)),
                                       encoding="utf-8")
            else:
                shutil.copy2(src_path, out / dst)
            print(f"{src:45s} -> site/{page}/{dst}")

    refresh_landing_nav()

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

    version_links()

    total = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file())
    print(f"\nsite/ is ready: {total / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
