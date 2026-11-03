/* fixtures.js — G5a clickable prototypes.
 *
 * FIXTURE DATA, NOT COMPUTED.
 * Every polygon and point in this file was hand-authored for the Gate G5a usability
 * comparison. Nothing here comes from routing, isochrones, or real travel-time data.
 * The region polygons do not change shape when the criteria change; the prototypes
 * only switch between the "tight" and "relaxed" fixtures (or show none).
 *
 * Coordinates are [longitude, latitude] (GeoJSON order), WGS84.
 * Centre: Durham / Chapel Hill, NC.
 */
(function (root) {
  'use strict';

  var FIXTURES = {
    note: 'FIXTURE DATA, NOT COMPUTED. Hand-authored geometry for the G5a usability test.',

    center: [-78.95, 35.95],
    zoom: 10,

    // Approximate Research Triangle coverage box. Places outside it are "outside coverage".
    coverageBbox: [-79.35, 35.55, -78.30, 36.25],
    coverage: {
      type: 'Feature',
      properties: { name: 'coverage (fixture)' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[-79.35, 35.55], [-78.30, 35.55], [-78.30, 36.25], [-79.35, 36.25], [-79.35, 35.55]]]
      }
    },

    // Two hand-drawn region fixtures. "tight" is shown when every card is on and at its
    // entered limit; "relaxed" when any card is turned off, deleted, or relaxed.
    regions: {
      tight: {
        type: 'Feature',
        properties: { name: 'fixture A (tight)', fixture: true },
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [-79.095, 35.955], [-79.090, 35.930], [-79.060, 35.885], [-79.000, 35.875],
            [-78.930, 35.880], [-78.870, 35.910], [-78.860, 35.960], [-78.890, 36.000],
            [-78.950, 36.020], [-79.010, 36.010], [-79.060, 35.980], [-79.095, 35.955]
          ]]
        }
      },
      relaxed: {
        type: 'Feature',
        properties: { name: 'fixture B (relaxed)', fixture: true },
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [-79.170, 35.950], [-79.140, 35.870], [-79.070, 35.820], [-78.970, 35.795],
            [-78.860, 35.790], [-78.770, 35.830], [-78.760, 35.920], [-78.790, 36.000],
            [-78.860, 36.060], [-78.950, 36.095], [-79.050, 36.105], [-79.130, 36.080],
            [-79.170, 35.950]
          ]]
        }
      }
    },

    // Scripted gazetteer. "aliases" are matched after lower-casing; "outside" marks places
    // beyond the coverage box; "options" marks an ambiguous name with several locations.
    places: [
      { id: 'unc-hospitals', name: 'UNC Hospitals', kind: 'employer', lng: -79.0520, lat: 35.9049,
        aliases: ['unc hospitals', 'unc hospital', 'unc medical center', 'unc health', 'unc'] },
      { id: 'duke-hospital', name: 'Duke University Hospital', kind: 'employer', lng: -78.9381, lat: 36.0070,
        aliases: ['duke university hospital', 'duke hospital', 'duke medical center', 'duke health', 'duke'] },
      { id: 'fidelity-rtp', name: 'Fidelity RTP', kind: 'employer', lng: -78.8636, lat: 35.8992,
        aliases: ['fidelity rtp', 'fidelity', 'fidelity investments'] },
      { id: 'cisco-rtp', name: 'Cisco RTP', kind: 'employer', lng: -78.8438, lat: 35.8687,
        aliases: ['cisco rtp', 'cisco'] },
      { id: 'ibm-rtp', name: 'IBM RTP', kind: 'employer', lng: -78.8589, lat: 35.8924,
        aliases: ['ibm rtp', 'ibm'] },
      { id: 'rtp', name: 'Research Triangle Park', kind: 'place', lng: -78.8600, lat: 35.8990,
        aliases: ['research triangle park', 'rtp', 'the park at rtp'] },
      { id: 'rdu', name: 'RDU Airport', kind: 'place', lng: -78.7875, lat: 35.8776,
        aliases: ['rdu airport', 'rdu', 'airport', 'the airport', 'raleigh durham airport', 'raleigh-durham airport', 'raleigh durham international airport'] },
      { id: 'downtown-durham', name: 'Downtown Durham', kind: 'place', lng: -78.8986, lat: 35.9940,
        aliases: ['downtown durham', 'durham'] },
      { id: 'downtown-raleigh', name: 'Downtown Raleigh', kind: 'place', lng: -78.6382, lat: 35.7796,
        aliases: ['downtown raleigh', 'raleigh'] },
      { id: 'wakemed', name: 'WakeMed Raleigh', kind: 'employer', lng: -78.5950, lat: 35.7900,
        aliases: ['wakemed raleigh', 'wakemed', 'wake med'] },
      { id: 'ncsu', name: 'NC State University', kind: 'employer', lng: -78.6821, lat: 35.7847,
        aliases: ['nc state university', 'nc state', 'ncsu', 'north carolina state university'] },
      { id: 'unc-ch', name: 'UNC Chapel Hill (campus)', kind: 'employer', lng: -79.0469, lat: 35.9049,
        aliases: ['unc chapel hill', 'unc campus', 'chapel hill campus'] },
      { id: 'chapel-hill', name: 'Chapel Hill', kind: 'town', lng: -79.0558, lat: 35.9132,
        aliases: ['chapel hill', 'downtown chapel hill', 'franklin street'] },
      { id: 'carrboro', name: 'Carrboro', kind: 'town', lng: -79.0753, lat: 35.9101, aliases: ['carrboro'] },
      { id: 'hillsborough', name: 'Hillsborough', kind: 'town', lng: -79.0997, lat: 36.0754, aliases: ['hillsborough'] },
      { id: 'morrisville', name: 'Morrisville', kind: 'town', lng: -78.8253, lat: 35.8235, aliases: ['morrisville'] },
      { id: 'cary', name: 'Cary', kind: 'town', lng: -78.7811, lat: 35.7915, aliases: ['cary', 'downtown cary'] },
      { id: 'apex', name: 'Apex', kind: 'town', lng: -78.8503, lat: 35.7327, aliases: ['apex'] },
      { id: 'pittsboro', name: 'Pittsboro', kind: 'town', lng: -79.1772, lat: 35.7202, aliases: ['pittsboro'] },
      { id: 'southpoint', name: 'Southpoint', kind: 'place', lng: -78.9450, lat: 35.9055,
        aliases: ['southpoint', 'streets at southpoint', 'southpoint mall'] },
      { id: 'hope-valley', name: 'Hope Valley', kind: 'place', lng: -78.9500, lat: 35.9400, aliases: ['hope valley'] },
      { id: 'north-durham', name: 'North Durham', kind: 'place', lng: -78.8900, lat: 36.0500,
        aliases: ['north durham', 'braggtown'] },
      { id: 'brier-creek', name: 'Brier Creek', kind: 'place', lng: -78.7800, lat: 35.9000, aliases: ['brier creek'] },

      // Outside the coverage box
      { id: 'greensboro', name: 'Greensboro', kind: 'town', lng: -79.7920, lat: 36.0726, aliases: ['greensboro'], outside: true },
      { id: 'burlington', name: 'Burlington', kind: 'town', lng: -79.4378, lat: 36.0957, aliases: ['burlington'], outside: true },
      { id: 'charlotte', name: 'Charlotte', kind: 'town', lng: -80.8431, lat: 35.2271, aliases: ['charlotte'], outside: true },
      { id: 'wilmington', name: 'Wilmington', kind: 'town', lng: -77.9447, lat: 34.2257, aliases: ['wilmington'], outside: true },

      // Ambiguous names (several locations in the area)
      { id: 'whole-foods', name: 'Whole Foods', kind: 'store', aliases: ['whole foods', 'whole foods market', 'wholefoods'],
        options: [
          { id: 'whole-foods-ch', name: 'Whole Foods — Chapel Hill (Elliott Rd)', lng: -79.0566, lat: 35.9188 },
          { id: 'whole-foods-durham', name: 'Whole Foods — Durham (Broad St)', lng: -78.9339, lat: 35.9906 },
          { id: 'whole-foods-raleigh', name: 'Whole Foods — Raleigh (Wade Ave)', lng: -78.6960, lat: 35.8060 }
        ] },
      { id: 'trader-joes', name: "Trader Joe's", kind: 'store', aliases: ['trader joes', 'trader joe', 'trader joe s', 'tjs'],
        options: [
          { id: 'tj-ch', name: "Trader Joe's — Chapel Hill (Fordham Blvd)", lng: -79.0400, lat: 35.9280 },
          { id: 'tj-cary', name: "Trader Joe's — Cary (Crossroads)", lng: -78.7800, lat: 35.7900 },
          { id: 'tj-raleigh', name: "Trader Joe's — Raleigh (North Hills)", lng: -78.6400, lat: 35.8350 }
        ] },
      { id: 'harris-teeter', name: 'Harris Teeter', kind: 'store', aliases: ['harris teeter', 'harris teeters', 'ht'],
        options: [
          { id: 'ht-carrboro', name: 'Harris Teeter — Carrboro', lng: -79.0800, lat: 35.9120 },
          { id: 'ht-southpoint', name: 'Harris Teeter — Durham (Southpoint)', lng: -78.9450, lat: 35.9080 },
          { id: 'ht-ninth', name: 'Harris Teeter — Durham (Ninth St)', lng: -78.9220, lat: 36.0080 },
          { id: 'ht-cary', name: 'Harris Teeter — Cary', lng: -78.7800, lat: 35.7950 }
        ] },
      { id: 'target', name: 'Target', kind: 'store', aliases: ['target'],
        options: [
          { id: 'target-durham', name: 'Target — Durham (New Hope Commons)', lng: -78.9700, lat: 35.9700 },
          { id: 'target-ch', name: 'Target — Chapel Hill (Eastgate)', lng: -79.0480, lat: 35.9270 },
          { id: 'target-cary', name: 'Target — Cary', lng: -78.7700, lat: 35.7900 }
        ] }
    ],

    // Amenity categories with fixture points used only for the scripted
    // "why is this out?" estimates (nearest fixture point, straight line × circuity).
    categories: {
      park: { label: 'Park', aliases: ['park', 'parks', 'green space', 'greenspace', 'city park', 'public park'],
        points: [[-78.8993, 35.9990], [-78.9330, 36.0020], [-79.0310, 35.8900], [-78.9160, 35.9220], [-78.9120, 35.9560],
                 [-79.0350, 35.9350], [-79.0650, 35.9420], [-78.8080, 35.8000], [-79.1000, 36.0720], [-78.9030, 36.0240],
                 [-78.8900, 36.0520], [-78.7850, 35.9020], [-78.8300, 35.8250], [-79.0760, 35.9100], [-78.6630, 35.7790],
                 [-78.8700, 35.7300], [-78.9700, 35.9100], [-78.8500, 35.9600], [-78.9900, 35.9800], [-78.9400, 35.9400]] },
      grocery: { label: 'Grocery store', aliases: ['grocery', 'grocery store', 'groceries', 'supermarket', 'grocer', 'food store', 'market'],
        points: [[-79.0566, 35.9188], [-79.0800, 35.9120], [-78.9100, 35.9500], [-78.9339, 35.9906], [-78.9450, 35.9080],
                 [-78.8950, 36.0480], [-78.7820, 35.9000], [-78.8280, 35.8230], [-78.7800, 35.7950], [-79.1000, 36.0750],
                 [-78.6500, 35.8000], [-78.9700, 35.9700], [-78.9220, 36.0080], [-78.8600, 35.9300], [-79.0100, 35.9000]] },
      coffee: { label: 'Coffee shop', aliases: ['coffee', 'coffee shop', 'cafe', 'coffeeshop', 'coffee place'],
        points: [[-78.9010, 35.9960], [-79.0550, 35.9130], [-79.0770, 35.9100], [-78.9220, 36.0080], [-78.9450, 35.9060],
                 [-78.8930, 36.0490], [-78.7830, 35.9010], [-78.8270, 35.8240], [-78.7810, 35.7920], [-79.0990, 36.0750]] },
      pharmacy: { label: 'Pharmacy', aliases: ['pharmacy', 'drugstore', 'drug store', 'chemist'],
        points: [[-78.9050, 35.9930], [-79.0540, 35.9180], [-79.0790, 35.9110], [-78.9200, 36.0060], [-78.9440, 35.9070],
                 [-78.8940, 36.0470], [-78.7840, 35.9000], [-78.8260, 35.8240], [-78.7800, 35.7930], [-79.0980, 36.0740]] },
      playground: { label: 'Playground', aliases: ['playground', 'play ground', 'playgrounds'],
        points: [[-78.8990, 35.9985], [-79.0320, 35.8910], [-78.9170, 35.9230], [-79.0640, 35.9430], [-78.8900, 36.0510],
                 [-78.7850, 35.9030], [-78.8300, 35.8260], [-78.8080, 35.8010], [-79.0760, 35.9105], [-79.1000, 36.0715]] },
      library: { label: 'Library', aliases: ['library', 'libraries', 'public library'],
        points: [[-78.8990, 35.9950], [-79.0530, 35.9140], [-79.0770, 35.9090], [-78.9410, 35.9100], [-78.8920, 36.0440],
                 [-78.8200, 35.8230], [-78.7800, 35.7900], [-79.0990, 36.0760], [-78.9800, 35.9600]] },
      transit_stop: { label: 'Transit stop', aliases: ['bus stop', 'transit stop', 'bus', 'transit', 'bus line', 'bus route'],
        points: [[-78.9000, 35.9960], [-79.0520, 35.9100], [-79.0750, 35.9100], [-78.9220, 36.0070], [-78.9450, 35.9060],
                 [-78.8950, 36.0500], [-78.8600, 35.8990], [-78.8270, 35.8230], [-78.7810, 35.7910], [-79.0990, 36.0750],
                 [-78.9400, 35.9400], [-78.9700, 35.9650]] },
      trailhead: { label: 'Trailhead', aliases: ['trail', 'trailhead', 'trails', 'greenway', 'hiking trail', 'hiking'],
        points: [[-79.0000, 35.9700], [-78.9200, 35.9800], [-79.0800, 35.9200], [-78.8900, 36.0500], [-78.7850, 35.9050],
                 [-78.8300, 35.8200], [-78.8100, 35.8000], [-79.1000, 36.0700], [-78.9300, 35.9100]] },
      school: { label: 'School', aliases: ['school', 'schools', 'elementary school', 'middle school', 'high school'],
        points: [[-78.9050, 35.9950], [-79.0530, 35.9150], [-79.0780, 35.9120], [-78.9200, 36.0050], [-78.9430, 35.9100],
                 [-78.8920, 36.0480], [-78.7860, 35.9000], [-78.8280, 35.8220], [-78.7820, 35.7940], [-79.0980, 36.0740],
                 [-78.9500, 35.9450], [-78.9800, 35.9650]] }
    },

    // Named spots for the keyboard "Why is a place out?" control and for snapping map taps.
    // These are the spots the protocol uses; both scenarios resolve to a single failing card here.
    checkSpots: [
      { id: 'north-durham', name: 'North Durham (near Braggtown)', lng: -78.8900, lat: 36.0500 },
      { id: 'brier-creek', name: 'Brier Creek', lng: -78.7800, lat: 35.9000 },
      { id: 'hillsborough', name: 'Hillsborough', lng: -79.0997, lat: 36.0754 },
      { id: 'morrisville', name: 'Morrisville', lng: -78.8253, lat: 35.8235 },
      { id: 'carrboro', name: 'Carrboro', lng: -79.0753, lat: 35.9101 },
      { id: 'hope-valley', name: 'Hope Valley', lng: -78.9500, lat: 35.9400 },
      { id: 'southpoint', name: 'Southpoint', lng: -78.9450, lat: 35.9055 },
      { id: 'downtown-durham', name: 'Downtown Durham', lng: -78.8986, lat: 35.9940 },
      { id: 'cary', name: 'Cary', lng: -78.7811, lat: 35.7915 },
      { id: 'downtown-raleigh', name: 'Downtown Raleigh', lng: -78.6382, lat: 35.7796 },
      { id: 'apex', name: 'Apex', lng: -78.8503, lat: 35.7327 },
      { id: 'pittsboro', name: 'Pittsboro', lng: -79.1772, lat: 35.7202 }
    ],

    // Scripted "typical conditions" speeds in miles per minute, and a straight-line to
    // road-distance factor. Used only for the scripted explanations. Not routed.
    speeds: { drive: 0.5, bike: 0.2, walk: 0.05 },
    circuity: 1.3
  };

  root.G5A_FIXTURES = FIXTURES;
  if (typeof module === 'object' && module.exports) { module.exports = FIXTURES; }
})(typeof window !== 'undefined' ? window : globalThis);
