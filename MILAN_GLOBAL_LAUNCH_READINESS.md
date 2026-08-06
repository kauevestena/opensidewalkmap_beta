# OSWM Milan pilot and global-launch readiness

## Decision

The repository infrastructure now passes the local launch-readiness gate and
is suitable for a **controlled, read-only Milan cold-start pilot**. It is not
yet evidence for a many-node global launch: Milan still needs a successful
hosted cold start, an idempotent no-change rerun, and a controlled incremental
update.

This is an isolated branch of `opensidewalkmap_beta`, intended to become the
source for a dedicated Milan repository. It deliberately contains no generated
Milan products and should not be merged into the Curitiba reference node as a
city-identity change.

## Reproducible configuration

- City: `Milan, Italy`
- Short name: `milan`
- Intended repository: `kauevestena/opensidewalkmap_milan`
- Exact OSM administrative boundary: [relation 44915](https://www.openstreetmap.org/relation/44915)
- Fallback bounding box in OSWM order `(south, west, north, east)`:
  `(45.3867381, 9.0408867, 45.5358482, 9.2781103)`
- Initial map center: `(45.4641943, 9.1896346)`
- Metadata timezone: `Europe/Rome`
- Daily schedule: `17 3 * * *` UTC
- Weekly schedule: `43 4 * * 0` UTC
- Shared codebase pin: `01d4bd2f6d1814f8bdd772be1406b1b4d550f8e2`
- Core launch-readiness branch:
  <https://github.com/kauevestena/oswm_codebase/tree/agent/global-launch-readiness>

The exact relation prevents fuzzy Nominatim ranking from silently choosing a
different Milan. The non-default cron values prove that node-specific schedule
rendering survives managed core synchronization.

## Old-file finding and cleanup

A config-only shallow clone was not a clean new node. It retained Curitiba
boundaries, update state, raw/processed data, PMTiles, hazard and routing
products, quality pages, statistics, snapshot summaries, static API pages, and
embedded URLs.

- Generated state selected for removal: `302,483,091` bytes.
- Tracked generated files removed: `369`.
- Approximate files explicitly carrying Curitiba/template identity before the
  reset: `221 MB`.
- Remaining node-level Curitiba markers after reset: `0`.

`scripts/reset_node_outputs.py` is dry-run-first and now delegates its path
contract to `oswm_codebase/node_outputs.py`, so initialization and production
rebuilds no longer maintain competing cleanup lists. It preserves Git data,
`README.md`, `index.html`, `config.py`, and the codebase gitlink, then recreates
only an empty `data/updates/registry.json`.

Managed synchronization also removed three dangling workflow files:

- `deploy_pages.yml` (superseded by the canonical `pages.yml`);
- `fix_submodules.yml` (could silently move or recreate the gitlink);
- `manual_stash.yml` (obsolete and unsafe automation).

The node-only `node_launch_readiness.yml` was preserved, demonstrating that
core synchronization no longer replaces the complete workflow directory.

## Core changes exercised by Milan

The node is pinned to the exact remote core feature-branch SHA above. The
following behavior is active in the copied node workflows:

- normal commits, fetch/rebase, and non-force pushes;
- one shared writer concurrency group across setup, daily, weekly, special,
  custom, and codebase-update workflows;
- scoped generated-output staging and a 95 MiB staged-file gate;
- explicit least-privilege GitHub Pages deployment;
- recorded gitlink checkout rather than an implicit pull of core `main`;
- exact main-reachable SHA input for future codebase promotion;
- literal Milan cron rendering from `config.py`;
- managed-file state in `.oswm-managed-files.json`;
- fail-fast setup/weekly runners and an error-propagating daily runner;
- machine-readable cold/generate/rebuild/skip decisions;
- full derived-output reconciliation, including stale sentinels;
- UTC ISO timestamps with legacy local-time parsing;
- exact-relation Nominatim lookup and bounded Overpass failover;
- exact Python 3.12 runtime/development locks;
- browser modules that also load under the Node test runner.

## Current local evidence

The final dependency-free node audit reports:

- **0 errors**
- **0 warnings**
- exact candidate gitlink equals checked-out core SHA
- all commit-candidate files far below the 95 MiB guard

Tests and static validation:

- Milan readiness helpers: **4 passed**;
- core Python suite through the Milan topology: **91 passed, plus 12
  subtests**;
- JavaScript module suite: **28 passed**;
- Milan workflow YAML: all files parse;
- core runner shell scripts: all parse;
- rendered workflow tokens: none remain;
- rendered schedules: daily `17 3 * * *`, weekly `43 4 * * 0`;
- `git diff --check`: passes.

The audit intentionally did not use `--require-generated`, because this branch
contains no unverified Milan deployment products. That gate must remain red
until the hosted cold-start job produces them.

## Run the checks locally

From the node root:

```bash
# Show inherited/generated reset targets without mutation.
python scripts/reset_node_outputs.py

# Apply only when deliberately initializing a fresh node checkout.
python scripts/reset_node_outputs.py --apply

# Re-render the managed workflows from the pinned core and config literals.
python oswm_codebase/special_updates.py

# Audit infrastructure without requiring products that do not exist yet.
python scripts/audit_node_readiness.py \
  --json /tmp/oswm-milan-audit.json \
  --markdown /tmp/oswm-milan-audit.md

# Dependency-free node helper tests.
python -m unittest scripts/test_node_readiness_tools.py -v

# After a cold generation, make every deployment product mandatory.
python scripts/audit_node_readiness.py --require-generated \
  --json /tmp/oswm-milan-final-audit.json \
  --markdown /tmp/oswm-milan-final-audit.md
```

Core CI uses `oswm_codebase/requirements-dev.txt`, Python 3.12, pytest, and the
two Node module suites.

## Hosted cold-start procedure

`.github/workflows/node_launch_readiness.yml` is read-only: it has
`contents: read`, never commits, never pushes, and never deploys. In a temporary
runner checkout it:

1. audits the clean node state;
2. installs the exact development lock;
3. runs Python, JavaScript, and node-helper tests;
4. applies the canonical initialization reset;
5. patches source identity;
6. plants obsolete-output sentinels;
7. runs a Milan cold start with a 150-minute inner timeout;
8. validates PMTiles and all required generated outputs;
9. requires the sentinels to have disappeared;
10. uploads logs, timing, disk footprint, audit reports, and Git status for 14
    days.

A workflow introduced only on a feature branch cannot be manually dispatched
until it exists on the default branch. The workflow therefore also has a
narrow PR trigger for this exact head branch. No PR is created by this work;
triggering the hosted run remains a deliberate follow-up action.

## What remains before accepting Milan

1. Review/merge or otherwise promote the core launch-readiness branch, then
   repin Milan to the resulting tested `main` SHA.
2. Create the dedicated `opensidewalkmap_milan` repository from this clean
   branch rather than changing the Curitiba reference node.
3. Enable the repository's GitHub Pages environment and run the read-only cold
   gate.
4. Require nonempty boundary, raw, processed, PMTiles, routing, hazard,
   snapshot, QC, statistics, metadata, homepage, webmap, and API products.
5. Confirm no output reaches 95 MiB and capture duration, memory, disk, provider
   attempts, and final repository size.
6. Run an immediate second daily cycle; require decision mode `skip` and an
   idempotent output tree.
7. Apply a known small OSM fixture/change and prove the incremental watermark
   and affected products are correct.
8. Visually verify the deployed homepage, MapLibre themes, chart control,
   printable snapshot, routing profiles, hazard views, quality pages,
   statistics, metadata catalogue, and static API links.

## What remains before a global fleet launch

- Provide controlled Overpass or regional-extract capacity. Earlier Milan
  probing produced a `504` for the full OSWM tag union at a public endpoint,
  while a highway-only subset already represented about 70,000 elements.
- Run the same acceptance sequence on at least two geographically and
  operationally different nodes with distinct schedules.
- Load-test concurrent codebase promotions and daily writers across pilot
  repositories.
- Add fleet observability for node/core SHA, last successful stage, duration,
  output sizes, provider failures, and Pages deployment state.
- Decide whether long-term generated assets belong in permanent Git history or
  a bounded artifact/publication store.
- Extend bounded provider/circuit-breaker policy to every optional acquisition,
  OSM changeset, OHSOME history, and Copernicus request.

## Acceptance criterion

Milan is accepted only after cold, no-change, and incremental hosted runs all
pass; no stale output or foreign city identity remains; the exact tested core
SHA is recorded; no workflow rewrites history; Pages is visually verified; and
provider failure is bounded and actionable. Fleet enrollment begins only after
the same evidence exists for multiple staggered pilots.
