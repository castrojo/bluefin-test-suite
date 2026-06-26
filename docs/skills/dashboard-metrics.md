---
name: dashboard-metrics
description: Use when modifying the QA dashboard, compiling test run JSON logs, updating Pagefind indexes, or adjusting GitHub Pages deployment workflows.
metadata:
  context7-sources:
    - /addyosmani/agent-skills
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
- Modifying Argo/KubeVirt cluster infrastructure manifests — use `testing-lab` repo
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
   const TELEMETRY_URL = "https://raw.githubusercontent.com/projectbluefin/testing-lab/main/docs/data/factory-stats.json";
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

5. **Astro custom base URL constraints**: The custom domain `qa.projectbluefin.io` is mapped to the root of the site. Therefore, when the custom domain is active, `astro.config.mjs` MUST keep `base: '/'` and `site: 'https://qa.projectbluefin.io'`. Do not change them to sub-paths.

6. **Deploy CNAME Preservation**: Deployment scripts that reset the `gh-pages` branch will wipe out the repository's `CNAME` setting, returning a 404 on the custom domain. The Pages deploy workflow must explicitly rewrite `qa.projectbluefin.io` to a `CNAME` file inside the deployment root on every run:
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

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I will hardcode `./raw-runs` in my script since I am running it from the root." | Someone else or the GHA run will execute it from another folder and fail with a directory mismatch. Always resolve paths relative to the script location. |
| "Astro should fetch all logs from a remote database in the browser." | Fetching hundreds of logs in client-side JS introduces major latency. Compiling them statically at build-time using `import.meta.glob` is faster and completely serverless. |
| "GitHub handles the custom domain automatically, no need to push CNAME." | Cleaning the pages branch during deploy deletes the CNAME file, which instantly breaks the custom domain. Always write CNAME back during the build. |

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
