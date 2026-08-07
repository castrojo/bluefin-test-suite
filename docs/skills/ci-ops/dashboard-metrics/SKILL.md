---
name: dashboard-metrics
version: "1.0"
last_updated: "2026-07-28"
id: dashboard-metrics
one_line_purpose: Read and extend the live testsuite dashboard metrics.
entry_point: docs/skills/ci-ops/dashboard-metrics/SKILL.md
category: ci-ops
mcp_compliance_level: partial
status: active
dependencies: []
tags: [dashboard, metrics, astro, telemetry]
description: "How to read and contribute to the live test dashboard metrics. Load when updating metrics collection or interpreting dashboard data."
metadata:
  type: pattern
  audience: agents
  maturity: stable
---
# QA Dashboard & Metrics compilation

## Overview
This skill guides agents through modifying, compiling, and deploying the QA dashboard located in `dashboard/` and managing its serverless static-site data pipelines.

## When to Use
- Modifying Astro page components (`index.astro`, `run/[id].astro`, headers, layouts, logs viewer)
- Adjusting the python compilation pipeline (`compile_data.py`, `convert_behave.py`)
- Troubleshooting Pagefind search indexing or broken CSS asset paths on the custom domain
- Updating pages deployment actions (`publish-to-pages.yml`)

## When NOT to Use
- Writing or debugging GDM/AT-SPI behave test scenarios inside `tests/**` — use `gnome.md` or `behave.md`
- Modifying Argo/KubeVirt cluster infrastructure manifests — use `projectbluefin/lab` repo
- Adjusting core reusable workflow configurations (`e2e.yml`) — use `e2e-workflow.md`

## Core Process

1. **Path-Robust Script Design**: When writing python aggregation or data conversion scripts under `dashboard/scripts/`, never hardcode relative string paths like `./raw-runs` or `./src/data/`. Execution directories differ between local development and CI runs. Always resolve path coordinates dynamically relative to the script's actual directory:
   ```python
   from pathlib import Path
   SCRIPT_DIR = Path(__file__).resolve().parent
   DASHBOARD_DIR = SCRIPT_DIR.parent
   RUNS_DIR = DASHBOARD_DIR / "src" / "data" / "runs"
   ```

2. **Build-Time Compilation Power**: Take full advantage of Astro's build-time static generation. Instead of loading logs client-side at runtime, import raw run JSONs in the frontmatter of your Astro pages using Vite globbing:
   ```typescript
   const runFiles = import.meta.glob('../data/runs/*.json', { eager: true });
   const runs = Object.entries(runFiles).map(([path, content]: [string, any]) => ({
     id: path.split('/').pop().replace('.json', ''),
     ...(content.default || content)
   }));
   ```
   Compute aggregations, pass rates, trend lists, and top failing scenarios during the static build, resulting in instant load times for users.

3. **Inline Script Bypasses**: Astro typechecks `<script>` blocks by default. To prevent TypeScript compiler errors (such as `Property 'style' does not exist on type 'Element'`) when writing standard client-side vanilla JavaScript, use the `is:inline` Astro directive:
   ```html
   <script is:inline>
     // Vanilla JS runs verbatim on client-side with no strict TS compilation checks
     document.querySelectorAll('.items').forEach(el => el.style.display = 'none');
   </script>
   ```

4. **Client-Side Telemetry Fetching**: To integrate live, dynamic infrastructure status (like KubeVirt node states and active semaphore VM slots) that change rapidly, fetch the latest compiled JSON from raw GitHub Pages endpoints, and implement an offline-safe local fallback `SEED` dataset:
   ```javascript
   const TELEMETRY_URL = "https://raw.githubusercontent.com/projectbluefin/lab/main/docs/data/factory-stats.json";
   async function getLiveTelemetry() {
     try {
       const res = await fetch(TELEMETRY_URL);
       const stats = await res.json();
       updateNodesDOM(stats);
     } catch (e) {
       console.warn("Fallback to offline dataset:", e);
     }
   }
   ```

5. **Build-Time SSG Data Fetching (Astro Frontmatter)**: For high-performance landing page rendering with zero dynamic scraping lag, fetch external JSON datasets (like `factory-stats.json` or individual suite JSON files) during build time inside Astro's frontmatter blocks. This converts raw runtime REST fetching into statically pre-rendered HTML cards, tables, and charts:
   ```typescript
   // src/pages/index.astro
   const statsRes = await fetch('https://projectbluefin.github.io/lab/data/factory-stats.json');
   const stats = statsRes.ok ? await statsRes.json() : {};
   ```

6. **Node-Based Markdown Skills Loader**: Standard Astro Content Collections cannot access files located outside the dashboard's `src/` folder (such as standard repository documentation in `docs/skills` or a sibling repository like `../common/docs/skills`). Bypass this restriction by writing a dynamic build-time filesystem loader in `src/utils/getSkills.js` utilizing `gray-matter` for YAML parsing and `marked` for Markdown rendering.

7. **Pagefind Search Indexing for Dynamically Loaded Skills**: Enable Pagefind search on dynamically loaded Markdown files by adding `data-pagefind-body` directly on the `<main>` or `<article>` element containing the rendered skill body, and use Pagefind metadata selectors (such as `data-pagefind-meta="category"`) to expose tags to the client-side search component.

8. **Astro custom base URL constraints**: The custom domain `qa.projectbluefin.io` is mapped to the root of the site. Therefore, when the custom domain is active, `astro.config.mjs` MUST keep `base: '/'` and `site: 'https://qa.projectbluefin.io'`. Do not change them to sub-paths.

9. **Deploy CNAME Preservation**: Deployment scripts that reset the `gh-pages` branch will wipe out the repository's `CNAME` setting, returning a 404 on the custom domain. The Pages deploy workflow must explicitly rewrite `qa.projectbluefin.io` to a `CNAME` file inside the deployment root on every run:
   ```yaml
   - name: Deploy Compiled Dashboard to gh-pages
     run: |
       cd old-gh-pages
       find . -maxdepth 1 ! -name '.' ! -name '..' ! -name '.git' -exec rm -rf {} +
       cp -r ../dashboard/dist/* .
       touch .nojekyll
       echo "qa.projectbluefin.io" > CNAME  # MUST PRESERVE
       git add . && git commit -m "Deploy Astro QA dashboard"
       git push origin gh-pages
   ```

10. **Astro major upgrades are gated by `@astrojs/tailwind`**: `publish-to-pages.yml` runs `npm ci`, which enforces peer ranges strictly. `@astrojs/tailwind@6.x` declares `peer astro@"^3.0.0 || ^4.0.0 || ^5.0.0"` and has no release supporting astro 6+. Bumping `dashboard/package.json` past astro 5 makes every scheduled Pages run fail with `npm error code ERESOLVE`. `renovate.json` pins `astro` to `<6.0.0` for `dashboard/package.json` for this reason. Before lifting that pin, first migrate off `@astrojs/tailwind` to `@tailwindcss/vite`, and verify locally with `cd dashboard && rm -rf node_modules && npm ci && npm run build` — `npm install` alone is not sufficient, because it resolves differently than `npm ci`.

11. **`publish-to-pages.yml` is not exercised by PR checks**: the workflow only triggers on `schedule`, `workflow_dispatch`, and pushes to `main` under `dashboard/**`. A dependency PR can therefore merge fully green and only break the dashboard hours later on the next 2-hourly cron. Any PR touching `dashboard/package.json`, `dashboard/package-lock.json`, or `dashboard/scripts/**` must be validated locally with `npm ci && npm run build` before merge.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I will hardcode `./raw-runs` in my script since I am running it from the root." | Someone else or the GHA run will execute it from another folder and fail with a directory mismatch. Always resolve paths relative to the script location. |
| "Astro should fetch all logs from a remote database in the browser." | Fetching hundreds of logs in client-side JS introduces major latency. Compiling them statically at build-time using `import.meta.glob` is faster and completely serverless. |
| "GitHub handles the custom domain automatically, no need to push CNAME." | Cleaning the pages branch during deploy deletes the CNAME file, which instantly breaks the custom domain. Always write CNAME back during the build. |
| "A dependency bump PR is green, so the dashboard still builds." | `publish-to-pages.yml` never runs on pull requests. Green PR checks say nothing about `npm ci`; run it locally before merging any `dashboard/` dependency change. |

## Red Flags
- Setting `base: '/testsuite/'` in `astro.config.mjs` while deploying to the custom domain `qa.projectbluefin.io` (breaks CSS andPagefind assets).
- Adding complex TypeScript type assertions inside a vanilla JS client-side script tag when `<script is:inline>` would safely bypass them.
- Creating static aggregations that fail silently when a directory is empty instead of logging a meaningful exception.
- Forgetting to write the `CNAME` file inside the Pages deploy step, causing domain 404s on the next push.

## Verification
- [ ] Astro build passes with **0 errors and 0 warnings**: `cd dashboard && npm run build`
- [ ] Pagefind client-side search index is compiled successfully.
- [ ] Path resolution in Python scripts works correctly from any folder directory.
- [ ] Custom domain `CNAME` file generation is included in the `publish-to-pages.yml` file.
