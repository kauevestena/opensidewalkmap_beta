# OpenSidewalkMap, <CITYNAME>Curitiba<CITYNAME> node

<!-- TODO: README SHALL BE GENERATED AUTOMATICALLY -->

Main project repository: https://github.com/kauevestena/opensidewalkmap

Codebase Repository: https://github.com/kauevestena/oswm_codebase

OSWM is a project intended to be a full-fledged inventory solution for the management of pedestrian network data, using only open data, basically OpenStreetMap data!

It is a *decentered* and *modular* project, fully GitHub hosted and maintained!

By *decentered* we mean that each city/region is stored in a separate repository, (inspired by https://equalstreetnames.org/ which uses the same concept)

By *modular* we mean that each node has several apps, each intended to
accomplish a task in pedestrian-network data management:

<!-- TODO: GENERATE AUTOMATICALLY THE DESCRIPTION OF THE MODULES  -->

* Webmap: an interactive cartographic representation of the data;
* Accessible Routing: static distance, wheelchair, blind/low-vision, and
  older/reduced-mobility routing profiles with directional precomputed grades;
* Hazard Analysis: profile-specific screening from OSM kerb, tactile, surface,
  cross-slope, barrier, and longitudinal-slope evidence;
* Dashboard: featuring charts containing the bigger picture of the data;
* Data Quality Tool: indexing possible errors in the data, mainly invalid values on tags, which are easy to find, but still errors;
* Data Watcher: to monitor edits on data creating .rss feeds, which may have alerts if there are huge modifications, mainly deletions or possible vandalism;
* Data Hub and Acquisition: distributing node data and listing projects on
  platforms such as Tasking Manager, MapRoulette, and Pic4Review.

Routing and hazard terrain context uses the globally available Copernicus DEM
2021 Cloud Optimized GeoTIFFs from the AWS Open Data Registry. GLO-30 is the
preferred source and GLO-90 is the worldwide fallback. These are surface models
used as contextual terrain evidence, not surveyed sidewalk or cross slope.

## Creating a new node

After creating a repository from this template, GitHub Pages must be enabled
once before the included deployment workflow can publish the node.

1. Open the new repository on GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.
4. Do not create a suggested Pages workflow. This template already provides
   `.github/workflows/deploy_pages.yml`.
5. Run the node setup and data-generation workflows as instructed for the new
   node. Then run `deploy_pages`, or push a generated site change that triggers
   it.
6. Confirm that the deployment succeeds and that the node is available at
   `https://<owner>.github.io/<repository>/`.

### Organization repositories

An organization owner may first need to allow Pages publication:

1. Open the organization **Settings**.
2. Go to **Member privileges**.
3. Under **Pages creation**, allow **Public** Pages sites and save.
4. Return to the repository's **Settings → Pages** and select
   **GitHub Actions**.

This is a required one-time repository bootstrap step. A workflow's
`GITHUB_TOKEN` may have `pages: write` permission but still be unable to
create the Pages site for a new organization repository. In that case,
`actions/configure-pages` fails with
`Resource not accessible by integration`. Enable Pages in the repository
settings, then rerun the failed deployment; no replacement workflow is needed.
