# OpenSidewalkMap reference node — Curitiba

This repository is the current Curitiba reference node for [OpenSidewalkMap (OSWM)](https://github.com/kauevestena/opensidewalkmap). It demonstrates how one geographic area can configure the shared OSWM codebase, generate pedestrian-network products, and publish them as a static GitHub Pages site.

It is a working node model, not a universal template. Future nodes may use different geographic settings or automation while preserving the same submodule and static-output contracts.

## How an OSWM node fits into the project

OSWM is decentralized: each city or region can live in its own repository and pin a tested revision of the shared [`oswm_codebase`](https://github.com/kauevestena/oswm_codebase). The codebase supplies reusable generators, modules, workflows, and branding. This node supplies Curitiba-specific configuration and stores the generated data and pages served by GitHub Pages.

```text
OSWM project
├── oswm_codebase repository       reusable source and assets
└── this node repository
    ├── config.py                  Curitiba-specific configuration
    ├── oswm_codebase/             pinned Git submodule
    ├── data/                      generated data products
    ├── quality_check/             generated quality reports
    ├── statistics/                generated charts
    ├── hub/                       generated data hub, API, and watcher
    └── index.html, map.html        published entry pages
```

The node records an exact codebase commit as a gitlink. Cloning this repository does not implicitly use whatever happens to be the latest codebase revision.

## Clone and prerequisites

Prerequisites for local generation are Git, Python 3 with `venv` and `pip`, and GDAL command-line tools (notably `ogr2ogr`) for the complete data/tile pipeline. Node.js is useful for the codebase's JavaScript tests.

Clone recursively so the pinned codebase is present immediately:

```bash
git clone --recurse-submodules https://github.com/kauevestena/opensidewalkmap_beta.git
cd opensidewalkmap_beta
```

For an existing non-recursive clone:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

Create a Python environment and install the dependencies declared by the shared codebase:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r oswm_codebase/requirements.txt
```

On Debian/Ubuntu, the system dependency used by the existing workflows can be installed with:

```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev
```

## Working with the submodule

The actual contract is recorded in [`.gitmodules`](.gitmodules): the submodule path is `oswm_codebase`, its remote is `kauevestena/oswm_codebase`, and its tracking branch is `main`.

Inspect the pinned revision:

```bash
git submodule status
git -C oswm_codebase rev-parse --short HEAD
git diff --submodule=log
```

Restore the revision recorded by the current node commit:

```bash
git submodule update --init --recursive oswm_codebase
```

Deliberately test and pin a newer codebase commit:

```bash
git -C oswm_codebase fetch origin
git -C oswm_codebase checkout <tested-commit-or-origin/main>

# Run validation and review generated changes before recording the new pin.
git add oswm_codebase
git commit -m "chore: update oswm_codebase"
```

`git submodule update --remote oswm_codebase` follows the branch configured in `.gitmodules`; it is convenient, but it should not replace review and deliberate pinning. The manual [Update oswm_codebase workflow](.github/workflows/update_codebase.yml) performs this bump to the latest `origin/main` and commits only when the gitlink changes.

## Node-specific files and generated outputs

| Path | Ownership | Purpose |
|---|---|---|
| [`config.py`](config.py) | Node-specific | City name, repository identity, bounding box, zoom range, and pedestrian-tag rules |
| [`.gitmodules`](.gitmodules) | Node-specific contract | Submodule URL, path, and tracking branch |
| [`.github/workflows/`](.github/workflows/) | Node automation | Scheduled/manual generation, submodule updates, validation, and Pages deployment |
| `oswm_codebase/` | Shared, pinned | Reusable source code and assets; do not copy it into node-owned files |
| `data/` | Generated | Boundaries, raw/processed GeoParquet, PMTiles, snapshots, VRTs, versioning, and update state |
| `quality_check/` | Generated | QA maps, tables, JSON, and completeness output |
| `statistics/`, `statistics_specs/` | Generated | Dashboard pages and chart specifications |
| `hub/` | Generated | Data hub, serverless API, acquisition results, watcher pages, and feeds |
| `index.html`, `map.html`, `webmap_params.json` | Generated/published | Homepage and Webmap entry artifacts |

Generated files are committed because the repository itself is the static deployment artifact. Change their generators under `oswm_codebase/` whenever possible, regenerate, and then review the resulting node diff.

## Modules exposed by this node

- **Webmap and scrutiny snapshots:** MapLibre/PMTiles map, thematic styles, legend, popups, and printable analytical snapshots.
- **Dashboard/statistics:** interactive layer-specific and aggregate charts.
- **Data quality:** tag/geometry validation, tables, JSON reports, QA maps, external providers, and completeness analysis.
- **Routing demo:** experimental client-side pedestrian routing over generated route geometry.
- **Data hub/static API:** browsable access to GeoParquet, PMTiles, JSON, VRT, chart specifications, and other static endpoints.
- **Acquisition:** discovery of relevant projects on supported mapping platforms.
- **Watcher/RSS:** change detection, update history, pages, and feeds for relevant OSM activity.

The routing demonstration remains experimental. Prototype and deprecated components in the shared codebase are not advertised as stable node modules.

## Generate locally

Run commands from this node's root so shared scripts can read `config.py` and write node-relative outputs.

Representative targeted generators:

```bash
python oswm_codebase/webmap/create_webmap_new.py --development
python oswm_codebase/webmap/snapshot/generate_snapshot_summary.py
python oswm_codebase/datahub/datahub_index_generator.py
python oswm_codebase/datahub/API/generate_api.py
python oswm_codebase/data_quality/completeness/completeness_runner.py --silent
```

Existing orchestration scripts:

```bash
sh oswm_codebase/runners/setup.sh
sh oswm_codebase/runners/daily.sh
sh oswm_codebase/runners/weekly.sh
```

The daily and weekly jobs can access external services and rewrite a large part of the committed output tree. Use targeted generators for small UI changes and inspect `git status`/`git diff` after every run.

## Validate and serve locally

Run shared automated checks from the codebase checkout:

```bash
python oswm_codebase/tests/test_branding_manifest.py
python -m unittest discover -s oswm_codebase/tests/webmap_snapshot -p 'test_*.py'
node --test oswm_codebase/webmap/snapshot/snapshot_stats.test.mjs
git diff --check
```

Serve this node root over HTTP so manifest fetching and submodule-relative URLs behave as they do on GitHub Pages:

```bash
python3 -m http.server 8000
```

Open the homepage at `http://localhost:8000/`, then smoke-test:

- `/map.html` and its snapshot composer;
- `/oswm_codebase/routing/routing_demo.html`;
- `/statistics/index.html`;
- `/quality_check/oswm_qc_main.html` and `/quality_check/completeness/index.html`;
- `/hub/index.html`, `/hub/API/index.html`, and `/hub/watcher/index.html`.

Browser developer tools should show successful responses for the branding manifest, favicon, project logos, and both normal and dark page-logo variants.

## Branding inheritance

Shared branding is inherited from `oswm_codebase/assets/branding/manifest.json`. Identity resources are addressed by semantic keys such as `favicon`, `logos.page_clean`, `logos.page_dark_clean`, and `logos.project`; static browser code and Python generators resolve those keys without embedding environment-specific URLs in the manifest.

This node currently has no `config.py` option for overriding shared branding. Node-specific module imagery under `oswm_codebase/assets/homepage/` is separate from the canonical identity registry.

After a codebase branding-path change:

1. pin the tested codebase commit as described above;
2. run `python oswm_codebase/tests/test_branding_manifest.py`;
3. regenerate the homepage/module entry pages and any affected committed outputs through the shared runners or targeted generators;
4. serve the node root locally and inspect all entry points;
5. commit the submodule pointer and regenerated outputs together.

## GitHub Pages publication

The existing [deploy workflow](.github/workflows/deploy_pages.yml) runs on pushes to `main` and by manual dispatch. It checks out submodules recursively, uploads the repository root as the Pages artifact, and deploys it with GitHub's official Pages actions.

The [daily update workflow](.github/workflows/data_daily_updating.yml) also checks out the pinned submodule, installs GDAL/Python dependencies, runs the daily pipeline, validates core PMTiles outputs, commits successful changes, and deploys the repository root. Failed pipeline or tile validation prevents deployment and opens a tracking issue.

No separate application server or build-time Pages framework is used; the committed repository tree is the website.

## Troubleshooting

### `oswm_codebase/` is empty or commands are missing

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

### The submodule is on the wrong or a stale commit

Use `git submodule status` and `git diff --submodule=log`. To return to the node's recorded pin, run `git submodule update --init oswm_codebase`. To upgrade, fetch inside the submodule, check out the chosen commit, test it, and commit the changed gitlink in the node.

### `git status` shows `oswm_codebase (new commits)`

The submodule checkout moved but the node has not recorded that revision. Either commit the intended gitlink with `git add oswm_codebase`, or restore the recorded pin with `git submodule update oswm_codebase`.

### Branding or other static assets return 404

Serve the node root rather than `oswm_codebase/`, confirm that the submodule is initialized, and inspect the URL relative to the generated page. Branding consumers must resolve semantic keys from `oswm_codebase/assets/branding/manifest.json`; rerun affected generators after changing the submodule pin.

### Generated pages do not reflect source changes

Changing the submodule does not regenerate node outputs automatically. Run the relevant generator or runner from the node root, review the generated diff, and commit it alongside the submodule pointer.

### A clean clone differs from a development checkout

Check for an uncommitted submodule branch, ignored local files, or generated outputs that were never committed. Validate with a fresh `git clone --recurse-submodules` before publishing structural changes.

## Project links

- [OpenSidewalkMap project](https://github.com/kauevestena/opensidewalkmap)
- [Shared codebase](https://github.com/kauevestena/oswm_codebase)
- [OpenSidewalkMap organization](https://github.com/opensidewalkmap)
- [This node's issues](https://github.com/kauevestena/opensidewalkmap_beta/issues)

The repository is distributed under the terms in [LICENSE](LICENSE).
