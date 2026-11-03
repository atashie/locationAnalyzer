# 02 — Landscape: Hotel/Trip Tools and Business Site-Selection Tools

**Date:** 2026-11-03 · **Status:** complete (first pass; see Open Questions) · **Stream:** 02 of the V2 rethink research program

## Scope and method

This document reviews two later use cases of the location finder so that the shared engine built for the home-search wedge does not paint us into a corner:

- **Part A — Hotel / trip stay finder.** A traveler or family wants a hotel (or a region to search for one) near a WeWork, a client's office, a stadium, etc., by bus/tram/metro/car/bike/walk time, with coffee shops and wine bars nearby. Reviewed: Google Maps "Ask Maps" and Google Hotels, Booking.com (consumer UI, Demand API, affiliate program), Expedia Group (Rapid API, Travel Creator Program, Romie), Kayak (KAYAK.ai, AI Mode, affiliate network), Priceline (Penny), Airbnb, TripAdvisor, trivago, HotelMap, Stay22, Rome2rio, Citymapper, Moovit, Transitland/Interline, TravelTime, Google Maps Platform Isochrones API, Amadeus Self-Service, LiteAPI (Nuitée).
- **Part B — Business site selection.** A small operator (tutoring, elder care, café) wants locations matching demographics (school-age children, 65+, traffic counts) and proximity, linked to commercial property to buy or lease. Reviewed: Esri ArcGIS Business Analyst, Placer.ai, SiteZeus, Buxton (now Audiense In-Person), Kalibrate (incl. eSite, Intalytics, TrafficMetrix), CARTO, Unacast/Gravy, SafeGraph/Advan/Dewey, Near→Azira, Localintel, Tango, SiteSeer, Geoblink, Regrid, Reonomy (Altus), CoStar/LoopNet, Crexi, Brevitas, Catylist (Moody's); free options: Census Business Builder, LEHD/LODES/OnTheMap, Census Data API, NCDOT AADT, PolicyMap, Social Explorer, Overture Maps, county open parcel data.

**Method.** ~50 web searches and ~75 primary-page fetches on 2026-11-03. Pricing pages, developer docs, and official newsroom posts were preferred; trade press (Skift, PhocusWire, 9to5Google, Engadget) was used for feature launches; review/aggregator sites were used only where a vendor hides prices, and are labelled as secondary. Anything not confirmed from a primary or two independent secondary sources is marked **(unverified)**. Several vendor pages returned HTTP 403 to automated fetches (trivago support, Crexi Intelligence, Social Explorer plans, TripAdvisor AI, Priceline Penny, LoopNet terms); those are noted inline. The web-search budget was exhausted before Airbnb API status, Replica, and Travelpayouts/Hotellook could be checked.

---

## Executive summary

1. **Nobody in the hotel market sells "hotels within N minutes by transit of X."** Google tried it (Hotel Finder isochrone layer, 2012) and dropped it; the 2026 Google "Ask Maps" hotel search accepts qualitative proximity ("within walking distance of a gym") but not a numeric travel-time budget. Booking.com, trivago, Airbnb and the Demand API all express proximity as **straight-line distance** to a city centre, landmark, or coordinate radius. This is the gap our engine fills.
2. **Transit isochrones remain a specialist capability.** Google Maps Platform's new Isochrones API (July 2026, preview, free during preview, $3.00/1k requests post-GA) covers driving/cycling/walking only. Interline/Transitland's isochrone endpoint is Valhalla street costing with no transit; transit reach there requires OTP point-to-point planning ($4/1k). Citymapper discontinued self-service APIs (23 June 2023); Moovit sells metered APIs with no isochrone product. TravelTime is the only commercial API with public-transport isochrones, on custom annual pricing (free tier is dev-only). Our own OTP/r5-style precompute is therefore not duplicating a commodity.
3. **Bookable hotel inventory is gated by partner contracts, not by code.** Booking.com Demand API requires Managed Affiliate status and a signed contract; Expedia Rapid requires partner approval and a site review; Amadeus Self-Service (the one open, pay-per-call hotel API) **shut down 17 July 2026** (SDK repo archived that day; official notice not fetched). Realistic routes for a tiny project: (a) affiliate deep links via Expedia Travel Creator Program (up to 4%), Kayak Affiliate Network, or Booking.com via CJ/Awin; (b) LiteAPI/Nuitée, which offers a free sandbox and production keys with a credit card and no stated minimums; (c) Stay22-style embedded maps that monetize via multiple OTAs.
4. **Google Hotels offers no affiliate or referral revenue.** "Free booking links" are for hotels and booking partners in Hotel Center; third parties earn nothing. Deep-linking to Google Hotels is useful as a zero-cost "see prices" handoff, not as monetization.
5. **AI trip assistants (Ask Maps, Romie, Penny, KAYAK.ai, Booking Smart Filter, Airbnb AI search) all translate natural language into existing filters.** None expose a geometry; none let the user see *the region* that satisfies constraints. The map-first "show me where" output is still differentiated.
6. **Site-selection incumbents are priced for chains, not sole proprietors.** Esri Business Analyst Web App Standard is $700/user/yr (AWS Marketplace) and the Advanced bundle with void analysis and drive-time trade areas is $5,200/user/yr; Placer.ai public contracts run $12,000–$34,000 in year one; Buxton/SiteZeus/Kalibrate/Tango/Geoblink are quote-only, typically reported at $20k+/yr. Esri's trade areas support drive, walk, trucking and rural driving — **not transit**.
7. **Foot traffic is the expensive layer; everything else has a free floor.** Mobile-panel foot traffic (Placer, Advan, Unacast, Azira, PassBy) is five-figure and up, legally fraught (FTC order against Gravy/Unacast, Near Intelligence bankruptcy and 2026 fraud charges), and academic-only via Dewey. Demographics (ACS at block group, free API), jobs (LODES at block level), traffic counts (NCDOT AADT stations and segments, 2015–2025, downloadable), POIs (Overture Places, CDLA-Permissive 2.0), and parcels (Wake County CC BY 4.0, daily) are all free.
8. **Commercial listings have no legitimate pull API.** CoStar/LoopNet: no sanctioned API, scraping prohibited. Crexi's only official API is a password-gated *push* Listing API for MLSs/brokerages; Crexi Intelligence is $299/mo (secondary) and portal-only. Catylist and Brevitas allow free search with paid lister tiers. The legal path is deep links into each marketplace's search with a bounding box or address, plus county parcel data for ownership and zoning.
9. **"Trade area" and "region" are the same engine.** Esri's ring / drive-time / walk-time trade areas, Placer's "True Trade Area" (CBGs visitors actually come from), and our isochrone-intersection polygons are all polygon-plus-enrichment. A region → block-group apportionment → ACS/LODES/AADT summary step gives us a credible "lite Business Analyst" at near-zero data cost.
10. **Monetization in both markets is commission or subscription, never per-query.** Hotels: 2–6% hotel commission (Expedia), up to 25% of Booking's commission via networks, Kayak click/booking/ad revenue. Site selection: annual seats, quote-based, with CPI/5–8% escalators in public contracts. For friends-and-family use, affiliate links cost nothing; for a later public product, the hotel side has a clearer first dollar than site selection.

---

## Part A — Hotel and trip tools

### A.1 Landscape table

| Tool | Proximity model | Transit travel time? | Multi-constraint | Link to inventory | API / affiliate | Access date |
|---|---|---|---|---|---|---|
| Google Maps "Ask Maps" (Gemini) | Qualitative ("walking distance from a gym"); routes/ETAs on request | Real-time transit info yes; transit *reach* no | NL multi-constraint (price, rating, vibe, nearby amenities) | Real prices/availability; booking in limited US test (Amadeus, direct suppliers) | None for third parties | 2026-11-03 |
| Google Hotels / Hotel Center | Map pan; sort by distance to centre | No (2012 Hotel Finder isochrone experiment discontinued) | Filters only | Free booking links for hotels/OTAs | No affiliate program; no commission to third parties | 2026-11-03 |
| Booking.com consumer | "Distance from city centre" filter; distance to landmark shown | No | Filters + Smart Filter (NL → filters) | Native | Affiliates via CJ/Awin since June 2025 | 2026-11-03 |
| Booking.com Demand API v3.2 | `city`/`landmark`/`airport`/`district`/`coordinates{lat,lon,radius km}`; `sort.by=distance` | No | Price, rating, facilities, meal plan, etc. | Full search/book | Managed Affiliate Partner + contract only | 2026-11-03 |
| Expedia Group Rapid API | Search by geography/coordinates (unverified detail) | No | Standard filters | Full book | Partner approval + site review; no published fee | 2026-11-03 |
| Expedia Travel Creator Program | n/a (deep links) | n/a | n/a | Deep links to hotel/flight/activity pages | Free to apply; up to 4% on eligible bookings; widgets; "APIs" listed | 2026-11-03 |
| Hotels.com (Expedia) | Same as Expedia | No | AI Compare, Property Expert Q&A | Native | Same program | 2026-11-03 |
| Kayak / KAYAK.ai / AI Mode | Map; NL chat (ChatGPT-powered AI Mode, Oct 2025) | No | NL trip planning | Meta-search → OTA/hotel | Affiliate Network: deeplinks, widgets, whitelabel, APIs incl. hotel search | 2026-11-03 |
| Priceline Penny | "Penny Maps" plots places mentioned; Neighborhood Edition matches "vibes" | No | NL, 10+ agents (Claude, Google, OpenAI) | Native booking in chat | None public | 2026-11-03 |
| Airbnb | Map POI layer; tap POI → straight-line distance from home; AI search | Transit *map view* (secondary); no travel-time filter | AI suggests filters from keywords | Native | No public API/affiliate (unverified; search budget exhausted) | 2026-11-03 |
| TripAdvisor AI Assistant / Trips | Map side-by-side; proximity-aware suggestions | No | NL itinerary | Live rates, deep links to OTAs | Content API (POIs/reviews) exists; page 403 on fetch | 2026-11-03 |
| trivago | Distance to city centre default; change to POI under "Location" | No | Price, rating, type | Meta-search | Support page 403; details secondary | 2026-11-03 |
| HotelMap (events) | Hotels around venue, distance-based | No | Dates, price | Contracted blocks + OTA links | B2B; Pro/Lite(free)/Magellan/Dynamo; commission reclaimed by organiser | 2026-11-03 |
| Stay22 ("Let Me Allez") | Embedded map around a venue; distance, price, availability | No | Dates, guests, budget | Booking.com, Agoda, Expedia, Hotels.com, Trip.com, Vrbo, GetYourGuide, Viator | Free iframe/script; revenue share | 2026-11-03 |
| Rome2rio | A→B multimodal routes | Point-to-point only | n/a | Hotels sidebar with Booking deep links (unverified) | Public docs 404; API not self-service | 2026-11-03 |
| Citymapper | Point-to-point | Yes, P2P | n/a | n/a | Self-service APIs discontinued 23 June 2023; enterprise only | 2026-11-03 |
| Moovit | Point-to-point, nearby stops | Yes, P2P | n/a | n/a | Six volume-metered APIs, no isochrone; contact sales | 2026-11-03 |
| Transitland / Interline | Isochrone (street modes), OTP transit plan | Transit P2P yes; transit isochrone **no** | n/a | n/a | Free 5k/1k; PAYG $2/1k street, $4/1k transit & isochrone, $8/1k matrix | 2026-11-03 |
| TravelTime | Isochrones, time filter, routes | **Yes** (public transport) | Multi-origin intersection/union | n/a | Free dev-only tier (120 HPM); production custom annual, no per-call | 2026-11-03 |
| Google Maps Platform Isochrones API | Isochrone | **No** (drive/cycle/walk only, secondary) | n/a | n/a | Preview (July 2026); $0 in preview; $3.00/1k post-GA; 10k/mo free | 2026-11-03 |
| Amadeus Self-Service Hotel APIs | Hotel list by geocode/radius | No | n/a | Hotel offers/booking | **Shut down 17 July 2026**; Enterprise only | 2026-11-03 |
| LiteAPI (Nuitée) | Hotel search (lat/lon detail unverified) | No | n/a | 2M+ hotels, search→prebook→book | Free sandbox, no card; production with card + payout; commission/markup | 2026-11-03 |

### A.2 Detailed notes

**Google Maps "Ask Maps" and Google Hotels.** Ask Maps (Gemini) launched 12 March 2026 (Forbes, iTechGuides — secondary) and added hotel and event discovery on 6–7 August 2026 (9to5Google, Skift, PhocusWire). The demonstration query is instructive: "find me a decently priced, top-rated hotel with an artsy vibe, within walking distance from a gym and restaurants." Proximity is qualitative; there is no slider for "20 minutes by metro from the convention centre." Skift confirms "hotel functionality stops at discovery and comparison; travelers cannot yet book," with a limited US test of agentic booking with Amadeus and direct suppliers. Ask Maps also surfaces live transit departures ("virtual departure board") and uses Gmail reservations via Personal Intelligence. The exact label "Ask about this area" on Google Hotels' map could not be confirmed **(unverified)**; everything confirmed is under the Ask Maps brand.
Google's 2012 Hotel Finder experiment drew isochrones ("hotels within a 30 minute public transit travelling time from the 2012 London Olympics Park," Google Maps Mania, Jan 2012). Jarrett Walker's 2015 critique (Human Transit) is still the best statement of the hard part: isochrones that ignore headway-driven wait time overstate transit reach — a 15-minute ride on a 30-minute-headway bus is really ~30 minutes. Our precompute must include wait time (OTP/r5 do by default when using a time window).
Google Hotels has **no affiliate program**: "Hotel partners pay no fee for free booking links, and Google doesn't collect any payment" (Hotel Center Help). Deep links to google.com/travel/hotels are permissible as a convenience handoff but yield no revenue.

**Booking.com.** Consumer UI: "Distance from city centre" filter and per-property distance to the searched landmark (HardReset how-to; Booking filter docs). Demand API v3.2 is the authoritative view of what Booking can do programmatically: location is a top-level choice among `city`, `landmark`, `airport`, `district`, `coordinates` (lat, lon, radius in km), `country`, `region`, or a list of up to 100 `accommodations`; `sort.by` may be `distance|price|review_score|stars` and distance sorting requires coordinates; the `filters` object has no distance or travel-time filter. Access: "Registered as a Booking.com Managed Affiliate Partner," Partner Centre "provided by your Booking.com Account Manager after signing the agreed contract." Separately, Booking.com terminated thousands of direct affiliates effective 20 June 2025 ("Bookinggeddon," Skift 30 May 2025); new small affiliates are routed to CJ (Europe) and Awin (elsewhere), earning "up to 25% of Booking.com's commission" with a 30-day cookie (track360 teardown, secondary). AI: Smart Filter (natural language → applied filters), Property Q&A and Review Summaries launched 30 Oct 2024 for US/UK/AU/NZ/SG mobile; AI Trip Planner since June 2023. None of these mention travel-time constraints.

**Expedia Group.** Rapid API: "To integrate with Rapid API, you need to be an Expedia partner"; six-step onboarding ending in a site review before production; no fee is published but third parties report selective vetting that "prioritises higher-volume partners" (Zentrumhub, secondary). The Travel Creator Program (Partnerize) is the open door: "Apply in minutes. It's free and fast," "up to 4% on every eligible booking," with link builder, widgets, a "Travel Shop," and "APIs" listed among tools (details behind login). Romie (May 2024) is the consumer AI; Hotels.com has AI Compare and Property Expert Q&A, and an Activity Planner in 2026 (secondary).

**Kayak.** KAYAK.ai pilot launched 29 April 2025; AI Mode (ChatGPT-powered natural-language search) launched 15 October 2025 (Skift). The Kayak Affiliate Network (affiliates.kayak.com) lists deeplinks, search widgets, whitelabel, and "APIs: programmatic access … including hotel search," paid "through clicks, bookings, and ad revenue"; application required. This is the most API-like affiliate route that does not require a GDS relationship, and it covers HotelsCombined, Momondo and Cheapflights inventory.

**Priceline Penny.** Penny is a multi-agent assistant (10+ agents; Anthropic Claude plus Google Cloud and OpenAI components, per Investing.com/AltexSoft). The "Neighborhood Edition" (PR Newswire, live 30 April 2025) matches a traveler's "vibe" to neighborhoods and plots any place mentioned via "Penny Maps"; the release does not mention distance or travel time as a matching criterion.

**Airbnb.** The May 2025 Summer Release redesigned maps so users can "filter for nearby landmarks, attractions, restaurants and more" and tap a POI to see "how far it is from the home" (Touchstay, TechRadar — secondary; distance is straight-line). AI search and keyword-to-filter suggestions followed; Engadget (30 Sept 2026) adds neighborhood summaries and a social Travel Map. Airbnb's API/affiliate program is widely reported closed; not re-verified here **(unverified)**.

**TripAdvisor, trivago.** TripAdvisor's AI Assistant is free without an account (aitravel.tools, Oct 2026, secondary) and builds day-by-day plans with a map; the page itself returned 403. trivago's distance filter defaults to city centre and can be re-pointed at an attraction under "Location" (HardReset, UpgradedPoints — secondary; support article 403).

**Event-hotel tools: HotelMap and Stay22.** HotelMap is B2B: organisers "automate attendee hotel booking and effortlessly reclaim the commission"; products Pro (managed), Lite (free), Magellan (unifies booking systems), Dynamo (publishers). Stay22 is the closest existing analogue to a "stay near X" widget: one script ("Let Me Allez") embeds a map centred on a venue with pins priced by night, filterable by budget, dates, and distance; inventory from eight partners (Booking.com, Agoda, Expedia, Hotels.com, Trip.com, Vrbo, GetYourGuide, Viator); publishers "earn revenue when they book." Both use distance, not travel time.

**Transit and routing APIs.** Citymapper: "Our self-service developer products – SDKs and APIs – have been discontinued since 23rd June 2023." Moovit: six volume-metered APIs (Multimodal Trip Plan, Nearby, Stops, Lines, Real-time, Service Alerts), no isochrone, contact sales. Transitland/Interline: Explorer free tier (5,000 REST + 1,000 routing/month, non-commercial), Hobbyist/Academic by application (50,000/100,000), Pay-As-You-Go with 10,000 free each then $2.00/1k street routes, $4.00/1k transit routes, isochrones and map-matching, $8.00/1k matrix; the isochrone endpoint supports auto, bicycle, pedestrian, truck, bus, taxi, motor_scooter, motorcycle, bikeshare, and states "multimodal is not available. The street graph has no transit." TravelTime: Basic plan "Free forever," all modes including public transport, 120 hits/min, "Development and testing only — not for commercial use"; Production is a custom annual subscription, "No usage fees, no per-call charges." Google Maps Platform Isochrones API: pre-GA Preview, "no charge for API usage during Preview," post-GA $3.00 per 1k (1–100k), stepping to $0.24 per 1k above 5M, 10,000 free requests/month; supports driving, cycling and walking only (TravelTime comparison blog, secondary — the Google reference page returned 404). Rome2rio's documentation root returned 404; third-party profiles describe a Search API and a hotels-nearby sidebar with Booking deep links **(unverified)**.

**Hotel content/booking APIs for small developers.** Amadeus Self-Service — the only open pay-per-call hotel API — is gone: "Self-Service went dark on July 17, 2026 … the portal is offline and Self-Service keys no longer work" (Thunderbit, 20 Aug 2026, citing PhocusWire 9 Feb 2026); the amadeus-python repository "was archived by the owner on Jul 17, 2026." The official developer portal returned no content to our fetches. LiteAPI (Nuitée) now fills the self-service niche: free sandbox key with no credit card; production key requires attaching a credit card and a payout method; "2M+ hotels"; revenue via commission/markup with "zero volume minimums" (API Evangelist profile, secondary). Its ToS and search-by-coordinates specifics were not fetched **(unverified)**.

---

## Part B — Business site-selection tools

### B.1 Landscape table

| Tool | Demographic / traffic / foot-traffic data (source) | UX | Trade areas | Pricing (visible) | API | Listings link | Access date |
|---|---|---|---|---|---|---|---|
| Esri ArcGIS Business Analyst | Esri Updated Demographics (2,000+ vars); POIs from Data Axle, SafeGraph, Foursquare; traffic counts from Kalibrate (>1M US points, Q1 2026); AGS crime; Tapestry retired | Web/Pro/mobile; infographics, reports, void analysis (Advanced), AI assistant | Rings, drive-time, walk-time, trucking, rural driving; **no transit** | Web App Standard $700/user/yr; Advanced Bundle $5,200/user/yr (AWS Marketplace); Standard included with Creator+ and ArcGIS for Personal Use | ArcGIS REST/GeoEnrichment (credits) | None native | 2026-11-03 |
| Placer.ai | Mobile panel "tens of millions" devices (25–30M per 2024 deck, secondary); 13M+ venues | Dashboard, reports, API, feeds; freemium "taste" | "True Trade Area" from visitor home CBGs/ZIPs | Not published; public contracts $12k–$34k yr1 (104-credit $12k–$20.9k; 260-credit $30.4k–$34k); escalators 5–12.5%/yr | Yes (REST, public docs) | Marketplace partners | 2026-11-03 |
| SiteZeus (Locate, Zeus.ai) | "Olympus Data Exchange": foot traffic, card spend, demographics (providers unnamed) | Heat maps, forecasts, territories, chat ("Ask Zeus"); MCP for Claude/ChatGPT/Copilot/Gemini | Territories; method unstated | Quote-only (~$20k+/yr, secondary) | MCP integration | "Integrated real-estate listings" in May 2026 Atlas release (secondary, source unnamed) | 2026-11-03 |
| Buxton → Audiense In-Person | 44B foot-traffic points, 50+ sources, household-level | SCOUT: score sites, trade areas, market optimisation; 36 healthcare models | Trade areas; method unstated | Not shown; from $12k/yr, typically $20k+ (secondary) | Not stated | None | 2026-11-03 |
| Kalibrate Location Intelligence (TAS + eSite + Intalytics) | Demographics, mobility, competition; TrafficMetrix ~2.4M count points (Environics manual, secondary) | Forecasting, cannibalisation, trade areas | Yes | Quote-only | TrafficMetrix resold via Esri, Environics, Precisely | None | 2026-11-03 |
| CARTO Site Selection | Data Observatory (12,000+ datasets: demographics, POI, mobility, traffic, spend) | Cloud-warehouse native (BigQuery/Snowflake/etc.), workflows, AI agent | Drive/walk-time isolines "for every site at once" | PAYG (12-mo contract) / Enterprise / Strategic / Custom; metered units; no prices shown | Yes (limited on PAYG/Enterprise) | None | 2026-11-03 |
| Unacast (+Gravy, 2023) | Mobility panel "+1Bn monthly devices" (secondary) | Insights platform, datasets, APIs | Custom | From $40k/yr mobility API (secondary); page shows no prices; FTC order Jan 2025 | Yes | None | 2026-11-03 |
| SafeGraph | Places, Geometry, Address, Spend; **no foot traffic since 2023** | Data delivery, monthly | n/a | Custom annual fee; ~$150k/yr places (secondary) | Bulk/sample | None | 2026-11-03 |
| Advan via Dewey | 45M US devices (secondary); Patterns successor | Files/dashboards | n/a | Academic institutional only; non-commercial | Files | None | 2026-11-03 |
| Near → Azira | 13T mobility signals, 35.6B transactions, 43M POIs | Azira One (NL analytics), Insights, Audience, Campaigns | Custom | Not shown; Near Ch.11 Dec 2023, assets to Azira Mar 2024, exec fraud charges Jan 2026 (secondary) | Cloud feed | None | 2026-11-03 |
| Localintel | Public + licensed datasets for EDOs | Reports, Dashboards, Studio; 250+ gov/non-profit clients | n/a | Standard/Premium/Enterprise; quote | Embeds | Some EDO property tools (not verified here) | 2026-11-03 |
| Tango Predictive Analytics | Mobile/social, economic, competitive, psychographic; Azira foot traffic + INRIX vehicle (secondary) | SLM/IWMS suite; ML forecasts | Thematic/hotspot maps | Quote-only | Not stated | Lease data in-suite | 2026-11-03 |
| SiteSeer | AGS demographics (Explorer plan); mobile foot traffic; retail benchmarks | Void analysis, retail matching, scorecards | Yes | Void Analysis $299.99 (one-off, page) / $199.99 (secondary); from $1,495/yr (Capterra, secondary) | Not stated | None | 2026-11-03 |
| Geoblink | Foot traffic, competitors, demographics (Europe-centric) | Predictive models | Yes | Quote-only | Not stated | None | 2026-11-03 |
| Regrid | Parcels, ownership, zoning, footprints (all US counties) | Pro app; Parcel/Tiles API | n/a | Self-serve monthly from 2,000 records; $0.10/$0.15 overage, 200k tiles (secondary); Pro app $10/mo (secondary); enterprise $25k–$65k/yr (secondary); free 30-day sandbox | Yes | Parcels, not listings | 2026-11-03 |
| Reonomy (Altus) | 53M+ CRE properties, 68M+ transactions, 30M+ owner contacts (secondary) | Web app; 1,000 exports/mo | n/a | Monthly/annual self-serve (~$500/mo or $400/mo annual, secondary; page hides price); API/bulk quoted | Yes (quoted) | Ownership, not listings | 2026-11-03 |
| CoStar / LoopNet | Proprietary comps/listings | Free search; tiered lister plans | n/a | Lister plans Basic→Diamond (prices not disclosed) | **No sanctioned API; no scraping** (ToS fetch 403; secondary) | Deep links only | 2026-11-03 |
| Crexi | Listings; Intelligence: 153M+ records, 46M+ comps (secondary) | Free search; Intelligence $299/mo (secondary; page 403) | n/a | $299/mo Intelligence (secondary) | Official API = password-gated **push** Listing API (RESO/RETS/XML) for MLSs/brokerages | Deep links only | 2026-11-03 |
| Brevitas | Listings | Free basic search (secondary); Professional $29/mo for listers (secondary) | n/a | Freemium | None | Deep links | 2026-11-03 |
| Catylist (Moody's) | Listings | Free basic search; Full Access from $99/mo (SharpLaunch, Mar 2026, secondary) | n/a | $99/mo listers | None | Deep links | 2026-11-03 |
| Census Business Builder v5.12 | ACS, CBP, Economic Census, consumer spending (source unverified) | Map, dashboard, downloadable report | Counties/places/tracts (SBE) | Free | No (Census Data API separately) | None | 2026-11-03 |
| LEHD LODES v8 / OnTheMap | Jobs by 2020 census block: OD, RAC, WAC (age, earnings, industry) | Free map app; CSV download | Any block aggregation | Free | Download; LED Extraction Tool | None | 2026-11-03 |
| Census Data API (ACS 5-yr) | B01001 sex-by-age etc. at block group | API | Any | Free key; 50 variables/query | Yes | None | 2026-11-03 |
| NCDOT AADT | 44,000+ stations since 2002; AADT Stations + Traffic Segments 2015–2025 (2025 as file geodatabase) | Interactive Traffic Volume Map; downloads | n/a | Free; licence not stated ("Mapping Disclaimer") | ArcGIS Hub feature services | None | 2026-11-03 |
| PolicyMap | 170+ sources | Web maps, reports | n/a | Custom; Public Edition exists (secondary) | Data licensing via API/flat file/Snowflake | None | 2026-11-03 |
| Social Explorer | Census/ACS and more | Web maps, reports | n/a | Professional $135/mo annual, $150 quarterly, $195 monthly; 7-day trial (help centre via snippet; page 403) | No | None | 2026-11-03 |
| Overture Maps Places | 61M+ POIs (secondary); Meta/Microsoft/Foursquare/OSM | Explorer, CLI, GeoParquet | n/a | Free; CDLA-Permissive 2.0 (+Apache 2.0 Foursquare); other themes ODbL/CC BY | Download | None | 2026-11-03 |
| Wake County parcels (NC) | Boundaries, address, revenue attributes | Open data portal | n/a | Free, CC BY 4.0, updated daily | GeoServices REST, GeoJSON, CSV, Shapefile | Ownership/zoning | 2026-11-03 |

### B.2 Detailed notes

**Esri ArcGIS Business Analyst.** The AWS Marketplace listing is the clearest public price: Web App Standard $700/year per named user ("study areas based on distance or drive-time," 100+ templates) and Advanced Bundle $5,200/year ("drive time, territory design, consumer profiling, target marketing, void analysis, points of interest search, and suitability analysis"). Esri's own buy page confirms Standard is included with Creator/Professional user types and with ArcGIS for Personal Use, while Advanced, Pro (10,000 credits), and Enterprise are separate purchases. Data page for the US: demographics "Esri 2024/2025," business POIs from Data Axle, SafeGraph and Foursquare, "Traffic Counts," and a note that "Esri Tapestry Segmentation dataset has been retired." The Traffic Counts doc: sourced from Kalibrate, "more than 1 million points across the United States," with average daily traffic, count type, cross-street direction/distance, refreshed June 2026 with Q1 2026 vintage. Trade-area travel modes in Business Analyst (ArcGIS Pro doc): "driving time or distance, trucking time or distance, walking time or distance, or rural driving time or distance" — public transit is absent.

**Placer.ai.** The pricing page shows no numbers ("customized subscription packages"), a freemium tier Placer itself describes as "a taste," and dashboard/API/feed delivery. MarketIntelligenceTools (6 Oct 2026) compiled nine municipal order forms: $12,000–$34,000 in year one, two credit bands (104 credits/yr at $12,000–$20,900; 260 credits/yr at $30,400–$34,000), renewal escalators "greater of CPI or 5%" (2023–24) moving to "up to 8% or CPI" (2025–26), and multi-year steps of 5.0–12.5%. GrowthFactor's vendor comparison (updated 28 Oct 2026) widens the observed range to $12K–$126K and cites a 2024 deck claiming a 25–30M device panel. The "True Trade Area" concept (origin CBGs/ZIPs of actual visitors) is the industry's answer to rings; it requires panel data we will not have, but its *output shape* (a weighted set of block groups) is something our engine can emulate with LODES home-work flows for daytime population.

**SiteZeus, Buxton/Audiense, Kalibrate, Tango, Geoblink, eSite.** All quote-only. SiteZeus names no data partners publicly (the "Olympus Data Exchange" is a brand) but does advertise an MCP server so Claude/ChatGPT/Copilot/Gemini can query it, and a May 2026 "Atlas" release with "integrated real-estate listings" (MyTraffic/GrowthFactor, secondary; the listing source is not named). Buxton's pricing URL now redirects to Audiense In-Person, which advertises "44 billion foot traffic data points" and 50+ sources with household-level insight; pricing not shown. Kalibrate consolidated TAS, eSite and Intalytics into one platform and is the upstream for traffic counts at Esri, Environics and Precisely (TrafficMetrix "nearly 2.4 million traffic collection points" per the Environics manual). Tango's product page names no vendors, though trade press cites Azira foot traffic and INRIX vehicle data.

**CARTO.** Pricing is Pay-As-You-Go (monthly billing on a 12-month contract) or committed Enterprise/Strategic/Custom tiers, metered in weighted units across workflow runs, map loads and API calls; no dollar figures shown. The Site Selection app computes "drive- and walk-time trade areas for every site at once on pre-built road networks, inside your data warehouse," with twin-area matching, revenue prediction, cannibalisation, and an AI agent. The older "$100/user/month Starter" figure circulating on review sites is not on the current page **(unverified)**.

**Foot-traffic vendors.** SafeGraph sold Patterns to Advan in Nov 2022 and now sells Places/Geometry/Address/Spend on a custom annual fee. Advan is distributed to academia via Dewey ("academic-friendly pricing," institutional, non-commercial). Unacast merged with Gravy Analytics in Nov 2023; the FTC finalised an order against Gravy in Jan 2025 and Gravy disclosed a cloud-storage breach the same month; Unacast's mobility API is reported "from $40,000 a year." Near Intelligence filed Chapter 11 in Dec 2023; assets became Azira in March 2024; in Jan 2026 prosecutors and the SEC charged Near's former CEO and CFO with fraud (Yahoo/Gizmodo/Techdirt — secondary). The lesson for a small product: foot traffic is expensive, reputationally risky, and unavailable at hobby scale; the cheap, defensible proxies are LODES jobs (daytime population), AADT (vehicles passing), and POI density (Overture).

**SiteSeer.** The only incumbent with a published unit price: a one-off Void Analysis report at $299.99 (site page; $199.99 standard version per Capterra), and an "Explorer" plan "powered by Applied Geographic Solutions data" aimed at property owners; Capterra lists a $1,495/year starting price. SiteSeer is the closest existing "tiny-budget" site-selection product and its void-analysis framing ("which retailers are missing from this trade area") is a useful feature idea we can approximate with Overture POI category counts.

**Parcels and ownership: Regrid, Reonomy.** Regrid's support page confirms self-serve monthly plans "starting with 2,000 Parcel records per month plus additional per record pricing," a free 30-day sandbox, and enterprise licences above 10,000 records/month; ScoutData (secondary) reports $0.10/$0.15 per-record overage, 200,000 tiles included, a $10/month Pro app, and $25k–$65k/year nationwide bulk. Reonomy's pricing page hides dollar amounts (CRE Daily reports $500/month or $400/month annual) and quotes API/bulk separately. For the Research Triangle neither is needed: Wake County publishes parcels under CC BY 4.0, updated "at the end of every business day," via GeoServices REST, GeoJSON, CSV and Shapefile; Orange County runs an open GIS portal; Durham County was not verified **(unverified)**.

**Commercial listings: CoStar/LoopNet, Crexi, Brevitas, Catylist.** LoopNet and CoStar: free consumer search, tiered paid lister plans (Basic→Diamond, undisclosed), and — per multiple secondary sources — no sanctioned API and an explicit prohibition on scraping; our fetch of loopnet.com/terms returned 403, so the clause is not quoted here **(unverified wording)**. Apify hosts many LoopNet/Crexi scrapers; using them would violate ToS and is out of scope for a product we may later monetise. Crexi's only official API is the "Crexi Exchange API" at api-docs.crexi.com, password-gated, described by API Evangelist as a one-way Listing API (RESO/RETS/XML) for MLSs and large brokerages onboarded via integrations@crexi.com; Crexi Intelligence ($299/month, secondary) is portal-only. Catylist (Moody's) and Brevitas allow free search with paid lister tiers ($99/month and $29/month respectively, secondary). Net: there is no legitimate pull API for commercial listings at any price we could pay; the compliant pattern is a deep link that opens the marketplace's own search pre-filtered to a bounding box/address, plus parcel data to show "who owns the buildings in this region" and zoning.

**Free government data.** Census Business Builder (v5.12) offers a Small Business Edition (pick a business type and place; see customers, consumer spending, competitors on a map; download a report) and a Regional Analyst Edition (multi-county regions); data from ACS, County Business Patterns and the Economic Census; no API of its own. LEHD LODES version 8 (2020 census blocks) ships Origin-Destination, Residence Area Characteristics and Workplace Area Characteristics files; WAC includes jobs by worker age (≤29, 30–54, 55+), earnings band, and industry sector — i.e., daytime population by block, the missing piece for "cars passing / people working near here." The Census Data API is free with a key, 50 variables per call, ACS 5-year at block group, and table B01001 (sex by age) gives children 5–17 and adults 65+ directly. NCDOT publishes an Interactive Traffic Volume Map, AADT Stations (44,000+ since 2002) and Traffic Segments as GIS downloads for 2015–2025 (2025 as a file geodatabase), published "by August 31 for the previous year," and exposes them as ArcGIS Hub feature services; the licence is not stated and should be confirmed against NCDOT's Mapping Disclaimer **(unverified)**. Overture Places are CDLA-Permissive 2.0 (Foursquare subset Apache 2.0), buildings/transportation/divisions ODbL, addresses mixed; commercial use is permitted with attribution. PolicyMap is quote-based (API via data licensing); Social Explorer's Professional plan is $135/$150/$195 per month by billing period with a 7-day trial — both are visualisation layers over data we can get free.

---

## Cross-cutting lessons

**How tools represent travel time and multiple constraints.** In the hotel market the unit of proximity is straight-line distance to a single anchor (city centre, landmark, airport, or the map viewport). Travel time appears only as a *post hoc* route from a chosen hotel. AI assistants accept multiple soft constraints in one sentence but resolve them into the same single-anchor filters; they never return a region. In site selection the unit is the *trade area*: ring, drive-time, walk-time (Esri, CARTO), or visitor-origin polygon (Placer). Transit is absent everywhere except TravelTime's API and our own OTP-style precompute. Multi-constraint combination is done by scoring (SiteZeus, Tango, CARTO ML) rather than by geometric intersection; Esri's "suitability analysis" is the closest to weighted layers. No tool in either market shows the *intersection of several travel-time constraints* as a first-class object. That is our differentiator and the thing the engine must do well.

**How they monetise.** Hotels: commission on bookings — Expedia Travel Creator up to 4%, Booking "up to 25% of Booking's commission" through CJ/Awin, Kayak clicks+bookings+ads, Stay22 revenue share across eight OTAs, LiteAPI commission/markup, HotelMap commission reclaimed for organisers. No per-query fees anywhere; Google gives away free booking links to drive its own ad auction. Site selection: annual per-seat subscriptions (Esri $700/$5,200; Social Explorer $1,620/yr; SiteSeer from $1,495/yr) scaling to five- and six-figure quote-only contracts with CPI/5–8% escalators (Placer). Report-level pricing exists only at SiteSeer ($299.99). A friends-and-family product earns nothing; a later public product can attach affiliate links to hotel results at zero cost and could sell one-off "region reports" in the SiteSeer price band.

**The free-data floor for site selection.** Entirely free, licence-clean, and sufficient for a credible first version: ACS 5-year at block group (children, seniors, income, households), LODES WAC/RAC/OD at block (jobs, daytime population, commute flows), state DOT AADT stations and segments (vehicles/day on adjacent roads), Overture Places (competitors, complements, void analysis by category), county parcels (zoning, land use, assessed value, owner — Wake daily, CC BY 4.0), TIGER/OSM roads and GTFS for travel time. What this floor cannot do: panel-based foot traffic, true trade areas from device origins, card-spend, or chain-level sales benchmarks. For a tutoring or elder-care operator those are not the deciding inputs; children 5–17 and 65+ within a 10-minute drive, plus AADT on the frontage road, are.

**How to link to inventory legally.** Hotels: (1) deep links through Expedia Travel Creator, Kayak Affiliate Network, or Booking.com via CJ/Awin, each with its own link builder and tracking; (2) LiteAPI for actual search/book in our UI (sandbox free, production needs a card; confirm ToS); (3) Google Hotels deep links as a non-monetised price check. Do not use SerpApi/Apify-style Google Hotels, Booking, LoopNet or Crexi scrapers in anything we might publish. Commercial property: deep links into LoopNet/Crexi/Catylist/Brevitas searches, parcel data from counties/Regrid, ownership from Reonomy only if a paying user needs it. Hotel inventory partners (Booking Demand, Expedia Rapid) become reachable only once we have booking volume to show.

---

## Implications for our build

**The shared engine must support, from the start:**

1. **Travel-time surfaces per mode including transit with wait time** — gridded, precomputed for the Triangle (drive, bike, walk, GoTriangle/GoRaleigh/GoDurham transit via GTFS), on-demand elsewhere. Transit is the one capability no competitor sells to consumers; without wait-time-aware isochrones we repeat the 2012 Hotel Finder mistake Jarrett Walker identified.
2. **Constraint algebra over polygons**, not just filters: intersection (all of), union (any of), and k-of-n, with per-constraint mode and minutes. Home search needs two commutes; hotels need "venue by metro AND coffee within walk"; site selection needs "10-minute drive-time trade area" as a *single* polygon that is then enriched.
3. **Polygon enrichment by areal apportionment** of block groups/blocks: ACS (B01001 and friends), LODES WAC/RAC, AADT stations within or along boundary roads, Overture POI counts by category. This is the "lite Business Analyst" step and is the same code path that will later summarise a home-search region ("3 groceries, 2 parks, 1 elementary school inside").
4. **Anchor types:** a specific place (geocoded), a POI category (Overture/OSM), *and* a transient event location (stadium, convention centre, a WeWork) — the hotel case shows the anchor is often not a home or workplace.
5. **Inventory adapters as deep-link generators first, APIs second.** A `ListingLink` abstraction that emits a marketplace URL pre-filtered to a bbox/address (Zillow/Redfin for homes; Expedia/Kayak/Booking-via-network for hotels; LoopNet/Crexi/Catylist for CRE) keeps us legal and lets LiteAPI or a future Rapid/Demand integration slot in later without changing the region engine.
6. **Natural-language → structured constraints with a visible, editable intermediate.** Every AI competitor hides the resolved filters; we should show the parsed constraints (mode, minutes, anchor) so users can correct them, which is also what makes the region explainable.

**Defer:**

- Any booking flow inside our UI (LiteAPI integration) until there is a user who wants it; deep links suffice for friends and family.
- Foot-traffic, card-spend, and chain benchmark data; price and legal risk are both disqualifying at our scale.
- Reonomy/Regrid paid tiers; county open data covers the Triangle.
- Void analysis as a product feature; keep it as a cheap derived view (Overture category counts in the polygon) if site selection gets traction.
- Non-US transit precompute; Transitland's archive and TravelTime's API are fallbacks if a user needs a city we have not built.

---

## Open questions

1. **LiteAPI terms:** does its ToS allow display of rates in a non-booking "region finder" context, and what is the actual commission split? (Docs fetched do not say.)
2. **Kayak Affiliate "APIs including hotel search":** what exactly is exposed after approval — a hotel search endpoint with lat/lon, or only deep-link templates? Approval criteria for a hobby site are unknown.
3. **Amadeus Self-Service shutdown:** corroborated by the SDK repo archive date and trade press, but no official Amadeus notice was retrieved. Confirm before writing it into the data-sources doc (stream 04).
4. **Google Maps Platform Isochrones API modes:** the "no transit" statement comes from a competitor's blog; verify on Google's reference page when it is reachable, and check whether Preview terms permit our use.
5. **NCDOT AADT licence:** the GIS page defers to a "Mapping Disclaimer"; confirm redistribution terms and whether the ArcGIS Hub feature service may be queried live from our backend.
6. **Airbnb and TripAdvisor developer access** (budget exhausted before verification) — Airbnb API presumed closed; TripAdvisor Content API ToS verdict exists in `localUpdates/docs/research-findings.md` and should be cross-referenced.
7. **Durham County parcels** licence and refresh cadence (Wake and Orange confirmed open).
8. **Booking.com via CJ/Awin:** does the network programme permit *API-like* use (search box widgets with coordinates) or only static deep links? Also whether a new US publisher is accepted at all post-2025.
9. **SiteZeus "integrated real-estate listings":** which marketplace feeds them, and under what licence? If a listings partner exists that licences to small platforms, it changes the CRE picture.
10. **Replica / StreetLight on-demand AADT** for roads NCDOT does not count (budget exhausted; StreetLight's pricing page shows no numbers).

---

## Sources

All accessed 2026-11-03.

**Part A**
- Skift, "Google Brings Agentic AI to Ask Maps Hotel Search" (7 Aug 2026) — https://skift.com/2026/08/07/google-brings-agentic-ai-to-ask-maps-hotel-search/
- 9to5Google, "Ask Maps … Personal Intelligence, real-time transit, global launch" (6 Aug 2026) — https://9to5google.com/2026/08/06/google-ask-maps-global/
- Forbes, "Google Maps Adds Gemini AI With Conversational Search…" (16 Mar 2026) — https://www.forbes.com/sites/anishasircar/2026/03/16/google-maps-adds-gemini-ai-with-conversational-search-and-3d-immersive-navigation/
- Google Maps Mania, "Google Hotel Finder Isochrones Experiment" (Jan 2012) — https://googlemapsmania.blogspot.com/2012/01/google-hotel-finder-isochrones.html
- Human Transit, "How do I find a hotel near good transit? Part 2" (Mar 2015) — https://humantransit.org/2015/03/how-do-i-find-a-hotel-near-good-transit-part-2.html
- Google Hotel Center Help, "About hotel free booking links" — https://support.google.com/hotelprices/answer/10472393?hl=en
- Booking.com Demand API, "Filtering and sorting accommodation results v3.2" — https://developers.booking.com/demand/docs/accommodations/v3.2/filter-sorting
- Booking.com Demand API, "Search for accommodation" — https://developers.booking.com/demand/docs/accommodations/search-for-available-properties
- Booking.com Demand API, "Prerequisites" — https://developers.booking.com/demand/docs/getting-started/prerequisites
- Booking.com Newsroom, "Booking.com Enhances Travel Planning with New AI-Powered Features" (30 Oct 2024) — https://news.booking.com/bookingcom-enhances-travel-planning-with-new-ai-powered-features--for-easier-smarter-decisions/
- Skift, "Why Booking.com Cut 'Thousands' of Affiliate Partners" (30 May 2025) — https://skift.com/2025/05/30/why-booking-com-cut-thousands-of-affiliate-partners-and-what-comes-next/
- track360, "Booking.com Affiliate Program: Operator Teardown 2026" (secondary) — https://track360.io/blog/booking-com-affiliate-partner-program-operator-teardown-2026
- HardReset, "How to Sort By Distance From City Centre on Booking.com" (secondary) — https://www.hardreset.info/devices/apps/apps-bookingcom/sort-by-distance-city-centre/
- Expedia Group Developer Hub, "Rapid — Get started" — https://developers.expediagroup.com/docs/products/rapid/setup/getting-started
- Expedia Group Developer Hub, "Lodging API launch requirements" — https://developers.expediagroup.com/rapid/setup/launch-requirements/lodging-launch-reqs
- Expedia Group, "Travel Creator Program" — https://partner.expediagroup.com/en-us/solutions/explore-our-affiliate-program
- Zentrumhub, "Expedia Rapid Hotel API Integration" (secondary) — https://www.zentrumhub.com/blog/expedia-rapid-hotel-api-integration/
- Expedia Newsroom, "Spring product release 2024" — https://www.expedia.com/newsroom/spring-product-release-2024
- Skift, "Kayak Introduces AI Mode" (15 Oct 2025) — https://skift.com/2025/10/15/kayak-ai-mode-natural-language-search/
- Nasdaq/PR, "KAYAK Launches KAYAK.ai" (29 Apr 2025) — https://www.nasdaq.com/press-release/kayak-launches-kayakai-pilot-ai-first-features-tech-savvy-travelers-2025-04-29
- KAYAK Affiliate Network — https://affiliates.kayak.com/
- PR Newswire, "Priceline's New AI-Powered Neighborhood Edition…" (Apr 2025) — https://www.prnewswire.com/news-releases/pricelines-new-ai-powered-neighborhood-edition-is-first-to-match-travelers-preferences-and-vibes-with-unique-destination-recommendations-302441857.html
- Investing.com, "Priceline upgrades AI assistant Penny with Anthropic's Claude" (secondary) — https://www.investing.com/news/company-news/priceline-upgrades-ai-assistant-penny-with-anthropics-claude-93CH-4723858
- Engadget, "Airbnb is adding a personalized map and other discovery tools" (30 Sep 2026) — https://www.engadget.com/2272794/airbnb-is-adding-a-personalized-map-and-other-discovery-tools/
- TechRadar, "Airbnb's latest update brings AI search…" (secondary) — https://www.techradar.com/computing/websites-apps/airbnb-adds-ai-search-and-more-services-to-help-you-plan-your-next-getaway
- Touchstay, "Airbnb's 2025 summer release" (secondary) — https://touchstay.com/blog/airbnb-2025-summer-release
- Tripadvisor AI Assistant (403 on fetch) — https://www.tripadvisor.com/AIAssistant
- UpgradedPoints, "Trivago – How to Find and Compare Cheap Hotel Prices" (secondary) — https://upgradedpoints.com/travel/trivago-hotels/
- HotelMap — https://www.hotelmap.com/
- Stay22, "Interactive map widgets for event travel" — https://www.stay22.com/map
- Skift Meetings, "Stay22 review" (secondary) — https://meetings.skift.com/reviews/stay22-review/
- Citymapper Enterprise (developer products discontinued 23 Jun 2023) — https://citymapper.com/enterprise
- Moovit, "Public Transit APIs" — https://moovit.com/maas-solutions/transit-apis/
- Transitland, "Plans & Pricing" — https://www.transit.land/plans-pricing/
- Transitland, "Routing Platform — Isochrone" — https://www.transit.land/documentation/routing-platform/isochrone
- TravelTime, "Pricing" — https://traveltime.com/pricing
- Google Maps Platform, "Isochrones API Usage and Billing" — https://developers.google.com/maps/documentation/isochrones/usage-and-billing
- Google Maps Platform, "Isochrones API overview" — https://developers.google.com/maps/documentation/isochrones/overview
- TravelTime, "Google Isochrones API vs TravelTime Isochrone API" (secondary; no-transit claim) — https://traveltime.com/blog/google-isochrones-api-vs-traveltime
- Thunderbit, "10 Best Flight APIs in 2026: Free Tiers and Real Pricing" (updated 20 Aug 2026; Amadeus shutdown claim) — https://thunderbit.com/blog/best-flight-api-with-free-tiers
- GitHub, amadeus4dev/amadeus-python (archived 17 Jul 2026) — https://github.com/amadeus4dev/amadeus-python
- Zentrumhub, "Amadeus Hotel API: Complete Guide for OTAs" (17 Apr 2026, secondary) — https://www.zentrumhub.com/blog/amadeus-hotel-api-guide/
- LiteAPI docs, "Getting a sandbox key" — https://docs.liteapi.travel/docs/getting-a-sandbox-key
- LiteAPI docs, "Overview" — https://docs.liteapi.travel/reference/overview
- API Evangelist, Nuitée/LiteAPI profile (secondary) — https://github.com/api-evangelist/nuitee
- API Evangelist, Rome2rio profile (secondary) — https://github.com/api-evangelist/rome2rio

**Part B**
- AWS Marketplace, "ArcGIS Business Analyst Web App" (Standard $700/yr; Advanced $5,200/yr) — https://aws.amazon.com/marketplace/pp/prodview-kkpfgbxfp6qde
- Esri, "ArcGIS Business Analyst Pricing" — https://www.esri.com/en-us/arcgis/products/arcgis-business-analyst/buy
- Esri, "Data in Business Analyst" — https://doc.arcgis.com/en/business-analyst/web/data.htm
- Esri Demographics, "Traffic Counts" — https://doc.arcgis.com/en/esri-demographics/latest/esri-demographics/traffic-counts.htm
- ArcGIS Pro, "Generate standard geography, distance, or time-based trade areas" — https://pro.arcgis.com/en/pro-app/3.4/help/analysis/business-analyst/generate-standard-geography-distance-or-time-based-trade-areas.htm
- Placer.ai, "Pricing Plans" — https://www.placer.ai/pricing
- MarketIntelligenceTools, "Placer.ai Pricing 2026: $12,000 to $34,000 a Year in 9 Public Contracts" (6 Oct 2026, secondary) — https://marketintelligencetools.com/reports/placer-ai-pricing/
- GrowthFactor, "Foot Traffic Data Providers Compared (2026)" (updated 28 Oct 2026, secondary) — https://www.growthfactor.ai/resources/blog/foot-traffic-provider-comparison
- SiteZeus — https://sitezeus.com/ and https://sitezeus.com/locate
- MyTraffic, "Top 5 AI site selection tools" (SiteZeus Atlas claim, secondary) — https://www.mytraffic.io/en/post/5-ai-site-selection-tools
- Audiense In-Person (formerly Buxton; redirect from buxtonco.com/pricing) — https://www.audiense.com/products/audiense-in-person/
- GrowthFactor, "7 Buxton Alternatives" (secondary pricing) — https://www.growthfactor.ai/resources/blog/buxton-alternatives
- Kalibrate, "Enhancing our location intelligence capabilities" — https://kalibrate.com/insights/press-release/location-intelligence/enhancing-our-location-intelligence-capabilities/
- Environics Analytics, "Published Counts TrafficMetrix manual" (secondary) — https://environicsanalytics.com/docs/default-source/us---data-product-support-documents/kalibrate-trafficmetrixmanual-ea.pdf
- CARTO, "Pricing" — https://carto.com/pricing
- CARTO, "Site Selection Software with Location Intelligence" — https://carto.com/solutions/site-selection/
- Unacast, "Pricing" — https://www.unacast.com/pricing
- SafeGraph, "Pricing" — https://www.safegraph.com/pricing
- Dewey — https://www.deweydata.io/ ; Advan partner page — https://www.deweydata.io/data-partners/advan
- Azira — https://azira.com/
- Gizmodo, "A Data Broker Reportedly Tracked Visitors to Jeffrey Epstein's Island" (Near context, secondary) — https://gizmodo.com/a-data-broker-reportedly-tracked-visitors-to-jeffrey-ep-1851372504
- Localintel — https://localintel.com/ and https://www.localintel.com/faq
- Tango Analytics, "Tango Predictive Analytics" — https://tangoanalytics.com/products/tango-predictive-analytics/
- SiteSeer, "SiteSeer Professional" — https://www.siteseer.com/siteseer-professional/ ; "Subscribe for Unlimited Void Analysis Reports" — https://www.siteseer.com/subscribe-for-unlimited-void-analysis-reports/
- Capterra, "SiteSeer Technologies" (secondary pricing) — https://www.capterra.com/p/164129/SiteSeer-Technologies/
- Regrid, "Plan Options" — https://support.regrid.com/reference/plan-options ; "Parcel API" — https://regrid.com/parcel-api
- ScoutData, "Regrid Pricing 2026" (secondary) — https://scoutdata.com/guides/regrid-pricing
- Reonomy, "Pricing" — https://www.reonomy.com/pricing/
- CRE Daily, "Reonomy 2026 Review" (secondary pricing) — https://www.credaily.com/reviews/reonomy-review/
- Crexi Exchange API docs (password-gated) — https://api-docs.crexi.com/
- API Evangelist, CREXi profile (secondary) — https://github.com/api-evangelist/crexi
- NextAutomation, "CoStar vs Crexi vs LoopNet" (no-API/no-scraping claim, secondary) — https://nextautomation.us/blog/costar-vs-crexi-vs-loopnet
- SharpLaunch, "The Ultimate Guide to Commercial Real Estate Listings Sites" (17 Mar 2026, secondary) — https://www.sharplaunch.com/blog/the-ultimate-guide-to-commercial-real-estate-listing-sites
- Moody's CRE, "Catylist" — https://www.moodyscre.com/products/catylist/
- Brevitas, "Find Property" — https://brevitas.com/page/find-property
- U.S. Census Bureau, "Census Business Builder" — https://www.census.gov/data/data-tools/cbb.html
- U.S. Census Bureau LEHD, "Applications" — https://lehd.ces.census.gov/applications/ ; "Data (LODES)" — https://lehd.ces.census.gov/data/
- U.S. Census Bureau, "ACS 5-Year Data API" — https://www.census.gov/data/developers/data-sets/acs-5year.html
- NCDOT, "Traffic Survey GIS Data Products & Documents" — https://connect.ncdot.gov/resources/State-Mapping/Pages/Traffic-Survey-GIS-Data.aspx ; "Traffic Volume Maps" — https://connect.ncdot.gov/resources/State-Mapping/Pages/Traffic-Volume-Maps.aspx ; AADT Stations (ArcGIS Hub) — https://hub.arcgis.com/datasets/935fe47a0e5e43f08f96206fc99b7dd3
- PolicyMap, "Pricing" — https://www.policymap.com/pricing
- Social Explorer, "Social Explorer Plans" (help centre; fetched via search snippet, page 403) — https://help.socialexplorer.com/hc/en-us/articles/25084941016221-Social-Explorer-Plans
- Overture Maps, "Attribution and Licensing" — https://docs.overturemaps.org/attribution/
- Data.gov, "Wake County – Parcels" — https://catalog.data.gov/dataset/parcels-d1495 ; Wake Open Data — https://data-wake.opendata.arcgis.com/datasets/Wake::parcels-1/about
- Orange County NC Open GIS Data Portal — https://data-ocpw.opendata.arcgis.com/
- StreetLight Data, "Pricing" (no figures shown) — https://www.streetlightdata.com/pricing/
