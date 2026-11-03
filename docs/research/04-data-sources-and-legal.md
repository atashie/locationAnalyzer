# 04 — Data Sources and Legal Access

**Date:** 2026-11-03
**Status:** Draft v1 — research complete for the Research Triangle wedge; items marked *(unverified)* need a follow-up check before they are relied on.
**Scope:** Every data source the location finder might draw on, grouped A–F (residential listings; hotels and commercial; places/POIs; demographics and economy; traffic and transportation; quality-of-place layers). For each: coverage, granularity, freshness, access method, cost, and a license/ToS verdict for (i) storing, (ii) displaying with attribution, (iii) commingling with other data, (iv) commercial use; plus integration effort and an adopt/consider/reject verdict.
**Method:** Primary sources first (official API docs, terms pages, license texts, pricing pages, government portals), fetched 2026-11-03 unless noted. Where a site blocked automated fetching (Zillow, realtor.com, LoopNet, Crexi, Tripadvisor, TPL, HIFLD) the verdict rests on earlier in-house verification, a dated third-party mirror, or is flagged *(unverified)*. Two in-house documents were read first and are built on, not redone: `localUpdates/docs/research-findings.md` (§2.2, §2.5, §6) and `localUpdates/docs/legal-and-data-use.md` (commercialization matrix, 2026-06-28/07-01). Their verdicts on Google Places, Yelp, Tripadvisor, Foursquare, Overture, OSM/ODbL and the Census geocoder were re-checked and still hold (one upgrade and one new fact noted below).

> **This is research, not legal advice.** Terms change; several sources below changed materially in 2025–2026 (Yelp pricing, Google Places free tier, EJScreen removal, Tripadvisor API deprecation, Amadeus Self-Service). Have counsel review before public launch or monetization.

---

## 1. Executive summary

1. **Listings answer (plain language):** There is no free, legal API for live for-sale listings. The lawful free path is **deep-linking**: compute the result polygon, take its bounding box (and, where useful, the ZIP/city regions it covers), and send the user to Zillow/Redfin/Realtor.com/Trulia search pages pre-filled with that box and their filters. Zillow accepts a `?searchQueryState=` URL-encoded JSON containing `mapBounds{west,east,south,north}`; Redfin accepts `/filter/viewport=N:S:E:W`. A **polygon cannot be encoded** in either URL — Zillow's drawn regions become an opaque server-side `customRegionId` *(inference, see §4.1)* — so link the bbox and let our own map show the true polygon. We display *nothing* scraped: no prices, photos or counts from those sites.
2. **Scraping and "unofficial API" resellers are out.** Redfin's ToS (updated 2025-09-29, §2.3.5) bars "screen and database scraping, spiders, robots, crawlers"; Zillow's bars "any robot, spider, scraper or other automated means"; RapidAPI "Zillow/Realty-in-US" wrappers are scrapers wearing a REST façade and inherit the same exposure. Reject for a product meant to go public.
3. **Legal listing *data* (not links) means MLS/IDX.** Doorify MLS (formerly Triangle MLS) sells an IDX RESO Web API feed for a $35 connection fee and $5/month — cheap — but only to a participant brokerage, and NAR Policy 7.58 requires the display to be "under the actual and apparent control of the participant" and says participants "may not use IDX-provided listings for any purpose other than IDX display." A brokerage partner is the only route to showing real listing pins inside our polygon.
4. **Cheap paid listing data exists for a demo:** RentCast (Developer tier free, 50 requests/month; Foundation $74/month for 1,000) returns active sale and rental listings with explicit rights to "incorporate and store the API Data" and no attribution requirement. Good for friends-and-family and prototyping; audit provenance (it is aggregated, not MLS-licensed) before monetizing.
5. **County assessor data is the free "ground truth" layer.** Wake County parcels are CC BY 4.0, updated daily, with a daily real-estate file (ownership, sales, values, characteristics). Orange County publishes annual parcel snapshots and address points; Durham has a joint City/County portal *(contents unverified this session)*. This gives housing stock, recent sales and price levels for any polygon — legally, forever, commercially.
6. **Zillow Research (ZHVI/ZORI) is usable with attribution** ("free for public use … Proper and clear attribution of all data to Zillow is required"); commercial use is not addressed on the current page and historically was excluded — ask Zillow before monetizing. FHFA HPI (down to tract/ZIP) is the federal fallback.
7. **Hotels:** the free tier is gone. Amadeus Self-Service is reported decommissioned (July 2026) *(unverified — portal unreachable)*; Booking.com Demand API requires Managed Affiliate Partner status and a signed contract; Expedia Rapid requires a commercial agreement. Deep-link to Google Hotels/Booking with dates and location; add Hotelbeds (free sandbox) only if a hotel product is funded.
8. **Commercial real estate:** LoopNet (CoStar) and Crexi have no public APIs and block fetching; only scrapers exist. Deep-link only. Regrid parcels (2,000 records/month included, $0.10–0.15 per extra record) if zoning/ownership is needed.
9. **Places:** Overture Maps Places (CDLA-Permissive-2.0; Foursquare rows Apache-2.0 with NOTICE) stays the storable, commercial-safe POI base layer — re-verified. OSM via Overpass is fine for amenities **if kept as a separable layer**: the OSMF Collective Database guideline lets us join OSM to proprietary tables by key without share-alike, but *merging* OSM attributes into other records triggers it.
10. **Google Places (New):** only `place_id` is storable; everything else ≤30 days; free tier is now per-SKU (10,000 Essentials / 5,000 Pro / 1,000 Enterprise events per month) and Place Details Essentials (IDs Only) is unlimited free. Use live for hours/ratings; never as a stored layer.
11. **Yelp is paid-only** (Base $229/month, "Minimum 1,000 API calls billed daily") and **Tripadvisor Content API is deprecated** (readme.io: "no longer being updated", migrate to "Terra") on top of its no-database/no-commingling terms. Both rejected.
12. **Demographics, jobs, traffic, transit are free and public-domain:** ACS 5-year block-group tables (children, elderly, income, vehicles), LODES 8.4 (2023 jobs by block), NCDOT AADT (44,000+ stations, ArcGIS FeatureServer), GoTriangle/GoRaleigh/GoDurham/Chapel Hill Transit GTFS under CC BY 3.0.
13. **Quality-of-place layers are mostly free federal data**: NCES EDGE schools, NC School Report Cards (bulk download), FEMA NFHL REST, BTS noise raster, NLCD/USFS tree canopy (through 2025), EPA Walkability Index, FCC BDC, PAD-US, USGS 3DEP (live point query verified). Watch-outs: EJScreen is removed from EPA (use the PEDP mirror/Harvard Dataverse), HIFLD Open status is uncertain, GreatSchools/Walk Score/SchoolDigger are paid for commercial use.
14. **Legal posture in one line:** store open/public-domain/permissively licensed layers; link out to everything proprietary; keep OSM separable; keep Google to `place_id`; never scrape; document every source's terms in a registry before ingesting.

---

## 2. Category tables

Legend — verdict columns: **S** store, **D** display with attribution, **C** commingle, **$** commercial. ✓ allowed; ✓* allowed with the stated condition; ✗ not allowed; ? not determinable from the terms found.

### A. Residential listings

| Source | Coverage / granularity / freshness | Access | Cost | S | D | C | $ | Effort | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Zillow search deep link** | US; listing-level; live on their site | URL `?searchQueryState=` with `mapBounds` bbox (+ `regionSelection`, `filterState`) | Free | n/a (we store nothing) | n/a | n/a | ✓ (linking) | Low | **Adopt** (bbox only; polygon not encodable) |
| Zillow public API / Bridge Interactive | — | ZWSID retired 2021-09-30; Bridge needs MLS affiliation + MLS data license + Zillow approval | Brokerage-tier | ✗ for us | ✗ | ✗ | ✗ | — | **Reject** (ineligible) |
| Zillow scraping / RapidAPI "Zillow" wrappers | — | Unofficial | $5–50/mo | ✗ ToS | ✗ | ✗ | ✗ | — | **Reject** |
| **Zillow Research (ZHVI, ZORI, inventory)** | ZIP/city/county/metro; monthly; 1996→ | CSV download | Free | ✓* attribution | ✓* | ✓* | ? (ask Zillow) | Low | **Adopt** (non-commercial now; confirm before monetizing) |
| **Redfin search deep link** | US; live | `/zipcode/{zip}/filter/viewport=N:S:E:W` or `/city/{id}/{ST}/{City}/filter/...` | Free | n/a | n/a | n/a | ✓ (linking) | Low | **Adopt** |
| Redfin API | none public; Data Center = market CSVs (metro/county/city/zip/neighborhood, weekly/monthly) | Download | Free | ✓* (ToS §2.9.4 bars redistribution of "information provided through the Services" — treat Data Center as cite-and-link) | ✓* | ? | ? | Low | **Consider** (market stats only) |
| **Realtor.com deep link** | US; live | `realestateandhomes-search/{City}_{ST}/...` *(pattern unverified; site blocks fetch)* | Free | n/a | n/a | n/a | ✓ | Low | **Consider** |
| Realtor.com API | "no developer programme, no sandbox, no self-serve key" (API Evangelist); Lead Delivery API only | — | — | ✗ | ✗ | ✗ | ✗ | — | **Reject** |
| Trulia / HotPads | Zillow Group; same ToS posture | Deep link only *(URL pattern unverified)* | Free | n/a | n/a | n/a | ✓ | Low | Consider |
| Homes.com / Apartments.com (CoStar) | US | No public API; deep link only; ToS not fetchable (403) | Free | ✗ | ✗ | ✗ | ✓ link | Low | Consider (link) |
| Zumper / Rent. | Rentals | No public listing API found; syndication is inbound (landlord→site) | — | ✗ | ✗ | ✗ | ✓ link | Low | Consider (link) |
| **RentCast API** | "150+ million" US properties; active sale + rental listings, records, AVM, 38k+ ZIP market stats | REST | Developer $0/50 req·mo; Foundation $74/1,000; Growth $199/5,000; Scale $449/25,000; overage $0.20→$0.015 | ✓ "store the API Data within your internal systems" | ✓ (no attribution required, §3.4) | ✓* | ✓* (per API License §1 permitted uses) | Low | **Adopt for prototype**; re-read §1 scope before monetizing |
| ATTOM | US parcels, sales, AVM, listings | REST; 30-day trial | Unpublished; third-party reports ~$95/mo entry, enterprise quotes | ✓* (contract) | ✓* | ✓* | ✓* | Med | Consider later |
| Realty Mole | Rebranded as RentCast | — | — | — | — | — | — | — | (see RentCast) |
| RESO Web API | A *standard*, not a data source: "RESO does not provide MLS real estate data" | Via each MLS | Per MLS | — | — | — | — | — | n/a |
| **MLS/IDX — Doorify MLS (Triangle)** | Wake/Durham/Orange/Johnston etc. *(county list unverified)*; ~10,000 active; sold 36 mo; daily | RESO Web API via Spark; requires participant brokerage, data license, vendor agreement | $35 connection + $5/mo (IDX Broker page) | ✓* IDX display only, refresh ≤3 days | ✓* broker-controlled display, MLS disclosures | ✗ ("searched separately" rule) | ✓* via brokerage | High (partnership) | **Consider — the only legal path to listing pins** |
| Homesnap | Reported folded into Homes.com (CoStar) *(unverified)* | — | — | — | — | — | — | — | Reject |
| HAR | Houston-only MLS portal | — | — | — | — | — | — | — | n/a for NC |
| **Wake County parcels + real-estate files** | All Wake parcels; daily | ArcGIS REST, CSV, GeoJSON; xlsx/mdb/txt data files | Free | ✓ CC BY 4.0 | ✓ | ✓ | ✓ | Low | **Adopt** |
| **Orange County GIS downloads** | Parcels (annual Jan-1 snapshots 2000–2026), addresses, zoning | Shapefile/GDB directory | Free | ✓ (disclaimer file) | ✓ | ✓ | ✓ | Low | **Adopt** |
| Durham City/County Open Data | Parcels, crime, etc. | ArcGIS Hub | Free | ✓ *(license field unverified)* | ✓ | ✓ | ✓ | Low | Adopt (verify license) |
| FHFA HPI | Tract/ZIP/county/MSA; quarterly/annual | CSV | Free | ✓ public | ✓ | ✓ | ✓ | Low | Adopt |
| HUD (FMR, income limits, USPS crosswalk) | County/ZIP; annual | HUD User API / CSV *(API terms not fetched)* | Free | ✓ public | ✓ | ✓ | ✓ | Low | Adopt |

### B. Hotels and commercial

| Source | Coverage / freshness | Access | Cost | S | D | C | $ | Effort | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Amadeus Self-Service Hotel Search | Global | Reported decommissioned 2026-07-17; "enterprise-only" *(unverified; portal pages returned empty)* | — | — | — | — | — | — | **Reject** (unavailable) |
| Booking.com Demand API | Global live inventory | "Registered as a Booking.com Managed Affiliate Partner" + "signing the agreed contract" + Partner Centre key | Commission model | ✓* contract | ✓* | ? | ✓* | High | Consider later (needs partner status) |
| Booking.com affiliate deep link | Global | URL with destination + dates *(pattern unverified)* | Free | n/a | n/a | n/a | ✓ | Low | **Adopt** |
| Expedia Rapid | Global | Commercial agreement; "individual developers and non-travel businesses do not qualify" | Negotiated | ✓* | ✓* | ? | ✓* | High | Reject for now |
| Hotelbeds APItude | Global B2B | Free evaluation key + sandbox; certification before production; contract terms not stated on page | Free sandbox | ? | ? | ? | ✓* | Med | Consider (if hotel product funded) |
| Google Hotels deep link | Global | `google.com/travel/hotels?q=...` *(pattern unverified)* | Free | n/a | n/a | n/a | ✓ | Low | Adopt |
| Airbnb | — | No public API (partner program only) *(page not fetchable)* | — | ✗ | ✗ | ✗ | ✓ link | Low | Link only |
| LoopNet / CoStar | US commercial | No API; ToS 403 to fetch; only Apify scrapers exist | — | ✗ | ✗ | ✗ | ✓ link | Low | **Link only; never scrape** |
| Crexi | US commercial | No public API; ToS 403 | — | ✗ | ✗ | ✗ | ✓ link | Low | Link only |
| Brevitas / CommercialCafe | US commercial | No public API found *(unverified)* | — | ✗ | ✗ | ✗ | ✓ link | Low | Link only |
| Regrid parcel API | US parcels incl. zoning/ownership | REST + tiles; self-serve monthly plan includes 2,000 parcel records + 200,000 tiles; overage $0.10 (Standard) / $0.15 (Premium) per record; enterprise $12–18k/yr (third-party) | See left | ✓* plan terms | ✓* | ✓* | ✓* | Med | Consider (commercial site selection phase) |

### C. Places / POIs

| Source | Coverage / freshness | Access | Cost | S | D | C | $ | Effort | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **OpenStreetMap (Overpass)** | Global; live | Overpass API / planet extracts | Free | ✓ ODbL | ✓ "© OpenStreetMap contributors" | ✓* keep as separable layer (Collective Database) | ✓ | Low (already integrated) | **Adopt** |
| **Overture Maps Places** | Global; monthly releases (2026-09/10 cited) | Parquet (S3/Azure), DuckDB | Free | ✓ CDLA-Permissive-2.0 / Apache-2.0 (Foursquare rows) | ✓ (NOTICE for FSQ rows) | ✓ | ✓ | Med | **Adopt** (base POI layer) |
| Foursquare OS Places | "100M+" POIs | Hugging Face / S3 / Snowflake | Free | ✓ Apache-2.0 | ✓ NOTICE.txt | ✓ | ✓ | Med | Consider (Overture already includes FSQ rows) |
| **Google Places (New)** | Global; live | REST; field masks | 10k/5k/1k free events per SKU·mo; Text Search $32/$32/$35, Nearby Pro $32, Place Details $5/$17/$20/$25 per 1k; IDs-only unlimited | ✗ except `place_id`; others ≤30 days | ✓* Google Maps logo/text attribution | ✗ | ✓* | Med | **Consider — live enrichment only** |
| Yelp Places (Fusion) | US+ | REST | Base $229/mo (+$5.91/1k), Enhanced $299, Premium $643; 30-day/5,000-call trial; "Minimum 1,000 API calls billed daily" | ✗ (>24h) | ✓* | ✗ | ✓* paid | Med | **Reject** (cost + terms) |
| Tripadvisor Content API | Global | REST — **deprecated**, "no longer being updated", migrate to "Terra" | — | ✗ (no searchable DB) | ✓* | ✗ | ✓* | — | **Reject** |
| HERE Geocoding & Search | Global | REST; freemium *(limits unverified — pricing page did not disclose)* | Free tier | ? | ✓* | ? | ✓* | Med | Consider (fallback geocoder) |
| Mapbox Search Box / Geocoding / Isochrone | Global | REST | Search Box 500 sessions or 50k requests free; Geocoding (Temporary) 100k free; Isochrone 100k free; Static Images 50k free | ✗ for "Temporary" geocoding (store requires Permanent product) *(ToS not fetched)* | ✓* | ? | ✓* | Med | Consider (isochrone fallback to Valhalla) |
| Geoapify Places | Global (OSM-based) | REST | Free "Limited Commercial Use"; API 10 $59/mo | ✓* OSM-derived | ✓* OSM + Geoapify attribution | ✓* | ✓* paid | Low | Consider (in-house verified) |
| OpenAddresses | Global address points | Bulk | Free | ✓* per-source license ("not relicensed from the original sources") | ✓* | ✓* | ✓* | Med | Consider (NC county sources are generally open; check each) |

### D. Demographics and economy

| Source | Granularity / freshness | Access | Cost | S | D | C | $ | Effort | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Census ACS 5-year** (B01001 age/sex, B19013 income, B25044 vehicles, B11005 households w/ children, etc.) | Block group; annual (2020–2024 current) | api.census.gov (key; disclaimer string required) | Free | ✓ | ✓* disclaimer | ✓ | ✓ | Low | **Adopt** |
| Decennial 2020 (PL/DHC) | Block | API | Free | ✓ | ✓* | ✓ | ✓ | Low | Adopt |
| **LEHD LODES 8.4** (2023 data, Dec 2025) | Census block; WAC/RAC/OD | `lehd.ces.census.gov/data/lodes/LODES8/nc/` CSV.gz | Free | ✓ | ✓ | ✓ | ✓ | Low | **Adopt** (workplace locations) |
| OnTheMap | Same data, interactive | Web app | Free | — | — | — | — | — | Reference only |
| BLS (LAUS, QCEW, CES) | County/MSA; monthly/quarterly | Public Data API v1 (no key) / v2 (key) | Free | ✓ | ✓ | ✓ | ✓ | Low | Adopt (metro context) |
| IRS SOI migration | County-to-county; filing years 1991–2023 | CSV/XLSX | Free | ✓ | ✓ | ✓ | ✓ | Low | Adopt (metro context) |
| Census Geocoder | US; batch | REST | Free | ✓ public | ✓* disclaimer | ✓ | ✓ | Low | Adopt (in-house verified; ~81% match, fallback needed) |

### E. Traffic and transportation

| Source | Coverage / freshness | Access | Cost | S | D | C | $ | Effort | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **NCDOT AADT stations + traffic segments** | NC, 44,000+ stations, 2002→; annual (2025 published as GDB; 2015–2024 shapefiles) | ArcGIS FeatureServer `services.arcgis.com/NuWFvHYDMVmmxMeM/.../NCDOT_AADT_Stations`; GDB download | Free | ✓ (mapping disclaimer) | ✓ | ✓ | ✓ | Low | **Adopt** |
| FHWA HPMS public release | All states; 2018 shapefiles (AADT, truck AADT, functional class) | Shapefile / REST per state | Free | ✓ ("The user assumes the risk") | ✓ | ✓ | ✓ | Low | Adopt (other-metro fallback) |
| Other state DOT AADT portals | Varies | ArcGIS Hub typical | Free | ✓ typical | ✓ | ✓ | ✓ | Low–Med | Adopt per metro |
| Replica / StreetLight | US mobility models | Subscription; Replica $0.15–0.25/resident for agencies; StreetLight quote-based | $$$ | ✓* | ✓* | ✓* | ✓* | High | Reject for now |
| **GTFS — GoTriangle, GoRaleigh, GoDurham, GoCary, Chapel Hill Transit, Duke, NCSU** | Schedules + GTFS-RT | Agency URLs listed on gotriangle.org/developer-resources (CC BY 3.0); Mobility Database (mdb-376/377, GoDurham → tld-98); Transitland | Free | ✓ | ✓ | ✓ | ✓ | Low | **Adopt** |
| Transitland API | Global GTFS aggregator | REST; Explorer plan free; Pay-as-you-go commercial; datasets "free for non-commercial use" (beta) | Free→paid | ✓* | ✓ | ✓ | ✓* | Low | Consider (feed discovery) |
| BTS National Transit Map | US; NTAD | GeoJSON/Shapefile | Free | ✓ | ✓ | ✓ | ✓ | Low | Consider |
| Airports / flights | Not needed deeply | FAA/BTS public | Free | ✓ | ✓ | ✓ | ✓ | Low | Defer |

### F. Quality-of-place layers

| Source | Granularity / freshness | Access | Cost | S | D | C | $ | Effort | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **NCES EDGE school locations** | Points, public 2024-25 (annual), private (biennial) | CSV/GeoJSON/Shapefile; REST `nces.ed.gov/opengis/rest/services/K12_School_Locations/EDGE_GEOCODE_PUBLICSCH_2425` | Free | ✓ | ✓ | ✓ | ✓ | Low | **Adopt** |
| **NC School Report Cards** | School; 2024-25 (2-part dataset + dictionary) | Download from DPI | Free | ✓ (no stated terms) | ✓ | ✓ | ✓ | Low | **Adopt** (ratings without a vendor) |
| GreatSchools NearbySchools API | US; ratings | REST; School Essentials $52.50/mo (15k calls), School Quality $97.50/mo; 14-day trial | Paid | ? | ✓* branding | ? | ✓* | Low | Consider later |
| SchoolDigger API | US | Free DEV/TEST; Basic $19.90, Pro $89 (adds lat/long search), Enterprise $189 (adds district-by-address); 2,000 calls each | Paid | ? | ✓* | ? | ✓* | Low | Consider |
| **Crime — Raleigh (NIBRS since 2014 + daily), Durham (DPD Crime 2017→), Chapel Hill (Police Incident Reports Written)** | Incident-level; daily/weekly | ArcGIS Hub portals | Free | ✓ | ✓ | ✓ | ✓ | Med (schema differs per city) | **Adopt** |
| CrimeoMeter / SpotCrime | 700+ cities (CrimeoMeter) | REST; quote-based; SpotCrime *(no public API found; unverified)* | Paid | ✓* | ✓* | ? | ✓* | Low | Reject for now |
| **FEMA NFHL** | National; effective FIRM | REST `hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer`, WFS, nationwide download | Free | ✓ | ✓ | ✓ | ✓ | Low | **Adopt** |
| EPA EJScreen | Block group; v2.3 (2024) | **Removed from EPA 2025-02-05**; PEDP mirror `screening-tools.com/epa-ejscreen`; Harvard Dataverse DOI 10.7910/DVN/RLR5AX | Free | ✓ (public-domain federal data) | ✓ | ✓ | ✓ | Med | Consider (static 2024 snapshot) |
| AirNow API | Current/forecast AQI by lat/lon or ZIP | Account + key; six web services replaced Sept 2026; CSV/JSON/XML; "preliminary and subject to change" | Free | ✓* | ✓ | ✓ | ✓ | Low | Adopt (live) |
| **BTS National Transportation Noise Map 2020** | 30 m raster (road/rail/aviation) | GeoTIFF/GDB | Free | ✓ | ✓ | ✓ | ✓ | Med | **Adopt** |
| **NLCD Annual (Collection 1.2, 1985–2025) + USFS tree canopy** | 30 m | MRLC download | Free | ✓ public domain | ✓ | ✓ | ✓ | Med | **Adopt** (canopy) |
| ESA WorldCover 2020/2021 | 10 m | COG tiles | Free | ✓ CC BY 4.0 | ✓ "© ESA WorldCover project [year] / Contains modified Copernicus Sentinel data…" | ✓ | ✓ | Med | Consider (NLCD preferred for US) |
| **EPA National Walkability Index (2021)** | 2019 block groups | ZIP download | Free | ✓ | ✓ | ✓ | ✓ | Low | **Adopt** |
| Walk Score API | US scores | Free 5,000 calls/day "For free consumer-facing applications only"; Premium from $115/mo (adds caching permission, Travel Time, Score Details) | Free→paid | ✗ free tier (caching is a Premium feature) | ✓* logo + help link | ? | ✗ free tier | Low | Consider (Premium only if monetized) |
| **FCC BDC availability** | Location-level (Fabric IDs; coordinates licensed) and block/hex summaries; semiannual | CSV by state/technology/date | Free | ✓ (Fabric itself licensed from CostQuest) | ✓ | ✓ | ✓ | Med | Adopt (summaries) |
| TPL ParkServe | City parks + 10-min walk service areas | Download *(page 403; license unverified)* | Free | ? | ? | ? | ? | Low | Consider |
| **USGS PAD-US 4.1 (2024)** | Protected/park areas | GDB/KMZ by state | Free | ✓ (cite USGS) | ✓ | ✓ | ✓ | Low | **Adopt** |
| HIFLD hospitals | National | *(portal 403; 2025 HIFLD Open retirement reported, unverified)*; alternatives: CMS Provider of Services, NC DHSR facility lists | Free | ✓ | ✓ | ✓ | ✓ | Low | Consider (verify status) |
| USDA Food Access Research Atlas | Tract; 2019 LRAM (2010 tracts) + 2025 SRAM (2020 tracts) | CSV/XLSX + geospatial API | Free | ✓ | ✓ | ✓ | ✓ | Low | Adopt |
| **USGS 3DEP via EPQS** | 1 m–1/3″; live point query (verified: Durham 108.3 m) | `epqs.nationalmap.gov/v1/json?x=&y=&units=Meters&wkid=4326` | Free | ✓ | ✓ | ✓ | ✓ | Low | **Adopt** |

---

## 3. Detailed notes on high-stakes items

### 3.1 Zillow — deep links, polygon encoding, ToS

**URL scheme.** Zillow search pages are addressed by `https://www.zillow.com/homes/<slug>_rb/?searchQueryState=<URL-encoded JSON>`. Independent documentation (pseudo-r/Public-Zillow-API; Scrapfly; Apify Zillow actors) agrees on the JSON shape: `pagination`, `usersSearchTerm`, `mapBounds {west,east,south,north}`, `regionSelection [{regionId, regionType}]`, `filterState`, `isMapVisible`, `isListVisible`. The Apify actor's example input also shows a `customRegionId` inside `searchQueryState` and instructs users to copy the URL "from Zillow.com website" after drawing. None of the three sources documents a way to put polygon coordinates in the URL; the Public-Zillow-API README "does not mention custom polygon regions or a `customRegionId` parameter" and describes `regionSelection` only as autocomplete-derived IDs. **Inference (unverified):** `customRegionId` is an opaque identifier Zillow mints server-side when a user draws, so a third party cannot encode an arbitrary polygon — only a bounding box (`mapBounds`) plus optional known region IDs. Scrapfly's note that "with these 4 values we can draw a square" confirms bbox is the controllable primitive.

**What we must not do.** The `PUT https://www.zillow.com/async-create-search-page-state` endpoint those write-ups describe is an undocumented internal API; calling it is automated access. Zillow's Terms of Use (zillow.com returned HTTP 403 to our fetch; quoted via secondary sources and the ConductAtlas mirror captured 2026-10-16): *"You may not use any robot, spider, scraper or other automated means to access the Services for any purpose without our express written permission."* The mirror also summarizes a clause limiting MLS listing data to "Personal Non-Commercial Purposes" and a restriction on third-party links to agent profiles. Zillow's original ZWSID API was retired 2021-09-30; Bridge Interactive requires MLS affiliation, a data-licensing agreement with each MLS, and Zillow approval — not available to us.

**Product implication.** Build the link as `mapBounds` = polygon envelope, `isMapVisible:true`, `filterState` from the user's price/beds, and label it "Open these results on Zillow". Show the exact polygon on *our* map so the user can see which part of the Zillow box is in-region. Plain hyperlinks to public pages are not "automated access" and are the ordinary web; we store nothing from Zillow.

### 3.2 Redfin — URL format and ToS

**URL format.** Example from an actor README: `https://www.redfin.com/zipcode/32754/filter/viewport=28.61051:28.50029:-81.21071:-81.41155,no-outline` — the viewport is `north:south:east:west`; filters are path segments after `/filter/` (e.g., `include=sold-3mo`, `/rentals`). City searches use `/city/{regionId}/{ST}/{City}/filter/...` (region_type 6 = city, 5 = county, 1 = neighborhood per Piloterr/Litescrape docs).

**ToS (Last Updated September 29, 2025).** §2.3.5: *"You may not automatedly crawl or query the Services for any purpose or by any means (including, without limitation, screen and database scraping, spiders, robots, crawlers …) unless you have received prior express written permission."* §2.9.4: users *"will not … display, post, disseminate, distribute, publish, broadcast, transfer, sell, or sublicense, any information provided through the Services to another individual or entity"* and this *"expressly includes 'scraping' … 'data mining', or any other activity intended to collect, store, re-organize, summarize, or manipulate any information provided."* No clause restricts others linking to Redfin. **Verdict:** deep-link adopt; any data capture reject. Redfin Data Center CSVs (metro/county/city/ZIP/neighborhood, weekly/monthly) are published for download but the page states no separate license; §2.9.4 is broad enough that we should cite-and-link rather than redistribute them.

### 3.3 Realtor.com, Trulia, Homes.com, rentals

Realtor.com: *"no developer programme, no sandbox, no self-serve key, and no published rate card"* (API Evangelist profile); only a Lead Delivery API for CRMs. realtor.com blocked our fetch, so the search-URL pattern (`/realestateandhomes-search/{City}_{ST}/price-{min}-{max}/beds-{n}`) is recorded as *(observed pattern, unverified this session)*. Trulia/HotPads are Zillow Group and inherit the same posture. Homes.com and Apartments.com are CoStar; a CoStar document dated 2026-02-23 describes Homes.com's AI search as engineered so that "MLS listing data cannot be ingested and 'learned' … or accessed by third parties" — a signal of how tightly IDX data is guarded and how CoStar views third-party extraction. Rentals: Zumper/Rent./Apartments.com expose landlord-side syndication, not consumer-side APIs; link only.

### 3.4 MLS / IDX — what legal listing data actually requires

- **RESO** (reso.org): *"RESO does not provide MLS real estate data. RESO creates data standards."* and *"Access to data from the Web API is gained through local MLSs. After agreeing to an MLS's data use and licensing policies, data recipients work directly with that MLS's software provider."*
- **Doorify MLS** (formerly Triangle MLS): IDX feed via Spark Web API; IDX Broker lists "Data Connection Fee: $35.00", "Data Management Fee(s): $5.00 Monthly", ~10,000 listings, sold data 36 months, daily refresh. Vendor pages state you need an active Doorify subscription through a participating firm. doorifymls.com returned 403 to our fetch, so Doorify's own vendor/data-license page is *(unverified)*.
- **NAR IDX Policy (Policy Statement 7.58)** — the binding frame (verbatim from the NAR PDF):
  - *"Electronic display subject to this policy means displays on participants' public websites and displays using applications for mobile devices that participants control."*
  - *"All displays of IDX listings must also be under the actual and apparent control of the participant, and must be presented to the public as being the participant's display."* Actual control = "an agreement giving the participant authority to determine what listings will be displayed, and how"; apparent control = "a reasonable consumer … will understand the display is the participant's."
  - *"MLS participants may not use IDX-provided listings for any purpose other than IDX display."*
  - *"Participants must refresh all MLS downloads and displays automatically fed by those downloads not less frequently than every three (3) days."*
  - MLSs "can, as a matter of local option, require that listings obtained through IDX be searched separately from listings obtained from other sources."
  - Comments/reviews or "an automated estimate of the market value of the listing (or hyperlink to such estimate) in immediate conjunction with the listing" must be disabled at the seller's request.
- **Participation** requires a current real-estate broker's license (NAR "Qualification for MLS Participation and IDX").

**Implication.** We cannot hold an IDX feed ourselves. The viable structure is a partner brokerage that holds the Doorify feed and controls a listing panel (branded as theirs) embedded in our result view, with our polygon used only as a *search filter* passed to their display. Analytics over IDX data (counts, medians, "homes in your polygon") are *not* IDX display and would need a separate MLS data license (sometimes called "back-office"/"analytics" licenses; terms and fees *(unverified)*). County assessor sales data covers the analytics need without MLS.

### 3.5 RentCast — the cheap legal shortcut

Pricing (rentcast.io/api): Developer $0 for 50 requests/month ($0.20 overage); Foundation $74 for 1,000; Growth $199 for 5,000; Scale $449 for 25,000. API License (rentcast.io/terms-api): §1 grants rights *"to incorporate and store the API Data within your internal systems as necessary to perform the permitted uses"* and *"to sublicense, disclose, display, resell and distribute the API Data to third parties"* within the §1 permitted-use list; §4 limits redistribution to what §1 "expressly permit[s]"; §3.4: *"neither use of the RentCast API nor use of the API Data requires attribution."* Caveats: we captured fragments of §1, not the whole list — read it in full; RentCast aggregates listings from public sources rather than MLS licenses, so provenance risk sits with them, not with us, but a monetized product should confirm their upstream rights in writing.

### 3.6 County assessor data (Wake, Durham, Orange)

Wake County Parcels (DCAT feed): license `https://creativecommons.org/licenses/by/4.0`, modified 2026-11-03, "updates daily", GeoService `maps.wake.gov/arcgis/rest/services/Property/Parcels/MapServer/0`, CSV/GeoJSON downloads. Wake Tax Administration real-estate files: ownership, sale information, values "as of the most recent countywide reappraisal", building characteristics, qualified arms-length sales (24 months); xlsx/mdb/txt; "refreshed daily". Orange County (`web.co.orange.nc.us/gisdownloads/`): parcels as annual January-1 snapshots 2000–2026 (shapefile + GDB), addresses with data dictionary, zoning, boundaries; disclaimer `ReadMe_OCNC_Disclaimer.txt` (2018). Durham's joint portal exists (`live-durhamnc.opendata.arcgis.com`) and hosts the DPD crime table; parcel license *(unverified)*. Under North Carolina public records law these are public records; the CC BY 4.0 tag on Wake makes storage, commingling and commercial use explicit.

### 3.7 Zillow Research public data

zillowgroup.com developers page: *"All data accessed and downloaded from this page is free for public use by consumers, media, analysts, academics and policymakers, consistent with our published Terms of Use. Proper and clear attribution of all data to Zillow is required."* CSV at neighborhood/ZIP/city/county/metro/state; monthly; history to the late 1990s. A 2019 version of the research page reportedly limited use to non-commercial and directed other uses to Zillow Research; that language is gone but has not been replaced by a grant. **Verdict:** adopt with attribution for the friends-and-family phase; email Zillow Research before monetizing.

### 3.8 OSM / ODbL — mixing OSM with other data

Two OSMF-endorsed guidelines govern us (both read 2026-11-03):

- **Produced Work guideline:** a Produced Work is *"a work (such as an image, audiovisual material, text, or sounds) resulting from using the whole or a Substantial part of the Contents"*; the test is whether the output is *"intended for the extraction of the original data."* Our rendered result polygons and ranked lists are Produced Works (attribution required; share-alike does not attach), but if we publish an OSM-derived *database* (e.g., a downloadable POI table) it is a Derivative Database and must be ODbL.
- **Collective Database guideline:** OSM and non-OSM data remain a Collective Database (share-alike only on the OSM part) when *"the data used for a particular data type is either all OSM or all non-OSM within the same regional cut,"* when datasets do not cross-reference, when non-OSM data "completely replaces a particular type of geometry or data," or adds new feature types. Joining tables "by a key for purposes of a production database" is permitted (the phone-number example). *Merging* proprietary attributes into OSM records (or using OSM to correct proprietary records) "likely triggers share-alike."

**Design rule:** keep an `osm_poi` table (ODbL, attributed) separate from `overture_place`, `assessor_parcel`, `rentcast_listing`; link by our own entity ID; never backfill one from the other. Individual geocodes are insubstantial extracts (in-house verified). Nominatim/Overpass public instances carry usage policies (≤1 req/s, identifying User-Agent) — self-host for volume.

### 3.9 Overture Maps Places (re-verified)

docs.overturemaps.org/attribution: Places rows are CDLA-Permissive-2.0 from Meta, Microsoft, PinMeTo, Krick, RenderSEO, DAC, BrightQuery, Birdeye, Uberall, OpenTravel Alliance ("require no specific attribution"); Foursquare rows are Apache-2.0 ("Requires inclusion of their NOTICE.txt"); AllThePlaces CC0. Other themes are ODbL (base, buildings, divisions, transportation — attribute "© OpenStreetMap contributors") and addresses carry per-country permissive licenses. Releases continue monthly (2026-09-23.1 and October 2026 cited by downstream repos). The in-house live Chapel Hill test (655 venues, ~92% phone, ~91% website, confidence scores) still stands as the capability evidence; filter on confidence ≥0.85.

### 3.10 Google Places (New) — caching and pricing

Policies page (verbatim): *"Note that the place ID, used to uniquely identify a place, is exempt from the caching restrictions."* *"Attribution should take the form of the Google Maps logo whenever possible. In cases where space is limited, the text Google Maps is acceptable."* *"Position attribution near the top or bottom of the content, and within the same visual container."* AI summaries: *"Always include the localized disclosure text … immediately below the summary."* The 30-calendar-day cap on all other Content and the lat/lng temporary-cache rule were verified in-house against the Service Specific Terms (2026-06-28) and are unchanged in substance. Pricing (developers.google.com pricing page): free thresholds 10,000 (Essentials), 5,000 (Pro), 1,000 (Enterprise) events per SKU per month; Text Search $32/$32/$35 per 1,000; Nearby Search Pro $32, Enterprise $35; Place Details $5/$17/$20/$25 (Enterprise + Atmosphere); "Places API Place Details Essentials (IDs Only)" unlimited free. Caps do not pool across SKUs. **Verdict unchanged:** live enrichment only, store `place_id`, logo attribution on any visual surface, narrow field masks.

### 3.11 Yelp and Tripadvisor

Yelp Places API (business.yelp.com): Base $229/mo (+$5.91/1k), Enhanced $299 (+$6.57/1k, 3 photos, 3 review excerpts), Premium $643 (+$14.13/1k); trial 5,000 calls/30 days; *"Minimum 1,000 API calls billed daily."* ToS (in-house verified 2025-01-13 version): ≤24-hour cache, IDs only, no commingling, database carve-out non-commercial only. Reject.
Tripadvisor Content API overview (readme.io, 2026-11-03): the API is deprecated and *"no longer being updated"*; developers should migrate to *"Terra, … our new and actively maintained API platform."* The terms page we had on record now 404s; Terra's terms are *(unverified)*. The in-house reject (searchable-database and commingling bans) stands and is now moot for new integrations.

### 3.12 Hotels

Booking.com Demand API prerequisites (verbatim): *"Registered as a Booking.com Managed Affiliate Partner."* *"Access to Partner Centre (provided by your Booking.com Account Manager after signing the agreed contract)."* Expedia Rapid: commercial agreement; partners "negotiate minimum volume commitments" (secondary). Hotelbeds: "For a free API Key. Access to Evaluation Plan"; production needs certification. Amadeus: multiple secondary sources state the Self-Service portal was decommissioned 2026-07-17 and there is "no free tier for independent developers anymore"; developers.amadeus.com pages returned no content to our fetch, so this is *(unverified)* but should be treated as unavailable for planning.

---

## 4. Recommended data stack — Research Triangle wedge, and how it generalizes

**Stored, commercial-safe core (PostGIS):**
- Parcels + assessor sales: Wake (CC BY 4.0, daily), Orange (annual snapshots + addresses), Durham (verify license). → housing stock, lot sizes, recent sale prices, year built; "homes like this exist here" counts inside any polygon.
- Overture Places (monthly refresh, confidence ≥0.85) as the POI base; `osm_poi` as a separate ODbL table for amenity categories Overture lacks (playgrounds, trailheads, bus stops).
- ACS 5-year block groups (children <5 and 5–17, 65+, median income, vehicles available, commute mode), Decennial 2020 blocks, LODES 8.4 WAC/RAC blocks (where jobs are; where workers live).
- NCDOT AADT stations and segments (noise/traffic proxy), BTS 2020 noise raster, NLCD 2025 canopy, EPA Walkability Index, FEMA NFHL zones, PAD-US + municipal parks, NCES EDGE schools + NC School Report Card grades, Raleigh/Durham/Chapel Hill incident feeds (normalized to NIBRS categories, aggregated to block group), FCC BDC summaries, USDA food access, 3DEP elevation via EPQS (slope/views).
- GTFS (CC BY 3.0) for the seven Triangle feeds → stop density, headways; Valhalla multimodal isochrones already in the backend.

**Live-only, never stored:** Google Places (hours/rating, `place_id` only), AirNow AQI, GTFS-RT.

**Listings linkage (free):** per result polygon, emit (a) Zillow link with `mapBounds` = envelope and user filters; (b) Redfin `viewport=N:S:E:W` link; (c) Realtor.com and Trulia links *(patterns to verify)*; (d) rentals: Zillow Rentals/Apartments.com links. Show the polygon on our map; state plainly that the external site shows its box, not our shape. **Prototype listing pins:** RentCast Developer/Foundation tier, clearly labeled, stored per its API License. **Public/monetized listing pins:** a Doorify-participant brokerage partner controlling an IDX display component (refresh ≤3 days, broker branding, no AVM/review adjacency), or a licensed analytics feed if we need counts/medians beyond assessor data.

**Hotels (later):** Google Hotels and Booking deep links with dates; Hotelbeds sandbox for a funded pilot. **Commercial (later):** LoopNet/Crexi deep links; Regrid self-serve for zoning/ownership; LODES WAC for daytime population; AADT for exposure.

**Generalizing to other metros:** every layer above except the three NC specifics has a national equivalent already in the table — FHWA HPMS or the state DOT ArcGIS Hub replaces NCDOT; the county's ArcGIS Hub/Socrata parcel layer replaces Wake (license varies: most are public records, some restrict commercial use — check each); state DPI report cards replace NC's; Mobility Database/Transitland locate GTFS; the city's open-data portal supplies crime. The only layers that do not generalize cheaply are MLS listings (each MLS, each brokerage partner) and school ratings (buy GreatSchools/SchoolDigger or use state files).

---

## 5. Legal posture — rules the product must follow

1. **Never scrape or call undocumented endpoints** of Zillow, Redfin, Realtor.com, Trulia, Homes.com, Apartments.com, LoopNet, Crexi, Airbnb; never use RapidAPI/Apify "APIs" for them. Plain deep links only, with no data captured from the destination.
2. **Hold no MLS data without a license**; any IDX display must be a participant-controlled component meeting Policy 7.58 (actual/apparent control, brokerage identification, ≤3-day refresh, no AVM/review adjacency, searched separately from other sources). IDX data is for display only — no analytics.
3. **Google Places:** store `place_id` only; purge other fields ≤30 days; Google Maps logo/text attribution in the same container; narrow field masks; never show Google content as if it were ours.
4. **OSM separability:** OSM-derived rows live in their own tables/layers, attributed "© OpenStreetMap contributors"; no backfilling between OSM and proprietary records; publish derived *databases* (if ever) under ODbL.
5. **Overture/Foursquare:** carry the Foursquare NOTICE where Apache-2.0 rows are redistributed; don't republish raw bulk as a competing dataset.
6. **Public-domain federal data** (Census, LODES, BLS, FHFA, HUD, FEMA, BTS, NLCD, PAD-US, 3DEP, NCES, FCC): store freely; display the Census API disclaimer string; never combine to identify individuals.
7. **Attribution-required data:** Zillow Research ("Data: Zillow Research, zillow.com/research/data"), Wake County (CC BY 4.0), GoTriangle feeds (CC BY 3.0), ESA WorldCover string if used, Walk Score logo + help link if used.
8. **Paid-API terms travel with the data:** Yelp (24 h, no commingling) and Tripadvisor (no database) are rejected precisely because our architecture cannot honor them; GreatSchools/SchoolDigger/Walk Score need paid tiers for commercial use and caching.
9. **Commercialization tripwires to clear before monetizing:** Zillow Research commercial use; RentCast §1 scope and upstream provenance; Geoapify/Transitland "limited/non-commercial" free tiers; Walk Score free tier ("free consumer-facing applications only").
10. **Source registry discipline:** no layer enters the pipeline without a registry row (URL, license/ToS text, access date, permitted uses, refresh cadence, attribution string), mirroring `legal-and-data-use.md`.
11. **Facts, not expression:** store non-copyrightable facts and our own derived descriptors; never republish listing photos, remarks, or review prose.

---

## 6. Open questions

1. **Doorify MLS vendor terms:** exact participant/vendor agreements, whether an analytics (non-display) license exists and its price; whether a single partner brokerage can sponsor a third-party app's IDX component across the whole Doorify footprint. (doorifymls.com blocked our fetch.)
2. **Zillow `customRegionId`:** confirm by hand that drawing a region yields an opaque ID and that no polygon can be pre-encoded; confirm `mapBounds`-only links open as expected on mobile.
3. **Realtor.com and Trulia URL patterns** and realtor.com ToS linking clause (site blocks automated fetch — check manually).
4. **Zillow Research commercial use:** written confirmation from Zillow Research.
5. **RentCast API License §1** full permitted-use list and RentCast's upstream listing provenance.
6. **Amadeus Self-Service status** (reported decommissioned 2026-07-17) and whether any free hotel-search API remains.
7. **Durham parcel/sales license** on the joint portal; Orange County disclaimer text (2018 file).
8. **HIFLD Open status** and the best public hospital layer (CMS vs NC DHSR).
9. **TPL ParkServe license** (commercial use?) vs relying on PAD-US + municipal parks.
10. **Tripadvisor "Terra"** terms — does the new platform keep the no-database rule?
11. **AirNow rate limit** (fact sheet did not state it; commonly cited 500 requests/hour *(unverified)*).
12. **HERE freemium limits** (pricing page did not disclose).

---

## 7. Sources (accessed 2026-11-03 unless noted)

In-house:
- `C:/Users/arikt/documents/github/localUpdates/docs/research-findings.md` (2026-06-28) — §2.2, §2.5, §6.
- `C:/Users/arikt/documents/github/localUpdates/docs/legal-and-data-use.md` (2026-07-01) — commercialization matrix rows 3, 9–11, 15–18.

Listings:
- https://github.com/pseudo-r/Public-Zillow-API — searchQueryState structure; "Unofficial project … follow Zillow's terms of service."
- https://apify.com/maxcopell/zillow-scraper — URL "must contain `?searchQueryState=`"; `customRegionId` example.
- https://scrapfly.io/blog/posts/how-to-scrape-zillow — mapBounds description.
- https://conductatlas.com/platform/zillow/zillow-terms-of-use/ — third-party mirror/summary of Zillow ToU, captured 2026-10-16 (zillow.com/z/corp/terms/ and zillow.com/corporate/terms-of-use/ returned HTTP 403).
- https://zillapi.com/zillow-api/ and https://scrapeops.io/websites/zillow/ — secondary; ZWSID retirement 2021-09-30, Bridge Interactive requirements, ToS scraping quote.
- https://www.zillowgroup.com/developers/api/public-data/real-estate-metrics/ — Zillow Research data terms.
- https://apify.com/mlg14/redfin-scraper.md — Redfin viewport URL example.
- https://www.redfin.com/about/terms-of-use — Redfin Terms of Use, Last Updated 2025-09-29 (§2.3.5, §2.9.4).
- https://www.redfin.com/news/data-center/ and https://www.redfin.com/news/data-center/downloads/ — Data Center contents.
- https://github.com/api-evangelist/realtor-com — Realtor.com API status (no developer program).
- https://www.rentcast.io/api — pricing; https://www.rentcast.io/terms-api — API License §1, §3.4, §4; https://www.rentcast.io/terms.
- https://zillapi.com/blog/attom-api/ and https://blog.iq.dwellsy.com/attom-data-overview-2026-property-ownership-and-market-data-explained/ — ATTOM pricing (secondary).
- https://www.idxbroker.com/mls/doorify-mls-dmls — Doorify MLS feed fees, Spark Web API, refresh.
- https://showcaseidx.com/mls-coverage/triangle-mls-triangle-2/ — Doorify subscription requirement (secondary).
- https://www.reso.org/reso-web-api/ — "RESO does not provide MLS real estate data."
- https://www.nar.realtor/sites/default/files/migration_files/policies/2014/Internet-Data-Exchange-IDX-Policy.pdf — NAR IDX Policy Statement 7.58 (PDF text extracted).
- https://www.nar.realtor/about-nar/policies/qualification-for-mls-participation-and-idx — broker-license requirement.
- https://data-wake.opendata.arcgis.com/api/feed/dcat-us/1.1.json — Wake Parcels license (CC BY 4.0), modified 2026-11-03.
- https://www.wake.gov/departments-government/tax-administration/data-files-statistics-and-reports/real-estate-property-data-files — Wake real-estate files.
- https://web.co.orange.nc.us/gisdownloads/ — Orange County GIS downloads.
- https://live-durhamnc.opendata.arcgis.com/ — Durham portal (content not rendered).
- https://www.fhfa.gov/data/hpi — FHFA HPI.
- https://www.huduser.gov/portal/datasets/fmr.html — HUD FMR (page did not render).

Hotels / commercial:
- https://developers.booking.com/demand/docs/getting-started/prerequisites — Demand API prerequisites.
- https://stayapi.com/blog/expedia-rapid-api and https://www.zentrumhub.com/blog/expedia-rapid-hotel-api-integration/ — Expedia Rapid eligibility (secondary).
- https://developer.hotelbeds.com/ — evaluation key, sandbox, certification.
- https://www.zentrumhub.com/blog/amadeus-hotel-api-guide/ and https://thunderbit.com/blog/best-flight-api-with-free-tiers — Amadeus Self-Service decommission reports (secondary; developers.amadeus.com returned no content).
- https://support.regrid.com/changelog/self-serve-api-plans and https://support.regrid.com/reference/plan-options — Regrid self-serve plan structure.
- https://apify.com/tristana/cre-loopnet-crexi-scraper.md — evidence that only scrapers exist for LoopNet/Crexi (loopnet.com/terms-of-use and crexi.com/terms returned HTTP 403).

Places:
- https://osmfoundation.org/wiki/Licence/Community_Guidelines/Produced_Work_-_Guideline — Produced Work guideline (endorsed 2014-06-06).
- https://osmfoundation.org/wiki/Licence/Community_Guidelines/Collective_Database_Guideline_Guideline — Collective Database guideline.
- https://docs.overturemaps.org/attribution/ — Overture per-theme/per-source licenses.
- https://docs.overturemaps.org/guides/places/ — Places theme licenses.
- https://docs.foursquare.com/data-products/docs/access-fsq-os-places — FSQ OS Places Apache-2.0, access paths (page updated 2026-03-31).
- https://developers.google.com/maps/documentation/places/web-service/policies — place-ID exemption, attribution, AI disclosure.
- https://developers.google.com/maps/billing-and-pricing/pricing — Places (New) SKUs and free thresholds.
- https://cloud.google.com/maps-platform/terms/maps-service-terms — 30-day caching rule (verified in-house 2026-06-28; page too long to re-quote this session).
- https://business.yelp.com/data/products/fusion/ — Yelp Places API pricing.
- https://terms.yelp.com/developers/api_terms/20250113_en_us/ — Yelp API terms (in-house verified).
- https://tripadvisor-content-api.readme.io/reference/overview — Content API deprecated; migrate to Terra.
- https://www.mapbox.com/pricing — Search Box, Geocoding (Temporary), Isochrone, Static Images tiers.
- https://www.here.com/get-started/pricing — HERE pricing landing page (limits not disclosed).
- https://github.com/openaddresses/openaddresses — per-source licensing; sources CC0; code BSD-3.

Demographics / economy:
- https://www.census.gov/data/developers/data-sets/acs-5year.html and https://api.census.gov/data/2022/acs/acs5.html — ACS 5-year API, block-group detailed tables.
- https://www.census.gov/data/developers/about/terms-of-service.html — Census API ToS (in-house verified).
- https://lehd.ces.census.gov/data/lodes/LODES8/LODESTechDoc8.3.pdf and https://lehd.ces.census.gov/announcements.html — LODES 8.3/8.4.
- https://www.bls.gov/developers/ — BLS Public Data API v1/v2.
- https://www.irs.gov/statistics/soi-tax-stats-migration-data — SOI migration data.

Traffic / transit:
- https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer — NCDOT AADT FeatureServer.
- https://connect.ncdot.gov/resources/State-Mapping/Pages/Traffic-Survey-GIS-Data.aspx — NCDOT Traffic Survey GIS products.
- https://www.fhwa.dot.gov/policyinformation/hpms/shapefiles.cfm — HPMS 2018 public release.
- https://www.replicahq.com/pricing and https://tetoncountywy.gov/DocumentCenter/View/25060/03213-Streetlight-data-for-Location-Based-Services-Data-Subscription — Replica/StreetLight pricing (secondary).
- https://gotriangle.org/developer-resources/ — Triangle GTFS/GTFS-RT URLs, CC BY 3.0.
- https://mobilitydatabase.org/feeds/gtfs/mdb-377 and https://mobilitydatabase.org/feeds/gtfs/mdb-376 — GoDurham, Chapel Hill Transit entries.
- https://www.transit.land/documentation — Transitland plans.

Quality of place:
- https://data-nces.opendata.arcgis.com/datasets/nces::public-school-locations-2024-25 — NCES EDGE 2024-25.
- https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers — NC SRC 2024-25 datasets.
- https://www.greatschools.org/api — NearbySchools API plans.
- https://developer.schooldigger.com/ — SchoolDigger plans.
- https://data.raleighnc.gov/datasets/raleigh-police-incidents-nibrs ; https://live-durhamnc.opendata.arcgis.com/datasets/DurhamNC::dpd-crime-table-only/about ; https://opendata-townofchapelhill.hub.arcgis.com/datasets/townofchapelhill::police-incident-reports-written — crime feeds.
- https://www.crimeometer.com/ — CrimeoMeter.
- https://hazards.fema.gov/femaportal/wps/portal/NFHLWMS — NFHL REST/WMS/WFS.
- https://envirodatagov.org/epa-removes-ejscreen-from-its-website/ ; https://screening-tools.com/epa-ejscreen — EJScreen removal and PEDP mirror.
- https://docs.airnowapi.org/ and https://docs.airnowapi.org/docs/AirNowAPIFactSheet.pdf — AirNow API.
- https://www.bts.gov/geospatial/national-transportation-noise-map — 2020 noise map.
- https://www.mrlc.gov/data — Annual NLCD Collection 1.2.
- https://esa-worldcover.org/en/data-access — WorldCover CC BY 4.0.
- https://catalog.data.gov/dataset/walkability-index — EPA Walkability Index.
- https://www.walkscore.com/professional/api-sign-up.php ; https://www.walkscore.com/professional/pricing.php ; https://www.walkscore.com/professional/branding-requirements.php — Walk Score API.
- https://help.bdc.fcc.gov/hc/en-us/articles/5375384069659-What-is-the-Location-Fabric ; https://www.fcc.gov/sites/default/files/bdc-data-downloads-output.pdf — FCC BDC.
- https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-download — PAD-US 4.1.
- https://www.ers.usda.gov/data-products/food-access-research-atlas/download-the-data — FARA 2019/2025.
- https://epqs.nationalmap.gov/v1/json?x=-78.9382&y=35.9940&units=Meters&wkid=4326 — live EPQS query (108.3 m).
