# radityobw.github.io

Personal developer portfolio & GitHub Pages root hub for **Radityo Budi Waskito (`radityobw`)**, showcasing all public repositories (SIDIK, SIDIK-ML, Langkah Kecil, and more) plus root `robots.txt` (RFC 9309), personal favicons, and auto-discovered project sitemaps.

## How Auto-Sync Works

- `build_site.py` queries `https://api.github.com/users/radityobw/repos` (falling back to `repos_snapshot.json` when offline) and renders:
  - **Featured Projects** (`SIDIK`, `SIDIK-ML`, `langkah-kecil`, plus any starred/GitHub-Pages repo)
  - **All Public Repositories** directory (automatically including new public repositories)
  - **Root `robots.txt`, `sitemap.xml`, `sitemap.txt`**, automatically linking every repository with `has_pages == true` (`https://radityobw.github.io/<repo>/sitemap.xml`).
- `.github/workflows/pages.yml` runs on every `push`, manually via `workflow_dispatch`, and daily (`02:00 UTC`) so new repositories and Pages sub-sites appear automatically.

## Setup on GitHub

1. Create a public GitHub repository named **`radityobw.github.io`** under `github.com/radityobw`.
2. Push this directory to `main` (run from the folder that contains this repository):
   ```powershell
   cd radityobw.github.io
   git init -b main
   git add .
   git commit -m "feat: add auto-syncing personal GitHub Pages portfolio and root sitemaps"
   git remote add origin https://github.com/radityobw/radityobw.github.io.git
   git push -u origin main
   ```
3. On GitHub **Settings -> Pages**, choose **GitHub Actions** as the source (pre-rendered root `index.html` / `robots.txt` / `sitemap.xml` are also included as branch fallback).
4. Once `https://radityobw.github.io/` is live, verify it in Google Search Console, submit `sitemap.xml`, and re-submit `sitemap.xml` on `SIDIK` and `SIDIK-ML`.
