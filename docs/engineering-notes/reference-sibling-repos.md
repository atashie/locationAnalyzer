---
name: reference-sibling-repos
description: Paths to sibling repos whose code the V2 rebuild may reuse (CHCCS_geospatial gridded travel times, localUpdates NL-to-spatial-SQL agent)
metadata:
  type: reference
---

- C:/Users/arikt/documents/github/CHCCS_geospatial/src/school_desert.py -
  regular point grid over a region, snap to nearest OSM edge, multi-source
  Dijkstra travel times per mode, rasterize to GeoTIFF/PNG overlay. This is the
  "gridded travel-time + road network" work the user refers to.
- C:/Users/arikt/documents/github/localUpdates - location-aware info agent:
  natural language -> structured filter -> parameterized spatial SQL on DuckDB,
  Overture Maps places seed, provenance/freshness scoring, 988 tests.
  Prior tool survey at localUpdates/docs/research-findings.md.
- This repo's V1: backend/app/services/{location_analyzer,valhalla,tripadvisor}.py.
Related: [[project-v2-rethink-decisions]].
