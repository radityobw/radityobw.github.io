"""Auto-sync personal developer portfolio and root GitHub Pages hub for radityobw."""

import argparse
import html
import json
import os
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent
GITHUB_USER = "radityobw"
BASE_URL = "https://radityobw.github.io"
GSC_TOKEN = "6y-5Cff0WkeBj7_uWju39rv0nQnqmEgw81an57VJkGg"
PRIORITY_FEATURED = ("SIDIK", "SIDIK-ML", "langkah-kecil")
IGNORED_REPOS = {GITHUB_USER.lower(), f"{GITHUB_USER.lower()}.github.io"}

PYPI_BADGES: Dict[str, str] = {
    "SIDIK": "https://img.shields.io/pypi/v/sidik?label=PyPI&color=0ea5e9&cacheSeconds=3600",
    "SIDIK-ML": "https://img.shields.io/pypi/v/sidik-ml?label=PyPI&color=f59e0b&cacheSeconds=3600",
}
RELEASE_BADGES: Dict[str, str] = {
    "SIDIK": "https://img.shields.io/github/v/release/radityobw/SIDIK?label=Release&color=0284c7&cacheSeconds=3600",
    "SIDIK-ML": "https://img.shields.io/github/v/release/radityobw/SIDIK-ML?label=Release&color=ea580c&cacheSeconds=3600",
}


def _clean_text(val: Optional[str]) -> str:
    if not val:
        return ""
    return val.replace("\u2014", "-").strip()


def _load_snapshot() -> List[Dict[str, Any]]:
    snap = ROOT_DIR / "repos_snapshot.json"
    if not snap.is_file():
        return []
    data = json.loads(snap.read_text(encoding="utf-8"))
    return [dict(r) for r in data if isinstance(r, dict)]


def _fetch_public_repos(offline: bool = False) -> tuple[List[Dict[str, Any]], str]:
    snapshot = _load_snapshot()
    snap_by_name = {r["name"].lower(): r for r in snapshot if r.get("name")}
    repos: Optional[List[Dict[str, Any]]] = None
    source = "offline_snapshot"

    if not offline:
        headers = {
            "User-Agent": "radityobw-github-pages-builder",
            "Accept": "application/vnd.github+json",
        }
        tok = os.environ.get("GITHUB_TOKEN", "").strip()
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        try:
            url = f"https://api.github.com/users/{GITHUB_USER}/repos?type=owner&sort=updated&per_page=100"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            if isinstance(raw, list) and raw:
                repos = [r for r in raw if isinstance(r, dict) and not r.get("fork")]
                source = "github_api"
        except Exception:
            repos = None

    if repos is None:
        repos = snapshot

    filtered: List[Dict[str, Any]] = []
    for rp in repos:
        name = str(rp.get("name", "")).strip()
        if not name or name.lower() in IGNORED_REPOS or rp.get("fork"):
            continue
        fallback = snap_by_name.get(name.lower(), {})
        desc = _clean_text(rp.get("description")) or _clean_text(fallback.get("description"))
        lang = _clean_text(rp.get("language")) or _clean_text(fallback.get("language")) or "Repository"
        filtered.append({
            "name": name,
            "html_url": str(rp.get("html_url") or f"https://github.com/{GITHUB_USER}/{name}"),
            "description": desc or f"Public repository {name} by {GITHUB_USER}.",
            "language": lang,
            "stargazers_count": int(rp.get("stargazers_count") or 0),
            "has_pages": bool(rp.get("has_pages") or fallback.get("has_pages")),
            "homepage": _clean_text(rp.get("homepage")) or _clean_text(fallback.get("homepage")),
        })

    priority_map = {n.lower(): idx for idx, n in enumerate(PRIORITY_FEATURED)}
    filtered.sort(key=lambda r: (priority_map.get(r["name"].lower(), 999), -int(r["stargazers_count"]), r["name"].lower()))
    return filtered, source


def _render_card(repo: Dict[str, Any], featured: bool) -> str:
    name = repo["name"]
    esc_name = html.escape(name)
    esc_desc = html.escape(repo["description"])
    esc_lang = html.escape(repo["language"])
    esc_repo_url = html.escape(repo["html_url"])
    homepage = repo.get("homepage") or (f"{BASE_URL}/{name}/" if repo.get("has_pages") else "")

    accent_cls = "featured-card" if featured else "repo-card"
    if name == "SIDIK":
        accent_cls += " accent-blue"
    elif name == "SIDIK-ML":
        accent_cls += " accent-amber"
    elif name == "langkah-kecil":
        accent_cls += " accent-green"

    badges_html = ""
    if name in PYPI_BADGES:
        pypi_pkg = name.lower()
        rel_img = RELEASE_BADGES.get(name, "")
        badges_html = (
            f'\n          <div class="badges">'
            f'<a href="https://pypi.org/project/{pypi_pkg}/"><img src="{PYPI_BADGES[name]}" alt="{esc_name} PyPI" /></a>'
            + (f'<a href="{esc_repo_url}/releases/latest"><img src="{rel_img}" alt="{esc_name} Release" /></a>' if rel_img else "")
            + "</div>"
        )

    actions = [f'<a class="btn primary" href="{esc_repo_url}">GitHub</a>']
    if homepage:
        lbl = "Documentation" if name in ("SIDIK", "SIDIK-ML") else "Website"
        actions.insert(0, f'<a class="btn docs" href="{html.escape(homepage)}">{lbl}</a>')
    if name in ("SIDIK", "SIDIK-ML"):
        actions.append(f'<a class="btn" href="https://pypi.org/project/{name.lower()}/">PyPI</a>')

    return (
        f'        <article class="card {accent_cls}">\n'
        f'          <div class="card-top">\n'
        f'            <h3>{esc_name}</h3>\n'
        f'            <span class="lang-pill">{esc_lang}</span>\n'
        f'          </div>\n'
        f'          <p>{esc_desc}</p>{badges_html}\n'
        f'          <div class="links">{"".join(actions)}</div>\n'
        f'        </article>'
    )


def build_site(out_dir: Path, offline: bool = False, update_root: bool = False) -> None:
    repos, source = _fetch_public_repos(offline=offline)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    featured_names = set(PRIORITY_FEATURED)
    featured = [r for r in repos if r["name"] in featured_names or r["has_pages"] or r["stargazers_count"] > 0]
    others = [r for r in repos if r not in featured]

    pages_repos = [r["name"] for r in repos if r["has_pages"]]
    sitemap_urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/{n}/" for n in pages_repos]
    sitemap_refs = [f"Sitemap: {BASE_URL}/sitemap.xml"] + [f"Sitemap: {BASE_URL}/{n}/sitemap.xml" for n in pages_repos]

    robots_txt = "User-agent: *\nAllow: /\n\n" + "\n".join(sitemap_refs) + "\n"
    sitemap_txt = "\n".join(sitemap_urls) + "\n"

    url_nodes = []
    for idx, u in enumerate(sitemap_urls):
        prio = "1.0" if idx <= 1 else "0.9"
        url_nodes.append(
            f"  <url>\n"
            f"    <loc>{html.escape(u)}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            f"  </url>"
        )
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(url_nodes)
        + "\n</urlset>\n"
    )

    ld_items = []
    for idx, rp in enumerate(repos, 1):
        ld_items.append({
            "@type": "ListItem",
            "position": idx,
            "name": rp["name"],
            "url": rp["homepage"] or rp["html_url"],
        })

    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": "Radityo Budi Waskito (radityobw)",
                "alternateName": "radityobw GitHub Pages",
                "url": f"{BASE_URL}/",
            },
            {
                "@type": "Person",
                "name": "Radityo Budi Waskito",
                "alternateName": GITHUB_USER,
                "url": f"{BASE_URL}/",
                "sameAs": [f"https://github.com/{GITHUB_USER}"] + [rp["html_url"] for rp in featured],
            },
            {
                "@type": "ItemList",
                "name": "Public GitHub Repositories by Radityo Budi Waskito",
                "numberOfItems": len(repos),
                "itemListElement": ld_items,
            },
        ],
    }, indent=2)

    featured_html = "\n".join(_render_card(r, featured=True) for r in featured)
    others_html = "\n".join(_render_card(r, featured=False) for r in others)

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Radityo Budi Waskito (radityobw) - Projects, Security Tools &amp; Repositories</title>
  <meta name="description" content="Official developer portfolio and repository directory of Radityo Budi Waskito (radityobw): SIDIK polyglot SAST & 8-ecosystem SCA, SIDIK-ML Non-ANN AI, Langkah Kecil Godot game, web apps, and programming projects." />
  <meta name="author" content="Radityo Budi Waskito" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{BASE_URL}/" />
  <link rel="icon" href="/favicon.ico" sizes="48x48" />
  <link rel="icon" type="image/png" href="/favicon-48x48.png" sizes="48x48" />
  <link rel="icon" type="image/png" href="/favicon-192x192.png" sizes="192x192" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180" />

  <meta name="google-site-verification" content="{GSC_TOKEN}" />

  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Radityo Budi Waskito (radityobw)" />
  <meta property="og:title" content="Radityo Budi Waskito (radityobw) - Developer Portfolio &amp; Open Source Projects" />
  <meta property="og:description" content="Cybersecurity tools (SIDIK, SIDIK-ML), educational games (Langkah Kecil), and open-source software repositories by radityobw." />
  <meta property="og:url" content="{BASE_URL}/" />
  <meta property="og:image" content="{BASE_URL}/avatar.png" />

  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="Radityo Budi Waskito (radityobw) - Open Source Projects" />
  <meta name="twitter:description" content="Explore SIDIK, SIDIK-ML, Langkah Kecil, and all public repositories by radityobw." />
  <meta name="twitter:image" content="{BASE_URL}/avatar.png" />

  <script type="application/ld+json">
  {json_ld}
  </script>

  <style>
    :root {{
      --bg: #0b1120;
      --bg-card: #111827;
      --border: #1e293b;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --blue: #0ea5e9;
      --amber: #f59e0b;
      --green: #10b981;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Arial, sans-serif;
      background: radial-gradient(circle at top right, #102a43 0%, var(--bg) 52%);
      color: var(--text);
      line-height: 1.6;
    }}
    a {{ color: #38bdf8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1080px; margin: 0 auto; padding: 40px 20px 64px; }}
    .hero {{
      background: linear-gradient(145deg, #0f172a 0%, #111c33 100%);
      border: 1px solid #1e3a5f;
      border-radius: 18px;
      padding: 32px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      box-shadow: 0 18px 40px rgba(2, 6, 23, 0.5);
    }}
    .hero-left {{ display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }}
    .hero-left img {{
      width: 84px;
      height: 84px;
      border-radius: 20px;
    }}
    h1 {{ margin: 0 0 6px; font-size: clamp(24px, 3.6vw, 34px); color: #f8fafc; }}
    .sub {{ margin: 0; color: #cbd5e1; max-width: 640px; font-size: 15.5px; }}
    .hero-actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    section {{ margin-top: 38px; }}
    h2 {{
      font-size: 21px;
      color: #f8fafc;
      margin: 0 0 14px;
      border-left: 4px solid var(--blue);
      padding-left: 12px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .accent-blue {{ border-top: 4px solid var(--blue); }}
    .accent-amber {{ border-top: 4px solid var(--amber); }}
    .accent-green {{ border-top: 4px solid var(--green); }}
    .card-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }}
    .card-top h3 {{ margin: 0; font-size: 17.5px; color: #f8fafc; word-break: break-word; }}
    .lang-pill {{
      flex-shrink: 0;
      font-size: 11.5px;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 999px;
      background: #172033;
      border: 1px solid #293548;
      color: #bae6fd;
    }}
    .card p {{ margin: 0; color: var(--muted); font-size: 14px; flex-grow: 1; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .btn {{
      display: inline-block;
      padding: 7px 13px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      background: #1e293b;
      color: #f8fafc;
      border: 1px solid #334155;
    }}
    .btn.docs {{
      background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%);
      border-color: #38bdf8;
      color: #ffffff;
    }}
    .btn:hover {{ text-decoration: none; filter: brightness(1.08); }}
    footer {{
      margin-top: 48px;
      padding-top: 18px;
      border-top: 1px solid var(--border);
      font-size: 13px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <div class="hero-left">
        <img src="/avatar.png" alt="Radityo Budi Waskito (@{GITHUB_USER})" width="84" height="84" />
        <div>
          <h1>Radityo Budi Waskito (<code>@{GITHUB_USER}</code>)</h1>
          <p class="sub">
            Informatics &amp; Cybersecurity developer building offline static security analyzers (<strong>SIDIK</strong>, <strong>SIDIK-ML</strong>), educational Godot software (<strong>Langkah Kecil</strong>), web apps, and open-source utilities.
          </p>
        </div>
      </div>
      <div class="hero-actions">
        <a class="btn docs" href="https://github.com/{GITHUB_USER}">GitHub Profile</a>
        <a class="btn" href="{BASE_URL}/SIDIK/">SIDIK</a>
        <a class="btn" href="{BASE_URL}/SIDIK-ML/">SIDIK-ML</a>
        <a class="btn" href="https://jurnal.mediaakademik.com/index.php/jma/article/view/9068/6647">JMA Paper</a>
      </div>
    </header>

    <section>
      <h2>Featured Projects &amp; Active Research Software</h2>
      <div class="grid">
{featured_html}
      </div>
    </section>

    <section>
      <h2>All Public GitHub Repositories ({len(repos)} Total)</h2>
      <div class="grid">
{others_html}
      </div>
    </section>

    <footer>
      <span>Radityo Budi Waskito (@{GITHUB_USER}) - Auto-synced from GitHub API ({today})</span>
      <span><a href="https://github.com/{GITHUB_USER}">GitHub</a> | <a href="{BASE_URL}/SIDIK/">SIDIK</a> | <a href="{BASE_URL}/SIDIK-ML/">SIDIK-ML</a> | <a href="/sitemap.xml">Sitemap</a></span>
    </footer>
  </div>
</body>
</html>
"""

    targets = [out_dir]
    if update_root and out_dir.resolve() != ROOT_DIR.resolve():
        targets.append(ROOT_DIR)

    for target in targets:
        if target.resolve() != ROOT_DIR.resolve() and target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(index_html, encoding="utf-8")
        (target / "robots.txt").write_text(robots_txt, encoding="utf-8")
        (target / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
        (target / "sitemap.txt").write_text(sitemap_txt, encoding="utf-8")
        if target.resolve() != ROOT_DIR.resolve():
            for asset in (".nojekyll", "avatar.png", "favicon.ico", "favicon-48x48.png", "favicon-192x192.png", "apple-touch-icon.png"):
                src = ROOT_DIR / asset
                if src.is_file():
                    shutil.copy2(src, target / asset)

    print(f"Built root portfolio ({len(repos)} repos, pages={pages_repos}, source={source}) -> {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build auto-synced root GitHub Pages portfolio for radityobw.")
    parser.add_argument("--out", default="_site", help="Output directory (default: _site)")
    parser.add_argument("--offline", action="store_true", help="Use bundled repos_snapshot.json without network API calls")
    parser.add_argument("--update-root", action="store_true", help="Also write rendered index.html, robots.txt, and sitemaps into repo root")
    args = parser.parse_args()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT_DIR / out_path
    build_site(out_path, offline=args.offline, update_root=args.update_root)


if __name__ == "__main__":
    main()
