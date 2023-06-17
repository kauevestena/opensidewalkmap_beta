# OpenSidewalkMap, <CITYNAME>Curitiba<CITYNAME> node

Main project page:

OSWM is a project intended to be a full-fledged inventory solution for the management of pedestrian network data, using only open data, basically OpenStreetMap data!

It is a *decentered* and *modular* project, fully GitHub hosted and maintained!

By *decentered* we mean that each city/region is stored in a separate repository, (inspired by https://equalstreetnames.org/ which uses the same concept)

By *modular* we mean that each node has many "apps", each one intended to accomplish a task in the context of management of pedestrian network data, currently we have 4:

* Webmap: an interactive cartographic representation of the data;
* Optimized Routing: currently just a Streamlit prototype, in the future shall be a more complete routing engine;
* Dashboard: featuring charts containing the bigger picture of the data;
* Data Quality Tool: indexing possible errors in the data, mainly invalid values on tags, which are easy to find, but still errors;

For the future, we are planning some additional ones, like:

* Data Watcher: to monitor edits on data creating .rss feeds, which may have alerts if there are huge modifications, mainly deletions or possible vandalism;
* Data Acquisition: listing projects ar platforms like Tasking Manager, MapRoulette, and Pic4Review to expand current data;
