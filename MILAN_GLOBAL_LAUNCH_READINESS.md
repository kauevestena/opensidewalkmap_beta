# OSWM Milan and Global Launch Readiness

## Status

**Current verdict: not ready for a many-node global launch.**

The codebase is mature enough for a controlled Milan pilot, but the pilot must
first prove a clean cold start, a no-change rerun, and an incremental update.
The repository automation also has blocking history, setup, deployment, and
timezone problems that should be fixed before nodes are deployed at scale.

This branch is deliberately a clean-room Milan node. Generated products copied
from the Curitiba template were removed instead of being used as incremental
state.

## Milan node configuration

- City: `Milan, Italy`
- Short name: `milan`
- Candidate repository: `kauevestena/opensidewalkmap_milan`
- OSM municipal boundary: [relation 44915](https://www.openstreetmap.org/relation/44915)
- Bounding box, in OSWM order `(south, west, north, east)`:
  `(45.3867381, 9.0408867, 45.5358482, 9.2781103)`
- Initial map center: `(45.4641943, 9.1896346)`
- Shared codebase pin: `c8e101efded2cf0113e9f862602569d05e354bc3`

## Files introduced by this branch

- `scripts/reset_node_outputs.py`: dry-run-first removal of generated products
  inherited from a node template.
- `scripts/audit_node_readiness.py`: dependency-free checks for configuration,
  city identity, submodule integrity, workflow safety, output completeness, and
  GitHub file-size risks.
- `scripts/test_node_readiness_tools.py`: unit tests for the cleanup and audit
  helpers.
- `.github/workflows/node_launch_readiness.yml`: read-only branch/PR stress run
  that tests a Milan cold start and uploads diagnostic evidence.

## Evidence collected

### Template contamination and old files

A config-only clone retained Curitiba boundaries, update state, raw and
processed data, PMTiles, hazard products, quality-control pages, statistics,
snapshot summaries, API pages, and embedded URLs.

- Generated state selected for removal: `302,483,091` bytes.
- Tracked generated files removed on this branch: `369`.
- Approximate bytes explicitly matching Curitiba/template identity before the
  reset: `221 MB`.
- Remaining node-level Curitiba/template markers after the reset: `0`.

The reset preserves `README.md`, `index.html`, `config.py`, Git metadata, and
the `oswm_codebase` submodule. It recreates only an empty
`data/updates/registry.json` so the first acquisition is treated as a cold
start.

### Current audit result

After removing inherited city products, the readiness audit reports:

- **8 errors**
- **11 warnings**

Blocking errors:

1. `workflow.force_push`: daily updates amend and force-push repository history.
2. `workflow.requirements`: `customizable.yml` references a missing root
   `requirements.txt`.
3. `workflow.requirements`: `setup.yml` references a missing root
   `requirements.txt`.
4. `workflow.requirements`: `special_updates.yml` references a missing root
   `requirements.txt`.
5. `runner.masked_failures`: `runners/setup.sh` can exit successfully after all
   commands fail.
6. `core.workflow_replacement`: `special_updates.py` deletes node-specific
   workflows before copying the core workflow directory.
7. `core.pages_deploy_missing`: the canonical workflow set pushes generated
   products but has no GitHub Pages deployment.
8. `timestamps.naive_as_utc`: local naive update timestamps are later
   interpreted as UTC.

Warnings cover node/core workflow drift, a manual dispatch hardcoded to `main`,
the absence of a generated-file size gate, identical schedules across cloned
nodes, a Brazil-specific timezone, broad `git add .` operations, an unrelated
Nominatim user agent, and unbounded runtime dependencies.

### Tests

- Readiness helper tests: **4 passed**.
- Core Python suite: **68 passed, 3 failed, 1 skipped, 12 subtests passed**.
- Theme-chart JavaScript suite: **7 passed**.
- Snapshot JavaScript suite: cannot start in Node because a module imports an
  `https:` URL.

The three Python failures are webmap theme-chart contract drift involving the
ECharts renderer, the renamed default scope, and the ECharts module URL.

### Production workflow history

The current Curitiba node has improved recently, with the latest 20 daily runs
succeeding. Across the latest 100 runs, however, 77 succeeded and 23 failed.

The successful daily workflow still rewrites history. The run triggered from
commit `d7a5be9541f10490cf0e4b64efa2da9f0ea91c5b` produced current main commit
`db057e88aff7baf685bda7f94b565182f54f98da`; both commits have parent
`22b5f10a83d54eba7d7912e39abbbfb963fdecc9`. This is replacement, not an
ordinary descendant commit, and makes concurrent work and long-lived PR bases
unsafe.

Draft [opensidewalkmap_beta PR #17](https://github.com/kauevestena/opensidewalkmap_beta/pull/17)
contains part of the intended synchronization and normal-push design, but it is
currently open and non-mergeable and its diff has accumulated generated data.

### Milan acquisition stress probe

Nominatim resolved `Milan, Italy` to the intended municipal relation and bounds.
The public Overpass cold-fetch probe was much less encouraging:

- Full OSWM tag union: HTTP `504` from `overpass-api.de`.
- Highway-only OSWM subset: HTTP `200`, but already `69,954` elements
  (`69,735` ways and `219` relations).
- A second public Overpass provider also timed out during the investigation.

This does not prove that OSMnx can never complete the request, but it does show
that simultaneous cold starts for many nodes must not depend on best-effort
public endpoints without backoff, staggering, and a fallback data source.

## How to run the local checks

From the node repository root:

```bash
# Inspect what would be removed; this is the default and does not mutate files.
python scripts/reset_node_outputs.py

# Apply the cleanup only when intentionally initializing a new node.
python scripts/reset_node_outputs.py --apply

# Audit configuration and infrastructure before generation.
python scripts/audit_node_readiness.py \
  --json launch-readiness/audit.json \
  --markdown launch-readiness/audit.md

# After a full generation, require all deployment products.
python scripts/audit_node_readiness.py --require-generated \
  --json launch-readiness/final-audit.json \
  --markdown launch-readiness/final-audit.md

# Dependency-free tests for the new tools.
python -m unittest scripts/test_node_readiness_tools.py -v
```

The audit intentionally returns a nonzero exit code while any blocking error is
present.

## How to run the GitHub-hosted Milan stress test

The workflow has `contents: read`, does not push generated products, and does
not deploy Pages. It performs the following actions in its temporary runner
checkout:

1. Audits inherited template state.
2. Installs the geospatial runtime dependencies.
3. Runs Python and JavaScript tests.
4. Removes inherited generated products.
5. Patches the Milan identity into source pages.
6. Plants obsolete-output sentinels.
7. Runs a timed Milan cold start, limited to 150 minutes.
8. Validates PMTiles and all required generated products.
9. Checks whether obsolete sentinels survived generation.
10. Uploads logs, audit reports, resource timing, footprint, and Git status for
    14 days.

Because a newly introduced `workflow_dispatch` workflow cannot be launched
until the workflow exists on the default branch, this branch also includes a
narrow pull-request trigger restricted to
`agent/milan-global-launch-readiness`. Opening or updating a PR from this
branch starts the stress test. Manual dispatch remains available if the
workflow is later adopted on the default branch.

The first run is expected to be red while the documented infrastructure and
test failures remain. Its purpose is to produce complete cold-start evidence,
not to hide known failures.

## Work remaining before global launch

### Priority 0: repository and automation safety

- Replace amend/force-push daily updates with serialized normal commits,
  rebase-before-push, and fast-forward-only publication.
- Rebase or supersede PR #17 with a clean infrastructure-only diff.
- Make successful codebase synchronization write directly to `main`, while
  failures create intervention PRs, following the existing OSWM policy.
- Make every setup command fail the job when it fails.
- Use `oswm_codebase/requirements.txt` consistently and introduce reproducible
  dependency constraints or a lock file.
- Stop `special_updates.py` from replacing the complete workflow directory.
- Restore an explicit, validated Pages deployment in the canonical workflow.
- Stage only declared generated paths; do not use broad `git add .` or
  `git add -A` in production jobs.

### Priority 0: correct global node state

- Store registry timestamps as timezone-aware UTC ISO-8601 values and migrate
  existing registry timestamps.
- Add an explicit OSM relation/area identifier to node configuration so city
  selection does not depend only on fuzzy place-name ranking.
- Identify the Nominatim client as OSWM and comply with provider usage policy.
- Convert the cleanup list into a canonical generated-output manifest shared by
  initialization, daily reconciliation, audits, and deployment.
- Ensure each generator removes outputs that are no longer declared. The
  obsolete-output sentinel check must pass.

### Priority 0: Milan pilot acceptance

- Complete one clean Milan cold start within the workflow timeout.
- Produce nonempty core PMTiles and all required API, routing, hazard, snapshot,
  QC, statistics, homepage, and webmap products.
- Pass the readiness audit with `--require-generated`.
- Run a second no-change cycle and confirm it is idempotent.
- Apply a known small OSM change or fixture and confirm the incremental cycle
  updates only the expected products.
- Confirm that no output exceeds the 95 MiB pre-push guard.
- Visually verify the deployed Milan homepage, webmap themes, chart control,
  snapshot, routing profiles, hazard views, QC pages, statistics, and API links.

### Priority 1: many-node operations

- Stagger schedules per node instead of cloning the same daily and weekly cron
  times.
- Add bounded retries, exponential backoff, and provider fallback for
  Nominatim, Overpass, OHSOME, OSM, Copernicus DEM, and acquisition sources.
- Evaluate regional extracts, a controlled Overpass instance, or another
  reproducible bulk source for cold starts.
- Separate source history from generated deployment artifacts to prevent every
  node repository from growing indefinitely.
- Add fleet observability: node version, codebase SHA, last successful stage,
  product sizes, durations, provider failures, and deployment status.
- Test concurrent synchronization and daily updates across multiple pilot
  nodes before broad rollout.

## Launch decision criteria

Milan can be considered a successful pilot only when:

- the cold-start, no-change, and incremental runs all pass;
- all code and readiness tests are green;
- the obsolete-output sentinels are removed;
- no workflow rewrites shared history;
- the canonical workflow preserves node-specific configuration and deploys
  Pages explicitly;
- external-provider failure produces a controlled retry or actionable failure,
  never a falsely successful run; and
- a newly cloned node contains no products or identity from its template city.

Global rollout should begin only after the same workflow succeeds on several
geographically and operationally different pilot nodes with staggered
schedules.
