# Consumer "Where Should I Live" and Home-Search Tools: Competitive Landscape

**Date:** 2026-11-03
**Status:** Draft v1 (research complete for named tools; several portal help pages blocked automated fetching and are flagged as unverified)
**Research stream:** 01 of the competitive review. Companion streams cover B2B site-selection and GIS tooling.

## Scope and method

This review covers consumer-facing tools that help a person decide *where* to live: the big US listing portals (Zillow, Redfin, Realtor.com, Trulia, Homes.com, Compass, Apartments.com), UK portals and their travel-time partner TravelTime (Rightmove, Zoopla, Jitty, Nestoria), standalone isochrone/commute-map tools (Walk Score, Mapnificent, Mapumental, Smappen, CommuteTimeMap, TravelTime's own map app, several Show HN projects), "city matching" quality-of-life sites (Niche, AreaVibes, Dwellics, Teleport, Nomad List, Hoodmaps), and general mapping apps (Google Maps, Apple Maps). Special attention went to tools that combine multiple constraints (two commutes plus amenities) and show the intersection region, since that is the core idea of our product.

Method: 200 web searches and roughly 100 page fetches between 2026-11-03 09:00 and 12:00 local time, favoring primary sources (press releases, help centers, pricing pages, vendor case studies, app-store listings, Hacker News and Blind threads). Zillow.com, Trulia.com, Realtor.com, Fast Company, GeekWire, Estate Agent Today, Capterra and Ask MetaFilter returned HTTP 403 to automated fetching; where I relied on a search-engine summary of those pages instead of the page itself, I say so. Anything I could not confirm is marked **(unverified)**. All sources were accessed on 2026-11-03.

---

## 1. Executive summary

1. **Every major US portal now has both a commute filter and a natural-language/AI search, but all of them treat commute as a single destination and a hard cutoff.** Zillow (filter June 2024; NL commute queries Sept 2024), Realtor.com (filter 2019, TravelTime-powered), Apartments.com (filter with rush-hour toggle), Redfin (per-listing commute display, then conversational search Nov 2025), Homes.com (Smart Search Oct 2025, Homes AI Feb 2026). None lets you enter two workplaces and see where both fit.
2. **The only mainstream products that ever supported multiple destinations were Homesnap (up to five, 2018; reviewers found it non-functional; brand sunset 2023), Mapumental Property (UK, 2012; withdrawn 2020) and the UK portals Rightmove/Zoopla via TravelTime.** In the US the multi-commute problem is currently served only by hobby projects and generic isochrone tools.
3. **Users explicitly ask for the two-commute intersection and have for 15 years.** HN 2011: "if only there was a way to enter 2 addresses (for spouses/roommates)." HN 2022: "I long for a map experience that's more like a SQL query than a catalog." HN 2023 Show HN requests: multiple origin points, walking/cycling modes, bookmarkable URLs. Blind 2020s: a filter, not just a displayed number.
4. **Showing the region matters more than the chat.** Zillow's 2026 app reviews punish replacing a commute filter with "a line on the map." Jitty's co-founder says switching from "complex polygons to a simple, elegant hex grid" is what "clicks with users." Realtor.com and Homes.com render an isochrone shade on the map alongside the list.
5. **Natural-language entry is now table stakes and measurably liked:** Jitty reports 75% of its users prefer NL search over filters; Redfin's conversational search testers viewed almost 2x the listings and were 47% more likely to request a tour. But the successful implementations (Jitty, Homes.com, Redfin) translate the sentence into *visible, editable* structured filters rather than hiding the logic in a chat.
6. **Standalone isochrone tools without listings do not retain house-hunters.** The 2021/2025 Everyday Old House review faults TravelTime's map for "not linked to real estate databases" and requiring extra cross-referencing; Mapumental, Teleport, Nestoria's WhereCanILive and Flyhomes' AI portal are all gone. The products that survived are the ones embedded in a listings marketplace.
7. **Rush-hour vs off-peak is the one time-of-day control every portal ships; nobody ships departure-time precision or transit reliability.** Both come up as complaints (Everyday Old House; HN 2023 "your arrival time entirely depends on the train schedule").
8. **Amenity *categories* are handled badly everywhere.** Portals accept "near a park" in NL and resolve it per-listing (Homes.com: "within a 15-minute walk to a Whole Foods"); none shows "the region where a grocery store is within a 10-minute walk" as a layer you can intersect with commutes. Walk Score aggregates amenities into a 0-100 number instead, which critics note treats a supermarket and a convenience store the same.
9. **Weighted or soft constraints are absent from every house-search tool.** Only the city-ranking sites (AreaVibes, Dwellics, Nomad List) let users reweight factors, and they operate at city granularity with no map region output.
10. **The data layer is commoditized and cheap enough for us:** TravelTime sells flat-rate unlimited calls to portals; Walk Score's Travel Time API is $115/month; Geoapify powers a free consumer tool with intersection/union; Mapbox's Isochrone API powers a two-commuter GitHub project; TravelTime and Jitty both moved to H3 hexagons for performance. Our tiered-precompute H3 plan is in line with where the leaders went.
11. **The gap we can fill:** a map-first, NL-assisted tool that takes *N* hard constraints (two or more commutes, by mode, at rush hour) plus amenity-coverage layers, shows the intersection as a shaded hex region with per-constraint "fits/doesn't fit" coloring, persists the constraint set in a shareable URL for a couple to co-edit, and links the region to live listings. Nothing live in the US does all of this; Jitty is the closest in the UK.
12. **Risk to watch:** the portals are iterating fast (four major AI search launches in Oct 2025 to Aug 2026). Our defensible edge is the multi-constraint region and the two-person workflow, not NL search itself.

---

## 2. Landscape table

| Tool | Type | Multi-constraint? | Modes | Result presentation | Pricing | Status (2026-11-03) | Verdict |
|---|---|---|---|---|---|---|---|
| Zillow | US portal | No: one destination; NL accepts one commute clause | Drive, bike, walk, transit; rush/off-peak; 10-60 min | Listing list/pins; per-listing travel times; 2026 reviews describe "a line on the map" | Free (ads/leads) | Live; commute filter reported broken/removed June 2026 | Learn-from (and compete-with on region) |
| Redfin | US portal | No: shows commute per listing, no filter; conversational search asks about commute | Drive, transit (per-listing) | List + map; chat refines results | Free | Live; conversational search Nov 2025 | Learn-from |
| Realtor.com | US portal | No: one destination | Drive, transit, walk, cycle (TravelTime); rush/off-peak | Isochrone shade on map + filtered list; commute on each listing | Free | Live; RealAssist AI beta June 2026 | Learn-from |
| Trulia (Zillow Group) | US portal | No | Drive; transit where GTFS (2012 feature) | Commute heat map with slider; 34 map overlays | Free | Live; heat-map status **(unverified)** | Learn-from (visual model) |
| Homes.com (CoStar) | US portal | Partial: multi-geo and POI proximity in NL; multi-destination **(unverified)** | "Multi-modal" via TravelTime | Isochrone reachable area + list; shows which filters were applied | Free | Live; Smart Search Oct 2025, Homes AI Feb 2026 | Compete-with / learn-from |
| Homesnap | US portal app | **Yes, up to 5 destinations (2018)**; non-functional per 2021 review | Drive (8 AM weekday only per review) | Neighborhoods within max drive time of all locations | Free | Defunct (sunset 2023, folded into Homes.com) | Learn-from (the one US precedent) |
| Compass | Brokerage portal | No | n/a | Dynamic map, draw boundaries, Collections | Free | Live; AI focused on agents | Ignore |
| Apartments.com (CoStar) | US rental portal | No: one destination | Drive, transit, walk, bike; rush/no-traffic | Boundary drawn on map + list | Free | Live | Learn-from |
| Walk Score (Redfin) | Scores + API | No | Walk/Transit/Bike scores; Travel Time API drive/transit/walk/bike | 0-100 scores; API returns times/polygons | API free <=5k/day; Premium from $115/mo | Live; 2011 apartment-by-commute search page 404 | Learn-from (data) |
| Rightmove (UK) | UK portal | **Yes: "My Places" multiple POIs** (TravelTime) | Walk, cycle, drive, transit | Travel times on each listing; filter status **(conflicting sources)** | Free | Live | Learn-from |
| Zoopla (UK) | UK portal | **Yes: multiple destinations** (TravelTime) | Drive, transit, walk, cycle, combos | Custom search area; list or map | Free | Live ("Travel time search" link confirmed) | Learn-from |
| Jitty (UK) | AI-native portal | Partial: NL commute + features; multi-destination **(unverified)** | TravelTime modes | **H3 hex grid shaded by time** + listings | Free to consumers | Live; 500k searches/mo Nov 2025 | **Closest analogue; learn-from** |
| HouseMe.ai (US) | AI-native portal | Lifestyle prompts; no region output | n/a | Chat ("Paige") + listing Intelligence Reports | Free | Live; US launch Aug 2026 | Watch |
| Flyhomes AI | AI-native portal | No | n/a | Conversational Q&A | Free | Consumer portal gone; site now mortgage products | Ignore (cautionary) |
| TravelTime map app | Isochrone tool | **Yes: up to 3 origins, overlap** | Car, transit, walk, cycle | Isochrone / H3 / geohash; POIs with times | Free, no sign-up; API paid flat-rate | Live | Learn-from |
| CommuteTimeMap (Geoapify) | Isochrone tool | **Yes: union and intersection** | Transit, car, bike, walk | Polygons; POI search inside | Free | Live | Learn-from |
| Mapnificent | Transit isochrone | Multiple markers (per HN) | Transit only | Shaded reachable area + slider | Free, open source | Live, low maintenance | Learn-from (UX) |
| Mapumental Property (mySociety) | Isochrone + listings | **Yes: multiple destinations, price bands, scenicness** | Transit (GB) | Travel-time bands + Zoopla listings | Free (showcase) | Defunct (2020) | Learn-from (the model we want, 2012) |
| Smappen | B2B isochrone SaaS | Yes: overlap of zones | Drive, walk, bike | Polygons + demographics/POIs | Free tier; $99-$399/mo | Live | Ignore (B2B) |
| commute-map (GitHub, kaylaajturner) | Hobby project | **Yes: two commuters, AM and PM** | Drive (Mapbox) | Hex grid colored by longer commute; hatched over limit | Free | Live (GitHub Pages) | Learn-from (UX detail) |
| Transit Travel Time Map (Show HN 2023) | Hobby project | No (requested) | Transit | Road-colored heat map | Free | Live | Learn-from (feedback) |
| CommuteCompass (iOS) | London app | No | Transit | List with rent/crime/amenities | Free | Dormant (v1.0.1 Oct 2023) | Ignore |
| Nestoria WhereCanILive | Portal mashup (2009) | No | Tube/DLR station-to-station | Ranked list by price and time | Free | Defunct | Ignore |
| Niche / AreaVibes / Dwellics | City/neighborhood rankings | Weighted factors (AreaVibes, Dwellics) | n/a | Ranked lists, grades | Free (ads/leads) | Live | Ignore (different problem) |
| Teleport Cities | City matching | 17 dimensions | n/a | Ranked cities | Free | Defunct (2024) | Ignore (cautionary) |
| Nomad List (nomads.com) | City matching | 500+ parameters | n/a | Ranked cities | One-time membership | Live | Ignore |
| Hoodmaps | Crowd vibe map | No | n/a | Painted neighborhood categories + tags | Free | Live | Learn-from (overlay idea) |
| Google Maps | General mapping | No | All | Commute tab (2018), demoted 2024 **(unverified)** | Free | Live | Ignore |
| Apple Maps | General mapping | No home-search features found | All | n/a | Free | Live | Ignore |
| Opendoor / Offerpad | iBuyers | No | n/a | City/ZIP search + filters | Free | Live | Ignore |

---

## 3. Detailed notes per tool

### Zillow

Zillow launched natural-language search on 26 Jan 2023 (iOS first) with example queries like "$700K homes in Charlotte with a backyard"; it positioned itself as "the first major residential real estate marketplace" to do so and said it was "training machine learning models to better respond" to sentences ([Zillow press release](https://zillow.mediaroom.com/2023-01-26-Zillows-new-AI-powered-natural-language-search-is-a-first-in-real-estate)). A ChatGPT plugin followed in alpha on 2 May 2023 ([press release](https://zillow.mediaroom.com/2023-05-02-Zillow-builds-ChatGPT-plugin-for-real-estate-searches)).

The dedicated **commute time filter** arrived 13 Jun 2024 in the mobile app: enter one address, pick driving/biking/walking/transit, rush hour or off-peak, and a maximum of 10-60 minutes; results are the listings that qualify. Zillow's 2023 survey, cited in the launch, says 53% of buyers prioritize commute time, 67% walkability and 43% transit access ([Inman](https://www.inman.com/2024/06/13/time-is-of-the-essence-with-zillows-latest-search-filter/)). On 4 Sep 2024 the NL search was extended to commute, affordability and points of interest, with the example "Homes within 30 minutes of downtown Dallas" ([HousingWire](https://www.housingwire.com/articles/zillow-artificial-intelligence-search/)) and "Homes 30 minute drive from the Minneapolis Institute of Art" ([BAM](https://nowbam.com/goodbye-to-filters-zillows-ai-powered-home-search-is-smarter-than-ever/)). Listing pages also have a "Travel times" toggle that estimates time to a saved address by car, transit, bike or foot (Zillow Learn page; summary via search result, page blocked).

Reception: an analysis of 380 one-to-three-star app reviews collected 31 Jul 2026 found 12 complaining specifically about the commute feature after a June 2026 update: "Latest June 2026 update completely broke the Commute/Travel Time feature inside property listings. Saved destinations no longer load." and "Why would you get rid of the ability to filter by commute time, and replace it with a line on the map?" and "My saved searches ... are no longer limited to ... the commute distance I set from work." ([Unstar](https://unstar.app/blog/zillow-app-problems-removed-features-listing-data-2026)). On HN in 2022, user etskinner wrote: "Zillow doesn't have isochrones, for one. I long for a map experience that's more like a SQL query than a catalog." ([HN](https://news.ycombinator.com/item?id=32277313)). Routing provider: not disclosed **(unverified)**. Multiple destinations: not supported in any source found.

### Redfin

Redfin historically had no commute *filter*; you add a work address and each listing shows the commute time ("Add a Commute" under My Favorites). A Blind thread from a Microsoft employee asking for a 30-minute cutoff drew the replies "You can add your work address on Redfin and then it'll start showing commute time on each listing!" and "You can sort by that," plus a suggestion to use Zillow instead ([Blind](https://www.teamblind.com/post/redfin-why-dont-you-create-a-filter-on-commute-time-zwrvuasg)). Redfin owns Walk Score (acquired Oct 2014; [Wikipedia](https://en.wikipedia.org/wiki/Walk_Score)).

On 13 Nov 2025 Redfin launched **conversational search**: describe the home in your own words, then answer follow-ups about "preferred commute time" and "proximity to a school"; early testers viewed nearly 2x as many listings and were 47% more likely to request a tour; web and mobile web first, iOS in December ([press release](https://www.redfin.com/news/press-releases/redfin-debuts-conversational-search-to-reinvent-how-people-find-homes/)). Redfin's how-to post (1 May 2026) recommends detailed prompts such as "Show me homes in Chicago for less than $2 million, within 25 minutes of Willis Tower and near an L station, with a pool" and says the assistant asks about commute times during rush hour; results show on the homepage map and at Redfin.com/chat ([Redfin blog](https://www.redfin.com/blog/redfin-conversational-search/)). "Ask Redfin" is a separate AI Q&A on listing pages. A third-party tool, ListingMap, exists to add "nearby places and real travel times" to Redfin listings, which it says Redfin lacks natively ([ListingMap](https://www.listingmap.site/for/redfin)).

### Realtor.com

Realtor.com shipped a commute time filter on 1 Jul 2019 (iOS first) with a rush-hour/off-peak toggle and 10-minute increments up to 60+ minutes; its CPO called the toggle the differentiator, and a survey claimed 85% of respondents would trade home amenities for a shorter commute ([PR Newswire](https://www.prnewswire.com/news-releases/new-realtorcom-commute-time-filter-lets-buyers-test-drive-their-commute-before-buying-a-home-300878096.html)). TravelTime's case study says the feature supports driving, transit, walking and cycling, shows "an isochrone map view" of all areas reachable within the threshold next to the filtered list, puts commute estimates on every listing, and lets users add or adjust the commute from a listing page; wording implies a single destination ([TravelTime case study](https://traveltime.com/case-study/realtor-commute-search-traveltime)). A homebuyer blog (Jan 2021, updated Oct 2025) rated it "easiest to use" because listings appear immediately inside the commute area, but complained about no exact departure/arrival times and said public transit was unavailable as an option, which conflicts with TravelTime's claim **(conflict noted)** ([Everyday Old House](https://everydayoldhouse.com/free-commute-radius-maps-for-homebuyers/)).

**RealAssist AI** launched in beta 8 Jun 2026 on desktop, mobile web and app, built with Google Gemini and Google Cloud; it offers commute-time insights, nearby amenities, side-by-side home/neighborhood comparisons and visualizations at different times of day ([RISMedia](https://www.rismedia.com/2026/06/08/realtor-com-launches-realassist-conversational-home-search-experience/)). A trade report says it uses "Grounding with Google Maps" for commute and amenity data (National Mortgage Professional; via search summary, page blocked).

### Trulia

Trulia was the first portal to make commute a *map*: in June 2012 it added commute-time heat maps you adjust with a time slider, driving times from OpenStreetMap everywhere and transit where agency data existed, layered with crime, schools and amenities ([The American Genius](https://theamericangenius.com/commute-times-as-heat-maps-trulia-search/)). A 2013 roundup describes dragging a marker to set the origin and sliding the time ([Google Maps Mania](https://googlemapsmania.blogspot.com/2013/04/commuting-times-on-google-maps.html)). Consumer Reports (2016) said "You can set a commute time by auto or public transportation to a specific location; the search tool identifies properties with commute times that fit" ([Consumer Reports](https://www.consumerreports.org/personal-finance/go-house-hunting-virtually)). Trulia's neighborhood pages advertise 34 map overlays and "What Locals Say" polls (2018). Whether the slider heat map is still live in 2026 I could not verify; Trulia pages blocked fetching **(unverified)**.

### Homes.com, Homesnap and Apartments.com (CoStar)

**Homesnap** (acquired by CoStar 2020, brand sunset 2023 and folded into Homes.com; [Clever](https://listwithclever.com/real-estate-blog/homesnap-reviews/)) launched "Search by Commute" on 13 Sep 2018 with up to five destinations (employers, schools, daycare, gyms), returning neighborhoods within the maximum drive time "from all combined locations, even if they are not contiguous," with save/sync/share across devices. Co-founder Guy Wolcott: "Many households have two full-time working adults, and face traffic jams and long commutes." ([Inman](https://www.inman.com/2018/09/13/homesnap-launches-search-by-commute-tool-for-homebuyers/)). The 2021 review found the multi-address feature advertised but "not functional during testing" and times fixed to 8 AM weekday traffic ([Everyday Old House](https://everydayoldhouse.com/free-commute-radius-maps-for-homebuyers/)). This is the only US portal precedent for our core feature, and it died quietly.

**Homes.com Smart Search** launched 14 Oct 2025 with speech-to-text and examples "ranch-style house with a pool in Austin," "2-bedroom condos in Arlington and Alexandria near metro stations," and "condos near CoStar's Arlington and Richmond offices" ([RISMedia](https://www.rismedia.com/2025/10/14/homes-com-launches-smart-search-with-ai-home-searching-capabilities/)). TravelTime powers it and shows an image of "free-text search and isochrones to display a reachable area"; TravelTime's CCO: "If you let users search for anything, you better be able to service their demands." ([TravelTime](https://traveltime.com/blog/homes-ai-search-announcement)). **Homes AI** (17 Feb 2026) adds voice/text conversation, neighborhood and school questions, de-furnishing photos, fair-housing guardrails, and displays which filters were applied to the NL query; CoStar plans to extend it to Apartments.com ([HousingWire](https://www.housingwire.com/articles/homes-ai-launch-openai/)). CoStar's technical overview for MLSs (23 Feb 2026) lists "Points of Interest: ... 'condos in Santa Monica within a 15-minute walk to a Whole Foods'" and multi-geo search, and describes the LLM as "a translator, not a student" that sees only a transient snippet ([Council of MLS PDF](https://resources.councilofmls.org/wp-content/uploads/2026/04/AI-Technical-Overview-Homes.pdf)). Multiple commute destinations: not mentioned **(unverified)**.

**Apartments.com** has a "Travel Time" panel with a "Search by Commute Time" checkbox: destination (work/school/other), mode (drive/transit/walk/bike), minutes, rush hour vs no traffic; "a new boundary is created" on the map (Apartments.com blog; via search summary, page blocked; help center confirms the tool exists: [Renter Help](https://renterhelp.apartments.com/article/752-how-can-i-maximize-the-search-on-apartments-com)). The iOS app has 4.9 stars on 485k ratings; a 2020 review asked for better bus/metro integration: "I don't want to have to have both google maps and this app open" ([App Store](https://apps.apple.com/us/app/apartments-com-rental-finder/id319836632)).

### Compass

Compass's 2019 consumer release emphasized dynamic map search, drawing custom boundaries, cross-market search and AI "Recommended for You," with no commute feature ([Compass newsroom](https://www.compass.com/newsroom/press-releases/2SotgA2Oh2rFkFE48UGD0R/)). Its 2025-2026 AI investment is an assistant for agents and conversational lead intake (Inman, HousingWire; via search). Not relevant to region-finding.

### Walk Score (Redfin)

Founded 2007; Transit Score 2010; an apartment search by commute time in 2011; Bike Score 2012; Travel Time API 2013; acquired by Redfin Oct 2014. Critics note it ignores sidewalks, crossings and crime and "treats a supermarket identically to a convenience store" ([Wikipedia](https://en.wikipedia.org/wiki/Walk_Score)). API pricing: free up to 5,000 calls/day for free consumer apps; Premium from $115/month adds Score Details, transit data and the Travel Time API; Enterprise custom ([pricing](https://www.walkscore.com/professional/pricing.php)). The Travel Time API covers the US and Canada, drive times with rush-hour or free-flow traffic "for over 100 metro areas ... on a road-by-road basis," plus transit, walk and bike, as a JS library or REST, with map "time-shed" overlays ([Travel Time API](https://www.walkscore.com/professional/travel-time-api.php)). The 2011 Show HN for the apartment search is the earliest record I found of the two-commute ask: philfreo: "if only there was a way to enter 2 addresses (for spouses/roommates) and have it give you the places with the best cumulative commute times"; perssontm: "The middle-point between 3 coworkers, with least commutetime for everyone" ([HN](https://news.ycombinator.com/item?id=3060748)). On 2026-11-03 `walkscore.com/apartments/search/` returned 404; the commute-based apartment search appears discontinued **(unverified)**.

### Rightmove and Zoopla (UK) and TravelTime

**TravelTime** is the routing vendor behind Realtor.com, Rightmove, Zoopla, OnTheMarket, Homes.com and Jitty; it sells "unlimited calls to all endpoints for one fixed custom price" and pitches multi-modal commute search, personal POIs, ranking by travel time and H3 hex grids "simpler than complex polygons" ([property portals page](https://traveltime.com/property-portals)). Its free consumer map (app.traveltime.com) supports up to three origins and shows where their areas overlap, car/transit/walk/cycle, output as isochrones, H3 cells or geohashes, POIs with per-place times, no registration ([TravelTime app](https://app.traveltime.com/)). Its London blog explicitly frames "combine multiple commute times and transport modes to see whether there are overlapping areas" for choosing where to live ([TravelTime blog](https://traveltime.com/blog/london-commuter-map-wheres-best-to-live-meet-friends)).

**Rightmove**: TravelTime's case study describes "My Places" (e.g., "Mum's House, Lucy's School, or New Office"), four modes, and travel times "displayed directly within the Rightmove interface" that persist across the session; it does not describe a polygon ([case study](https://traveltime.com/case-study/rightmove-property-poi-search-traveltime)). TravelTime's blog says the Rightmove app let users enter multiple locations with a max time and mode for each and see a map of matching properties. A 2025-26 Chrome extension, Commutable, claims "Rightmove doesn't currently let you filter listings by commute or journey time out of the box" (via search summary; site returned 404) **(conflict; current native filter status unverified)**. Third-party browser extensions have filled this gap since 2014 ("Commuter Homes London," [Rightmove article](https://www.rightmove.co.uk/news/articles/dream-properties/calculate-your-commute-from-any-london-property-on-rightmove/)); one, "Commute Time (for Rightmove & Zoopla)," has 103 installs, a 3.0 rating, was last updated 2017 and is now delisted ([Extpose](https://extpose.com/ext/47939)).

**Zoopla**: users name frequent destinations, modes and max times; multiple destinations are supported; results in list or map; CPO Matt Cohan: "our travel time tool has achieved an impressive 300% increase in conversions" (viewing bookings) within 10 months versus distance search ([case study](https://traveltime.com/case-study/isochrone-map-tool-case-study-zoopla)). A live London listings page shows "Travel time search" and "Search homes by travel time" links (zoopla.co.uk, checked 2026-11-03); the dedicated page URL could not be fetched.

### Jitty (UK) - the closest analogue

Jitty (founded 2022; backed by REA Group and Google's Gradient Ventures) combines an LLM, computer vision over listing photos and TravelTime. Its homepage says "Type '40 mins to Old Street station' to discover homes across different neighbourhoods" and shows prompts like "4 bed house with a treehouse, 1 hour commute from London" ([jitty.com](https://jitty.com/)). Unified search (10 Mar 2025) mixes NL and filters: "3 bed, 1-hour commute to Paddington with a freestanding bath," "15 min cycle to Shoreditch with a bike garage"; applied filters are visible in the URL ([Jitty blog](https://jitty.com/post/jittys-new-unified-search)). TravelTime's case study: reachable areas render as H3 hex grids "with shaded gradients communicating time ranges"; co-founder Daniel Cooper: "We went from rendering complex polygons to a simple, elegant hex grid that clicks with users"; hex cells replaced point-in-polygon lookups and enable real-time ranking by journey time ([case study](https://traveltime.com/case-study/jitty-property-search-traveltime-h3)). Metrics (13 Nov 2025): on track for 500k searches that month, 25% month-on-month growth, zero acquisition spend, "75% of users prefer AI-powered natural language search over traditional filters" ([The Negotiator](https://thenegotiator.co.uk/news/proptech/jitty-passes-half-a-million-property-searches-as-ai-reshapes-market/)). A conversational search launched March 2026 (Estate Agent Today; page blocked). Multi-destination support **(unverified)**.

### Other AI-native entrants

**Flyhomes AI** (11 Jun 2024) bought ZeroDown's conversational search, claimed 900 data points per home across 28 states, and answered questions like "Are there high-voltage transmission lines near this property?" ([Inman](https://www.inman.com/2024/06/11/flyhomes-joins-portal-wars-with-launch-of-ai-powered-search/)). On 2026-11-03 flyhomes.com shows only "Buy Before You Sell" mortgage products for loan officers and agents, with no search product; the consumer portal appears discontinued (no announcement found) **(unverified)**. **HouseMe.ai** launched in the US on 5 Aug 2026 (DC, MD, VA, DE, PA, NJ, WV) with an assistant named Paige, lifestyle prompts ("a park nearby, a top-rated school within walking distance"), direct MLS feeds, and per-listing "Intelligence Reports"; free to consumers ([Inman](https://www.inman.com/2026/08/05/housemeai-lifestyle-search-us-launch/), [HousingWire](https://www.housingwire.com/articles/houseme-ai-us-mls/)). Neither produces a region.

### Standalone isochrone and commute-map tools

- **Mapnificent** (Stefan Wehrmeyer, inspired by Mapumental): drop a marker, slide the time, see the transit-reachable area; GTFS-based, free, open source (407 stars), JS API; the site lists 26 cities including Boston, Chicago, LA, NYC ([mapnificent.net](https://www.mapnificent.net/), [GitHub](https://github.com/mapnificent/mapnificent), [TransitWiki](https://www.transitwiki.org/TransitWiki/index.php/Mapnificent)). A 2011 HN comment says it supports multiple addresses **(interaction unverified)**.
- **Mapumental / Mapumental Property** (mySociety, 2006-2020, AGPL): postcode in, colored travel-time bands out; the Property version (Nov 2012) filtered Zoopla rentals/sales by price band and commute, supported "multiple destination points for multi-person households," and added a crowdsourced "scenicness" filter; withdrawn 2020, positioned as a showcase rather than a competitor to portals ([mySociety](https://www.mysociety.org/2012/11/10/mapumental-property-extra-insight-for-househunters/), [Wikipedia](https://en.wikipedia.org/wiki/Mapumental)). This is the fullest historical realization of our idea.
- **CommuteTimeMap** (Geoapify): free web app for transit/car/bike/walk isochrones that computes union and intersection of multiple areas and runs POI searches inside them, using transit approximation where GTFS is missing; Geoapify's own example is "apartments reachable within 30 minutes from two different workplaces" ([TransitWiki](https://www.transitwiki.org/TransitWiki/index.php/CommuteTimeMap), [Geoapify](https://www.geoapify.com/isochrone-maps/)). No listings.
- **Smappen**: B2B catchment tool; free tier (10 areas and one POI search per search summary; the product page says "unlimited" **(conflict)**), paid $99/$199/$399 per month (via search summary); drive/walk/bike; overlap of zones for "cannibalization" analysis ([Smappen](https://www.smappen.com/isochrone-tool-for-drawing-amp-analyzing-areas-travel-time/); [Felt roundup, Mar 2026](https://felt.com/blog/isochrone-map)).
- **commute-map** (GitHub, kaylaajturner): the best small UX precedent for two commuters. Work address, arrival and departure times and max commute per person; Mapbox Isochrone, Directions and Geocoding APIs; Turf.js hex grid client-side; "The map shows where both commutes fit, and where only one does," colored by whichever commute is longer, hatched where over the limit; "All times use typical traffic for the next Tuesday" ([GitHub](https://github.com/kaylaajturner/commute-map)).
- **Transit Travel Time Map** (Show HN, 24 Jul 2023; map.henryn.xyz): Rust GTFS backend, React + Mapbox; feedback asked for multiple origins, walk/cycle modes, bookmarkable URLs, click-to-lock instead of hover; baq: isochrone maps are "criminally unpopular" but great for house hunting; midoridensha: "you can only arrive at discrete times"; forrestthewoods: Google Maps is the only reliable source but pricing is prohibitive ([HN](https://news.ycombinator.com/item?id=36847960)).
- **RadiusMapper** blog recommends the manual overlap method for two workplaces and the heuristic "prioritize neighborhoods that minimize the longer of the two commutes" ([RadiusMapper](https://radiusmapper.com/blog/commute-time-map-find-ideal-commute)).
- **Map Across: Multiple Places** (iOS, 2025, $24.99/yr): finds areas where several *place types* cluster ("bar AND cinema") within 100 m-10 km radii, a rare consumer precedent for amenity-category intersection ([App Store](https://apps.apple.com/app/id6748239882)).
- **CommuteCompass** (iOS, London, v1.0.1 Oct 2023): single commute destination, sorts by rent, crime, amenities, council tax; free; no ratings ([App Store](https://apps.apple.com/fi/app/commutecompass/id6468519462)).
- **Nestoria WhereCanILive** (Jan 2009): nearest Tube/DLR station plus budget, properties "ranked by price and commuting time," station-to-station only, a UCL master's project ([TechCrunch](https://techcrunch.com/?p=501332)). Defunct **(unverified)**. "Placy" turned out to be a Japanese music-based place-discovery app unrelated to home search (search results only).

### City-matching and neighborhood-vibe sites

**Niche** grades places with z-scores across cost of living (12.5%), public schools, crime, housing, employment and a 5% user-survey component, from Census, FBI, BLS and CDC data (niche.com methodology; via search summary, page blocked). **AreaVibes** (since 2010) scores any address 0-100 on amenities, commute, cost of living, crime, employment, health, housing, schools and user ratings and lets you reweight metrics; amenities are businesses within two miles ([AreaVibes](https://www.areavibes.com/about/)). **Dwellics** covers 60,000 US places from 50+ sources with customizable calculators and ranked lists, free, funded by relocation-partner ads ([press release, Dec 2022](https://www.einpresswire.com/article/605087926/dwellics-com-offers-customizable-calculators-to-compare-cities-for-relocation)). **Teleport Cities** (2014-2024) was acquired by MOVE Guides/Topia in 2017 and redirected away in April 2024; a competitor's post-mortem blames the enterprise-HR mismatch and the omission of household-level factors like after-tax income and childcare ([Cityparity](https://cityparity.com/blog/teleport-cities-shut-down/)). **Nomad List** now lives at nomads.com with 500+ filters, one-time membership fees and a claimed 49,145 members ([nomads.com](https://nomads.com/)). **Hoodmaps** (Pieter Levels, 2016) lets crowds paint neighborhoods as hipster/tourist/rich/normie/suits/uni and add tags; free and live ([hoodmaps.com](https://hoodmaps.com/)). All operate at city or neighborhood granularity and output rankings, not regions; none takes a user's specific places as input.

### General mapping apps and iBuyers

Google Maps added a Commute tab on 1 Oct 2018 with mixed-mode legs and live delays ([Google blog](https://blog.google/products-and-platforms/products/maps/take-control-your-commute-google-maps/)); reports say its bottom-bar shortcut was removed in the Aug 2024 iOS redesign **(unverified; low-quality source)**. It never offered a "where could I live" region. Google's own design guidance for commute search in job boards is instructive: collect mode, max time (capped at 60 minutes), start location and traffic/departure time; offer a two-tab toggle between distance and commute search; display with heatmap plus marker clustering ([Google Cloud Talent docs](https://docs.cloud.google.com/talent-solution/job-search/v3/docs/commute-search)). I found no Apple Maps home-search or commute-region feature. Opendoor's help center describes only city/ZIP/address search with price/bed/bath filters ([Opendoor Help](https://help.opendoor.com/buying/finding-touring/browse-and-tour)); nothing resembling a "find your area" tool was found for Opendoor or Offerpad.

---

## 4. Cross-cutting lessons

### Interaction models observed

| Model | Examples | What works | What fails |
|---|---|---|---|
| Form filter (address + mode + minutes + rush toggle) | Zillow 2024, Realtor.com 2019, Apartments.com | Familiar; immediate listing results; rush/off-peak toggle valued | Single destination; buried in filter drawer; Zillow users lost it in a redesign |
| Per-listing display, no filter | Redfin, Rightmove "My Places" | Cheap to build; useful once shortlisting | Users explicitly ask to filter, not just view (Blind thread) |
| Map-first heat map with slider | Trulia 2012, Mapnificent, Mapumental | Instantly legible; invites exploration; drag marker + slider is a strong pattern | Transit-only or drive-only; standalone versions lacked listings |
| Pure chat | Flyhomes AI, HouseMe.ai, RealAssist | Good for Q&A about a listing | No spatial output; Flyhomes' portal is gone |
| Hybrid NL to visible filters to map region | Jitty, Homes.com Smart Search, Redfin conversational | NL lowers entry cost; filters stay editable; region visible; measurable engagement lifts | Still single commute in US; Homes.com and Jitty multi-destination unconfirmed |

### How they handle "two commutes"

US portals: not at all. Homesnap tried five destinations in 2018, implemented as the union of neighborhoods reachable from "all combined locations" (which reads as a union, not an intersection), reviewers found it broken, and the brand died. UK portals via TravelTime: multiple destinations each with own mode and max time (Zoopla, Rightmove app), but the on-map presentation of the intersection is not documented. Standalone tools: TravelTime's app (3 origins, overlap), CommuteTimeMap (explicit intersection/union), Mapnificent (multiple markers), and the commute-map GitHub project (two people, AM and PM, "both fit / only one fits" coloring). The user heuristic from RadiusMapper, "minimize the longer of the two commutes," suggests a scoring layer inside the intersection.

### How they link to listings

Portals filter their own inventory and show the isochrone as a shade behind pins (Realtor.com, Homes.com) or hex gradient (Jitty). Standalone tools show POIs with travel times (TravelTime app) but not homes; this is the single most cited reason house-hunters abandon them. Mapumental Property solved it by pulling Zoopla listings into the travel-time bands in 2012 and still did not survive as a product, suggesting distribution and maintenance matter as much as the feature.

### What nobody does well

1. Intersection of two or more commutes with independent modes and rush-hour settings, shown as a region with per-constraint coloring, inside a listings product.
2. Amenity categories as coverage layers ("within a 10-minute walk of any grocery store") that can be intersected with commutes; portals resolve amenities per listing, scores collapse them to one number.
3. Soft or weighted constraints and visible trade-offs (only city-ranking sites reweight, with no map).
4. Departure-time precision and transit reliability/frequency (complaints in both the homebuyer review and the HN transit thread).
5. Persistence: saving the constraint set, sharing it with a partner, bookmarking via URL (Zillow saved-search complaints; HN URL-parameter requests; Homesnap's share feature was the one praised idea).
6. Honest data limits: TravelTime's CCO warns "If you let users search for anything, you better be able to service their demands."

### What users ask for in forums (verbatim themes)

- Two addresses for spouses/roommates and "best cumulative commute" (HN 2011).
- "A map experience that's more like a SQL query than a catalog" (HN 2022).
- Filter by commute, not just show it (Blind).
- Multiple origins, walking/cycling, click-to-lock, URL params, reliability metrics (HN 2023).
- Do not remove the filter and replace it with "a line on the map" (Zillow reviews 2026).
- Transit integration so you do not need Google Maps open in another tab (Apartments.com review 2020).

---

## 5. Implications for our build

1. **Lead with the map region, assisted by NL, never chat-only.** Recommended model: a single NL/command bar ("30 min drive to Duke at rush hour, 20 min bike for Sam to downtown Durham, walkable to a grocery store") that is parsed into visible constraint chips (destination, mode, max time, rush/off-peak), each editable and removable, with the intersection region re-rendering live on the map. This is the Jitty/Homes.com pattern plus the multi-constraint piece they lack.
2. **Render as an H3 hex grid, not polygons.** Two leaders (TravelTime, Jitty) moved to hexes for performance and legibility; hexes also let us shade by "how many constraints fit" and by the longer-of-two-commutes heuristic, which polygon intersections cannot express. Our tiered precompute of gridded travel-time layers matches this.
3. **Make the two-person case the headline.** Use commute-map's visual grammar: color where both fit, hatch or desaturate where only one fits, and show each person's layer on toggle. No live US product does this.
4. **Ship rush-hour vs off-peak from day one;** it is the one time-of-day control every portal has, and Realtor.com's CPO called it the differentiator. Departure-time precision can wait, but label the assumption (commute-map's "typical traffic for the next Tuesday" is a good honest default).
5. **Treat amenity categories as coverage layers,** precomputed per hex ("minutes to nearest grocery/park/coffee"), so they intersect with commutes instead of being per-listing lookups. This is the biggest unserved pattern and plays to our OSM/POI work.
6. **Link listings early, even crudely.** Every standalone isochrone tool failed the house-hunter test for lack of listings. For friends-and-family, a deep link into Zillow/Redfin with a drawn boundary, or a pin layer from an MLS/IDX feed later, is enough to clear the bar.
7. **Persist and share.** Encode the full constraint set in the URL and offer a "share with partner" link; saved-search drift is Zillow's most-cited 2026 complaint.
8. **Keep hard constraints as the default, add soft ranking inside the region later.** Users think in cutoffs ("under 30 minutes") but then rank within; the RadiusMapper heuristic and AreaVibes-style reweighting are the model for a v2 score.
9. **Data vendors to shortlist:** Valhalla self-hosted (already in use) for precompute; Walk Score Travel Time API ($115/mo, US/Canada, rush-hour traffic) or Mapbox Isochrone for on-demand gaps; Geoapify for cheap transit approximation; TravelTime if we ever need portal-grade multi-modal at flat-rate. GTFS for Triangle transit (GoTriangle, GoRaleigh, GoDurham) feeds Mapnificent-style transit layers.
10. **Borrow Homes.com's guardrails** for the NL layer: show the filters that were applied, keep the model stateless over listing data, and add fair-housing screening on free-text (no steering by protected-class proxies).
11. **Do not over-invest in NL novelty.** Four portals shipped AI search between Oct 2025 and Aug 2026; our edge is the multi-constraint region and the couple workflow, so measure success as "time to a shaded region the household agrees on," not chat engagement.

---

## 6. Open questions

1. Does Rightmove currently offer a native commute *filter* or only per-listing times? Sources conflict (TravelTime case study vs Commutable guide). Needs a manual check in a UK browser session.
2. Did Zillow actually remove the commute filter in June 2026, or was it a bug? Only app-review evidence so far; re-check the current app.
3. Is Walk Score's 2011 apartment-search-by-commute fully retired (search URL 404s)?
4. Does Trulia still ship the 2012 slider heat map, and does Homes.com Smart Search accept two destinations? Both sites block automated fetching.
5. Do Zoopla or Jitty draw the *intersection* of multiple destinations on the map, or only filter the list? The case studies describe inputs, not the rendering.
6. What does TravelTime's flat-rate API actually cost at our scale, and is there a hobby tier?
7. Listings access for the Research Triangle: which MLS/IDX route (Doorify MLS, a broker partner, or deep links) is realistic for friends-and-family use?
8. Do users want weighted scores inside the intersection, or do hard cutoffs plus sort suffice? No tool has tested this; worth a quick prototype with 3-5 households.
9. How much do transit reliability and frequency matter for Triangle users versus drive-time, given the region's transit coverage?
10. Is there any Apple Maps or Google Maps feature in development for "where to live" regions that would commoditize this? Nothing found as of 2026-11-03.

---

## 7. Sources (all accessed 2026-11-03)

Zillow and Zillow Group
- https://zillow.mediaroom.com/2023-01-26-Zillows-new-AI-powered-natural-language-search-is-a-first-in-real-estate - Zillow press release, natural-language search launch
- https://zillow.mediaroom.com/2023-05-02-Zillow-builds-ChatGPT-plugin-for-real-estate-searches - Zillow press release, ChatGPT plugin
- https://www.inman.com/2024/06/13/time-is-of-the-essence-with-zillows-latest-search-filter/ - Inman, Zillow commute time filter
- https://www.housingwire.com/articles/zillow-artificial-intelligence-search/ - HousingWire, Zillow AI search adds commute and affordability
- https://nowbam.com/goodbye-to-filters-zillows-ai-powered-home-search-is-smarter-than-ever/ - BAM, Zillow AI search examples
- https://unstar.app/blog/zillow-app-problems-removed-features-listing-data-2026 - Unstar, analysis of 380 negative Zillow app reviews (2026)
- https://www.zillow.com/learn/zillow-advanced-search/ - Zillow Learn, advanced search (blocked; summary via search)
- https://theamericangenius.com/commute-times-as-heat-maps-trulia-search/ - The American Genius, Trulia commute heat maps (2012)
- https://googlemapsmania.blogspot.com/2013/04/commuting-times-on-google-maps.html - Google Maps Mania, commuting time maps (2013)
- https://www.jeffreydonenfeld.com/blog/2012/06/interactive-mapping-trulias-local-commuter-map/ - Donenfeld, Trulia Local commuter map
- https://www.consumerreports.org/personal-finance/go-house-hunting-virtually - Consumer Reports, virtual house hunting (2016)

Redfin and Walk Score
- https://www.redfin.com/news/press-releases/redfin-debuts-conversational-search-to-reinvent-how-people-find-homes/ - Redfin press release, conversational search
- https://www.redfin.com/blog/redfin-conversational-search/ - Redfin blog, how to use conversational search
- https://www.teamblind.com/post/redfin-why-dont-you-create-a-filter-on-commute-time-zwrvuasg - Blind thread on Redfin commute filter
- https://www.listingmap.site/for/redfin - ListingMap for Redfin
- https://en.wikipedia.org/wiki/Walk_Score - Wikipedia, Walk Score
- https://www.walkscore.com/professional/pricing.php - Walk Score Professional pricing
- https://www.walkscore.com/professional/travel-time-api.php - Walk Score Travel Time API
- https://news.ycombinator.com/item?id=3060748 - HN, "Find apartments by commute times" (2011)

Realtor.com
- https://www.prnewswire.com/news-releases/new-realtorcom-commute-time-filter-lets-buyers-test-drive-their-commute-before-buying-a-home-300878096.html - PR Newswire, Realtor.com commute time filter (2019)
- https://traveltime.com/case-study/realtor-commute-search-traveltime - TravelTime case study, Realtor.com
- https://www.rismedia.com/2026/06/08/realtor-com-launches-realassist-conversational-home-search-experience/ - RISMedia, RealAssist AI launch
- https://nationalmortgageprofessional.com/news/realtorcom-launches-ai-home-search-platform-built-google - National Mortgage Professional, Realtor.com and Google (blocked; summary via search)

CoStar: Homes.com, Homesnap, Apartments.com
- https://www.rismedia.com/2025/10/14/homes-com-launches-smart-search-with-ai-home-searching-capabilities/ - RISMedia, Homes.com Smart Search
- https://traveltime.com/blog/homes-ai-search-announcement - TravelTime, Homes.com Smart Search powered by TravelTime
- https://www.housingwire.com/articles/homes-ai-launch-openai/ - HousingWire, Homes AI launch with Azure OpenAI
- https://resources.councilofmls.org/wp-content/uploads/2026/04/AI-Technical-Overview-Homes.pdf - CoStar, Homes.com AI Technical Overview (23 Feb 2026)
- https://www.inman.com/2018/09/13/homesnap-launches-search-by-commute-tool-for-homebuyers/ - Inman, Homesnap Search by Commute
- https://listwithclever.com/real-estate-blog/homesnap-reviews/ - Clever, Homesnap shutdown
- https://everydayoldhouse.com/free-commute-radius-maps-for-homebuyers/ - Everyday Old House, 3 free commute radius maps (2021, updated 2025)
- https://renterhelp.apartments.com/article/752-how-can-i-maximize-the-search-on-apartments-com - Apartments.com Renter Help
- https://www.apartments.com/blog/how-to-find-an-apartment-with-a-great-commute - Apartments.com blog (blocked; summary via search)
- https://apps.apple.com/us/app/apartments-com-rental-finder/id319836632 - App Store, Apartments.com Rental Finder

Compass
- https://www.compass.com/newsroom/press-releases/2SotgA2Oh2rFkFE48UGD0R/ - Compass newsroom, consumer experience launch (2019)

UK portals, TravelTime, Jitty
- https://traveltime.com/property-portals - TravelTime, property portals page
- https://app.traveltime.com/ - TravelTime travel time map app
- https://traveltime.com/blog/london-commuter-map-wheres-best-to-live-meet-friends - TravelTime, London commuter map
- https://traveltime.com/case-study/rightmove-property-poi-search-traveltime - TravelTime case study, Rightmove
- https://traveltime.com/case-study/isochrone-map-tool-case-study-zoopla - TravelTime case study, Zoopla
- https://traveltime.com/case-study/jitty-property-search-traveltime-h3 - TravelTime case study, Jitty and H3
- https://www.rightmove.co.uk/news/articles/dream-properties/calculate-your-commute-from-any-london-property-on-rightmove/ - Rightmove, Commuter Homes London extension (2014)
- https://extpose.com/ext/47939 - Extpose, "Commute Time (for Rightmove & Zoopla)" extension
- https://commutable.io/guides/rightmove-travel-time-search/ - Commutable guide (404 on fetch; summary via search)
- https://www.zoopla.co.uk/for-sale/property/london/ - Zoopla London listings page (travel time search links)
- https://jitty.com/ - Jitty homepage
- https://jitty.com/post/jittys-new-unified-search - Jitty, unified search
- https://thenegotiator.co.uk/news/proptech/jitty-passes-half-a-million-property-searches-as-ai-reshapes-market/ - The Negotiator, Jitty metrics
- https://techcrunch.com/?p=501332 - TechCrunch, Nestoria WhereCanILive (2009)

AI-native entrants
- https://www.inman.com/2024/06/11/flyhomes-joins-portal-wars-with-launch-of-ai-powered-search/ - Inman, Flyhomes AI launch
- https://www.flyhomes.com/ - Flyhomes homepage (current offering)
- https://www.inman.com/2026/08/05/housemeai-lifestyle-search-us-launch/ - Inman, HouseMe.ai US launch
- https://www.housingwire.com/articles/houseme-ai-us-mls/ - HousingWire, HouseMe.ai

Standalone isochrone and commute tools
- https://www.mapnificent.net/ - Mapnificent
- https://github.com/mapnificent/mapnificent - Mapnificent source
- https://www.transitwiki.org/TransitWiki/index.php/Mapnificent - TransitWiki, Mapnificent
- https://www.mysociety.org/2012/11/10/mapumental-property-extra-insight-for-househunters/ - mySociety, Mapumental Property
- https://en.wikipedia.org/wiki/Mapumental - Wikipedia, Mapumental
- https://www.transitwiki.org/TransitWiki/index.php/CommuteTimeMap - TransitWiki, CommuteTimeMap
- https://www.geoapify.com/isochrone-maps/ - Geoapify, isochrone maps
- https://commutetimemap.com/ - CommuteTimeMap
- https://www.smappen.com/isochrone-tool-for-drawing-amp-analyzing-areas-travel-time/ - Smappen isochrone tool
- https://www.smappen.com/pricing/ - Smappen pricing (tiers without prices)
- https://felt.com/blog/isochrone-map - Felt, 9 isochrone platforms (Mar 2026)
- https://github.com/kaylaajturner/commute-map - commute-map, two-commuter drive-time map
- https://news.ycombinator.com/item?id=36847960 - HN, Show HN transit travel time map (2023)
- https://news.ycombinator.com/item?id=32277313 - HN, isochrone maps discussion (2022)
- https://radiusmapper.com/blog/commute-time-map-find-ideal-commute - RadiusMapper, commute time map guide
- https://apps.apple.com/app/id6748239882 - App Store, Map Across: Multiple Places
- https://apps.apple.com/fi/app/commutecompass/id6468519462 - App Store, CommuteCompass
- https://mapitout.welcome-to-nl.nl/ - Mapitout (Netherlands), minimal content

City matching and vibe maps
- https://www.niche.com/about/methodology/best-places-to-live/ - Niche methodology (blocked; summary via search)
- https://www.areavibes.com/about/ - AreaVibes, about
- https://www.einpresswire.com/article/605087926/dwellics-com-offers-customizable-calculators-to-compare-cities-for-relocation - Dwellics press release (2022)
- https://cityparity.com/blog/teleport-cities-shut-down/ - Cityparity, Teleport Cities shutdown (competitor blog)
- https://nomads.com/ - Nomad List / nomads.com
- https://hoodmaps.com/ - Hoodmaps

General mapping and iBuyers
- https://blog.google/products-and-platforms/products/maps/take-control-your-commute-google-maps/ - Google, Commute tab launch (2018)
- https://www.androidpolice.com/google-maps-create-commute/ - Android Police, set up a commute in Google Maps
- https://docs.cloud.google.com/talent-solution/job-search/v3/docs/commute-search - Google Cloud Talent Solution, implementing commute search in a UI
- https://help.opendoor.com/buying/finding-touring/browse-and-tour - Opendoor Help Center, browsing homes
