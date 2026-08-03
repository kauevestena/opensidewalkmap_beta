# OpenSidewalkMap, <CITYNAME>Milan, Italy<CITYNAME> node

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
