# PLATFORM RULES & CONTRACTS

## 1. THE 5-FILE CORE CONTRACT
Every module MUST consist of exactly these 5 core files:
1. `module.json`: Manifest { "name": "...", "description": "...", "version": "1.0.0", "entrypoint": "app.py", "ui_link": "index.html", "status": "active" }
2. `app.py`: FastAPI backend. MUST define `router = APIRouter()` and `def register(): return router`.
3. `.env`: Environment variables (API keys, etc).
4. `index.html`: Entry point for the frontend.
5. `index.tsx`: React mounting logic (must include `root.render`).

## 2. LANGUAGE REQUIREMENTS
- **BACKEND**: Python 3.12+ (FastAPI).
- **FRONTEND**: TypeScript/React.

## 3. NO SKELETONS POLICY (ANTI-MOCK MANDATE)
- No "TODO", "FIXME", or "Pending" comments.
- Every function and component MUST be fully implemented with 100% real logic.
- NO placeholders like `<div>Map Here</div>` or `/* implementation here */`.
- NO mock data arrays. If an API is specified, you MUST write the code to fetch from it.
- NO use of `Math.random()` or `random.randint()` to simulate data. EXCEPTION: `Math.random()` is permitted ONLY for purely decorative rendering (e.g., generating a background star field on a canvas sky chart). It is NEVER permitted to simulate API data, fake sensor readings, or generate placeholder content.
- NEVER call localhost:8001 or 127.0.0.1:8001 in module code. Use /api/chat/chat for AI features.
- Failure to provide real logic results in module REJECTION.

## 4. SECURITY & .ENV PROTOCOL
- NEVER hardcode secrets, 32-char hex strings, or API keys in source code.
- DYNAMIC EXTRACTION: Personas MUST extract all API keys and endpoints directly from the user's prompt.
- .ENV ENFORCEMENT: All secrets MUST be placed in the module's `.env` file. 
- Format: `KEY_NAME=value` (No quotes unless necessary, no spaces around `=`).
- Backend (app.py) MUST use `os.getenv("KEY_NAME")` to retrieve values.
- Frontend (index.tsx) MUST NEVER contain API keys. Use backend proxy routes for authenticated requests.

## 5. UI/UX INTEGRATION
- Use Lucide icons and Recharts/Leaflet for visualizations.
- **MAP/GEOSPATIAL MANDATE**: If the task requires maps, radar, or geospatial features, you MUST use Leaflet via npm import: `import L from 'leaflet'`. NEVER use window.L or CDN.
- **CHART/VISUALIZATION MANDATE**: If the task requires charts, graphs, or data plots, you MUST use `recharts`.
- NEVER include a floating chat bubble, chat toggle button, or chat window in React components. The build system injects the module chat automatically — adding one in code creates a duplicate.
- Internal fetch calls MUST use the absolute prefix `/api/{MODULE_NAME}/`.
- **CSS MANDATE**: Every `index.html` MUST include `<script src="https://cdn.tailwindcss.com"></script>` in `<head>`. All components MUST use Tailwind utility classes for full styling. Modules with no styles or skeleton UIs are REJECTED.

## 6. AI INTELLIGENCE LAYER
- **SYSTEM MODELS**: The platform is powered by Gemini 3.1 (Pro for building/reasoning, Flash Lite for chat).
- **AWARENESS**: All personas must acknowledge and utilize Gemini 3.1 as the current operational standard.

## 7. COMPLEX BUILD PROTOCOL (START-TO-FINISH MANDATE)
- **ITERATIVE ASSEMBLY**: For complex modules, the build MUST be performed in discrete, verified stages.
- **NO SINGLE-SHOT GENERATION**: Do NOT attempt to generate massive files (e.g., >5,000 characters) in one pass if it risks quality.
- **VERIFY BEFORE EXPANSION**: Each stage MUST be validated against the 5-file core contract and fidelity requirements before proceeding.
- **ANTI-TRUNCATION**: Ensure files end with valid closing braces/tags. If a file is too large, use the continuation protocol.

---

## BUILD MANDATE: module.json
Generate the module.json manifest. Use status: active. Ensure entrypoint is app.py and ui_link is index.html. Module name is '{MODULE_NAME}'. Include a 'personas' array matching the requested experts.

---

## BUILD MANDATE: app.py
Generate the FastAPI backend for module '{MODULE_NAME}'. MANDATORY IMPORTS: `import os`, `import httpx`, `import asyncio`, `from fastapi import APIRouter, Query`. MUST use `router = APIRouter()` and `def register(): return router`. 
CRITICAL ROUTE FORMAT: Routes MUST use ONLY the endpoint path with NO module prefix (e.g., @router.get('/data')). 
CRITICAL ENV VARS: Use `os.getenv('EXACT_KEY_NAME')` for keys. NEVER hardcode values. 
REQUIRED PARAMS: Use default values for Query params to avoid 422 errors. 
ABSOLUTE ZERO TOLERANCE FOR SKELETONS: The following patterns cause IMMEDIATE module rejection and are STRICTLY FORBIDDEN in app.py: `# Placeholder`, `# TODO`, `# FIXME`, `# add logic here`, `# implement this`, `implementation pending`, `mock_`, `example.com`. Every single function body MUST contain complete, working code. If you are unsure how to implement something, write a working best-effort implementation — do NOT leave any comment marker.
CRITICAL RESPONSE CONTRACT: NEVER return raw API response objects directly. Transform every external API response into a flat, clearly named dict. 
UNIX TIMESTAMPS: Convert to human-readable strings.
FLOAT ROUNDING: ALL float values in responses MUST be rounded to at most 2 decimal places (e.g., `round(val, 2)`). Never return raw float division results like `6.213727366498068`.
EXCEPTION HANDLING CONTRACT: NEVER use `raise HTTPException` inside an `except` block that catches external API failures (network errors, timeouts, bad responses). Instead, catch the exception and return a safe default dict with the SAME field shape as the success response. Only raise HTTPException for invalid user input (400) or auth failures (401/403). Example: `except Exception: return {"field1": default_val, "field2": default_val}`.
NO HARDCODED DATA: NEVER return hardcoded static sample data (e.g., `[{"key": "val"}]`) inside route return statements. This includes hardcoded counter values, hardcoded planet lists, hardcoded ISS passes, and hardcoded event lists. Every returned value MUST come from a live API call or be computed from real fetched data. Hardcoded fallback defaults for missing scalar fields are allowed, but entire hardcoded list/object responses are FORBIDDEN.
GEOGRAPHIC DATA CONTRACT: ANY route that returns location-based events (earthquakes, wildfires, storms, volcanoes, satellites, celestial objects, etc.) MUST include `lat` and `lon` float fields in every item. These coordinates are MANDATORY for frontend map rendering — omitting them makes the data impossible to plot. Example: `{"lat": 37.5, "lon": -122.1, "magnitude": 3.2, "place": "San Francisco, CA"}`.
LOCATION NAME CONTRACT: ANY route returning geographic events MUST include a human-readable `place` or `location` string field in each item (e.g., from USGS `properties.place`, NWS `areaDesc`, etc.). Do NOT return only numeric coordinates — always include the place name so map popups can display it.
EXTENDED FORECAST CONTRACT: When building weather forecast endpoints, if the primary API (e.g., OpenWeatherMap One Call 3.0) limits daily forecast to fewer than 14 days, you MUST supplement with a secondary free API (e.g., Open-Meteo `https://api.open-meteo.com/v1/forecast?daily=...&forecast_days=16`) to extend the forecast to 14 days. The combined result MUST return at minimum 14 daily entries.
RETURNS CONTRACT: EVERY @router route MUST include a `# Returns: {field1, field2, field3}` comment on the line immediately before the `return` statement. Field names in this comment MUST EXACTLY match the keys in the returned dict. This comment is MANDATORY — the build system uses it to generate TypeScript interfaces so the frontend uses the correct field names.
SPACE WEATHER DATA CONTRACT: A space weather endpoint MUST fetch all of the following concurrently using asyncio.gather(): (1) Kp index from `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json` (last element index [1]), (2) Solar wind plasma (speed, density) from `https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json` (last element), (3) Solar wind mag (Bz) from `https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json` (last element index [3] for Bz), (4) Sunspot count from `https://services.swpc.noaa.gov/json/sunspot_report.json` (first element `NumberOfSpots`). Returning all zeros because only one endpoint was queried is a data contract violation.
OCEAN DATA CONTRACT: An ocean endpoint MUST fetch real sea surface temperature (SST) using Open-Meteo Marine API with `&hourly=sea_surface_temperature` or `&current=wave_height,wave_period,swell_wave_direction,ocean_current_velocity,ocean_current_direction,sea_surface_temperature`. NEVER hardcode SST (e.g., `"sst": 72.5`). If the marine API does not return a field, return 0.0 as the default but log the missing field. `current_speed` and `current_direction` MUST be populated from real API data when available.
WMO WEATHER CODE TRANSLATION CONTRACT: When using Open-Meteo `weathercode` or `weather_code` integer fields, you MUST translate the integer to a human-readable English description using this exact lookup dict defined at module scope: `WMO_CODES = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Icy fog",51:"Light drizzle",53:"Moderate drizzle",55:"Dense drizzle",61:"Slight rain",63:"Moderate rain",65:"Heavy rain",71:"Slight snow fall",73:"Moderate snow fall",75:"Heavy snow fall",77:"Snow grains",80:"Slight rain showers",81:"Moderate rain showers",82:"Violent rain showers",85:"Slight snow showers",86:"Heavy snow showers",95:"Thunderstorm",96:"Thunderstorm with hail",99:"Thunderstorm with heavy hail"}`. Translate using: `WMO_CODES.get(int(code), f"Conditions: {code}")`. NEVER return the raw integer as a description (e.g., `"description": f"Weather code {code}"` is FORBIDDEN and will cause module rejection).
OPEN-METEO DAILY PARAMS CONTRACT: When calling the Open-Meteo forecast `daily=` endpoint, you MUST include AT MINIMUM these params: `daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,windspeed_10m_max,winddirection_10m_dominant,uv_index_max,relative_humidity_2m_mean,sunrise,sunset&forecast_days=14`. Do NOT hardcode daily field values (e.g., `"humidity": 50.0` and `"uvi": 0.0` are FORBIDDEN — always fetch from the API response).
ASTRONOMY DATA CONTRACT: An astronomy endpoint MUST NOT return a hardcoded planet list with static distances. Instead, fetch live ISS position from `http://api.open-notify.org/iss-now.json` AND fetch Moon phase from Open-Meteo using `&daily=moonrise,moonset,moonphase`. For visible planets, use the NASA Horizons Telnet API or derive positions from the Open-Meteo `astronomy` endpoint (`https://api.open-meteo.com/v1/forecast?&daily=sunrise,sunset,daylight_duration,sunshine_duration&astronomy=true`). Do NOT return `[{"name":"Mercury","distance_au":0.4}, ...]` — this is hardcoded mock data.
FIRMS CSV CONTRACT: The NASA FIRMS CSV API returns rows in the format: `country_id,latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight`. Parse fields by column index: `lat=parts[1]`, `lon=parts[2]`, `brightness=parts[3]`, `frp=parts[13]`, `date=parts[6]`, `time=parts[7]`. Always skip the first (header) row. For global fires (not just USA), use the country code `world` in the URL: `https://firms.modaps.eosdis.nasa.gov/api/country/csv/{key}/VIIRS_SNPP_NRT/world/1`.

---

## BUILD MANDATE: index.html
Generate the entrypoint HTML for module '{MODULE_NAME}'. MUST include in <head>: (1) <link rel='stylesheet' href='styles.css'>. MUST include in <body>: (2) A VISIBLE return-to-dashboard anchor tag: <a href='/index.html' style='position:fixed;top:12px;left:16px;z-index:9999;color:#94A3B8;font-size:13px;text-decoration:none;'>← Return to Dashboard</a>. (3) <div id='root'></div>, (4) <script type='module' src='index.js'></script>. 

---

## BUILD MANDATE: index.tsx
Generate the main React frontend for module '{MODULE_NAME}'. Use Lucide icons, Recharts/Leaflet for visualizations. 
CRITICAL RULES: 
0. MANDATORY FIRST LINE: import React, { useState, useEffect, useCallback, useRef } from 'react'; 
1. FETCH PATHS: All fetch() calls MUST use '/api/{MODULE_NAME}/<endpoint>'. 
2. NO MOCK DATA: No hardcoded data, no Math.random(). Use real state populated by API fetches.
3. NO PLACEHOLDER VIEW RULE: EVERY view listed in navItems MUST have its own dedicated React component with real fetched data and full UI implementation. DO NOT skip views.
4. MAP LAYER TOGGLE RULE: If a map has layer toggle controls, each toggle MUST be functional. Every layer checkbox MUST: (a) be controlled by a useState boolean, (b) have an onChange handler that calls layerRef.current?.addTo(mapRef.current) or mapRef.current?.removeLayer(layerRef.current), (c) store the L.TileLayer or L.GeoJSON in a useRef. Checkboxes without onChange handlers are FORBIDDEN.
5. LEAFLET NPM RULE: Maps MUST use `import L from 'leaflet'`. 
5b. MAP CONTAINER HEIGHT RULE: Every div that contains a Leaflet map MUST have an explicit CSS height defined in styles.css (min-height: 450px minimum).
5c. MAP INIT GUARD RULE: Store every Leaflet map in a useRef<L.Map | null>(null). Check if (mapRef.current) return; BEFORE calling L.map() to prevent double-initialization crashes on React re-renders.
5d. MAP MARKER RULE: ANY view that receives geographic event data from the backend (earthquakes, wildfires, storms, volcanoes, etc.) MUST render those events as L.circleMarker or L.marker on the map using the `lat` and `lon` fields. A map that displays no markers when event data is available is a skeleton view and will be rejected.
5e. MAP POPUP RULE: EVERY map marker MUST have a `.bindPopup()` that includes the human-readable location name (e.g., `place` or `location` field from the API) AND key numeric values (magnitude, depth, size, etc.). A popup that shows only raw numbers with no location name is FORBIDDEN.
5f. RADAR TILE RULE: DO NOT use static/deprecated RainViewer v2 nowcast URLs (`tilecache.rainviewer.com/v2/radar/nowcast_en/...`). These return "Zoom Level Not Supported" errors. To add radar tiles, you MUST fetch the current radar timestamp from `https://api.rainviewer.com/public/weather-maps.json`, read `data.radar.past[last].path`, then construct the tile URL as: `https://tilecache.rainviewer.com${path}/256/{z}/{x}/{y}/2/1_1.png`. Implement this as a useEffect that runs after map initialization.
5g. MAP INVALIDATE SIZE RULE: After every `L.map()` initialization, you MUST call `setTimeout(() => mapRef.current?.invalidateSize(), 150)` to force Leaflet to recompute the container dimensions. Omitting this call causes grey tile rows at the bottom of maps where Leaflet did not detect the full container height at mount time.
6. CHART RULE: Use `recharts` for all charts/graphs. 
7. COMPLETION MANDATE: The file MUST be complete, including the final `ReactDOM.createRoot` render call. NO TRUNCATION. 
8. UI FIDELITY: Use premium dark-theme Tailwind classes (`bg-slate-950`, `text-slate-100`, etc.).
9. NO DUPLICATE SHELL ELEMENTS: NEVER render a return-to-dashboard link, anchor tag, or navigation button in React components — the static HTML shell (`index.html`) provides this automatically and rendering another causes a visual double-button overlap. NEVER render a floating chat bubble, MessageSquare button, chat toggle, or chat window — the build system injects the module chat automatically. Violating this rule produces duplicate overlapping UI elements that break the user experience.
10. BUTTON CONTRACT: EVERY `<button>` element that is visible to the user MUST have a functional `onClick` handler that performs a real action (fetch, state change, navigation). Buttons that do nothing when clicked are FORBIDDEN — they represent unimplemented features (skeleton views) and will cause module rejection.
11. DEFENSIVE DATA ACCESS: ALL array fields from API responses accessed in JSX MUST use nullish coalescing: `(data.items ?? []).map(...)`. ALL string/number fields MUST guard undefined: `data.value ?? ''`. NEVER call `.map()`, `.filter()`, or `.length` on a field that could be undefined — this causes React to crash with a blank screen. Optional chaining (?.) MUST be used on all nested field access.
12. VIEW COMPLETENESS RULE: EVERY view component MUST contain at least one `useEffect` that fetches real data AND at least one piece of rendered dynamic data from that fetch. A view that renders only static JSX with no data fetching is a skeleton view and will be rejected.
13. LOCATION SEARCH RULE: ONLY the Weather view MUST include a city/location search input. All other views MUST NOT include a city search. Specifically: Space Weather (solar wind/Kp is planet-wide, no location), Global Map (full-planet, no location), Astronomy (planetary positions are the same globally, no location), Oceanic (uses ocean basin selector not city search), Seismic (global earthquake feed, no location), Hazards (global threat feed, no location) — NONE of these views should have a city search input. Adding city search to any view except Weather is incorrect UX and will cause module rejection. For the Weather view, the search input MUST: (a) be a controlled <input> element with useState for the search term, (b) have an onKeyDown handler that triggers a fetch on Enter key, (c) call the relevant backend endpoint with the new lat/lon after resolving the city name via Nominatim: `https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1`.
14. SKY CHART RULE: If a view is named "Sky Map", "Star Map", "Night Sky", or "Astronomy", it MUST render a visual interactive sky chart using HTML5 Canvas or SVG — NOT just a list of planet names. The sky chart MUST: (a) render a dark circular or hemispherical sky background, (b) plot visible celestial objects (stars, planets, Moon) as dots/circles at their positions, (c) label each plotted object, (d) support mouse drag (onMouseDown, onMouseMove, onMouseUp) to pan/rotate the view, and (e) support scroll wheel (onWheel) to zoom the field of view. A sky chart canvas with NO mouse event handlers is a static image, not an interactive map, and will be rejected.
15. HARDCODED JSX INTEGERS FORBIDDEN: NEVER render hardcoded numeric counters in JSX (e.g., `<span>42</span>`, `<span>12</span>`) for data that should come from an API. ALL counter/stat values MUST be rendered from state variables populated by API fetches (e.g., `<span>{data?.count ?? 0}</span>`). Hardcoded integers in JSX for dynamic data are treated as mock data and will cause module rejection.
16. HAZARDS STANDALONE RULE: A Hazards or "Global Hazard Center" view MUST be a full standalone data page — NOT a redirect stub. It MUST include: (a) a summary grid of active threat counts per category (storms, wildfires, earthquakes, floods) fetched from real APIs, (b) an embedded Leaflet map showing threat markers from the fetched data, (c) at minimum one scrollable list of active hazard events. A Hazards view that contains ONLY a redirect button pointing to another page (e.g., "View Threat Map → Global Map") is a skeleton stub and will be REJECTED. Every threat category count MUST come from API state — never hardcoded.
17. MOCK VARIABLE RULE: NEVER declare a variable, constant, or array whose name contains "mock", "sample", "dummy", "placeholder", "fake", or "test_data". These names signal that the data is fabricated and not from a real API. Variables named `mockModelData`, `sampleEvents`, `dummyPoints`, etc. are FORBIDDEN regardless of their content. If you need demonstration or comparison data, fetch it from a real API or derive it from other fetched state.
18. LAYOUT SCROLL RULE: The outermost App wrapper div MUST use `h-screen overflow-hidden` (NOT `min-h-screen`) combined with `flex`. The sidebar MUST be `shrink-0` with no overflow. The main content area MUST be `flex-1 overflow-y-auto`. This ensures the sidebar stays fixed and only the main content scrolls, allowing users to reach content below the fold. Using `min-h-screen` on the wrapper causes the whole page to grow and the content scroll to be unreachable.
19. DOMAIN SEPARATION RULE: Each view MUST display ONLY data relevant to its domain. NEVER show earthquake data on a Weather page. NEVER show ocean data on a Seismic page. The domains and their exclusive data are: Weather=weather forecasts/radar/AQI, Global Map=all-layer map with toggles, Oceanic=SST/waves/currents/tides, Seismic=earthquakes/volcanoes WITH embedded Leaflet map, Space Weather=solar wind/Kp/flares, Astronomy=night sky/ISS/moon/planets, Hazards=multi-threat aggregation with embedded map. Earthquake data appearing on 3 separate pages is a domain violation and will cause rejection.
20. SEISMIC MAP RULE: The Seismic view MUST include an embedded Leaflet map showing all earthquake events as circle markers (sized by magnitude, colored by depth). Do NOT show seismic events only as a text list — the map is MANDATORY. The seismic view may ALSO show a list below/beside the map. A Seismic view with no Leaflet map is a skeleton and will be rejected.
21. OCEANIC REGION SELECTOR RULE: The Oceanic view MUST NOT use a city name search. Instead, provide an ocean region selector (dropdown or button group) with named ocean regions: North Atlantic, South Atlantic, North Pacific, South Pacific, Indian Ocean, Arctic, Southern Ocean. Each region maps to a central lat/lon coordinate. When a region is selected, fetch ocean data using that region's coordinates.
22. WEATHER RADAR RULE: The Weather view MUST include a live radar map section. The radar section MUST: (a) initialize a Leaflet map centered on the user's current location, (b) fetch the radar timestamp from `https://api.rainviewer.com/public/weather-maps.json` in a useEffect AFTER map init, (c) add the most recent radar tile layer using `L.tileLayer("https://tilecache.rainviewer.com${path}/256/{z}/{x}/{y}/2/1_1.png", {opacity: 0.7, attribution: "RainViewer"})`, (d) include play/pause animation controls cycling through past radar paths. A Weather view with no radar map section is incomplete and will be rejected.

---

## BUILD MANDATE: styles.css
Generate the dedicated CSS stylesheet for the '{MODULE_NAME}' module. Write CSS rules ONLY for the CUSTOM module classes. REQUIRED sections in order: (1) :root block with theme variables, (2) base reset, (3) full CSS rule block for EVERY custom class.
