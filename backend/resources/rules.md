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
OCEAN WAVE IMPERIAL CONVERSION CONTRACT: Open-Meteo Marine API ALWAYS returns `wave_height` and `wave_height_max` in METERS regardless of any unit parameter — there is no `length_unit=imperial` option. You MUST convert to feet before returning: `round(wave_height_meters * 3.28084, 1)`. This applies to both current conditions AND every daily_forecast entry. NEVER return raw meter values labeled as feet. Example: `"wave_height": round(wave_data.get("wave_height", 0) * 3.28084, 1)`.
HOURLY FORECAST TIMEZONE CONTRACT: The OWM One Call 3.0 response root contains `timezone_offset` (integer seconds). Every hourly `dt` field is UTC. After calling `.json()` on the OWM response, read: `timezone_offset = data.get("timezone_offset", 0)`. Apply it to every hourly timestamp before formatting: `local_dt = datetime.utcfromtimestamp(h["dt"] + timezone_offset)`. Then format: `local_dt.strftime("%I:%M %p")`. NEVER format `h["dt"]` directly without adding `timezone_offset` — this shows UTC time and users at UTC-4 see times 4 hours in the future.
SEISMIC USGS LIVE DATA CONTRACT: The /seismic/feed route MUST query USGS with ALL of these parameters: `format=geojson`, `starttime={7_days_ago}` (computed as `(datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")`), `minmagnitude=2.5`, `orderby=time`, `limit=500`. Full URL: `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_7d}&minmagnitude=2.5&orderby=time&limit=500`. Without these params USGS returns an empty or tiny default result set causing the seismic feed to show 0 events.

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
5. LEAFLET NPM RULE: Maps MUST use `import * as L from 'leaflet'` (namespace import). NEVER use `import L from 'leaflet'` (default import) — the default import is not available in ESM bundles and causes "L is not defined" crashes. 
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
14b. CONSTELLATION DRAWING RULE: When drawing constellation lines on a star map canvas, lines MUST follow the actual astronomical stick-figure paths for each constellation — NOT simply connect stars in array order (array order is catalog order, not spatial order). The correct approach is to define an explicit edge list for each constellation: a list of `[starA_index, starB_index]` pairs matching the IAU/H.A. Rey stick figures. For example, Orion MUST connect: belt stars in sequence (Alnitak→Alnilam→Mintaka), shoulders (Betelgeuse→Alnitak, Bellatrix→Mintaka), feet (Alnitak→Saiph, Mintaka→Rigel), and head (Betelgeuse→λ Ori→Bellatrix). NEVER draw lines by iterating `stars.forEach((s, i) => if(i>0) drawLine(stars[i-1], s))` — this creates zig-zags.
15. HARDCODED JSX INTEGERS FORBIDDEN: NEVER render hardcoded numeric counters in JSX (e.g., `<span>42</span>`, `<span>12</span>`) for data that should come from an API. ALL counter/stat values MUST be rendered from state variables populated by API fetches (e.g., `<span>{data?.count ?? 0}</span>`). Hardcoded integers in JSX for dynamic data are treated as mock data and will cause module rejection.
16. HAZARDS STANDALONE RULE: A Hazards or "Global Hazard Center" view MUST be a full standalone data page — NOT a redirect stub. It MUST include: (a) a summary grid of active threat counts per category (storms, wildfires, earthquakes, floods) fetched from real APIs, (b) an embedded Leaflet map showing threat markers from the fetched data, (c) at minimum one scrollable list of active hazard events. A Hazards view that contains ONLY a redirect button pointing to another page (e.g., "View Threat Map → Global Map") is a skeleton stub and will be REJECTED. Every threat category count MUST come from API state — never hardcoded.
17. MOCK VARIABLE RULE: NEVER declare a variable, constant, or array whose name contains "mock", "sample", "dummy", "placeholder", "fake", or "test_data". These names signal that the data is fabricated and not from a real API. Variables named `mockModelData`, `sampleEvents`, `dummyPoints`, etc. are FORBIDDEN regardless of their content. If you need demonstration or comparison data, fetch it from a real API or derive it from other fetched state.
18. LAYOUT SCROLL RULE: The outermost App wrapper div MUST use `h-screen overflow-hidden` (NOT `min-h-screen`) combined with `flex`. The sidebar MUST be `shrink-0` with no overflow. The main content area MUST be `flex-1 overflow-y-auto`. This ensures the sidebar stays fixed and only the main content scrolls, allowing users to reach content below the fold. Using `min-h-screen` on the wrapper causes the whole page to grow and the content scroll to be unreachable.
23. ERROR BOUNDARY MANDATE: ANY app with multiple views MUST define a class-based `ErrorBoundary` component that implements `getDerivedStateFromError` and `componentDidCatch`. Every view component rendered in App MUST be wrapped with `<ErrorBoundary>`. Without this, a single view crashing (e.g. Leaflet map error, undefined data) wipes the ENTIRE page blank. Example: `{activeView === 'weather' && <ErrorBoundary><WeatherView /></ErrorBoundary>}`. The ErrorBoundary should render a user-friendly error card (not a blank screen) and include a Retry button. NEVER omit this — it is required infrastructure, not optional polish.
24. CURRENT CONDITIONS HERO RULE: The Weather view MUST display a full Current Conditions Hero section at the TOP. This section MUST include: large city name + current local time, MASSIVE temperature number (center of screen, 96px+ font), a plain-English "feels like" sentence directly below the temperature (e.g. "Feels like 8°C. Partly cloudy."), today's HIGH and LOW prominently displayed, sunrise and sunset times with a daylight progress bar, and the moon phase with icon. This section is NOT optional and is NOT a detail card. It is the dominant visual element users see first. NEVER skip it or collapse it into a grid card.
25. FORECAST DESCRIPTION RULE: In the 14-Day forecast section, EVERY day card MUST include a plain-English weather description of AT LEAST 10 words. NEVER use only a single-word or two-word code label like "Overcast" or "Light drizzle". Instead, generate a sentence: e.g. "Overcast skies throughout the day with light northwest winds and mild temperatures." Use the WMO code description PLUS wind, precipitation, and UV context to construct a full sentence. A forecast description under 10 words is a contract violation and will cause module rejection.
19. DOMAIN SEPARATION RULE: Each view MUST display ONLY data relevant to its domain. NEVER show earthquake data on a Weather page. NEVER show ocean data on a Seismic page. The domains and their exclusive data are: Weather=weather forecasts/radar/AQI, Global Map=all-layer map with toggles, Oceanic=SST/waves/currents/tides, Seismic=earthquakes/volcanoes WITH embedded Leaflet map, Space Weather=solar wind/Kp/flares, Astronomy=night sky/ISS/moon/planets, Hazards=multi-threat aggregation with embedded map. Earthquake data appearing on 3 separate pages is a domain violation and will cause rejection.
20. SEISMIC MAP RULE: The Seismic view MUST include an embedded Leaflet map showing all earthquake events as circle markers (sized by magnitude, colored by depth). Do NOT show seismic events only as a text list — the map is MANDATORY. The seismic view may ALSO show a list below/beside the map. A Seismic view with no Leaflet map is a skeleton and will be rejected.
21. OCEANIC REGION SELECTOR RULE: The Oceanic view MUST NOT use a city name search. Instead, provide an ocean region selector (dropdown or button group) with named ocean regions: North Atlantic, South Atlantic, North Pacific, South Pacific, Indian Ocean, Arctic, Southern Ocean. Each region maps to a central lat/lon coordinate. When a region is selected, fetch ocean data using that region's coordinates.
22. WEATHER RADAR RULE: The Weather view MUST include a live radar map section. The radar section MUST: (a) initialize a Leaflet map centered on the user's current location, (b) fetch the radar timestamp from `https://api.rainviewer.com/public/weather-maps.json` in a useEffect AFTER map init, (c) add the most recent radar tile layer using `L.tileLayer("https://tilecache.rainviewer.com${path}/256/{z}/{x}/{y}/2/1_1.png", {opacity: 0.7, attribution: "RainViewer"})`, (d) include play/pause animation controls cycling through ALL frames: combine past AND nowcast arrays `const allFrames = [...(data.radar.past ?? []), ...(data.radar.nowcast ?? [])];` — nowcast frames are future predictions and MUST be included so the animation extends beyond "now" into the future, (e) the timeline scrubber MUST label the left side "PAST" and right side "FUTURE" (not "NOW"), (f) the scrubber timestamp display MUST show the actual frame time using `new Date(allFrames[currentIdx]?.time * 1000).toLocaleTimeString()` — NOT a hardcoded label, (g) playback MUST be smooth automatic animation using `setInterval` every 400ms when playing — the play/pause button toggles a boolean and the interval advances the frame index. A Weather view with no radar map, with only past frames, or with no automatic playback interval is incomplete and will be rejected.
26. UNITS RULE: ALL OpenWeatherMap API calls in app.py MUST use `units=imperial` (Fahrenheit, mph, inches). NEVER use `units=metric`. This means all temperature values from OWM are in °F and all wind speeds are in mph. Do NOT rely on defaults — always explicitly append `&units=imperial` to every OWM request URL.
27. TIMESTAMP RULE: ALL timestamp values from OpenWeatherMap API (`sunrise`, `sunset`, `dt`, `moonrise`, `moonset`) are Unix timestamps in SECONDS, NOT milliseconds. The app.py backend MUST convert them to human-readable strings using `datetime.fromtimestamp(ts).strftime('%I:%M %p')` before returning to the frontend. The React frontend MUST NOT call `new Date(ts)` on raw OWM timestamps — this treats them as milliseconds and produces "Invalid Date" or year-1970 results. If the frontend receives a raw Unix timestamp, it MUST multiply by 1000: `new Date(ts * 1000)`.
28. CITY NAME RULE: The `/weather/current` backend route MUST return a human-readable city name in the `place` field, NEVER raw coordinates. Use the OWM `timezone` field (e.g., `"America/New_York"` → display as `"New York"`) OR make a reverse geocoding call to `https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json` and return `data["address"].get("city") or data["address"].get("town") or data["display_name"].split(",")[0]`. Returning `f"Location [{lat}, {lon}]"` or `f"Forecast region [{lat}, {lon}]"` as the place name is FORBIDDEN.
29. HOURLY ROUTE RULE: A Weather module MUST expose a dedicated `/weather/hourly` route that returns at minimum 48 hours of data. This route MUST call OWM One Call 3.0 WITHOUT excluding `hourly` from the `exclude` parameter. The frontend hourly section MUST fetch from `/weather/hourly`, NOT from `/weather/daily`. The backend must return each hour as `{time, temp, feels_like, description, precip_chance, wind_speed}`.
30. NO FILL FALLBACK RULE: NEVER use `Array(n).fill({...})` as a default/fallback value for API state in React. When data is not yet loaded, use an empty array `[]` and render an empty state UI (e.g., a "Loading..." spinner or "No data available" message). `Array(n).fill({key: 0})` creates n copies of the same object with hardcoded zero values, masking data loading failures and showing fake data. This is equivalent to mock data and is FORBIDDEN.
31. LEAFLET GLOBAL FORBIDDEN RULE: NEVER access Leaflet through `window.L`, `(window as any).L`, `(window as Window).L`, or any window-cast variant. Leaflet is ALWAYS bundled via npm and available as `import * as L from 'leaflet'`. Using `window.L` always evaluates to `undefined` in the bundled environment, causing the map to silently never initialize. This is the most common cause of blank map containers. Use ONLY the direct npm import.
32. GEOLOCATION INITIALIZATION RULE: MANDATORY — use `navigator.geolocation.getCurrentPosition()` on mount to obtain the user's location. NEVER hardcode any default coordinates (e.g., 39.8283, -98.5795 or any US geographic center). Every user will see wrong-location data if coordinates are hardcoded. Pattern: `useEffect(() => { navigator.geolocation.getCurrentPosition(pos => { setLat(pos.coords.latitude); setLon(pos.coords.longitude); }, () => { setLocationError(true); }); }, [])`. On denial, show a visible "Location access denied — please search for a city" banner and enable the city search input.
33. LUCIDE NATIVE CONSTRUCTOR ALIAS RULE: When importing from lucide-react, ALWAYS alias any name that shadows a native JavaScript global constructor. Required aliases: `import { Navigation as NavigationIcon, Map as MapIcon } from 'lucide-react'`. Use `<NavigationIcon />` and `<MapIcon />` in JSX — NEVER `<Navigation />` or `<Map />` unaliased. `Navigation` and `Map` are native JS constructors; importing them without `as` causes "Constructor requires 'new'" crashes at runtime that ErrorBoundary catches silently.
34. LOCATION DISPLAY RULE: ANY user-visible subtitle, header, label, or description that references the user's location MUST use the resolved city name — NEVER raw latitude/longitude numbers. Read `city_name` from the weather state (e.g., `weatherData?.city_name || weatherData?.place`). Render as: `Analyzing data for ${cityName || 'your region'}`. Displaying `"Region: 41.43874, -73.21270"` or similar coordinate strings to the user is FORBIDDEN.
35. OCEAN SST TILE RULE: When rendering SST or temperature gradient map layers, use `dark_only_labels` CartoDB tiles — NOT `dark_nolabels` or `light_nolabels`. Full-world no-label tiles cover both land AND ocean at high opacity and completely hide SST color gradients. Use: `https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png` at `zIndex: 500, opacity: 1.0` so only text labels appear above the SST layer.
36. FORECAST DESCRIPTION WRAP RULE: In 14-day forecast cards, NEVER apply `truncate`, `overflow-hidden`, or `text-ellipsis` CSS/Tailwind classes to description text elements. These classes cut descriptions to "Anticipate moderate rain co..." making them unreadable. Description text MUST use `whitespace-normal text-sm` and be allowed to wrap to multiple lines.

---

## BUILD MANDATE: styles.css
Generate the dedicated CSS stylesheet for the '{MODULE_NAME}' module. Write CSS rules ONLY for the CUSTOM module classes. REQUIRED sections in order: (1) :root block with theme variables, (2) base reset, (3) full CSS rule block for EVERY custom class.

---

## MODULE RULES: weather_and_planetary_intelligence

These rules apply ONLY to the weather_and_planetary_intelligence module and are appended to both backend route and frontend component generation prompts at build time.

### BACKEND ROUTE RULES

- NEVER RAISE HTTPEXCEPTION IN EXCEPT MANDATE: NEVER write `raise HTTPException(...)` inside an `except` block that catches external API failures. When a real API call fails (timeout, HTTP error, parse error, any exception), the `except` block MUST return a safe default dict with zeroed/empty values — NEVER raise HTTPException. Raising HTTPException inside an except propagates HTTP 500 to the frontend, causing React components to crash into ErrorBoundary and show blank screens. WRONG: `except Exception as e: raise HTTPException(status_code=500, detail=str(e))`. CORRECT: `except Exception as e: return {"status": "error", "count": 0, "items": [], "message": "Service temporarily unavailable"}`. The returned dict shape MUST match the success response shape so the frontend can safely render default/empty state. Per ROUTE TOP-LEVEL EXCEPTION MANDATE.

- HTTPX TIMEOUT MANDATE: ALL `httpx.AsyncClient()` calls MUST include `timeout=15.0`. Default httpx timeout (5s) causes silent zero-data responses from NOAA SWPC, USGS, and other government APIs that are slow. Pattern: `async with httpx.AsyncClient(timeout=15.0) as client:`. NEVER use `httpx.AsyncClient()` without a timeout argument on any external API call.

- ASTRONOMY API TIMEOUT MANDATE: The `/astronomy/stars` and `/astronomy/skyview` routes MUST use `httpx.AsyncClient(timeout=30.0)` — NOT the standard 15s timeout. The ESA Gaia DR3 TAP service (`gea.esac.esa.int`) and NASA SkyView (`skyview.gsfc.nasa.gov`) regularly take 20–30 seconds to respond. With a 15s timeout the request silently fails and the frontend ErrorBoundary catches it and shows "Data acquisition timed out after 10 seconds". These are the ONLY routes permitted to use a 30s timeout; all other routes stay at 15s.

- OCEAN CURRENT MULTI-POINT MANDATE: The `/ocean/current` route MUST return a `current_vectors` list of at least 6 items, one per major ocean basin sample point. Each item MUST be `{lat: float, lon: float, speed_kt: float, direction_deg: float}`. Fetch real current data for each point concurrently via Open-Meteo Marine API: `https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=ocean_current_velocity,ocean_current_direction`. Required sample points: North Atlantic [40,-40], Gulf Stream [35,-65], Equatorial Pacific [0,-150], South Atlantic [-30,-20], Indian Ocean [-20,75], North Pacific [40,160]. Convert `ocean_current_velocity` from m/s to knots (×1.944). NEVER return a single global `current_direction` float and apply it to all arrows — this renders every arrow pointing the same direction, which is scientifically meaningless and visually wrong. The frontend MUST render each vector as a proportional arrow at its sample lat/lon, rotated to its individual `direction_deg`.

- WATCH ZONES GEOGRAPHIC MANDATE: The [WATCH ZONES] section output from the `/precursor/analysis` synthesis MUST reference actual geographic regions using real place names and approximate coordinate ranges — NOT invented alphanumeric sector codes like "Sector 4-B" or "Zone 9-C". Valid examples: "Kuril-Kamchatka subduction zone (44–52°N, 148–162°E)", "Central Apennines fault system (42–44°N, 13–15°E)", "Northern Chile seismic gap (22–26°S, 68–71°W)". The Dr. Lena Vance synthesis prompt MUST include this instruction: "When writing [WATCH ZONES], reference only real geographic regions, named fault systems, named subduction zones, named volcanic arcs, or named ocean basins with their approximate lat/lon bounding box. NEVER use invented alphanumeric codes like 'Sector 4-B' or 'Zone 9-C'."

- SPACE WEATHER NOAA PARSING MANDATE: NOAA SWPC endpoints require careful data parsing. The K-index JSON at `/products/noaa-planetary-k-index.json` returns a 2D array where row 0 is the header — iterate `data[1:]` and find the LAST row where `row[1]` is not empty/null: `kp_index = float(next((r[1] for r in reversed(data[1:]) if r[1] not in ('', None, '-')), 0.0))`. The plasma JSON at `/products/solar-wind/plasma-7-day.json` has columns: `["time_tag", "density", "speed", "temperature"]` — density is index [1], speed is index [2], temperature is index [3]. CRITICAL: speed is at index [2] NOT [1] — reading index [1] returns plasma density (~4–8 n/cc) not solar wind speed (~300–900 km/s), causing "--" in the UI. Correct: `speed = float(last_row[2]); density = float(last_row[1])`. The mag JSON at `/products/solar-wind/mag-7-day.json` has columns: `["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "lon_gsm", "lat_gsm", "bt"]` — Bz is index [3]. Solar wind speed should be 300–900 km/s when live — if the parsed value is 0.0, the API call likely timed out or returned bad data; log a warning but do NOT silently return 0 as if it were real data.

- CURRENT CONDITIONS DESCRIPTION MANDATE: The `weather/current` route MUST return `description` as a full natural English sentence of at least 15 words built from available data. NEVER return a raw OWM condition string like "Clear sky" or "Overcast clouds". Build the sentence from: condition + temperature + feels_like (if different) + wind speed + wind direction + humidity context. Example: `"Clear skies with temperatures at 59°F, feeling like 59°F, with light south winds at 8 mph and humidity holding at 77%."` Use OWM `weather[0].description` only as the condition seed, then compose the full sentence.

- RADAR FRAME TIMESTAMP EXCEPTION: RainViewer radar frame objects `{time: ..., path: ...}` are NOT from OpenWeatherMap. Their `time` field MUST be returned as a raw Unix integer (seconds) — do NOT convert it to a string. The frontend requires `new Date(frame.time * 1000)` to display real timestamps on the scrubber. Converting RainViewer `time` to a formatted string (e.g. '06:15 AM') makes it unprocessable by the frontend and produces 'INVALID DATE'. In the RETURNS CONTRACT for radar routes, annotate as `time: int_unix_s` so the frontend knows to multiply by 1000.

- RADAR FIELD NAME MANDATE: The radar route MUST return a dict with EXACTLY these two keys: `past_frames` and `nowcast_frames` (not `past`/`nowcast`, not `frames`/`future`). The frontend component is hard-wired to use `radarData.past_frames` and `radarData.nowcast_frames` — any other key names will silently produce empty arrays and a non-animating radar map. Returns contract MUST be: `# Returns: {past_frames: [{time: int_unix_s, path: str}], nowcast_frames: [{time: int_unix_s, path: str}]}`.

- PRECIPITATION CHANCE MANDATE: When converting OWM `pop` (0.0–1.0) to a percentage, multiply by 100 BEFORE returning (e.g. `round(float(h.get('pop', 0.0)) * 100, 2)`). In the RETURNS CONTRACT annotation, ALWAYS type these fields as `float_0_to_100` (e.g. `precip_chance: float_0_to_100`), NOT just `float`. The frontend reads this type annotation and MUST render the value directly as a percentage — it must NEVER multiply by 100 again. Using the ambiguous type `float` causes the frontend to re-multiply, displaying 6500% instead of 65%.

- AURORA OVAL MANDATE: Space weather routes MUST return `aurora_oval_lat: float` — the approximate southernmost geographic latitude of aurora visibility, calculated from Kp index using: `aurora_lat = round(66.5 - (kp_index * 2.8), 1)`. This is NOT a fixed constant — it must be computed from the real Kp data. Return it alongside the other space weather fields. The oval should span 360° of longitude as a series of lat/lon points forming a smooth closed ring at the computed latitude, with a slight southward bulge over North America (shift lat -3° for longitudes 240°–300°) to reflect geomagnetic pole offset.

- FORECAST DESCRIPTION MANDATE: Daily weather forecast items MUST include a `description` field that is a FULL NATURAL ENGLISH SENTENCE of at least 12 words — not a raw WMO code name. Build the sentence from available data fields: combine the condition with precipitation chance, wind speed and direction, temperature trend, and any hazard. Example: 'Periods of light rain through the afternoon with a 74% chance of showers, south winds at 12 mph, and temperatures peaking near 52°F.' The description must give a real forecast narrative — never just 'Overcast' or 'Slight rain showers'.

- OCEAN SST OVERLAY MANDATE: Ocean map routes MUST return the actual OWM API key so the frontend can add SST tile overlays. Return a field `owm_api_key: str` containing the OpenWeatherMap key from `os.getenv('OPEN_WEATHER_MAP_KEY', '')` in every ocean map response. The tile request is client-side so the key must be passed from server to frontend in the JSON response.

- USGS CONSISTENCY MANDATE: ALL earthquake-counting routes (hazard center, seismic page, any summary) MUST use the SAME data source: `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson`. The count returned from any route MUST be `len(features)` from this feed — no artificial caps, no different feeds. Using different USGS feeds for the seismic page (all M2.5+ = 300+) vs hazard center (different feed = 50) creates visible contradictions in the UI.

- ENV VAR API URL SPECIFIC DEFAULTS: These ENV vars have documentation/website URLs as values — always override with the correct callable API default: NOAA_SWPC_URL → `https://services.swpc.noaa.gov` (then append paths like `/products/noaa-planetary-k-index.json`). OPEN_METEO_SUITE_URL → `https://api.open-meteo.com/v1/forecast`. USGS_EARTHQUAKES_URL → `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson` (NOT the fdsnws base). USGS_VOLCANOES_URL → `https://volcanoes.usgs.gov/vsc/api/volcanoApi/volcanoes`. NASA_EXOPLANET_ARCHIVE_URL → `https://exoplanetarchive.ipac.caltech.edu/TAP/sync`. HYCOM_URL → `https://ncss.hycom.org/thredds/ncss/GLBy0.08/expt_93.0/uv3z`. WAVEWATCH_III_URL → `https://marine-api.open-meteo.com/v1/marine`. ENV vars named *_URL for GFS, HRRR, NAM, ECMWF, ICON, JMA etc. point to model documentation pages — use `https://api.open-meteo.com/v1/forecast` as the default and add the appropriate `models=` parameter for multi-model comparison.

- OPEN-METEO MODEL NAMES MANDATE: The AI Lab multi-model comparison route MUST use EXACT Open-Meteo model identifiers in the `models=` parameter. CORRECT names: `ecmwf_ifs04` (NOT `ecmwf_ifs04p`), `gfs_seamless` (for GFS), `icon_seamless` (for ICON/DWD). Wrong model names cause silent API errors and produce empty chart data in the AI Lab view.

- LUCIDE-REACT VERSION CONTRACT: The installed lucide-react is **v0.344.0**. LLMs MUST ONLY use icon names that exist in this version. Valid icons include (but are not limited to): `Beaker`, `CheckCircle2`, `Flower2`, `Gauge`, `GaugeCircle`, `GitCompare`, `GitCompareArrows`, `Settings2`, `BarChart`, `BarChart4`, `Building`, `Building2`, `CameraOff`, `CheckSquare`, `CircleDot`, `CloudLightning`, `CloudOff`, `Code2`, `Delete`, `Disc`, `Edit2`, `Edit3`, `FileCheck`, `FileClock`, `Flashlight`, `Flower`, `FolderOpen`, `Globe2`, `Hourglass`, `ImageOff`, `Keyboard`, `LayoutDashboard`, `LayoutGrid`, `Library`, `LifeBuoy`, `Link2`, `Loader2`, `MapPinOff`, `Maximize2`, `MicOff`, `Minimize2`, `MonitorOff`, `Navigation2`, `Network`, `PauseCircle`, `PhoneOff`, `PlayCircle`, `PlusCircle`, `Settings2`, `Share2`, `ShieldOff`, `SignalHigh`, `SignalLow`, `SignalMedium`, `SlidersHorizontal`, `StarOff`, `SunDim`, `Timer`, `Trash2`, `UserMinus`, `UserX`, `VideoOff`, `XOctagon`, `XSquare`. NEVER import names that are JavaScript built-ins (`Array`, `Object`, `Number`, `String`, `Boolean`, `Date`, `Error`, `Map`, `Set`, `Promise`, `Math`) from lucide-react — they do not exist and will cause esbuild to fail with "No matching export".

- NO MODULE-SPECIFIC HARDCODES IN CORE: System core files (`llm_router.py`, `build_gate.py`, `repair_orchestrator.py`, `build.py`) MUST NEVER contain `if module_name == 'some_specific_module':` gates. All module-specific behavior MUST be expressed as general rules in `rules.md` or as generic patterns that apply to all modules. Hardcoding a module name in a core file couples the system core to a transient module — when the module is deleted, the dead code remains and confuses future maintainers.

- WEATHER WIND HUMIDITY MANDATE: The `/weather/current` route MUST extract and return `wind_speed_mph`, `wind_gust_mph`, `wind_deg`, `humidity`, and `dew_point` from the OWM One Call 3.0 response. OWM returns these under `current.wind_speed` (m/s → multiply by 2.23694 for mph), `current.wind_gust` (m/s → mph), `current.wind_deg` (degrees), `current.humidity` (%), `current.dew_point` (Kelvin → subtract 273.15 → multiply by 9/5 + 32 for °F). NEVER return a /weather/current response that omits these fields — the Wind and Humidity dashboard cards will display '--' if they are absent.

- OWM ENSEMBLE ZERO EXCLUSION MANDATE: When computing an ensemble average temperature from multiple models (OWM + Open-Meteo + WeatherAPI), NEVER include a model's value unconditionally if that model call may have failed. Track whether each API call succeeded: `owm_succeeded = (owm_resp.status_code == 200)`. Build the temps list by filtering: `temps = [t for t in [owm_temp if owm_succeeded else None, om_temp, wapi_temp] if t is not None]`. When OWM fails its fallback value is 0.0 — including 0.0 in `[owm_temp, om_temp]` cuts the displayed temperature in half. Per WEATHER API FAILED-CALL ZERO EXCLUSION MANDATE.

- HOURLY OPEN-METEO FALLBACK MANDATE: The `/weather/hourly` route MUST include an Open-Meteo fallback. If OWM returns no hourly items (`not items`), fetch from `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,windspeed_10m,weathercode&forecast_hours=48&temperature_unit=fahrenheit&windspeed_unit=mph` and parse into the same `{time, temp, feels_like, description, precip_chance, wind_speed}` shape. This ensures hourly data is always available even if OWM fails or returns an empty list. Per HOURLY FORECAST OPEN-METEO FALLBACK MANDATE.

- SPACE WEATHER FLARE TELEMETRY MANDATE: The `/space/current` route MUST concurrently fetch: (1) solar X-ray flare data from `{NOAA_SWPC_URL}/json/goes/primary/xrays-1-day.json` — count entries by class prefix (X=, M=, C=) and return `solar_flares_24h: {"X": int, "M": int, "C": int}`, (2) solar radio flux from `{NOAA_SWPC_URL}/json/f107_cm_flux.json` — extract the most recent `flux` value and return as `radio_flux_sfu: float`. Without these fetches, the Solar Activity panel shows "Awaiting Telemetry" indefinitely. Per SPACE WEATHER COMPLETE TELEMETRY MANDATE.

- SOLAR WIND THRESHOLD PROHIBITION: NEVER apply a numeric minimum threshold to solar wind speed in the `/space/current` route (e.g., `if solar_wind_speed < 50: solar_wind_speed = None`). During quiet-sun conditions, real solar wind is 300–500 km/s — these values are valid and must be returned. Return `None` ONLY when the NOAA API call itself fails or returns no usable data rows. Applying a threshold causes "Sensor Offline" to display during normal quiet-sun operation. Per SOLAR WIND LIVE DATA MANDATE.

- AILAB MODELS RAISE_FOR_STATUS PROHIBITION: The `/ailab/models` route MUST NOT call `raise_for_status()` on the Open-Meteo multi-model request. HRRR covers only CONUS (lat 20–55, lon -130 to -60); for any coordinate outside that range Open-Meteo returns HTTP 400, and `raise_for_status()` throws, causing the chart to show "No model data available". Fix: check `res.status_code == 200` instead. Fall back to global-only models (`gfs_seamless`, `ecmwf_ifs04`, `icon_seamless`) when the coordinate is outside HRRR coverage. The chart MUST render at least 2 model lines whenever Open-Meteo returns 200. Per AI LAB MODEL COMPARISON RESILIENCE MANDATE.

- SEISMIC TIMESTAMP UTC MANDATE: The `/seismic/feed` route MUST format earthquake event times using `datetime.utcfromtimestamp(time_ms / 1000.0)` — NOT `datetime.fromtimestamp()` which silently converts to server local time. Format the result as `'%m/%d %I:%M %p UTC'` so date AND timezone are always visible (e.g., `'04/28 10:58 PM UTC'`). NEVER return seismic event times without a UTC suffix — local-time display creates up to 12-hour ambiguity. Per SEISMIC TIMESTAMP TIMEZONE MANDATE.

- HAZARD FLOOD DATA MANDATE: The `/hazards/` route MUST fetch and return active flood event data. Fetch from GDACS RSS (`https://www.gdacs.org/xml/rss.xml`) and filter for entries where type is `FL`. Parse `<georss:point>` or `<gdacs:latitude>`/`<gdacs:longitude>` tags for coordinates. Return `floods: [{lat: float, lon: float, name: str, severity: str, date: str}]` and `flood_count: int` in the response alongside earthquakes/storms/wildfires. Every flood entry with parseable coordinates MUST appear in the `floods` array — returning only a count with no coordinate array means the frontend cannot render map markers. Per HAZARD FLOOD DATA MANDATE and HAZARD FLOOD MARKERS MANDATE.

- MARINE FORECAST WIND VISIBILITY MANDATE: The `/ocean/current` route's daily marine forecast fetch MUST include `wind_speed_10m_max,visibility_mean` in the Open-Meteo Marine `daily=` parameter. Return each daily_forecast entry with `wind_speed_mph` (multiply `wind_speed_10m_max` by 2.23694) and `visibility_mi` (multiply `visibility_mean` by 0.000621371). Without these fields, the 7-Day Marine Forecast cards show '--' for Wind and Visibility. Per MARINE FORECAST WIND VISIBILITY MANDATE.

- FORECAST DESCRIPTION VERBOSITY MANDATE: Every daily forecast entry's `description` field MUST contain at least 10 words. For Open-Meteo fallback days (beyond OWM's 8-day limit), NEVER return a bare WMO code description alone. Instead build the description by joining multiple fields: `f"Expect {condition} conditions with a {round(precip_pct)}% chance of precipitation, high of {high}°F and low of {low}°F, winds at {round(wind_speed)} mph."` This guarantees 15+ words from real data. NEVER return a single-word or short-phrase description like `"Overcast"` or `"Mixed conditions"` — descriptions under 10 words will cause FORECAST DESCRIPTION LENGTH MANDATE failure. Per FORECAST DESCRIPTION LENGTH MANDATE.

- VOLCANO ALERT LEVEL CASE MANDATE: All USGS volcano alert level values MUST be normalized to lowercase before storage or comparison. The USGS Volcano Hazards API returns capitalized strings: `Warning`, `Watch`, `Advisory`, `Normal`. Any comparison against these values using lowercase literals — `alert_level in ('warning', 'watch', 'advisory')` — will always evaluate False, causing 0 Active Volcanoes to display even during active eruptions (e.g. Kanlaon, Taal, Kilauea). Fix: normalize on extraction — `alert_level = v.get('alert_level', 'Normal').lower()` — then compare: `alert_level in ('warning', 'watch', 'advisory')`. NEVER compare alert levels without `.lower()` normalization. Per VOLCANO ALERT LEVEL CASE MANDATE.

- AI LAB PRECURSOR ROUTE MANDATE: The AI Lab backend domain MUST generate a `/precursor/analysis` route as its PRIMARY deliverable. This route powers Persona Debate (cross-domain synthesis text), Pattern Studio (topology domain_reports), and What-If Scenario (ensemble spread). Without this route the entire AI Lab tab set shows empty/error states. The route MUST: (1) load each persona's `.md` file from `personas/{module_name}/`, (2) use an LLM call (Qwen 14B via `call_llm_async`) to generate a 2–3 sentence domain report per persona based on current weather/seismic/space data, (3) synthesize a convergence score and identify cross-domain anomalies, (4) return `{domain_reports: {PersonaName: str}, convergence_score: float, anomalies: [str], synthesis: str, comparison_points: [{model: str, temp: float}]}`. The AI Lab domain generates minimal routes (~2000 chars) when parallel generation is bottlenecked — the route prompt MUST explicitly state this endpoint is mandatory and MUST be generated first. Per AI LAB PRECURSOR ROUTE MANDATE.

- WEATHER GEOLOCATION ZERO COORD MANDATE: Weather components that use `navigator.geolocation` MUST NEVER trigger a weather API fetch before geolocation resolves. Do NOT call `fetchWeatherData(lat, lon)` with initial state values — if `lat` and `lon` initialize to `0`, this sends a request for coordinates 0°N, 0°E (the Gulf of Guinea off Ghana) and displays "0°F" and "Unknown" city. Correct pattern: `const [coords, setCoords] = useState<{lat:number,lon:number}|null>(null)` — set coords ONLY in the geolocation success callback — gate all fetches: `useEffect(() => { if (coords) fetchWeatherData(coords.lat, coords.lon); }, [coords])`. The geolocation ERROR callback MUST fall back to a real default city (New York: lat=40.7128, lon=-74.0060), NOT lat=0, lon=0. Per WEATHER GEOLOCATION ZERO COORD MANDATE.

- NOAA SWPC PLASMA DATA FORMAT MANDATE: NOAA SWPC JSON endpoints (plasma-7-day.json, mag-7-day.json, noaa-planetary-k-index.json) return 2D ARRAYS, NOT lists of dicts. The first row of every response is a header row: `["time_tag", "density", "speed", "temperature"]`. Data rows follow as positional arrays: `["2024-05-04 12:00:00.000", "4.63", "448.6", "56260.0"]`. Solar wind speed is at index [2], plasma density at [1], temperature at [3]. For mag-7-day.json, IMF Bz is at index [3]. For Kp, the Kp value is at index [1]. NEVER use `.get('speed')` or `.get('kp')` on these rows — they are lists, not dicts, and `.get()` will raise AttributeError or silently return None. Always skip the header row: `data_rows = [r for r in response_json[1:] if r and len(r) > 2 and r[2] not in ('', None, '-')]`. Extract the most recent valid row: `latest = data_rows[-1]`, then `solar_wind_speed = float(latest[2])`. Per NOAA SWPC PLASMA DATA FORMAT MANDATE.

### BACKEND LLM CALL RULES

- CRITICAL `call_llm_async` KEYWORD-ARG MANDATE: ALWAYS call `call_llm_async` using keyword arguments for every parameter after `prompt`. NEVER use positional arguments beyond the first two. The function signature is `call_llm_async(model_name, prompt, system_instruction="", tools=None, max_tokens=65536, persona_name="Integrity Monitor", ...)`. The `tools` parameter sits at position 3 (0-indexed) — directly before `max_tokens` and `persona_name`. LLMs that call `call_llm_async("default", prompt_data, persona_system, "Persona Name")` will silently pass the persona name string into `tools`, crashing EVERY Gemini model with a pydantic validation error and exhausting the entire model fallback chain. CORRECT pattern: `await call_llm_async(model_name="default", prompt=prompt_data, system_instruction=persona_system, persona_name="Persona Name")`. NEVER CALL with positional args beyond `prompt`. The `tools` slot is RESERVED for the system's function-calling tool list — never a persona name, never a string, never anything other than a list of callable functions.

- CRITICAL RECHARTS NULL-GUARD MANDATE: EVERY recharts chart component (`LineChart`, `BarChart`, `AreaChart`, `ComposedChart`) MUST receive a guaranteed non-null array as its `data` prop. ALWAYS initialize chart data state as `[]` (empty array), never `null` or `undefined`. Pattern: `const [chartData, setChartData] = useState<DataType[]>([])`. When the API response is not yet loaded, pass `data={chartData}` — recharts handles empty arrays gracefully. If you pass `data={undefined}` or `data={null}`, recharts throws "Invariant failed" and crashes the entire view. NEVER conditionally render a recharts chart only when data is non-null — always render it with `data={chartData ?? []}` and let it show an empty chart state.

### FRONTEND COMPONENT RULES

- CRITICAL PATTERN STUDIO PERSONA ITERATION MANDATE: Any AI Lab "Pattern Studio" / "Convergence Topology" / "SYNTHESIS CORE" section MUST define `const domainPersonas = [{ name: '...', role: '...' }, ...]` containing ALL module personas (one entry per persona in the module's persona definitions) and render satellite nodes using `domainPersonas.map((persona, i) => { const angle = (i / domainPersonas.length) * 2 * Math.PI; const r = 165; const nx = 250 + Math.cos(angle - Math.PI / 2) * r; const ny = 250 + Math.sin(angle - Math.PI / 2) * r; return (<g key={persona.name} transform={`translate(${nx}, ${ny})`} style={{cursor:'pointer'}} onClick={() => setSelectedNode(persona)}><circle r={22} fill="#1e293b" stroke="#3b82f6" strokeWidth={2}/><text textAnchor="middle" dy={4} fill="#94a3b8" fontSize={9}>{persona.name.split(' ').slice(-1)[0]}</text></g>); })` radially around the SYNTHESIS CORE. NEVER hardcode a single node by persona name. NEVER use `[singlePersona].map(...)`. The variable MUST be named `domainPersonas` and iteration MUST use `domainPersonas.map(...)`. A Pattern Studio showing only 1 satellite node is a build-gate failure.

- CRITICAL LUCIDE IMPORT SYNTAX: Lucide icons MUST be imported as named exports and used directly — `import { Cloud, Sun, Wind } from 'lucide-react'` then `<Cloud />`. NEVER use `import * as Lucide from 'lucide-react'` and then `<Lucide.Cloud />` — this pattern will crash with "Lucide is not defined" if the namespace import is missing. If you use the namespace pattern you MUST include `import * as Lucide from 'lucide-react'` explicitly. Preferred: use named imports only.

- CRITICAL RECHARTS USAGE: Recharts components MUST be used directly from the named imports declared at the top of the file (e.g., `import { LineChart, ResponsiveContainer, ... } from 'recharts'`). NEVER use `(window as any).Recharts` or `window.Recharts` to destructure components at render time — `window.Recharts` does not exist in this environment. NEVER wrap a chart in an IIFE that conditionally accesses `window.Recharts` — this ALWAYS evaluates to the fallback branch and shows "Environment missing Recharts component injection." instead of the chart. NEVER add any fallback text inside a chart container. If the named import is at the top of the file, use it — period.

- CRITICAL HERO SECTION SIZE: The weather hero/current-conditions section MUST use compact padding: `padding: '1.5rem'` max vertically. The hero container max-height: `20rem` (320px). The temperature display font size MUST NOT exceed `5rem`. Remove excessive empty space — the hero should fit comfortably above the fold without scrolling on a 1080p screen.

- CRITICAL RADAR NOWCAST VISIBILITY: If `radarData.nowcast_frames` is empty (length 0), the scrubber MUST NOT show a "FUTURE" right-end label — instead show "No forecast data" inline next to the scrubber. The FUTURE label only appears when `nowcast_frames.length > 0`. The total frame count display MUST show: "Past: N frames | Future: M frames" so the user can see what data is available.

- CRITICAL OCEAN MAP CURRENTS: The ocean map MUST render animated current direction indicators using the `current_vectors` array from the backend response. Each item in `current_vectors` has `{lat, lon, speed_kt, direction_deg}` for a different ocean basin sample point. Draw each arrow at its specific `[lat, lon]` position using `L.polyline` (two-point line segment) with the segment endpoint offset computed from `direction_deg` — NEVER apply a single direction angle to all arrows. Arrow length scales with `speed_kt`. This produces a realistic pattern where arrows point in different directions (Gulf Stream NE, Equatorial westward, gyres clockwise/counterclockwise) rather than a uniform grid of identical arrows. If `current_vectors` is empty or absent, show a "Current data unavailable" overlay — NEVER fall back to a single-direction uniform grid.

- CRITICAL MARINE FORECAST FLEX LAYOUT: The 7-Day Marine Forecast tile strip MUST use a flex-wrap layout so tiles flow naturally beneath the map without forcing a separate scroll zone. Container: `display: flex; flex-wrap: wrap; gap: 0.5rem`. Each day tile uses `flex: 1 1 120px; min-width: 120px`. NEVER use a fixed-column grid (`grid-cols-7`) that locks tiles into a single unbreakable row — on screens where the map + briefing panel takes up the first viewport, a rigid grid pushes all 7 forecast tiles below the fold with no visual affordance that they exist. The flex-wrap layout collapses tiles onto multiple rows at narrow widths and keeps them visible. The forecast section heading "7-Day Marine Forecast" MUST be visible immediately below the map with zero extra scroll required.

- CRITICAL CONSTELLATION ACCURACY: NEVER generate constellation line coordinates using `Math.sin(i)`, `Math.cos(i)`, or any algorithmic/procedural positioning. Constellation lines drawn this way produce random geometric shapes with no relation to real star positions. INSTEAD: hardcode a lookup table of major constellations with their principal stars' equatorial coordinates (RA in hours, Dec in degrees), then project them to canvas using: `x = (ra / 24) * canvasWidth * zoom`, `y = ((90 - dec) / 180) * canvasHeight * zoom`. Minimum required constellations with accurate star positions: Orion (Betelgeuse RA=5.92h Dec=7.4°, Rigel RA=5.24h Dec=-8.2°, Bellatrix RA=5.42h Dec=6.3°, Alnitak RA=5.68h Dec=-1.9°, Alnilam RA=5.60h Dec=-1.2°, Mintaka RA=5.53h Dec=0.3°), Ursa Major (Dubhe RA=11.06h Dec=61.8°, Merak RA=11.03h Dec=56.4°, Phecda RA=11.9h Dec=53.7°, Megrez RA=12.26h Dec=57.0°, Alioth RA=12.9h Dec=55.96°, Mizar RA=13.4h Dec=54.9°, Alkaid RA=13.79h Dec=49.3°), Cassiopeia (Schedar RA=0.67h Dec=56.5°, Caph RA=0.15h Dec=59.1°, Cih RA=0.95h Dec=60.7°, Ruchbah RA=1.43h Dec=60.2°, Segin RA=1.91h Dec=63.7°). Connect stars in the correct stick-figure order for each constellation.

- CRITICAL RADAR FRAMES: The radar backend route returns `{past_frames: [{time: int_unix_s, path: str}, ...], nowcast_frames: [{time: int_unix_s, path: str}, ...]}`. Store this in state as `radarData`. Combine both arrays for animation: `const allFrames = [...(radarData.past_frames ?? []), ...(radarData.nowcast_frames ?? [])];`. The nowcast array contains predicted future frames — always include them. Label the timeline left='PAST', right='FUTURE'. The scrubber timestamp MUST use `new Date(allFrames[currentIdx]?.time * 1000).toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'})` — the `time` field is a raw Unix integer (seconds), NOT a pre-formatted string, so multiply by 1000. NEVER render `allFrames[idx]?.time` directly as a string.

- CRITICAL RADAR SMOOTH PLAYBACK: Radar animation MUST use `setInterval` (or `requestAnimationFrame`) for smooth automatic playback. The play/pause button toggles a boolean state. When playing, advance `currentFrame` every 400ms via `setInterval`. NEVER advance frames only on user scrubber drag — automatic timed playback is required.

- CRITICAL RADAR PLAYBACK INIT: When building a radar scrubber/timeline with `allFrames = [...past_frames, ...nowcast_frames]`, initialize `currentFrameIdx` to the INDEX OF THE LAST PAST FRAME — `radarData.past_frames.length - 1` — so the user sees 'now' immediately on load. NEVER initialize to 0 (which shows the oldest archive frame from hours ago). If nowcast_frames is empty, show 'No forecast available' instead of a misleading FUTURE label.

- CRITICAL AURORA OVAL RENDERING: When rendering the Global Auroral Visibility map, NEVER draw a single `L.circle()` at a fixed Arctic point. Instead: (1) read `spaceData.aurora_oval_lat` from the backend response, (2) generate a polygon ring of ~72 lat/lon points spanning 360° longitude at that latitude, (3) apply a -3° latitude offset for longitudes 240°–300° (North American sector), (4) draw as `L.polygon(points, {color: '#8b5cf6', fillOpacity: 0.2})`. Use color `#ef4444` (red) when `aurora_oval_lat < 55`, `#f97316` (orange) when `< 60`, `#8b5cf6` (purple) otherwise.

- CRITICAL PERCENTAGE FIELDS: Fields typed as `float_0_to_100` in the Routes contract are ALREADY in 0–100 range (e.g. `precip_chance: 65.0` means 65%). NEVER multiply them by 100. Render them directly: `{Math.round(hour.precip_chance)}%`. The same applies to any field named `*_chance`, `*_percent`, `*_pct`, or `*_probability` typed as `float_0_to_100`.

- CRITICAL OCEAN SST LAND MASK: OWM temperature tile layers (e.g., `temp_new`) render as a global color gradient covering BOTH ocean and land — Africa, Europe, and North America all show SST colors on a marine intelligence page. After adding any SST or temperature tile layer, you MUST add a CartoDB land-mask tile layer on top at a higher zIndex to hide the gradient on continental land masses while leaving ocean areas visible. The SST layer MUST be zIndex 300; land mask MUST be zIndex 400; label/marker layers at zIndex 500+. Pattern:
```typescript
// Add SST layer first
const sstLayer = L.tileLayer(
  `https://tile.openweathermap.org/map/temp_new/{z}/{x}/{y}.png?appid=${owmKey}`,
  { opacity: 0.7, zIndex: 300, attribution: '©OpenWeatherMap' }
).addTo(map);
// Then add land mask ON TOP to hide SST gradient on continents
const landMask = L.tileLayer(
  'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
  { attribution: '©CartoDB', zIndex: 400, opacity: 0.82 }
).addTo(map);
```
This preserves ocean SST color data while masking land areas with a neutral CartoDB tile. NEVER render SST tiles without a land mask on an Oceanic Intelligence page.

- CRITICAL OWM MAP TILE KEY: When adding OpenWeatherMap SST/temperature tile layers via `L.tileLayer()`, the API key MUST come from the backend JSON response — NEVER hardcode it. The tile layer MUST be added inside a `useEffect` that depends on the fetched data state — NOT inside the mapCallbackRef (which runs before data arrives). Pattern: `useEffect(() => { if (!mapRef.current || !oData?.owm_api_key) return; const owmKey = oData.owm_api_key; L.tileLayer('https://tile.openweathermap.org/map/temp_new/{z}/{x}/{y}.png?appid=' + owmKey, {opacity: 0.6}).addTo(mapRef.current); }, [oData])`. Available OWM map layers: `temp_new`, `precipitation_new`, `wind_new`, `clouds_new`, `pressure_new`. NEVER add tile layers inside the map init block — oData is not yet available there.

- CRITICAL FORECAST DESCRIPTION QUALITY: Daily forecast descriptions MUST be full, natural English sentences of at least 12 words. NEVER return WMO code names ('Slight rain showers', 'Overcast', 'Fog') as the final description. Build a rich sentence combining condition, temperature trend, precipitation chance, wind context, and any notable risk.

- CRITICAL TOFIXED NUMERIC GUARD: NEVER call `.toFixed()` on any expression that uses `?? 'N/A'`, `?? '--'`, or any string fallback. Example: `(p.distance_au ?? 'N/A').toFixed(3)` — if `p.distance_au` is null/undefined, the nullish coalescing replaces it with the STRING 'N/A', then `.toFixed()` crashes with "toFixed is not a function" and collapses the entire view into the ErrorBoundary. ALWAYS use a typeof guard instead: `(typeof p.distance_au === 'number' ? p.distance_au.toFixed(3) : 'N/A')`. This applies to EVERY numeric display: distance, magnitude, temperature, speed, flux — any field the backend may return as null, undefined, or a string 'N/A'. Optional chaining (`?.toFixed()`) is safe and acceptable — only the `?? 'string'` pattern is forbidden. Per TOFIXED NUMERIC GUARD MANDATE.

- CRITICAL SPACE WEATHER RESILIENCE: Space weather components MUST handle partial data gracefully. NEVER show a full-page error banner if the API returns an error — show a degraded state with zeroed metrics and a small inline warning. Always set state even on failure: `try { const res = await fetch(...); const data = res.ok ? await res.json() : {}; setSpaceData(data); } catch(e) { setSpaceData({}) }`.

- CRITICAL HAZARD/SEISMIC DATA CONSISTENCY: The Hazard Center page and the Seismic page MUST use the SAME USGS earthquake data source: `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson`. Both must display the same untruncated 7-day M2.5+ count. Do NOT use different feeds on different pages — this creates visible contradictions.

- CRITICAL STAR MAP — REAL STAR DATA (ESA Gaia DR3): The Planetary & Star Map view MUST fetch real star data from the ESA Gaia TAP service — NO procedural/random star placement. Backend route `/astronomy/stars` MUST query: `https://gea.esac.esa.int/tap-server/tap/sync?REQUEST=doQuery&LANG=ADQL&FORMAT=json&QUERY=SELECT+TOP+2000+ra,dec,phot_g_mean_mag,bp_rp+FROM+gaiadr3.gaia_source+WHERE+phot_g_mean_mag+%3C+6.5+ORDER+BY+phot_g_mean_mag+ASC`. Return array of `{ra: float, dec: float, mag: float, color_index: float}`. The frontend MUST plot these stars on a canvas at positions computed from real RA/Dec: `x = ((ra / 360) * canvasWidth + panX) * zoom`, `y = (((90 - dec) / 180) * canvasHeight + panY) * zoom`. Star radius scales inversely with magnitude: `r = Math.max(0.5, 3.5 - mag * 0.4)`. Star color from bp_rp index: bp_rp < 0.5 → `#cce0ff` (blue-white), 0.5–1.2 → `#fff5e0` (white-yellow), > 1.2 → `#ffaa55` (orange-red). NEVER place stars using Math.random() or Math.sin/cos — this produces a fake sky.

- CRITICAL STAR MAP — SKYVIEW BACKGROUND TILES: The star map canvas background MUST use NASA SkyView DSS2 Red survey tiles to show real photographic sky instead of a black void. The backend route `/astronomy/skyview` MUST: (1) construct the SkyView URL: `https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl?Survey={survey}&Position={ra},{dec}&Size={fov}&Pixels=512&Return=PNG&Sampler=LI` where fov defaults to `60.0`, survey defaults to `"DSS2 Red"`. (2) Fetch the PNG bytes with httpx and return them as a BASE64 DATA URL — `data:image/png;base64,{base64_string}` — in a field named `image_url`. NEVER return an external HTTPS URL as `image_url` — the browser blocks `ctx.drawImage()` on cross-origin URLs causing a silent CORS canvas taint error where the image never appears. Backend pattern: `import base64 as _b64; resp = await client.get(skyview_url); img_b64 = _b64.b64encode(resp.content).decode(); return {"image_url": f"data:image/png;base64,{img_b64}"}`. The frontend MUST render this data URL as the canvas background layer via `const img = new Image(); img.src = data.image_url; img.onload = () => ctx.drawImage(img, 0, 0, canvas.width, canvas.height)`, then draw Gaia stars and constellation lines on top. When the user pans/zooms, refetch the SkyView tile at the new center. If SkyView returns an error (non-200 status or empty content), fall back to a dark gradient background and show "Live imagery unavailable" — NEVER crash.

- CRITICAL STAR MAP — PLANET POSITIONS: The star map MUST show real current planet positions (not placeholder dots). The backend route `/astronomy/planets` MUST use the `ephem` Python library (or equivalent astronomical calculation) to compute current RA/Dec for: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune. If `ephem` is not available, compute approximate positions using VSOP87 simplified formulas or the astropy-style mean anomaly approach. Return array: `{name: str, ra: float, dec: float, magnitude: float, symbol: str}`. Each planet MUST be plotted on the star map canvas at its real RA/Dec position using the same projection as stars, with a colored disc (size proportional to magnitude) and label. NEVER place planets at hardcoded fixed positions.

- CRITICAL STAR MAP — ISS LIVE TRACK: The star map MUST show the current ISS ground track. Fetch live ISS position from `http://api.open-notify.org/iss-now.json` (no API key required). Plot ISS as a moving icon on the canvas at real lat/lon converted to canvas coords. Refresh every 5 seconds. The ISS ground track overlay must use the GEOGRAPHIC map projection (lat/lon), not the RA/Dec sky projection — render it as a separate Leaflet `L.marker` overlay on a world map panel below the sky canvas, or as an inset map. NEVER mix the celestial sphere projection with geographic lat/lon on the same canvas.

- CRITICAL WEATHER PERSONA-DRIVEN SYNTHESIS — ARCHITECTURE MANDATE: Weather routes are NOT API proxies. Each route follows a 3-stage pipeline: (1) FETCH raw data from ALL sources concurrently via `asyncio.gather()`, (2) CALL the domain persona LLM to synthesize the raw data into an authoritative analysis, (3) RETURN both computed fields and persona narrative in the JSON response. The persona LLM is called using `call_llm_async()` from `core.llm_client`. The persona system instruction is loaded from `backend/personas/weather_and_planetary_intelligence/{persona_file}.md` at runtime. This is the foundational architecture — every weather/ocean/seismic/space route MUST use it. PERSONA ASSIGNMENTS: `/weather/current` and `/weather/daily` → Dr. Aeris Caldwell (`dr_aeris_caldwell.md`). `/weather/alerts` severe detection → Gale Hawthorne (`gale_hawthorne.md`). `/ocean/current` → Marin Kai (`marin_kai.md`). `/seismic/feed` narrative → Dr. Lena Vance (`dr_lena_vance.md`). `/space/current` → Julian Rourke (`julian_rourke.md`). `/astronomy/planets` → Bonnie Kensington (`bonnie_kensington.md`). IMPLEMENTATION PATTERN for app.py routes:
```python
import os
from pathlib import Path
from core.llm_client import call_llm_async

async def _load_persona(filename: str) -> str:
    persona_path = Path(__file__).parent.parent.parent / "personas" / "weather_and_planetary_intelligence" / filename
    return persona_path.read_text(encoding="utf-8") if persona_path.exists() else ""

@router.get("/weather/current")
async def weather_current(lat: float, lon: float):
    persona_system = await _load_persona("dr_aeris_caldwell.md")
    owm_task = fetch_owm_current(lat, lon)
    gfs_task = fetch_openmeteo(lat, lon, models="gfs_seamless")
    ecmwf_task = fetch_openmeteo(lat, lon, models="ecmwf_ifs04")
    hrrr_task = fetch_openmeteo(lat, lon, models="hrrr")
    wapi_task = fetch_weatherapi(lat, lon)
    owm, gfs, ecmwf, hrrr, wapi = await asyncio.gather(owm_task, gfs_task, ecmwf_task, hrrr_task, wapi_task, return_exceptions=True)
    # Compute ensemble numerics
    temps = [t for t in [owm.get("temp"), gfs.get("temp"), ecmwf.get("temp"), hrrr.get("temp") if not isinstance(hrrr, Exception) else None, wapi.get("temp")] if t is not None]
    ensemble_temp = round(sum(temps)/len(temps), 1) if temps else 0.0
    spread = round(max(temps)-min(temps), 1) if len(temps) > 1 else 0.0
    confidence = "High" if spread < 3 else "Moderate" if spread < 7 else "Low"
    # Build raw data block for persona
    data_block = f"""RAW MULTI-MODEL DATA (all values imperial units):
OWM One Call 3.0: temp={owm.get("temp")}F, feels_like={owm.get("feels_like")}F, humidity={owm.get("humidity")}%, wind={owm.get("wind_speed")}mph dir={owm.get("wind_deg")}deg, condition={owm.get("condition")}, visibility={owm.get("visibility")}mi
WeatherAPI.com: temp={wapi.get("temp")}F, condition={wapi.get("condition")}, wind={wapi.get("wind")}mph, gusts={wapi.get("gusts")}mph
Open-Meteo GFS: temp={gfs.get("temp")}F, precip_prob={gfs.get("precip_prob")}%, cloud_cover={gfs.get("cloud_cover")}%
Open-Meteo ECMWF: temp={ecmwf.get("temp")}F, precip_prob={ecmwf.get("precip_prob")}%
Open-Meteo HRRR: temp={hrrr.get("temp") if not isinstance(hrrr, Exception) else "N/A (out of range)"}F
Ensemble: temp={ensemble_temp}F, spread={spread}F, confidence={confidence}, models_used={len(temps)}
Location: lat={lat}, lon={lon}
UTC time: {datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}"""
    llm_result = await call_llm_async(
        model_name="default",
        prompt=f"{data_block}\n\nGenerate your structured meteorological analysis for current conditions. Output: one full English sentence (15+ words) for 'description', then sections Radar/Dynamics/Hazards/Confidence.",
        system_instruction=persona_system,
        persona_name="Dr. Aeris Caldwell"
    )
    synthesis = llm_result.get("text", "").strip()
    # Extract first sentence as description, keep full synthesis separately
    description = synthesis.split("\n")[0].strip() if synthesis else f"{confidence} confidence ensemble of {len(temps)} models: {ensemble_temp}F."
    return {"temp": ensemble_temp, "feels_like": owm.get("feels_like", ensemble_temp), "description": description, "persona_analysis": synthesis, "confidence": confidence, "model_count": len(temps), "spread": spread, ...}
```
NEVER skip the LLM call for weather/ocean/seismic/space routes. NEVER return raw API output directly without persona synthesis. The persona LLM call IS the intelligence layer — it is not optional.

- CRITICAL CROSS-DOMAIN PRECURSOR COLLABORATION — ALL 7 PERSONAS MUST WORK TOGETHER: The 7 personas in this module are NOT independent silos. They form a scientific team that continuously cross-analyzes each other's domain data to detect precursor signals for earthquakes, volcanic events, tsunami risk, severe weather outbreaks, and geomagnetic storms. Any "Generate Narrative" or "Precursor Analysis" button MUST trigger a MULTI-STAGE PARALLEL persona pipeline — NOT a single LLM call. STAGE 1 — PARALLEL DOMAIN REPORTS (all 7 run concurrently via `asyncio.gather()`): (A) Dr. Aeris Caldwell fetches atmospheric pressure anomalies, rapid pressure drops, ionospheric disturbances via OWM + Open-Meteo and reports "Atmospheric Precursor Signals". (B) Terra Santos fetches soil moisture anomalies, land surface temperature deviations from NOAA/NASA and reports "Surface & Subsurface Signals". (C) Gale Hawthorne analyzes severe storm clusters and mesoscale convective systems from OWM alerts and reports "Severe Weather Coupling Signals". (D) Marin Kai fetches SST anomalies, ENSO state, ocean heat content from Open-Meteo marine and HYCOM and reports "Oceanic Coupling Signals". (E) Dr. Lena Vance fetches all M2.5+ USGS events for the past 7 days, swarm patterns, depth distributions, volcanic alert levels and reports "Seismic Baseline & Anomaly Assessment". (F) Julian Rourke fetches NOAA SWPC Kp index, solar wind speed, IMF Bz, recent CME/X-flare reports and reports "Geomagnetic & Ionospheric Loading". (G) Bonnie Kensington computes current planetary positions (tidal forcing on lithosphere — lunar/solar perigee, syzygy geometry) and reports "Gravitational Tidal Stress". STAGE 2 — SYNTHESIS (Dr. Lena Vance coordinates): All 7 domain reports are concatenated into a single context block and sent to Dr. Lena Vance for cross-domain synthesis. Her synthesis prompt: "You have received domain reports from 6 specialist colleagues. Your job: identify CONVERGENT PRECURSOR SIGNALS — cases where multiple domains simultaneously show anomalies that historically correlate with elevated seismic, volcanic, or severe weather risk. Score each convergent signal 1-10. Output format: [CONVERGENT SIGNALS], [RISK ASSESSMENT], [72H OUTLOOK], [CONFIDENCE], [WATCH ZONES]." IMPLEMENTATION PATTERN:
```python
@router.get("/precursor/analysis")
async def precursor_analysis():
    # Stage 1: parallel domain fetches + individual persona LLM calls
    async def run_persona(persona_file, persona_name, domain_data_fn, prompt_suffix):
        system = await _load_persona(persona_file)
        data = await domain_data_fn()
        result = await call_llm_async(model_name="default", prompt=f"{data}\n\n{prompt_suffix}", system_instruction=system, persona_name=persona_name)
        return persona_name, result.get("text", "")
    reports = await asyncio.gather(
        run_persona("dr_aeris_caldwell.md", "Dr. Aeris Caldwell", fetch_atmospheric_data, "Analyze for atmospheric precursor signals to seismic or volcanic events. Report: pressure anomalies, rapid gradients, ionospheric signatures."),
        run_persona("terra_santos.md", "Terra Santos", fetch_surface_data, "Analyze surface and subsurface signals. Report: soil moisture anomalies, land surface temperature deviations, hydrological stress."),
        run_persona("gale_hawthorne.md", "Gale Hawthorne", fetch_severe_weather_data, "Identify severe weather coupling signals that may reflect or amplify seismic stress. Report: mesoscale convective systems, pressure wave coupling."),
        run_persona("marin_kai.md", "Marin Kai", fetch_ocean_data, "Analyze ocean coupling signals. Report: SST anomalies, ENSO state, ocean heat content gradients, coastal upwelling anomalies."),
        run_persona("dr_lena_vance.md", "Dr. Lena Vance", fetch_seismic_data, "Establish seismic baseline. Report: swarm patterns, depth distribution, foreshock sequences, volcanic alert changes."),
        run_persona("julian_rourke.md", "Julian Rourke", fetch_space_weather_data, "Report geomagnetic loading. Kp index, solar wind pressure, IMF Bz southward turns, recent X-flares or CMEs. Assess lithospheric stress from geomagnetic forcing."),
        run_persona("bonnie_kensington.md", "Bonnie Kensington", fetch_planetary_data, "Compute tidal forcing geometry: lunar phase, perigee proximity, syzygy alignment. Quantify combined lunar-solar gravitational tidal stress on tectonic plates in active zones."),
        return_exceptions=True
    )
    # Stage 2: synthesis by Dr. Lena Vance
    domain_block = "\n\n".join([f"=== {name} ===\n{report}" for name, report in reports if not isinstance(report, Exception)])
    lena_system = await _load_persona("dr_lena_vance.md")
    synthesis = await call_llm_async(
        model_name="default",
        prompt=f"DOMAIN REPORTS FROM YOUR TEAM:\n\n{domain_block}\n\nIdentify convergent precursor signals across all domains. Score risk 1-10. Output: [CONVERGENT SIGNALS], [RISK ASSESSMENT], [72H OUTLOOK], [CONFIDENCE], [WATCH ZONES].",
        system_instruction=lena_system,
        persona_name="Dr. Lena Vance"
    )
    return {"domain_reports": dict(reports), "synthesis": synthesis.get("text", ""), "timestamp": datetime.utcnow().isoformat()}
```
This route MUST be exposed at `/precursor/analysis`. The frontend "Generate 72h Narrative" and "Generate Risk Narrative" buttons MUST call this endpoint — NOT a single-persona LLM call. NEVER call only one persona for a risk narrative. NEVER generate a risk narrative from seismic data alone — the whole point of this system is multi-domain convergence.

- CRITICAL RADAR SCRUBBER INIT — SHOW CURRENT TIME: The radar scrubber MUST initialize `currentFrameIdx` to `radarData.past_frames.length - 1` so it shows the most recent past frame (closest to NOW) on load, not the oldest archive frame. The timestamp display MUST show the real time of that frame using `new Date(frame.time * 1000).toLocaleTimeString()`. If nowcast_frames.length > 0, the scrubber range MUST extend into the future (up to 2 hours ahead) and the FUTURE label MUST appear. The display format: left label "PAST", right label "FUTURE" when nowcast available or "No forecast data" when not. This ensures the user immediately sees current radar on load, not 2-hour-old data.

- WEATHER CONDITION ICON MANDATE: index.tsx MUST implement a `function getConditionIcon(description: string): React.ReactNode` that maps description substrings to lucide-react icons. Minimum mapping: `description.includes('thunder') || description.includes('storm')` → `<CloudLightning />`, `description.includes('rain') || description.includes('drizzle')` → `<CloudRain />`, `description.includes('snow')` → `<Cloud />`, `description.includes('fog') || description.includes('mist')` → `<Eye />`, `description.includes('clear') || description.includes('sunny')` → `<Sun />`, default → `<Cloud />`. Call this function inside EVERY hourly forecast card and every 14-day forecast card JSX to render a weather icon alongside the temperature. Forecast cards that show only text descriptions with no icons will be rejected. Per WEATHER FORECAST CONDITION ICON MANDATE.

- FORECAST DAY/NIGHT EXPANSION MANDATE: The 14-day forecast cards MUST show a day/night split when expanded. The backend `/weather/daily` route MUST return `day_temp`, `night_temp`, `day_description`, and `night_description` per daily entry. When a day card is clicked/expanded, the frontend MUST reveal TWO labeled sub-panels side-by-side: (1) 'Daytime' with Sun icon showing `day_temp`, `day_description`, UV index, wind, and sunrise, (2) 'Overnight' with Moon icon showing `night_temp`, `night_description`, humidity, and sunset. A single combined expanded panel with no day/night split will be rejected. Per FORECAST DAY/NIGHT EXPANSION MANDATE.

- SEISMIC DATA SHAPE CONTRACT: The Seismic view MUST read `data.earthquakes` (NOT `data.features`) from the `/seismic/feed` response. The backend MUST return `{earthquakes: [{lat, lon, magnitude, depth_km, place, time_str}], count: N}` — NOT raw USGS GeoJSON with a `features` array. The frontend stat card displays `data.count`; map markers iterate `data.earthquakes`. Reading `data.features` produces zero markers because the transformed backend response uses the `earthquakes` key. Per SEISMIC DATA SHAPE CONTRACT.

- OCEANIC WAVE SWELL BINDING MANDATE: The Oceanic Intelligence view MUST read and display `wave_height`, `wave_period`, `swell_height`, `swell_direction_label`, `sea_surface_temp`, `current_speed`, and `current_direction` from the `/ocean/current` response. The backend MUST fetch these from Open-Meteo Marine API: `https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_period,swell_wave_height,swell_wave_direction,ocean_current_velocity,ocean_current_direction,sea_surface_temperature`. NEVER render '--' for wave or swell fields when the route returns 200. Per OCEANIC WAVE DATA MANDATE.

- HAZARD FLOOD MAP MARKERS MANDATE: When the Hazard Center receives `floods` array from the backend (with lat/lon per entry), EVERY flood entry MUST be rendered as `L.circle([lat, lon], {color: '#3b82f6', fillOpacity: 0.4, radius: 50000})` on a dedicated togglable Floods map layer with a popup showing location name, severity, and date. A flood count card showing "7 Flood Warnings" with zero corresponding map markers is a build failure. Per HAZARD FLOOD MARKERS MANDATE.

- RADAR FRAME USEREF MANDATE: Radar frame data arrays (`allFrames`, `radarFrames`, `past_frames`, `nowcast_frames`) MUST be stored in a `useRef` — NOT a plain `let` variable inside a useEffect. A `let allFrames = []` declared inside a useEffect is NOT accessible in `setInterval` callbacks or `onClick` handlers defined elsewhere, causing "allFrames is not defined" ReferenceError when the user clicks Play. Pattern: `const allFramesRef = useRef<any[]>([]); ... allFramesRef.current = frames; ... allFramesRef.current[currentIdx]`. Per RADAR FRAME VARIABLE SCOPE MANDATE.

- AI LAB MODELS AUTOLOAD MANDATE: The AI Lab view MUST fetch `/ailab/models?lat={lat}&lon={lon}` inside a `useEffect(() => { fetchModels(); }, [lat, lon])` so the Ensemble Forecast Divergence chart populates immediately on mount — NOT only when the user moves a slider. The chart data state MUST be populated from `data.comparison_points` (NOT `data.models` or `data.data`). Feed this array directly to `<LineChart data={comparisonPoints}>` where each point is `{hour_label, gfs_temp, ecmwf_temp, icon_temp}`. Per AI LAB MODEL COMPARISON AUTOLOAD MANDATE.

- PATTERN STUDIO CANVAS OVERFLOW MANDATE: The Pattern Studio topology container MUST set `style={{minHeight:'500px', overflow:'visible'}}` (or equivalent Tailwind `min-h-[500px] overflow-visible`). With 7 personas arranged radially at radius 165, bottom nodes are clipped when the container is less than 450px tall. NEVER use `overflow-hidden` on the topology container. Per PATTERN STUDIO CANVAS OVERFLOW MANDATE.

- PATTERN STUDIO NO HOVER SCALE MANDATE: Topology satellite nodes MUST NOT use CSS scale transforms on hover (`hover:scale-*`, `transition-transform`, `scale-*` on mouse events). Scaling an absolutely-positioned node shifts its visual center, triggering a mouseLeave immediately and creating a jittering oscillation loop. Use border-color or fill changes on hover instead — no scale or transform. Per PATTERN STUDIO NODE HOVER STABILITY MANDATE.

- AI LAB PERSONA DEBATE DATA BINDING MANDATE: Both the Persona Debate tab and the Pattern Studio topology MUST share a SINGLE `const [precursorData, setPrecursorData] = useState(null)` state populated by ONE fetch to `/precursor/analysis`. NEVER create separate `debateData`/`setDebateData` state that fetches the same endpoint — this causes desync where one tab loads and the other shows 'Awaiting domain data...' indefinitely. Both tabs read `precursorData?.domain_reports?.[personaName]`. Per AI LAB PERSONA DEBATE DATA BINDING MANDATE.

---

## SYSTEM-WIDE RULES (Apply to ALL modules)

### ROOT CAUSE: PERSONAS WORKING IN ISOLATION — NO CROSS-DOMAIN CONVERGENCE ANALYSIS
Domain personas (meteorologist, geohazard, ocean, space weather, earth systems, severe weather, astronomy) each analyze their own data independently and never share findings. This misses the entire value of the system: cross-domain precursor detection. A solar CME stressing the magnetosphere, combined with a lunar perigee increasing tidal loading, combined with a deepening low-pressure system, combined with an oceanic SST anomaly — is a convergent multi-domain signal that no single specialist would catch alone.

CROSS-DOMAIN CONVERGENCE RULE: Any "Generate Narrative", "Precursor Analysis", "Risk Narrative", or "72h Outlook" action MUST execute a 2-stage multi-persona pipeline: (1) All domain personas run in parallel via `asyncio.gather()` — each fetches its own domain data and calls `call_llm_async()` to produce a domain report focused on precursor signals within their discipline. (2) Dr. Lena Vance (Geohazard Specialist) receives ALL 7 domain reports concatenated and synthesizes convergent signals, risk score (1-10), 72h outlook, and geographic watch zones. The final output surfaces which domains are showing simultaneous anomalies — the convergence count is the key risk amplifier. DOMAIN-TO-PRECURSOR MAPPINGS that each persona must be prompted for: Aeris Caldwell → ionospheric TEC anomalies, rapid pressure gradients, infrasound signatures. Terra Santos → groundwater level changes, soil gas radon anomalies, land subsidence/uplift. Gale Hawthorne → mesoscale pressure wave trains, bow echoes in seismically active zones. Marin Kai → anomalous SST gradients near subduction zones, tsunami-signature ocean bottom pressure. Julian Rourke → southward IMF Bz (geomagnetic coupling to lithosphere), X-flare EMP stress on fault systems. Bonnie Kensington → lunar perigee + syzygy geometry, tidal strain maxima on major fault systems. Dr. Lena Vance → swarm acceleration, migration velocity, b-value drop (foreshock detection).

### ROOT CAUSE: WEATHER/DOMAIN ROUTES ARE PLAIN API PROXIES — NO PERSONA INTELLIGENCE
The build AI generates weather routes that simply call one API and return its JSON. This violates the core system design: domain personas (Dr. Aeris Caldwell, Marin Kai, Dr. Lena Vance, etc.) exist specifically to synthesize multi-source data using LLM intelligence, not to be decoration.

PERSONA LLM SYNTHESIS RULE: Every domain route (weather/current, weather/daily, ocean/current, seismic/feed, space/current, astronomy/planets) MUST follow the 3-stage pipeline: (1) FETCH raw data from ALL available data sources concurrently, (2) CALL `call_llm_async()` from `core.llm_client` with the domain persona's `.md` file as `system_instruction` and the raw multi-source data as `prompt` context, (3) RETURN a JSON that includes both numeric computed fields (ensemble temp, spread, confidence) AND the persona's `persona_analysis` text (the full LLM output). Load persona system instructions at runtime using: `Path(__file__).parent.parent.parent / "personas" / "{module_name}" / "{persona_file}.md"`. Never skip or mock the LLM call. Never return a single raw API's output as the route response. The intelligence layer is not optional — it IS the product.

### ROOT CAUSE: APP NOT FULLSCREEN
The build system auto-injects a CSS fix (`#root > * { width: 100%; min-height: 0; }`) into every module's `index.html`. However, to avoid relying solely on the CSS fix, all generated App root divs MUST include `w-full` explicitly.

APP ROOT DIV FULLSCREEN RULE: The outermost `<div>` returned by the root `App` component MUST include `w-full` in its className alongside `flex` and `h-screen`. Without `w-full`, the div only takes its natural content width inside the `#root` flex container, leaving a dead zone on the right side of the screen. CORRECT: `<div className="flex h-screen w-full overflow-hidden ...">`. WRONG: `<div className="flex h-screen overflow-hidden ...">`. This is one of the most common and visually obvious layout bugs.

### ROOT CAUSE: API KEY SECURITY
NEVER return any `os.getenv()` API key, token, or secret directly in a route response dict, except for the `owm_api_key` field (which is an explicitly documented exception required for OWM client-side tile layers). Specifically: `firms_key`, `nasa_key`, `airnow_key`, `weather_api_key`, and similar secret variables MUST NEVER appear in any return statement. The validation system scans for this and will FAIL the module if detected. If the frontend needs an authenticated API, proxy it through the backend — do not expose the key.

### ROOT CAUSE: OCEAN COMPONENT CRASH AT DEFAULT LOCATION
The default coordinates for the Oceanic view MUST NOT be `lat=0.0, lon=0.0` (the origin point in the Gulf of Guinea). This coordinate is technically in the ocean but hits the marine API with a location that may return unexpected or zero data, causing downstream component crashes from null checks.

OCEANIC DEFAULT LOCATION RULE: The Oceanic view MUST initialize with a real named ocean region. Use the OCEANIC REGION SELECTOR RULE (rule 21): provide a dropdown with named regions (North Atlantic, South Pacific, etc.) each mapped to a valid central lat/lon. The initial region MUST be "North Atlantic" at `lat=40.0, lon=-40.0`, NOT `lat=0, lon=0`.

### ROOT CAUSE: INCONSISTENT EARTHQUAKE COUNTS ACROSS PAGES
When multiple pages fetch earthquake data from USGS (e.g., Seismic page and Hazard Center), they MUST use the SAME endpoint and display the SAME type of count (either both show 7-day total, or both show 24h count). Showing "53 earthquakes" on one page and "365 earthquakes" on another (because one counts 24h and the other counts 7 days) creates visible contradictions.

CROSS-PAGE COUNT CONSISTENCY RULE: Any page that shows a headline earthquake count MUST label the time window explicitly in the UI label text: "53 Earthquakes (24h)" not just "53 Earthquakes". The Hazard Center summary count MUST label "7-Day Total" explicitly. Both pages MUST fetch from the same USGS endpoint: `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson`.

### ROOT CAUSE: RADAR NOWCAST RANGE LIMITATION
RainViewer's `nowcast` array provides predicted radar frames for approximately 30 minutes into the future — NOT 6 hours. Showing "No forecast data" is correct when `nowcast_frames` is empty, and showing 30 min of future radar is the maximum available from RainViewer.

RADAR FUTURE FRAMES RULE: To extend the forecast visualization beyond 30 minutes, supplement the radar map with a precipitation probability overlay: fetch `hourly=precipitation_probability` from Open-Meteo for the next 6 hours and render it as a chart below the radar map labeled "6-Hour Precipitation Outlook (Model Forecast)". Do NOT claim the radar itself shows 6-hour predictions — only the model probability chart shows that.

### ROOT CAUSE: STAR MAP CANVAS DOESN'T FILL WHEN PANNING
A canvas-based star map that stores stars at fixed pixel positions will go blank at the edges when the user pans, because no stars exist outside the initially drawn region.

CANVAS STAR MAP PAN RULE: Stars and constellation lines MUST be stored as RA/Dec coordinates (not pixel positions). Every render call MUST convert RA/Dec to canvas pixels using the current `panX`, `panY`, and `zoom` values: `px = (ra / 24 * canvasWidth + panX) * zoom`, `py = ((90 - dec) / 180 * canvasHeight + panY) * zoom`. On every `mousemove` pan event, update `panX`/`panY` and call `redrawCanvas()`. This ensures the full star catalog is always rendered relative to the current view — the canvas never goes blank when panning.

### ROOT CAUSE: HERO SECTION CLIPPING CITY NAME AND TIME
When a weather hero section uses `justify-center` + `overflow-hidden` + `max-h-[20rem]` together, content taller than 320px gets clipped symmetrically from both top and bottom. With 7+ stacked elements (city, time, temperature, description, H/L, sunrise/sunset, moon), the city name and time at the top are cut off.

HERO CONTENT CLIP RULE: NEVER combine `justify-center` + `overflow-hidden` + a fixed `max-h` on a hero section that contains more than 4 stacked elements. Instead, use `justify-start` with adequate `padding-top` (at least `1rem`) so content starts from the top. If a max-height cap is desired for visual containment, use `max-h-[28rem]` minimum and `overflow-y-auto` (not `overflow-hidden`) so content remains accessible. The city name and current time MUST always be visible without scrolling.

### ROOT CAUSE: 14-DAY FORECAST SHOWS ONLY 8 DAYS
OpenWeatherMap One Call 3.0 returns a maximum of 8 days in the `daily` array. Slicing `[:14]` from an 8-element list yields only 8 days. The remaining days 9–14 must come from a supplemental source.

OWM 14-DAY RULE: The `/weather/daily` backend route MUST merge OWM data (days 1–8) with Open-Meteo to fill days 9–14. Fetch Open-Meteo with `forecast_days=16`: `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,weather_code&forecast_days=16&temperature_unit=fahrenheit&wind_speed_unit=mph`. For days 9–14 (index 8–13 of the Open-Meteo daily array), build forecast items from the Open-Meteo fields. Merge the two lists: `days = owm_days + openmeteo_days[len(owm_days):16]`. The combined list MUST always yield exactly 14 items. NEVER return fewer than 14 days when both sources are available.

### ROOT CAUSE: LEAFLET MAPS RENDER PARTIAL OR COLLAPSED IN NON-DEFAULT VIEWS
Leaflet maps initialized inside React components that are not visible on first render (e.g., a map inside a tab that is not the default active tab, or inside a view hidden by CSS display:none) get a wrong container size. The result is partial tile loading, grey areas, or a collapsed zero-height map.

LEAFLET INVALIDATE SIZE RULE: Every `L.map()` initialization block MUST call `setTimeout(() => mapRef.current?.invalidateSize(), 150)` immediately after creating the map. When a view becomes visible (e.g., tab switch, navigation), MUST call `mapRef.current?.invalidateSize()` again. Pattern:
```
const map = L.map(containerRef.current, { ... });
setTimeout(() => map.invalidateSize(), 150);
mapRef.current = map;
```
Additionally, when a component receives `isActive` or `visible` prop changes, include `useEffect(() => { if (isActive) { setTimeout(() => mapRef.current?.invalidateSize(), 100); } }, [isActive])`.

### ROOT CAUSE: MISSING EXOPLANETS ROUTE (404)
The frontend Planetary & Star Map view fetches `/astronomy/exoplanets` but this route is absent from the backend, causing a 404. The exoplanet archive must be implemented.

EXOPLANETS ROUTE MANDATORY: The backend app.py MUST implement a route at `/astronomy/exoplanets` that queries the NASA Exoplanet Archive TAP service. Use the URL from `NASA_EXOPLANET_ARCHIVE_URL` env var (default: `https://exoplanetarchive.ipac.caltech.edu/TAP/sync`). Query: `SELECT+TOP+100+pl_name,hostname,disc_year,pl_rade,pl_bmasse,pl_orbper,st_dist,disc_facility+FROM+ps+WHERE+pl_rade+IS+NOT+NULL+ORDER+BY+pl_rade+DESC`. Return array of `{name, host_star, year_discovered, radius_earth, mass_earth, orbital_period_days, distance_ly, discovered_by}`. The frontend Exoplanet Archive section MUST display this data as a scrollable list of cards — NOT the "No Exoplanet Data Available / Awaiting archive sync" placeholder. NEVER ship a route that returns a static placeholder when a real NASA TAP API is available.

### ROOT CAUSE: RECHARTS `Radar` IMPORT NAME COLLISION
Both recharts and lucide-react export the name `Radar`. When both are imported in the same file, the later import silently shadows the earlier one, and whichever component named `Radar` is actually used in JSX renders the wrong thing (or crashes with a type mismatch).

RECHARTS RADAR ALIAS RULE: ALWAYS import the recharts radar chart component with an alias: `import { Radar as RadarChart, RadarChart as RadarChartContainer, ... } from 'recharts'` and use `<RadarChart>` in JSX. NEVER use the bare name `Radar` in JSX when both recharts and lucide-react are imported — this guarantees a collision. Additionally, NEVER import `Radar` from lucide-react in any module that also imports recharts. If a radar/spider chart and a radar lucide icon are both needed, use the recharts alias and substitute the lucide icon with a different icon (e.g., `Activity`, `Radio`, `Globe2`).

### ROOT CAUSE: STAR MAP PAGE DOES NOT SCROLL — CANVAS CAPTURES ALL EVENTS
A full-viewport canvas element set to `height: 100vh` or `position: fixed` captures all scroll and pointer events from the browser, making the rest of the page unreachable by scrolling.

STAR MAP PAGE SCROLL RULE: The star map canvas MUST have a fixed pixel height (`height: 500px`, never `100vh`). The outer page container MUST use `overflowY: 'auto'` — NEVER `overflow: 'hidden'`. The canvas element MUST NOT have `position: fixed` or `position: absolute` with a full-viewport size. If the canvas needs to capture mouse events for pan/zoom, it MUST still allow the page container to scroll — attach wheel events to the canvas with `{ passive: false }` and call `e.stopPropagation()` only when the wheel event is used for zoom (when the user is hovering the canvas), not when scrolling the outer page. Section cards (Solar System Positions, ISS Live Track, Exoplanet Archive) MUST appear below the canvas and MUST be reachable by scrolling.

### ROOT CAUSE: STAR MAP USES RENDERED DOTS INSTEAD OF REAL NASA SKY IMAGERY
The star map renders white dots on a black canvas to represent stars. This produces a fake, toy-like visualization with no scientific value. Real astronomical sky survey imagery is freely available from NASA SkyView and must be used instead.

STAR MAP NASA IMAGERY RULE: The Planetary & Star Map page MUST use NASA SkyView to load real deep-sky survey images as the map background. Implementation:
1. The backend MUST expose a `/astronomy/skyview` route that accepts `ra` (right ascension), `dec` (declination), `fov` (field of view degrees, default 60), and `survey` (default `"DSS2 Red"`) query params. It proxies a request to NASA SkyView: `https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl?Survey={survey}&Position={ra},{dec}&Size={fov}&Pixels=800&Return=PNG&Sampler=LI` using the NASA_API key from env. Return the PNG image as a data URL (`data:image/png;base64,...`) or stream it directly with content-type `image/png`.
2. The frontend star map MUST render the SkyView PNG as the canvas background image — drawn via `ctx.drawImage(img, 0, 0, canvas.width, canvas.height)` before any overlays (constellation lines, planet markers, labels). When the user pans or zooms, recalculate the center RA/Dec and FOV and re-fetch a new SkyView image. Debounce re-fetches by 500ms to avoid flooding the API.
3. On initial load, compute the current LST (Local Sidereal Time) from the user's longitude and the current UTC time to determine the correct RA/Dec center for "what's overhead right now". Default center: RA = LST converted to degrees, Dec = user's latitude.
4. Available surveys to offer in a dropdown: `"DSS2 Red"` (default, optical), `"DSS2 Blue"`, `"2MASS-K"` (infrared), `"RASS-Int"` (X-ray). Let the user switch surveys.
5. NEVER render a dot-only canvas when NASA SkyView is available. If the SkyView fetch fails (network error), fall back to a dark canvas with star dots and show a "Live imagery unavailable — showing synthetic map" warning banner.

### ROOT CAUSE: HAZARD CENTER MAP SHOWS UNLEGENDED COLORED MARKERS
The Hazard Center Global Threat Map renders colored circles (purple, orange, red, etc.) on the map with no legend, and shows these markers even when the corresponding metric count is 0. This creates a contradictory UI: "Active Wildfires: 0" in the stat card but fire markers on the map.

HAZARD CENTER MAP LEGEND AND ZERO-STATE RULE: (1) EVERY marker color on the Global Threat Map MUST have a visible on-map legend (overlaid `<div>` in the bottom-left corner): orange = Earthquake, red = Wildfire, cyan = Tropical Storm, blue = Flood, purple = Volcanic Alert. No unlabeled colors. (2) When a hazard type has 0 active events, its markers MUST NOT appear on the map — a zero count means no events to plot. (3) Earthquake markers MUST use the same USGS `2.5_week.geojson` feed as the Seismic page — do NOT use a different USGS endpoint. (4) The purple circles that appear when Volcanic Alerts = 0 are a bug — volcanic markers MUST only be added when `volcano.alert_level !== 'normal'` and `volcano.alert_level !== 'background'`.

### ROOT CAUSE: WEATHER HERO SHOWS COORDINATES INSTEAD OF CITY NAME
The weather page displays "Region 41.48, -73.21" instead of "Southbury, Connecticut" because no reverse geocoding step is included before rendering the hero header.

WEATHER CITY GEOCODING RULE: The `/weather/current` backend route MUST perform reverse geocoding for any lat/lon pair before returning. Use OpenWeatherMap geocoding: `https://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={OPEN_WEATHER_MAP_KEY}`. Return `city`, `state`, `country` fields in the response payload. The frontend hero MUST render `${city}, ${state}` (or `${city}, ${country}` outside US) and ONLY fall back to coordinates when the geocoding response is empty. NEVER ship a hero showing raw `Region {lat}, {lon}` — that is an unfinished UI. Additionally, the search bar lookup MUST use forward geocoding `https://api.openweathermap.org/geo/1.0/direct?q={query}&limit=5&appid={KEY}` and update both the displayed city name and the lat/lon used for downstream API calls.

### ROOT CAUSE: RADAR TIMELINE FROZEN — NEVER REACHES CURRENT TIME
The RainViewer radar map shows a frame timestamp 5–10 minutes old and never advances toward the current clock time. The `/weather/radar` backend route is caching frames or only returning the first/oldest frame. The frontend `LIVE` indicator should always point to the most recent past frame; future-cast frames should extend up to ~2 hours ahead.

RAINVIEWER FRESH FRAME RULE: (1) The backend `/weather/radar` route MUST fetch `https://api.rainviewer.com/public/weather-maps.json` on every request — NEVER cache the manifest server-side longer than 60 seconds. Return the COMPLETE `radar.past` (last 12 frames, ~2hr) AND `radar.nowcast` (next 6 frames, ~90min) lists with their `time` (unix sec) and `path` fields. (2) The frontend timeline slider MUST default to the LAST frame in `radar.past` (index = past.length - 1, which is the most recent observed frame), NOT index 0. (3) The frontend MUST poll `/weather/radar` every 60 seconds to pick up new frames as RainViewer publishes them every 10 min. (4) Display each frame's actual UTC timestamp converted to the user's local timezone — NEVER show stale timestamps from a cached response. (5) The "PLAY" button must animate from past[0] forward through past then into nowcast, then loop.

### ROOT CAUSE: HAZARD/SEISMIC MAP HAS DATA BUT NO MARKERS PLOTTED
Backend returns 376 earthquakes, the data card displays "376", but the Leaflet map shows zero circles/markers. The `useEffect` that fetches data does not also call the marker-add logic, OR the marker-add code references a stale map ref, OR markers are added before the map is initialized.

LEAFLET MARKER PLOTTING RULE: (1) Every Leaflet map that displays event data MUST have a SINGLE `useEffect` keyed on BOTH `[mapRef.current, dataArray]` that (a) waits for `mapRef.current` to be non-null, (b) clears prior markers via a stored `markerLayerRef` (`L.layerGroup`), and (c) iterates the data array, calling `L.circleMarker([lat, lon], {...}).addTo(markerLayerRef.current)` for EVERY item. (2) The marker layer MUST be created with `markerLayerRef.current = L.layerGroup().addTo(map)` on map init — NEVER call `addTo(map)` per-marker without a layer group (causes orphaned markers when data refreshes). (3) When the data array length > 0 but markers are not visible after 1 second, this indicates a missing data→marker bridge — explicitly log marker count to console for the render check to detect. (4) NEVER use `useState` for marker arrays — use refs (`useRef`) so the map is mutated imperatively without React reconciliation conflicts. (5) The marker-add effect MUST NOT depend on a derived/memoized data array that changes identity each render (causes infinite add/remove loops) — use the raw fetch result.

### ROOT CAUSE: AI LAB CRASHES WITH "Invariant failed" — RECHARTS RESPONSIVECONTAINER NEEDS FIXED HEIGHT
Recharts `<ResponsiveContainer>` throws "Invariant failed" when its parent has no defined height (height: auto / 0). The chart cannot calculate dimensions and the entire view crashes through the ErrorBoundary.

RECHARTS RESPONSIVECONTAINER HEIGHT RULE: Every `<ResponsiveContainer>` MUST be wrapped in a parent `<div>` with an EXPLICIT pixel or percentage height: `<div style={{ width: '100%', height: 400 }}><ResponsiveContainer width="100%" height="100%">...</ResponsiveContainer></div>`. NEVER nest ResponsiveContainer inside a flex container without a defined height. NEVER use `height="auto"` on ResponsiveContainer. If the chart data array is empty (`data.length === 0`), render a placeholder `<div>` with the SAME explicit height instead of mounting an empty chart — empty Recharts datasets also trigger Invariant failed in some versions. ALWAYS check `data && data.length > 0` before rendering the chart.

### ROOT CAUSE: ERROR BOUNDARY MESSAGES USE NON-STANDARD WORDING — RENDER CHECK CANNOT DETECT
Generated ErrorBoundary fallback UI uses arbitrary headings ("Module Rendering Error", "View Crashed", "View Render Failure", "Attempt Recovery") that the render-check JS keyword set may not match, causing false-pass results.

ERROR BOUNDARY NAMING CONVENTION RULE: Every ErrorBoundary fallback UI in generated index.tsx MUST use the EXACT heading text `"Module View Error"` (h2 or h3). The retry button MUST use the EXACT label `"Retry"`. The error message body MUST be wrapped in a `<code>` element. Example: `<div><h3>Module View Error</h3><code>{this.state.error?.message}</code><button>Retry</button></div>`. NEVER invent new error UI strings like "View Crashed", "Module Rendering Error", "Render Failure", "Attempt Recovery" — these are not in the build's render-check keyword whitelist and will produce false-pass results in CI. Only the canonical strings get caught.

### ROOT CAUSE: BACKEND ROUTES RETURN 200 BUT EMPTY PAYLOADS WHEN UPSTREAM FAILS
`/ocean/current`, `/seismic/feed`, `/space/current`, `/weather/current` return HTTP 200 with `{}` or `[]` when the upstream API call fails (timeout, 401, parse error). The frontend renders the page with all-zeros / N/A values and the render check sees a "200 OK" without realizing the data is empty.

BACKEND EMPTY-PAYLOAD GUARD RULE: Every route handler that fetches an upstream API MUST wrap the call in try/except and (a) log the upstream error with full traceback, (b) return HTTP 503 with `{"error": "upstream_unavailable", "source": "<api-name>", "detail": "<error>"}` body when the upstream fails — NEVER return 200 with empty data. The frontend MUST distinguish: 200 with data → render data, 503 → show "Live data temporarily unavailable from {source}" banner, 200 with empty → show "No active events" only when the upstream confirmed empty (e.g. USGS returned `features: []`). Additionally, every route handler MUST include a sanity check: if the parsed payload from the upstream is `{}` or `[]` AND the upstream HTTP status was 200, log a WARNING (`upstream returned empty payload — possible parsing bug`) so the build process can detect dead routes.

### ROOT CAUSE: BUILD SYSTEM DOES NOT VERIFY RULES.MD COMPLIANCE BEFORE INTEGRATION
The build successfully wrote a Star Map that uses synthetic dot canvas instead of NASA SkyView, even though the STAR MAP NASA IMAGERY RULE requires SkyView. There is no rule-compliance gate that scans the generated tsx for required code patterns.

RULES.MD COMPLIANCE GATE RULE: Before integration, the build process MUST scan generated `index.tsx` for these REQUIRED patterns when their corresponding views exist:
- Star Map view present → tsx MUST contain `astronomy/skyview` fetch AND `ctx.drawImage(` (proves SkyView image is drawn to canvas). If absent → fail validation with "STAR MAP NASA IMAGERY RULE violated — synthetic dots used instead of SkyView".
- Weather hero present → tsx MUST contain a city/state property reference like `data.city` or `\`${city}, ${state}\`` AND MUST NOT contain a literal `Region ${lat}` template. If `Region ${lat}` is present → fail validation.
- Recharts `<ResponsiveContainer>` present → MUST be wrapped in parent div with `height:` style literal nearby (within 200 chars). If absent → fail validation.
- Leaflet map present AND backend has data-returning routes → tsx MUST contain `L.circleMarker(` or `L.marker(` or `L.layerGroup(` (proves markers are plotted). If absent → fail validation.
- ErrorBoundary present → fallback render MUST contain literal text `"Module View Error"`. If a non-canonical string is used → fail validation with the offending string quoted.
This gate runs in `validation/systems.py` as a new `RulesComplianceChecker`. Failures are sent back to the same domain-component LLM with the rule excerpt and a directive: "REWRITE this view to comply with the cited rule."

### ROOT CAUSE: PRECURSOR ANALYSIS IS BUTTON-ONLY — SHOULD RUN CONTINUOUSLY
The build AI generates precursor analysis as a click-to-run function only. This misses the system design intent: domain personas are always-on monitoring agents, not on-demand reporters.

PRECURSOR CONTINUOUS MONITORING RULE: The backend MUST maintain a module-level `_precursor_cache` dict: `{'result': None, 'timestamp': 0.0, 'running': False}`. On module startup (`@router.on_event("startup")` or a background task), schedule `_run_precursor_analysis_background()` which runs the full 2-stage multi-persona pipeline (see CROSS-DOMAIN PRECURSOR COLLABORATION rule) and caches the result with its timestamp. The cache expires after 30 minutes (`time.time() - _precursor_cache['timestamp'] > 1800`). The GET `/precursor/analysis` route MUST return the cached result immediately if fresh, or trigger a refresh if stale. The POST variant (triggered by UI button) forces an immediate refresh. This means the UI "Generate 72h Narrative" button simply invalidates the cache and returns the latest result — it does NOT block on a fresh LLM call every time. The frontend MUST show "Last updated: X minutes ago" using the cache timestamp, so users know the analysis is live, not stale.

---


### ROOT CAUSE: WEATHER PAGE SQUISHED -- h-screen CRAMPING ON MULTI-SECTION PAGES
The weather page renders all sections inside a root container using h-screen with overflow-y-auto. This locks the container to 100vh and makes content scroll internally, cramping all sections into one viewport. City name is hidden, radar map is cut off.

LAYOUT CRAMPING RULE: NEVER use h-screen or height:100vh as the root container for multi-section scrollable page views. Use min-h-screen instead. Reserve h-screen ONLY for true single-screen layouts (a full-screen map with NO other sections). Hero sections MUST NOT use max-h-[N] overflow-y-auto -- this hides the temperature/city name when content grows. The build gate flags any View component root that uses h-screen with sibling section depth greater than 2.

### ROOT CAUSE: OCEANIC TABS ARE DECORATIVE SPANS WITH NO onClick HANDLERS
The Oceanic Intelligence map shows SST Active and Currents Active labels as span elements with no onClick. They look interactive but do nothing.

INTERACTIVE ELEMENT MANDATE: Every UI element that looks like a button, tab, toggle, or layer control MUST be a button element (or role=button) with a functional onClick handler connected to React state. Static span or div elements styled to look like active/inactive toggles are FORBIDDEN when they represent interactive layer controls. Layer controls MUST call map.addLayer / map.removeLayer when clicked. Build gate detects span elements with layer-label text and flags them UI_ERROR when no onClick is wired.

### ROOT CAUSE: OCEANIC MAP SST TILE LAYER NEVER ADDED -- owm_api_key NOT IN BACKEND RESPONSE
The Oceanic map conditionally adds the OWM SST tile layer only when oceanData.owm_api_key is defined. The /ocean/current backend route does NOT include owm_api_key in its response, so the condition never fires and the SST layer is never added.

OCEAN MAP DATA FLOW RULE: The /ocean/current backend route MUST return owm_api_key from os.getenv(OPEN_WEATHER_MAP_KEY) in the response payload. Alternatively expose a backend tile proxy route /ocean/tile/{z}/{x}/{y} and use it as the TileLayer URL so the API key never reaches the client. The SST overlay and current arrows MUST appear on initial page load.

### ROOT CAUSE: SPACE WEATHER MAP EXTENDS TOO FAR -- NO HEIGHT BOUND OR MAP MAX BOUNDS
At zoom 2, the Leaflet tile server only covers up to about 85 latitude, leaving blank gray tile area below the world map. The map container has no max-height so it expands to fill all remaining flex space creating a huge blank white region.

SPACE WEATHER MAP HEIGHT RULE: All aurora/space weather maps MUST set explicit style={{height:500px, width:100%}} on the map container div. Call map.setMaxBounds([[-85,-180],[85,180]]) and set minZoom:2, maxZoom:6 to prevent blank tile overflow. Never use h-full or flex-grow on a map container inside a flex-column layout.

### ROOT CAUSE: HAZARD CENTER MISSING STORMS -- JTWC WEST PACIFIC DATA NOT INTEGRATED
The Hazard Center shows Active Storms: 0 even when real storms exist (e.g., Tropical Storm Sinlaku near Wake Island). The system only queries OpenWeatherMap which does not cover JTWC-tracked western Pacific typhoons.

TROPICAL STORM COVERAGE MANDATE: The /hazards/summary route MUST integrate both: (1) NHC Active Storms (Atlantic/East Pacific): https://www.nhc.noaa.gov/CurrentStorms.json -- no API key required; (2) GDACS global TC feed: https://www.gdacs.org/xml/rss.xml (parse XML for TC type events) OR JTWC RSS: https://www.metoc.navy.mil/jtwc/rss/jtwc.rss. The combined storm list MUST be plotted on the Hazard map as cyan storm markers with name labels. The Active Storms stat MUST count ALL worldwide named storms. Zero is valid only when both feeds confirm no active systems.

### ROOT CAUSE: PRECURSOR API RETURNS 404 -- FRONTEND FETCH HAS NO BACKEND ROUTE
The AI Lab view fetches /api/MODULE/precursor/analysis but this route was never added to app.py. The build domain generator wrote the frontend call but not the backend route. The build gate had no check for this mismatch.

FRONTEND-BACKEND ROUTE COMPLETENESS RULE: Every fetch('/api/MODULE/...') in index.tsx MUST have a matching @router.get or @router.post in app.py. The build gate now extracts all frontend fetch paths and cross-references them against all backend router decorators. Any unmatched frontend fetch path is a CRITICAL CONTRACT_ERROR that blocks integration. The precursor/analysis route must return the cached result per the PRECURSOR CONTINUOUS MONITORING RULE.

### ROOT CAUSE: WEATHER VIEW DEFAULTS TO US GEOGRAPHIC CENTER (39.8283°N, -98.5795°W) — SMITH COUNTY, KANSAS
The build AI initializes weather components with hardcoded lat=39.8283, lon=-98.5795 — the geographic center of the continental United States. This causes every user to see "Smith County, Kansas" weather regardless of where they actually live.

BROWSER GEOLOCATION INITIALIZATION RULE: ANY module that fetches location-based weather or environmental data MUST initialize from the browser's real geolocation on mount:
1. Call `navigator.geolocation.getCurrentPosition()` inside a `useEffect(() => {...}, [])` on the Weather view component.
2. On success callback, use `position.coords.latitude` and `position.coords.longitude` for ALL initial API calls (weather/current, weather/hourly, weather/daily, weather/radar, weather/alerts).
3. On denial/error callback, render a visible banner: "📍 Location access denied — use the search bar to enter your city." AND enable the city search input. NEVER silently fall back to hardcoded coordinates.
4. FORBIDDEN DEFAULT COORDINATES: NEVER hardcode lat=39.8283 / lon=-98.5795 (US geographic center), lat=40.7128 / lon=-74.0060 (New York City), lat=37.7749 / lon=-122.4194 (San Francisco), or ANY other hardcoded city as the initial location. The ONLY permitted hardcoded coordinates are inside named-region selectors (e.g., ocean basin dropdowns) where the region label is explicitly displayed.
5. While awaiting geolocation, render a "Detecting your location..." loading state — never zeros, never Kansas.
Pattern:
```typescript
useEffect(() => {
  if (!navigator.geolocation) { setLocationError('Geolocation not supported'); return; }
  navigator.geolocation.getCurrentPosition(
    (pos) => { setLat(pos.coords.latitude); setLon(pos.coords.longitude); },
    () => setLocationError('Location access denied — enter your city above.')
  );
}, []);
```

---

### ROOT CAUSE: BUILD GATE PASSED DESPITE MULTIPLE DEFECTS -- GAPS IN INSPECTION LOGIC
The gate approved a module with: cramped h-screen layout, non-interactive span tabs, expanding space map, 404 precursor route, missing storm data. Root gaps and fixes:
- No h-screen multi-section cramping detection. FIXED: LAYOUT_ERROR check added to build_gate.py.
- Toggle detection only found input[type=checkbox/radio] and role=switch. FIXED: render_check.py now also tests button-style layer controls by visible label text and verifies onClick is present.
- No frontend-to-backend route cross-reference. FIXED: build_gate.py now extracts all fetch() paths from TSX and matches them against @router decorators in app.py.
- No map height overflow check. FIXED: render_check.py flags map containers taller than 85vh.
- Layer control state-change not verified after click. FIXED: render_check.py now clicks layer buttons and checks for DOM state change.

BUILD GATE MANDATORY TEST PROTOCOL (updated): Must verify: syntax validity, 5-file contract, frontend-backend route completeness (every fetch has a backend route), no h-screen on multi-section pages, rules.md compliance (star map SkyView, marker plotting, geocoding, ResponsiveContainer height, error boundary naming, empty payload guard), API URL fidelity, skeleton detection. Render check must verify: page renders, all nav tabs switch views, real data in each view, maps show tiles AND data overlays/markers, ALL visible layer controls are interactive buttons with onClick, layer-clicks produce DOM state changes, no ErrorBoundary crashes, no map container exceeds 85vh.

---

### ROOT CAUSE: GEOLOCATION `getCurrentPosition` HAS NO TIMEOUT — PAGE FREEZES ON "LOADING INTELLIGENCE MODELS..."
`navigator.geolocation.getCurrentPosition()` was called without a `timeout` option. When the browser's permission dialog is pending (user hasn't clicked Allow/Deny yet), neither the success nor error callback fires — the page stays in `loading=true` state indefinitely showing "Loading intelligence models..." with no way to recover. This affects ANY view that initializes from geolocation (Weather, AI Lab, etc.).

GEOLOCATION TIMEOUT MANDATE: EVERY call to `navigator.geolocation.getCurrentPosition()` throughout the ENTIRE module MUST pass a third `options` argument: `{ timeout: 8000, maximumAge: 30000 }`. After 8 seconds with no response the browser fires the error callback with code TIMEOUT, which MUST call `setLoading(false)` and display the city search fallback. NEVER call `getCurrentPosition(successFn, errorFn)` with only two arguments — the two-argument form hangs indefinitely on pending permission dialogs. CORRECT pattern:
```typescript
navigator.geolocation.getCurrentPosition(
  (pos) => fetchWeatherData(pos.coords.latitude, pos.coords.longitude),
  () => { setError('📍 Location access denied — use the search bar.'); setLoading(false); },
  { timeout: 8000, maximumAge: 30000 }
);
```
Views that have a geolocation-independent fallback (like AI Lab which can load global model data without user location) MUST also call their fallback fetch in the error callback so the view is not blank. The AI Lab MUST default to `lat=40.7128, lon=-74.0060` on geolocation failure since model comparison and precursor analysis are global, not location-specific.

---

### ROOT CAUSE: PRECURSOR ANALYSIS ROUTE RETURNS HARDCODED "BASELINE NORMAL" STRINGS — NO LLM CALLED
The `/precursor/analysis` backend route returns hardcoded strings for every persona ("Severe weather coupling signals baseline normal.", "Oceanic coupling signals baseline normal.", etc.) with no API fetches and no LLM calls. The `_precursor_cache` dict exists but is never populated. The PRECURSOR CONTINUOUS MONITORING RULE references `@router.on_event("startup")` which is deprecated in FastAPI v0.95+, so background tasks from startup never run.

PRECURSOR LLM CALL MANDATE: The `/precursor/analysis` route MUST NEVER return hardcoded placeholder strings for any persona. Every domain report MUST be generated from real fetched data. Implementation using TTL cache (avoids deprecated startup events):
```python
_precursor_cache = {"result": None, "timestamp": 0.0, "running": False}

@router.get("/precursor/analysis")
async def precursor_analysis():
    now = time.time()
    if _precursor_cache["result"] and (now - _precursor_cache["timestamp"] < 1800):
        return _precursor_cache["result"]
    if _precursor_cache["running"]:
        return _precursor_cache["result"] or {"domain_reports": {}, "synthesis": "Analysis in progress...", "timestamp": ""}
    _precursor_cache["running"] = True
    try:
        # Fetch real data for each domain concurrently
        usgs_data, plasma_data, ocean_data = await asyncio.gather(
            fetch_usgs_earthquakes(), fetch_noaa_plasma(), fetch_ocean_current_global(),
            return_exceptions=True
        )
        # Build real domain reports from actual data
        quake_count = len(usgs_data.get("features", [])) if not isinstance(usgs_data, Exception) else 0
        # ... call LLM for each persona with real data context ...
        lena_system = await _load_persona("dr_lena_vance.md")
        synthesis_result = await call_llm_async(
            model_name="default",
            prompt=f"Real seismic data: {quake_count} M2.5+ events this week. Real plasma: {plasma_data}. Real ocean: {ocean_data}. Cross-domain precursor synthesis: identify convergent signals, score risk 1-10, output [CONVERGENT SIGNALS], [RISK ASSESSMENT], [72H OUTLOOK], [CONFIDENCE], [WATCH ZONES].",
            system_instruction=lena_system, persona_name="Dr. Lena Vance"
        )
        result = {
            "domain_reports": {
                "Dr. Lena Vance": f"Seismic Baseline: {quake_count} earthquakes (M2.5+) detected globally over the past 7 days.",
                # ... other domains with real data summaries ...
            },
            "synthesis": synthesis_result.get("text", ""),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        _precursor_cache.update({"result": result, "timestamp": time.time(), "running": False})
        return result
    except Exception as e:
        _precursor_cache["running"] = False
        raise HTTPException(503, detail=str(e))
```
FORBIDDEN: returning any of these hardcoded strings: "baseline normal", "coupling signals baseline normal", "precursor signals baseline normal". The build gate will detect 3+ occurrences of "baseline normal" in the precursor route body and flag DATA_ERROR.

---

### ROOT CAUSE: NASA SKYVIEW URL HAS UNENCODED SPACE — SERVER RETURNS HTML INSTEAD OF PNG
The SkyView URL is built as `f"...?Survey={survey}&..."` where `survey = "DSS2 Red"`. The literal space in "DSS2 Red" produces a malformed URL (`Survey=DSS2 Red`) that causes the NASA SkyView CGI to return an HTML error page instead of a PNG binary. The backend then base64-encodes the HTML bytes and returns them as `image_url`, and when the frontend sets `img.src = data_url`, the `<img>` fires `onerror` (HTML is not a valid PNG), `setSkyviewImage` stays null, and the canvas shows only star dots on black.

SKYVIEW URL ENCODING MANDATE: The NASA SkyView URL MUST URL-encode the `survey` parameter: use `urllib.parse.quote(survey, safe='')` when building the query string. Pattern:
```python
import urllib.parse
encoded_survey = urllib.parse.quote(survey, safe='')
url = f"https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl?Survey={encoded_survey}&Position={ra},{dec}&Size={fov}&Pixels=512&Return=PNG&Sampler=LI"
```
After fetching, MUST verify the response is actually a PNG: `if not resp.headers.get('content-type', '').startswith('image/'): return {"image_url": ""}`. If the content is HTML or text (error page), returning base64-encoded HTML as `image_url` creates a broken data URL that silently fails on the frontend. Always validate content-type before base64 encoding.

---

### ROOT CAUSE: SEISMIC MAP HAS 3-TIER DEPTH COLOR SYSTEM BUT LEGEND ONLY SHOWS 2 TIERS
The seismic marker color logic uses 3 thresholds: orange (depth ≤ 30km), red (depth 30–100km), purple (depth > 100km). The map's top-right legend only labels "Shallow EQ" and "Deep EQ" — omitting the intermediate red tier entirely. Users see 3 distinct colors with labels for only 2, making purple unexplained and confusing.

SEISMIC MAP DEPTH LEGEND MANDATE: The seismic map MUST render an on-map legend box positioned absolute in the bottom-left or top-left corner (NOT just header dots at the top-right) that explicitly lists ALL depth tiers with numeric boundaries and matching colors:
- 🟠 Orange = Shallow (0–30 km depth)
- 🔴 Red = Intermediate (30–100 km depth)
- 🟣 Purple = Deep (>100 km depth)
- 🔵 Blue/Cyan = Volcano Warning (active alert)
The depth breakpoints in the legend MUST exactly match the breakpoints used in the marker color logic — if the code uses `depth > 100` for purple, the legend MUST say ">100 km". NEVER show a 2-tier legend for a 3-tier color system. Implementation: overlay a `<div>` positioned absolute inside the map container with `pointer-events: none; zIndex: 1000`.

---

### ROOT CAUSE: PLASMA DATA PARSING FAILS ON EMPTY STRING ROWS — SOLAR WIND SHOWS 1 KM/S OR 0
The NOAA plasma JSON rows occasionally contain `""` (empty string) for speed/density columns when data is missing. The filter `row[1] is not None` passes empty strings, then `float("")` throws `ValueError` which jumps to the outer exception handler, resetting `solar_wind_speed` to `0.0`. The frontend then displays "1 km/s" or "0 km/s" for solar wind — both physically impossible (real solar wind is 300–900 km/s).

PLASMA PARSING ROBUSTNESS MANDATE: The plasma row filter MUST explicitly exclude empty strings and sentinel dashes:
```python
valid_plasma = [
    row for row in plasma_data[1:]
    if len(row) > 2
    and row[1] not in ('', None, '-', 'null')
    and row[2] not in ('', None, '-', 'null')
]
```
After parsing, MUST sanity-check the speed value: `if solar_wind_speed < 50.0: solar_wind_speed = None` and set a `"data_quality": "sensor_error"` flag in the response. The frontend MUST display "Sensor Error" (in orange/yellow text) instead of "1 km/s" or "0 km/s" when `solar_wind_speed` is `None` or below 50. Solar wind < 50 km/s is physically impossible and indicates a failed parse or NOAA data gap. NEVER display an impossible value as if it were real.

---

### ROOT CAUSE: AI LAB PERSONA DEBATE SHOWS CACHED "BASELINE NORMAL" STUBS — NO REAL DEBATE
The Persona Debate tab renders `precursorData.domain_reports` which comes from the `/precursor/analysis` endpoint. Since that endpoint returns hardcoded "baseline normal" strings, the Debate tab shows static placeholder text for every persona. There are no LLM calls per persona, no actual analysis, and no debate — just 7 cards reading variations of "XYZ signals baseline normal."

AI LAB PERSONA DEBATE MANDATE: The Persona Debate tab MUST show genuinely different LLM-generated perspectives per persona based on actual current data. When the user views the Debate tab (or clicks a "Run Debate" button), the frontend calls `/precursor/analysis` which MUST execute the full 7-persona multi-stage pipeline (per the PRECURSOR LLM CALL MANDATE above). Each persona card MUST display that persona's REAL LLM output — minimum 3 sentences of domain-specific insight using actual data values (earthquake counts, Kp index, SST readings, etc.). The synthesis card must be Dr. Lena Vance's cross-domain convergence output, NOT a hardcoded string. A "Last Updated" timestamp MUST be shown so users know when the analysis ran. The Debate tab MUST NOT be a static display — it is the visual output of the running 7-persona pipeline.

---

### ROOT CAUSE: AI LAB SCENARIO BUILDER ECMWF AND GFS SCENARIOS ARE IDENTICAL OFFSETS — NO DIVERGENCE
The Scenario Builder applies `whatIfOffset` identically to both GFS and ECMWF temperature arrays: `'GFS Scenario': d.GFS + offset, 'ECMWF Scenario': d.ECMWF + offset`. Both scenario lines are parallel — they shift together by exactly the same amount. There is no physical divergence, making the "scenario comparison" meaningless since both models respond identically to the forcing.

SCENARIO BUILDER DIVERGENCE MANDATE: The Scenario Builder MUST model physical model divergence. ECMWF uses a higher-resolution boundary layer scheme that responds more aggressively to temperature anomalies at longer lead times. Apply a divergence factor:
```typescript
const ecmwfResponseFactor = 1.0 + 0.15 * Math.abs(whatIfOffset / 15);
const gfsResponseFactor = 1.0;
// GFS Scenario: offset applied linearly
'GFS Scenario': d.GFS !== null ? d.GFS + whatIfOffset * gfsResponseFactor : null,
// ECMWF Scenario: larger response factor AND time-growing divergence
'ECMWF Scenario': d.ECMWF !== null ? d.ECMWF + whatIfOffset * ecmwfResponseFactor * (1 + idx * 0.02) : null,
```
This produces visible separation between the two scenario lines that grows over the forecast period — scientifically motivated and visually informative. At `whatIfOffset = 0` both lines converge (baseline). As the slider moves, the lines diverge at the correct rate.

---

### ROOT CAUSE: RADAR TIMELINE HAS NO FORECAST FRAMES — "NO FORECAST DATA" AND CAPPED AT 6:30 AM
The Open-Meteo Radar API or RainViewer API is fetched without the `forecast` query parameter enabled. The timeline slider shows only `Past: 13 frames` and `Future: 0 frames`, capping at the most recent past frame (~6:30 AM) instead of showing forecast frames through 10:30 AM–12:30 PM. When clicked to the far right, the label reads "NO FORECAST DATA" instead of a future timestamp.

RADAR FORECAST FRAMES MANDATE: The weather radar implementation MUST request forecast frames from the radar tile provider. If using RainViewer API (`https://api.rainviewer.com/public/weather-maps.json`), the `radar.nowcast` array contains short-range forecast frames. BOTH `radar.past` AND `radar.nowcast` frames MUST be included in the timeline. Pattern:
```typescript
const allFrames = [
  ...(data.radar.past || []).map((f: any) => ({ ...f, isForecast: false })),
  ...(data.radar.nowcast || []).map((f: any) => ({ ...f, isForecast: true }))
];
setFrames(allFrames);
```
The slider MUST cover all frames including nowcast. The "NO FORECAST DATA" label MUST be replaced with `isForecast ? "Forecast" : "Past"` prefix on the timestamp. Forecast frames MUST display timestamps up to 2 hours ahead. The timeline label area MUST show `Past: N frames | Forecast: M frames` (NOT `Future: 0 frames` when M > 0). FORBIDDEN: showing only `radar.past` frames and ignoring `radar.nowcast`.

---

### ROOT CAUSE: AI LAB PATTERN STUDIO IS A STATIC NODE DIAGRAM WITH NO FUNCTIONALITY
The Pattern Studio tab renders a "Cross-Domain Convergence Topology" showing 7 domain node boxes around a central "Synthesis Core" brain icon. Clicking any node does nothing. The text reads "The pattern studio identifies causal linkages between the above domains. Refer to the Persona Debate tab for full synthesis output." — which is a dead end redirect to another non-functional tab.

AI LAB PATTERN STUDIO MANDATE: The Pattern Studio MUST visually represent ACTUAL convergence data from the precursor analysis, not static node labels. When `precursorData` is loaded, each domain node MUST display: (1) a live status indicator (green = nominal, yellow = elevated, red = anomaly) based on the persona's domain report content, (2) a "signal strength" percentage derived from whether the domain report contains anomaly keywords ("anomaly", "elevated", "unusual", "significant", "warning", "anomalous", "heightened"). The connecting lines from domain nodes to the Synthesis Core MUST have color-coded thickness: thin+grey = nominal, medium+yellow = elevated signal, thick+red = high signal. The central Synthesis Core must show the convergence count ("N of 7 domains showing anomalies") derived from the domain reports. NEVER show a static diagram that communicates nothing about the actual system state.

---

### ROOT CAUSE: LUCIDE-REACT `Map` IMPORT SHADOWS NATIVE JAVASCRIPT `Map` CONSTRUCTOR
`import { ..., Map, ... } from 'lucide-react'` brings a React component named `Map` into the module's scope, overwriting the native JavaScript `Map` constructor for the entire file. Any code in index.tsx that calls `new Map()` (e.g. to build a JavaScript Map data structure) will call the Lucide React icon component as a constructor, throwing "Map is not a constructor" or "Constructor Map requires 'new'". Leaflet and other libraries that bundle their own Map references are unaffected inside their own modules, but ANY inline code in index.tsx that uses `new Map()` crashes at runtime. The headless render check fails for ALL 6 map-dependent views.

LUCIDE-REACT NATIVE CONSTRUCTOR SHADOW MANDATE: FORBIDDEN to import any identifier from any icon library (lucide-react, @heroicons/react, react-icons, phosphor-react, etc.) whose name exactly matches a native JavaScript global constructor or Web API class. Forbidden names include: `Map`, `Set`, `Symbol`, `Error`, `Event`, `URL`, `Promise`, `Date`, `Array`, `Object`, `Function`, `Number`, `String`, `Boolean`, `Image`, `Text`, `Comment`, `Range`, `Screen`, `Selection`, `Navigation`, `History`, `Location`, `Document`, `Window`, `Worker`, `Request`, `Response`, `Headers`, `URL`, `FormData`, `Blob`, `File`, `URL`.
MANDATORY RENAME pattern — whenever you need the `Map` icon from lucide-react:
```typescript
import { Map as MapIcon } from 'lucide-react';
```
Then use `<MapIcon />` in JSX, never `<Map />`. Apply the same rename strategy to ANY icon whose export name collides with a built-in. The build gate will detect an unaliased `Map` (or other forbidden name) in any lucide-react/icon-library import line and flag RULES_COMPLIANCE.

---

### ROOT CAUSE: WEATHER ENSEMBLE AVERAGES ZERO FROM FAILED OWM API CALL — TEMPERATURE IS HALF THE TRUE VALUE
`owm_temp = 0.0` is initialized as a zero default before the OWM fetch. When the OWM API call fails (bad URL, wrong key, network error), `owm_temp` stays `0.0`. The ensemble calculation is `temps = [owm_temp, om_temp]` (always 2 elements), so `ensemble_temp = (0.0 + 40.0) / 2 = 20.0°F` when the true temperature is 40°F. Zero from a failed call is treated identically to zero from a successful reading.

WEATHER API FAILED-CALL ZERO EXCLUSION MANDATE: Track a boolean `owm_succeeded = False`. Only set `owm_succeeded = True` inside the block where `owm_res.status_code == 200` succeeds. Build the `temps` list excluding zero-defaults from failed calls:
```python
owm_succeeded = False
owm_temp, feels_like, owm_wind, owm_dir, humidity = 0.0, 0.0, 0.0, 0, 0
if not isinstance(owm_res, Exception) and owm_res.status_code == 200:
    owm_data = owm_res.json().get("current", {})
    owm_temp = float(owm_data.get("temp", 0.0))
    feels_like = float(owm_data.get("feels_like", owm_temp))
    owm_wind = float(owm_data.get("wind_speed", 0.0))
    owm_dir = int(owm_data.get("wind_deg", 0))
    humidity = int(owm_data.get("humidity", 0))
    owm_succeeded = True

om_temp = None
om_feels_like = om_wind = om_wind_dir = om_humidity = None
if not isinstance(om_res, Exception) and om_res.status_code == 200:
    om_data = om_res.json().get("current", {})
    om_temp = float(om_data.get("temperature_2m", 0.0))
    om_feels_like = float(om_data.get("apparent_temperature", 0.0))
    om_wind = float(om_data.get("wind_speed_10m", 0.0))
    om_wind_dir = int(om_data.get("wind_direction_10m", 0))
    om_humidity = int(om_data.get("relative_humidity_2m", 0))

temps = [t for t in ([owm_temp if owm_succeeded else None, om_temp]) if t is not None]
if not temps:
    return {"temp": 0.0, "confidence": "None", ...error response...}
ensemble_temp = round(sum(temps) / len(temps), 1)

# Fallback feels_like/wind/humidity from Open-Meteo when OWM fails
if not owm_succeeded and om_feels_like is not None:
    feels_like = om_feels_like
    owm_wind = om_wind or 0.0
    owm_dir = om_wind_dir or 0
    humidity = om_humidity or 0
```
FORBIDDEN: `temps = [owm_temp, om_temp]` with no guard for OWM failure. FORBIDDEN: `feels_like`, `wind_speed`, `wind_dir`, `humidity` left at 0.0/0 when OWM fails with no Open-Meteo fallback. Open-Meteo `current` MUST also request `apparent_temperature,wind_speed_10m,wind_direction_10m,relative_humidity_2m` fields.

---

### ROOT CAUSE: `/weather/hourly` ROUTE HAS NO OPEN-METEO FALLBACK — RETURNS EMPTY WHEN OWM FAILS
The `/weather/hourly` route calls only OWM (`CURRENT_FORECAST_URL` env var). When OWM fails (misconfigured URL, bad API key), `items = []` and the route returns `{"items": []}`. The frontend renders "Hourly data unavailable". Open-Meteo provides a free 48-hour hourly forecast with no API key, but the route never falls back to it.

HOURLY FORECAST OPEN-METEO FALLBACK MANDATE: If OWM hourly returns empty or fails, MUST fall back to Open-Meteo `v1/forecast` hourly endpoint:
```python
if not items:
    om_hourly_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,apparent_temperature,precipitation_probability,"
        f"wind_speed_10m,wind_direction_10m,weathercode"
        f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=2"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        om_h_res = await client.get(om_hourly_url)
    if om_h_res.status_code == 200:
        oh = om_h_res.json().get("hourly", {})
        times = oh.get("time", [])
        temps = oh.get("temperature_2m", [])
        feels = oh.get("apparent_temperature", [])
        pops  = oh.get("precipitation_probability", [])
        winds = oh.get("wind_speed_10m", [])
        wdirs = oh.get("wind_direction_10m", [])
        for i, t in enumerate(times[:48]):
            dt = datetime.fromisoformat(t)
            items.append({
                "time": dt.strftime("%I:%M %p"),
                "temp": round(float(temps[i] if i < len(temps) else 0), 2),
                "feels_like": round(float(feels[i] if i < len(feels) else 0), 2),
                "description": "Forecast",
                "precip_chance_pct": float(pops[i] if i < len(pops) else 0),
                "wind_speed": round(float(winds[i] if i < len(winds) else 0), 2),
                "wind_dir": round(float(wdirs[i] if i < len(wdirs) else 0), 2),
            })
```
FORBIDDEN: returning `{"items": []}` when Open-Meteo is accessible and no OWM fallback has been attempted.

---

### ROOT CAUSE: OCEAN SST LAND MASK USES `dark_nolabels` AT 0.95 OPACITY — COVERS OCEAN, HIDES SST
The "land mask" added on top of OWM SST tiles uses CartoDB `dark_nolabels` tiles at `opacity: 0.95`. CartoDB `dark_nolabels` is a full-world basemap — it tiles BOTH land AND ocean with a dark solid color. At 0.95 opacity, it covers the SST gradient (zIndex 300, opacity 0.65) completely on ocean as well as land. The resulting map shows only the near-black CartoDB tiles everywhere, with zero visible ocean temperature data.

OCEAN SST TILE VISIBILITY MANDATE: The ONLY tile layer permitted on top of SST data tiles is a labels-only overlay. Correct layering:
1. Dark basemap (CartoDB `dark_all`, zIndex 100, opacity 1.0) — provides the dark ocean background
2. OWM SST/temperature tile layer at **zIndex 200**, **opacity 0.65** — temperature gradient visible on ocean
3. **Labels-only** overlay: `https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png` at **zIndex 500**, **opacity 1.0** — shows only text labels, roads, and coastlines; transparent everywhere else

FORBIDDEN tile layer combinations:
- `dark_nolabels` or `light_nolabels` at opacity > 0.3 on top of a data layer (these are full-world tiles that cover ocean)
- Any full-world basemap tile (without `only_labels` in the URL) placed ABOVE a data/SST layer at opacity > 0.3

The SST toggle button MUST call `setShowSST(prev => !prev)` (or equivalent state setter) — NEVER an empty `onClick={() => { /* wire to state */ }}`. A non-functional SST toggle is a UI_ERROR.

---

### ROOT CAUSE: SEISMIC PRECURSOR ANALYSIS ONLY RUNS ON BUTTON CLICK — NOT AUTO-LOADED ON MOUNT
The `SeismicView` component's mount `useEffect` fetches only `/seismic/feed` and `/volcano/feed`. The `/precursor/analysis` endpoint is called exclusively inside `generateRiskNarrative()`, which fires from the "Generate Seismic Risk Narrative" button. On initial page load the Cross-Domain Precursor Analysis panel is always empty. The spec requires continuous background precursor monitoring — the precursor data MUST be visible immediately when the user navigates to the Seismic view.

SEISMIC PRECURSOR AUTO-LOAD MANDATE: The SeismicView `useEffect` on mount MUST also auto-fetch `/precursor/analysis`. The "Generate Seismic Risk Narrative" button becomes a "Refresh Analysis" button (re-fetches on demand), but the first load is automatic. Required pattern:
```typescript
const fetchPrecursor = React.useCallback(async () => {
  setPrecursorLoading(true);
  try {
    const res = await fetch('/api/weather_and_planetary_intelligence/precursor/analysis');
    if (res.ok) setPrecursorData(await res.json());
  } catch {}
  finally { setPrecursorLoading(false); }
}, []);

React.useEffect(() => {
  fetchData();
  fetchPrecursor(); // auto-load — never button-only
  const interval = setInterval(fetchData, 300000);
  return () => clearInterval(interval);
}, [fetchData, fetchPrecursor]);
```
FORBIDDEN: calling `setPrecursorData` or fetching `/precursor/analysis` ONLY inside a button click handler with no corresponding auto-load on mount.

---

### ROOT CAUSE: STAR MAP CANVAS STUCK ON LOADING SPINNER WHEN SKYVIEW RETURNS EMPTY `image_url`
When the backend SkyView proxy returns `{"image_url": ""}` (NASA unavailable or content-type error), the frontend checks `if (svData.image_url)` — the empty string is falsy, so `setSkyviewImage` is never called. The main `loading` state IS cleared by `finally { setLoading(false) }`, but the canvas itself renders a near-invisible black field (STARS: 0, PLANETS: 0 when backend also returns empty arrays). The user perceives the canvas as permanently broken. Additionally, the star/planet arrays return empty when backend API routes return empty defaults, compounding the blank appearance.

STAR MAP LOADING STATE MANDATE:
1. The skyview fetch result MUST be handled for BOTH truthy AND falsy `image_url`:
```typescript
if (skyviewRes?.ok) {
  const svData = await skyviewRes.json();
  if (svData.image_url) {
    setSkyviewImage(svData.image_url);
  } else {
    setSkyviewImage(null); // explicitly clears any stale image
    setSkyviewError("Deep sky imagery temporarily unavailable");
  }
}
```
2. The canvas overlay MUST show a degraded-gracefully message (NOT a permanent spinner) when `skyviewImage` is null after load completes. Replace `{loading && <spinner "Acquiring Deep Sky Imagery...">}` with:
```typescript
{loading && <spinner text="Acquiring Deep Sky Imagery..." />}
{!loading && !skyviewImage && (
  <div className="absolute bottom-4 left-4 text-xs text-slate-500 bg-slate-900/80 px-2 py-1 rounded">
    Deep sky imagery unavailable — showing star chart only
  </div>
)}
```
3. The canvas MUST still render constellation lines, star dots, and planet markers even when `skyviewImage` is null. NEVER leave the canvas black when data fetch completes.
4. A separate `const [skyviewError, setSkyviewError] = React.useState<string | null>(null)` state MUST exist to track skyview-specific failures independently from the main `loading` flag.

---

## HOURLY ICON PRECIPITATION COHERENCE MANDATE
Any hourly forecast strip MUST select its weather icon from the same data field that drives the daily/current condition text. If the current/daily summary reports "clear sky" / "sunny" but every hourly tile shows a rain icon, the icon mapping is broken. Required:
1. Map the hourly `weathercode` (or OWM `weather[0].main`) to an icon using the SAME WMO_CODES / OWM lookup the daily forecast uses. Do NOT pick the icon from `precipitation_probability` alone — a 0% chance hour MUST NOT render `<CloudRain />`.
2. When `precipitation_probability < 30` AND the weather code resolves to clear/mainly-clear/partly-cloudy, render `<Sun />` / `<CloudSun />`, never `<CloudRain />` / `<Droplets />`.
3. The "X% rain" text label MUST come from `precipitation_probability` (or `pop * 100`) — never hardcode "0% rain".

---

## RADAR FORWARD-NOWCAST FRAMES MANDATE
Any "Live Atmospheric Radar" / radar-loop player MUST animate BOTH past frames AND forecast (nowcast) frames. RainViewer's `weather-maps.json` returns both `data.radar.past` AND `data.radar.nowcast`. Required:
1. Concatenate `data.radar.past.concat(data.radar.nowcast)` into the frame list — do NOT use only `past`.
2. The timeline scrubber MUST visually distinguish past (solid) from forecast (dashed/lighter) and label the segments "PAST" and "FORECAST" — NEVER show "NO FORECAST DATA" while ignoring the `nowcast` array.
3. The timestamp label below the scrubber MUST update to "Forecast: HH:MM" when the active frame is from the `nowcast` array, and "Observed: HH:MM" when from `past`.

---

## MAP DATA OVERLAY LEGEND MANDATE
Any Leaflet map that displays a color-graded data overlay (sea-surface temperature, air temperature, wind speed, precipitation intensity, AQI, soil moisture, anything tile-based with a color ramp) MUST also render a visible color-scale legend control. Required:
1. Add an `L.control({position: 'bottomright'})` containing labelled color-stop swatches and units (e.g. "32°F → 86°F" with min/mid/max stops).
2. The legend MUST appear whenever the corresponding overlay is toggled on, and disappear when toggled off.
3. A bare colored tile layer with no legend is REJECTED — users cannot read values from raw color.

---

## OCEAN CURRENT VECTOR MANDATE
Any ocean / marine map MUST render visible direction-and-speed indicators for surface currents when the route returns `current_speed` and `current_direction` (or any `u/v` velocity components). Required:
1. Use `L.marker` with a rotated arrow `<DivIcon>` (rotation = current direction in degrees), or polyline arrows. Marker size scales with speed.
2. Marker `.bindPopup()` MUST include the numeric speed (`X.XX kt` or `m/s`) AND direction (`NNE @ 045°`).
3. Static dot markers with no rotation are insufficient — direction MUST be visually communicated.

---

## COORDINATE-ENTITY MAP RENDER MANDATE
Any view that displays an entity defined primarily by `lat`/`lon` (ISS, satellites, hurricanes, ships, planes, drifting buoys, etc.) MUST render those coordinates on a Leaflet map alongside the numeric readout. Required:
1. A small inline Leaflet map (≥200px height) MUST be present in the same card as the numeric coordinate display.
2. The entity MUST be plotted as `L.marker` or `L.circleMarker` at the current `lat`/`lon`, updating on each refresh.
3. A bare numeric "lat: X, lon: Y" with no map is REJECTED — coordinates without a map are useless to the user.

---

## ANOMALY BADGE DRILL-DOWN MANDATE
Any UI element that shows "Anomaly Detected", "Alert Active", "Warning", or any non-nominal state badge MUST be clickable and reveal the underlying observation. Required:
1. Wrap the badge / row in a `<button>` (or use `role="button"` + `tabIndex=0`) with an `onClick` that opens a modal, expands an accordion, or routes to a detail panel.
2. The drill-down MUST show: the raw metric value, the threshold that was crossed, the timestamp, the data source, and a plain-English explanation.
3. Decorative anomaly badges with no `onClick` are REJECTED — every flagged anomaly MUST be observable.

---

## TELEMETRY SENSOR-OFFLINE MANDATE
Numeric telemetry tiles (Kp index, solar wind speed, plasma density, Bz, F10.7, sunspot count, AQI, water level, etc.) that resolve to exactly `0` / `0.0` / `--` MUST NOT render the success/normal/nominal badge. Required:
1. When a metric value is null, undefined, exactly 0.0 across multiple correlated channels, or returned as the API's documented "no-data" sentinel, the tile MUST display "Sensor offline" / "Awaiting telemetry" with a muted/warning color — NEVER "Normal" or "Nominal".
2. The page-level status header (e.g. "Current condition: Normal") MUST aggregate from real values; if every contributing metric is 0.0/null, the header MUST read "Awaiting telemetry — current condition unknown".
3. A green "Normal" badge above all-zero readouts is REJECTED.

---

## LOADING SKELETON RESOLUTION MANDATE
Any "Loading..." / spinner / skeleton placeholder MUST resolve (to either real content OR a clear error state) within 10 seconds of mount. Required:
1. Every `useEffect` that fetches data MUST include a `setTimeout` (≤10s) that, on timeout, sets an error state and clears `loading` to `false`.
2. When the timeout fires, the UI MUST show a retry button and the failure reason — never an indefinite spinner.
3. A page that displays "Loading X..." with no error path after 10s is REJECTED. Pages that show only the loading text (e.g. "Loading Global Map..." with no map or error after fetch completes) indicate a missing render branch and MUST be fixed by always rendering the container even while loading.

---

## DEEP-SKY IMAGERY FALLBACK CHAIN MANDATE
Any star-map / planetary explorer view MUST attempt a multi-source imagery chain before showing a "digital dot" rendering. Required fallback order:
1. NASA SkyView (`https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl?...`) at the requested RA/Dec.
2. ESO / Hubble Legacy Archive cutout for the field of view.
3. Stellarium-Web rendered tile (`https://stellarium-web.org/...`) as a high-quality star chart.
4. Only if all 3 fail: the local canvas star-dot fallback, AND the UI MUST display the source attempted and the reason it failed (e.g. "SkyView quota exceeded — showing chart only").
The chain MUST be implemented as sequential `await fetch()` calls with `Promise.race` timeouts of 4s each, NOT a single attempt that immediately falls back to dots.

---

## LOCATION RESOLUTION MANDATE
Any view that displays "current conditions" / "near you" / a localized forecast MUST resolve the user's location through a deterministic chain — NEVER hardcode a fallback city, lat/lon, or "Unknown, Unknown".
Required chain (in order):
1. The user-provided search box value, geocoded server-side (OpenWeatherMap `/geo/1.0/direct`, Nominatim, or equivalent).
2. The browser's `navigator.geolocation.getCurrentPosition()` if previously granted.
3. IP-based geolocation (`https://ipapi.co/json/`, `https://ip-api.com/json/`, or equivalent free service) called server-side with the request's `X-Forwarded-For`/remote address.
4. Only if all three fail: the UI MUST render a prominent location-input prompt — NEVER fall back to NYC (40.7128, -74.0060), "Unknown, Unknown", or any other hardcoded default.
Backend routes that accept `lat`/`lon` MUST raise HTTP 400 if both are missing — they MUST NOT silently substitute a hardcoded default. The frontend hero card MUST bind to the SAME `location` state field that the daily/14-day forecast binds to — split sources cause "Unknown" hero with populated forecast cards.

---

## UNIT COHERENCE MANDATE
Any numeric metric tile that shows a unit suffix (°F, °C, mph, km/h, kt, mb, hPa, in, mm, ft, m) MUST agree with the unit displayed on any sibling map overlay legend, gauge, or tooltip in the same view.
Required:
1. If the gauge/tile reads "17.5°F" but the map color-ramp legend says "32°F → 90°F" and the visible color over the same coordinate maps to ~55°F, the unit conversion is broken — likely a Celsius value labelled as Fahrenheit. The backend route MUST convert exactly once, at the API boundary, with a single helper (`c_to_f(c) = c * 9/5 + 32`).
2. Backend payload field names MUST encode the unit (`temp_f`, `temp_c`, `wind_mph`, `wind_ms`) — never bare `temp` or `wind`. The frontend MUST select the field matching the unit suffix it displays.
3. Map overlay legends MUST use the SAME conversion helper as the gauge — never inline a different formula for the legend.

---

## RECHARTS INVARIANT MANDATE
Any view that imports from `recharts` MUST satisfy recharts' invariants or it crashes the React tree with `Invariant failed`, taking the entire view down with an ErrorBoundary.
Required:
1. Every `<Tooltip />`, `<Legend />`, `<XAxis />`, `<YAxis />`, `<CartesianGrid />`, `<Bar />`, `<Line />`, `<Area />`, `<Cell />` MUST be a direct child (or grandchild via `<LineChart>`/`<BarChart>`/`<PieChart>`) of a single `<ResponsiveContainer>`. They MUST NEVER be rendered standalone outside any chart wrapper.
2. The `data` prop passed to a chart MUST be `Array.isArray(data) ? data : []` — never `null`, `undefined`, or an object. A `null` data prop triggers `Invariant failed`.
3. `<Cell />` MUST appear only inside `<Pie>`, `<Bar>`, or `<Scatter>` — never bare.

---

## MAP HEIGHT VIEWPORT CAP MANDATE
Any Leaflet/MapLibre/Mapbox map container with an explicit pixel `height` (≥ 400px) MUST also carry a `maxHeight: '70vh'` (or smaller) style entry. Required:
1. Pixel-only heights overflow short viewports (laptops, tablets) and produce blank-tile bars beneath the visible map.
2. The build pipeline auto-injects `maxHeight:'70vh'` whenever `render_check` reports "Map container is Npx tall ... exceeds 85% viewport height".
3. Containers using `h-screen` / `100vh` are REJECTED — they push other view content out of the scroll area.

---

### ROOT CAUSE: `BarChart` NAME COLLISION — RECHARTS CHART CONTAINER REPLACED BY LUCIDE ICON, CRASHES WITH "Invariant failed"
The build auto-fix system injects `import { Bar, CartesianGrid, ... } from 'recharts'` — note it imports `Bar` (a series child), NOT `BarChart` (the chart container). Simultaneously, lucide-react is imported with `BarChart` as an icon. When JSX contains `<BarChart data={...}>` expecting the recharts chart container, it instead receives the lucide SVG icon component. Recharts child elements (`<Bar />`, `<XAxis />`, `<YAxis />`, `<CartesianGrid />`) inside a non-recharts parent trigger recharts' internal `invariant()` guard — crashing the entire view with "Invariant failed" and an ErrorBoundary takeover.

BARCHART ALIAS MANDATE: NEVER use the bare name `BarChart` in JSX when both recharts and lucide-react are present in the same file. Always import the recharts chart container with an alias:
```typescript
import { Bar, BarChart as RechartsBarChart, LineChart, ... } from 'recharts';
```
Then use `<RechartsBarChart data={...}>` in JSX. If you also need the lucide bar-chart icon, substitute it with `BarChart2` from lucide-react (which is NOT exported by recharts and avoids the collision). NEVER import and use both `BarChart` from lucide-react AND `BarChart` from recharts under the same unaliased name in one file — this is the direct cause of the "Invariant failed" crash pattern. The auto-fix injector MUST always import `BarChart as RechartsBarChart` from recharts and patch any bare `<BarChart>` JSX to `<RechartsBarChart>`.

---

### ROOT CAUSE: GEOLOCATION `lat`/`lon` STATE NEVER UPDATED — RADAR MAP LOCKED TO FALLBACK COORDINATES
The Weather view declares `const [lat, setLat] = useState(0); const [lon, setLon] = useState(0);` but `fetchData(targetLat, targetLon)` is called from the geolocation callback without ever calling `setLat(targetLat)` or `setLon(targetLon)`. The map re-center `useEffect` guards on `lat !== 0 && lon !== 0` — since lat/lon state stays at 0 forever, `setView` is never called and the radar map remains locked on its hardcoded fallback (typically the US geographic center at `[39.8, -98.5]`, i.e., Kansas) regardless of the user's actual location. All API calls receive the correct coordinates (passed directly to `fetchData`), so weather data shows correctly for the right city while the radar is visually wrong.

GEOLOCATION STATE SYNC MANDATE: The geolocation success callback MUST call `setLat` and `setLon` BEFORE or alongside `fetchData`. Required pattern:
```typescript
navigator.geolocation.getCurrentPosition(
  (pos) => {
    const { latitude, longitude } = pos.coords;
    setLat(latitude);      // MANDATORY — updates map re-center effect
    setLon(longitude);     // MANDATORY — updates map re-center effect
    fetchData(latitude, longitude);
  },
  () => { setError('Location access denied — use the search bar.'); setLoading(false); },
  { timeout: 8000, maximumAge: 30000 }
);
```
The city search handler MUST also call `setLat(newLat); setLon(newLon);` after geocoding the search term. The radar map `useCallback` MUST NOT be initialized with the real lat/lon (which are 0 at mount) — instead initialize the map at a placeholder center and rely on the `useEffect([lat, lon])` re-center after state updates. FORBIDDEN: calling `fetchData(lat, lon)` from a geolocation callback without also calling `setLat`/`setLon` — this silently breaks every map that depends on the lat/lon state.

---

### ROOT CAUSE: LEAFLET ZOOM BUTTONS (+/−) AND EMOJI DIVICONS FLAGGED AS REACT BUTTONS WITHOUT CLICK HANDLERS
The render-check system scans the DOM for all `<button>` elements and validates that each has a React `onclick` attribute. Leaflet's built-in zoom control generates `<a class="leaflet-control-zoom-in">+</a>` and `<a class="leaflet-control-zoom-out">−</a>` DOM elements using Leaflet's own event system — these have no React `onclick` attribute and are flagged as "buttons without handlers." Similarly, `L.divIcon({ html: '🛰️' })` creates a `<div>` with an emoji that the scanner misidentifies as a button. These are Leaflet-internal elements, fully functional, but invisible to React's event system.

LEAFLET ZOOM CONTROL DISABLE RULE: For small embedded/secondary maps (ISS tracker, mini reference maps, any map ≤ 300px height), ALWAYS create the map with `{ zoomControl: false }` to suppress Leaflet's zoom buttons entirely:
```typescript
const map = L.map(node, { zoomControl: false, scrollWheelZoom: false });
```
This eliminates the render-check false positive. Full-size interactive maps (radar, seismic, oceanic, hazard) MAY keep `zoomControl: true` since those maps are expected to have zoom controls. For divIcon emoji markers, always set `{ interactive: false }` on the marker if clicking it should have no behavior:
```typescript
L.marker([lat, lon], { icon: divIcon, interactive: false }).addTo(map);
```
This prevents the render check from expecting a click handler on the emoji element.

---

### ROOT CAUSE: DUPLICATE `style={{}}` JSX ATTRIBUTE — SECOND PROP SILENTLY OVERWRITES FIRST, LOSING STYLES
Domain assembly merges components from multiple generation passes. When two generation passes both emit a `style={{...}}` attribute on the same JSX element, the assembled file has a duplicate JSX key (e.g., `style={{ maxHeight: '70vh' }}` on one line and `style={{ height: '480px', width: '100%' }}` on the next line of the same tag). esbuild emits a `[duplicate-object-key]` warning and the second attribute silently wins — the `maxHeight` constraint is discarded and the map container can overflow the viewport.

SINGLE STYLE PROP MANDATE: EVERY JSX element MUST have at most ONE `style={{}}` attribute. Merge all inline style rules into a single object:
```tsx
// CORRECT
<div style={{ height: '480px', width: '100%', maxHeight: '70vh' }}>

// FORBIDDEN — duplicate style prop, second silently wins
<div
  style={{ maxHeight: '70vh' }}
  style={{ height: '480px', width: '100%' }}>
```
During domain assembly, the post-assembly auto-fix MUST scan for duplicate `style={{` attributes on the same JSX element and merge them. The build gate MUST treat any esbuild `[duplicate-object-key]` warning as a BUILD_ERROR, not a warning — duplicate JSX props indicate a merge defect that produces invisible style loss.

---

### ROOT CAUSE: CONDITIONALLY-RENDERED MAP BYPASSES LAT/LON RE-CENTER — RADAR LOCKED TO FALLBACK DESPITE STATE UPDATE
When a Leaflet map container is wrapped in a conditional block (e.g., `currentData ? <div ref={mapRef}>` — only rendered after API data loads), the sequence is: (1) geolocation resolves → `setLat`/`setLon` called → re-center `useEffect([lat, lon])` fires → but `mapRef.current` is still null because the map div hasn't mounted yet → `setView` skipped; (2) data loads → map div mounts → `useCallback(mapInit, [])` fires → stale closure captures `lat=0, lon=0` → map initializes at fallback (Kansas). The re-center effect never fires again because `lat`/`lon` state doesn't change after step 1. Result: map is locked at fallback coordinates forever even though geolocation succeeded.

CONDITIONAL MAP COORDINATE REF MANDATE: When the map container is conditionally rendered (any map div gated behind state such as `loading`, `currentData`, `selectedRegion`, etc.), coordinates MUST be stored in a `useRef` so the `useCallback` init always reads the latest value — NOT from React state:
```typescript
const coordsRef = useRef<{lat: number, lon: number}>({lat: 39.8, lon: -98.5}); // fallback only

// In geolocation callback — update ref FIRST, then state:
(pos) => {
  coordsRef.current = {lat: pos.coords.latitude, lon: pos.coords.longitude};
  setLat(pos.coords.latitude);
  setLon(pos.coords.longitude);
  fetchData(pos.coords.latitude, pos.coords.longitude);
}

// In mapCallbackRef — read from ref, not state:
const mapCallbackRef = useCallback((node: HTMLDivElement | null) => {
  if (!node || mapRef.current) return;
  const { lat, lon } = coordsRef.current; // always up-to-date
  mapRef.current = L.map(node, { scrollWheelZoom: false }).setView([lat, lon], 8);
  // ...
}, []); // [] deps OK because we read from ref
```
The re-center `useEffect([lat, lon])` is retained as a secondary guard but the primary init already uses the correct coordinates. FORBIDDEN: reading `lat` or `lon` state variables inside a `useCallback(..., [])` — stale closure will always see initial state (0, 0).

---

### ROOT CAUSE: LLM OUTPUT MARKDOWN RENDERED AS RAW TEXT IN UI — DOUBLE ASTERISKS AND POUND SIGNS VISIBLE
Backend routes that call LLM personas return raw markdown-formatted text (e.g., `**Description:** The Southbury area...`, `### [CONVERGENT SIGNALS]`, `* **Seismic Surge:**`). The frontend renders this string directly in JSX (`<p>{data.description}</p>`) without markdown parsing, so users see raw `**`, `##`, `*`, `###` characters. This affects weather descriptions, precursor analysis synthesis, persona debate reports, and any other LLM-generated text field.

LLM MARKDOWN STRIP MANDATE: Backend routes that invoke LLM calls and return the output as a plain-text field in the API response MUST strip markdown formatting before returning. Apply this cleanup to all persona/LLM text outputs:
```python
import re
def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)   # **bold** -> plain
    text = re.sub(r'\*(.*?)\*', r'\1', text)          # *italic* -> plain
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # ### headers
    text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)    # bullet points
    text = re.sub(r'`[^`]*`', lambda m: m.group(0)[1:-1], text) # `code`
    return text.strip()
```
Apply `strip_markdown()` to every field that contains LLM-generated text before including it in the route's return dict. Alternatively, if rich formatting IS desired, use `ReactMarkdown` on the frontend to render the markdown properly — but NEVER let raw markdown symbols appear as visible text in the UI. A description that reads `**Description:** The area is experiencing...` is a hard REJECT.

---

### ROOT CAUSE: WEATHER CONDITIONS GRID SHOWS HARDCODED VALUES INSTEAD OF LIVE API DATA
The weather conditions detail grid (Pressure, UV Index, Visibility, Air Quality, Pollen) renders hardcoded placeholder values: `29.92 inHg`, `"Rising steadily"`, `4 Moderate`, `10 mi`, `"Perfectly clear"`, `42 Good`, `"Ideal for outdoor activities"`, `Low`. These values are embedded as JSX string literals and never update from the API response. The hourly and daily forecast correctly uses `currentData.*` but the conditions grid was accidentally written with static strings.

CONDITIONS GRID REAL DATA MANDATE: Every metric tile in a weather conditions grid MUST bind to a live API field from `currentData`. Required field mapping:
- Pressure tile: `currentData.pressure` (inHg) + `currentData.pressure_trend` string
- UV Index tile: `currentData.uvi` (0-11) + label derived as `uvi >= 8 ? 'Very High' : uvi >= 6 ? 'High' : uvi >= 3 ? 'Moderate' : 'Low'`
- Visibility tile: `currentData.visibility` (miles)
- Air Quality tile: `currentData.aqi` (integer) + category derived from AQI breakpoints
- Pollen tile: `currentData.pollen_tree`, `currentData.pollen_grass`, `currentData.pollen_ragweed` from WeatherAPI
- Precipitation tile: `hourlyData[0]?.precip_chance` (%) and `currentData.precip_today` (inches)
FORBIDDEN: any JSX string literal matching `"29.92"`, `"10 mi"`, `"Perfectly clear"`, `"4 "`, `"42 "` appearing as static content in weather metric tiles. The build gate detects these sentinel strings and flags HARDCODED_DATA.

---

### ROOT CAUSE: OCEAN CURRENT ARROWS PLACED IN UNIFORM GRID — ALL SAME DIRECTION, NOT REPRESENTING GYRE PATTERNS
The ocean current implementation places 9 arrows in a 3x3 offset grid around the selected region center, ALL pointing in the same direction (`rotate(${dir}deg)`). This creates a uniform arrow field that looks artificial and does not represent real ocean gyre circulation patterns.

OCEAN CURRENT VISUALIZATION MANDATE:
1. The backend `/ocean/current` route MUST fetch `ocean_current_velocity` and `ocean_current_direction` from Open-Meteo Marine API `&current=ocean_current_velocity,ocean_current_direction`.
2. The frontend renders arrows at a 5x5 grid spanning ±12 degrees lat/lon from the region center.
3. Each arrow uses CSS `transform: rotate(${direction}deg)` where direction is the compass bearing (0=North, 90=East). Rotation MUST be applied directly so the arrow points in the direction of flow — not spins in circles.
4. Arrow font-size scales with speed: `Math.max(12, Math.min(24, 12 + velocity * 4))px`.
5. FORBIDDEN: all arrows in the layer having identical `rotate()` values from a single scalar API field. When only one direction reading is available, vary the displayed arrows by ±15 degrees per grid position to simulate divergence, with a disclaimer tooltip "Estimated from regional mean current".

---

### ROOT CAUSE: PLANET POSITIONS ENDPOINT RETURNS HARDCODED STATIC RISE/SET TIMES
The `/astronomy/planets` route hardcodes rise/set times as `"06:00 AM"` / `"08:00 PM"` for every planet regardless of latitude, date, or orbital position.

PLANET RISE/SET LIVE CALC MANDATE: Rise and set times MUST be computed from RA/Dec and observer latitude using the standard hour angle formula: `cos(H) = (sin(-0.5°) - sin(lat)*sin(dec)) / (cos(lat)*cos(dec))`. Convert H to local time using Local Sidereal Time. If the calculation produces no rise/set (circumpolar or never-rises), return `"Circumpolar"` or `"Below horizon"` respectively. NEVER return `"06:00 AM"` or `"08:00 PM"` as static strings for planet rise/set — these are hardcoded mock values and will cause build rejection.

---

### ROOT CAUSE: SOLAR WIND DATA NULLED BY LOW-VALUE THRESHOLD — "SENSOR OFFLINE / GAP" SHOWN FOR QUIET SOLAR CONDITIONS
Backend space weather routes apply a sanity threshold like `if solar_wind_speed < 50.0: solar_wind_speed = None` to reject what looks like bad data. However, during quiet solar periods the real solar wind speed is 300–500 km/s and solar flux / Bz values are legitimately near zero. The null-threshold check fires on valid quiet-sun data, causing the frontend to display "Sensor Offline / Gap" even though NOAA SWPC is fully operational and returning real readings.

SOLAR WIND LIVE DATA MANDATE: NEVER apply a minimum-value threshold that nullifies space weather readings. All parsed NOAA SWPC fields (Kp index, solar wind speed, solar wind density, IMF Bz, solar flux) MUST be returned as their parsed numeric value even when near zero. If the API call itself fails (HTTP error, timeout, empty response), return the field as `None` and let the frontend display "Sensor Offline". If the API responds but the value is legitimately low (e.g., Bz = 0.0 nT, Kp = 0.0), return that value and display it — do NOT set it to None. The ONLY valid reason to return `None` for a space weather metric is a failed API call or a response with truly empty/missing data columns (empty string, null, "-"). FORBIDDEN pattern: `if solar_wind_speed < 50: solar_wind_speed = None` — this kills valid quiet-sun readings.

---

### ROOT CAUSE: WEATHER FORECAST CARDS SHOW ONLY TEXT — NO WEATHER CONDITION ICONS
Hourly forecast strips and 14-Day forecast cards render text descriptions ("Moderate rain", "Light rain", "Clear sky") with no visual icon. The user cannot scan conditions at a glance. Every other weather platform uses icons precisely because humans process images faster than text at small scale.

WEATHER FORECAST CONDITION ICON MANDATE: Every hourly card AND every 14-day forecast card MUST render a weather condition icon above/beside the temperature. Implement a mapping helper in index.tsx:
```typescript
function getConditionIcon(description: string): React.ReactNode {
  const d = description.toLowerCase();
  if (d.includes('thunder') || d.includes('lightning')) return <CloudLightning size={20} />;
  if (d.includes('snow') || d.includes('blizzard') || d.includes('sleet')) return <Wind size={20} style={{color:'#93c5fd'}} />;
  if (d.includes('rain') || d.includes('drizzle') || d.includes('shower')) return <CloudRain size={20} />;
  if (d.includes('cloud') || d.includes('overcast')) return <Cloud size={20} />;
  if (d.includes('fog') || d.includes('mist') || d.includes('haze')) return <Eye size={20} />;
  if (d.includes('clear') || d.includes('sunny')) return <Sun size={20} />;
  return <Cloud size={20} />;
}
```
Call `getConditionIcon(hour.description)` in every hourly card JSX. Call `getConditionIcon(day.description)` in every 14-day card JSX. The icon MUST appear even when the card is minimal size. NEVER ship a forecast strip or daily list with zero icons — the build gate detects any weather forecast view that renders description text with no icon function call in the same component scope.

---

### ROOT CAUSE: SPACE WEATHER SHOWS "AWAITING TELEMETRY" FOR FLARES, CME, RADIO FLUX — ENDPOINTS NEVER FETCHED
The `/space/current` backend route only fetches the plasma JSON, mag JSON, and Kp index from NOAA SWPC. Solar flares, CME detections, and radio flux (10.7cm) require separate endpoint calls that are never made. The frontend Solar Activity panel renders "Awaiting Telemetry" for all three fields because they are never populated in the API response.

SPACE WEATHER COMPLETE TELEMETRY MANDATE: The `/space/current` backend route MUST fetch ALL of the following concurrently via `asyncio.gather()`:
1. **Kp Index**: `{NOAA_SWPC_URL}/products/noaa-planetary-k-index.json` — parse `data[-1][1]` as current Kp
2. **Plasma/Solar Wind**: `{NOAA_SWPC_URL}/products/solar-wind/plasma-7-day.json` — speed=`row[1]`, density=`row[2]`
3. **IMF Bz**: `{NOAA_SWPC_URL}/products/solar-wind/mag-7-day.json` — Bz=`row[3]`
4. **Solar Flares (24h)**: `{NOAA_SWPC_URL}/json/goes/primary/xrays-1-day.json` — count X/M/C-class events in last 24h by scanning `satellite_tag` and `flux` columns; return `{"X": n, "M": n, "C": n}`
5. **Radio Flux (10.7cm)**: `{NOAA_SWPC_URL}/json/f107_cm_flux.json` — return the most recent `flux` value (sfu units)
6. **CME Detections (7d)**: `https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/CME?startDate={seven_days_ago}&endDate={today}&api_key=DEMO_KEY` — count the entries in the returned array; return `{"count": n, "latest_speed_km_s": float_or_null}`

Return these in the response: `solar_flares_24h`, `radio_flux_sfu`, `cme_count_7d`, `cme_latest_speed`. The frontend MUST render these fields in the Solar Activity panel. "Awaiting Telemetry" is FORBIDDEN when the endpoint has been called — if the call fails, show `"N/A"` not "Awaiting Telemetry". Note: `NOAA_SWPC_URL` default is `https://services.swpc.noaa.gov` (NOT the documentation page URL `https://www.swpc.noaa.gov/products-and-data`).

---

### ROOT CAUSE: MARINE 7-DAY FORECAST SHOWS "AWAITING TELEMETRY" — NOT LOADED ON MOUNT
The 7-Day Marine Forecast panel renders "Awaiting 7-day extended marine forecast telemetry" indefinitely because the backend marine forecast endpoint either (a) is not fetched via `useEffect` on mount or (b) is only fetched when a button is clicked. The forecast data never arrives automatically.

MARINE FORECAST AUTOLOAD MANDATE: The Oceanic Intelligence view MUST fetch marine forecast data inside a `useEffect` that depends on `[lat, lon]` (or region coordinates) — the same effect that fetches SST, wave height, and current data. The backend `/ocean/current` route MUST return a `daily_forecast` array of 7 items alongside the current conditions. Each item: `{date, wave_height_ft, wave_period_s, swell_direction_deg, wind_speed_mph, visibility_mi, temp_f}`. Fetch from Open-Meteo Marine API:
```python
marine_url = (
  f"https://marine-api.open-meteo.com/v1/marine"
  f"?latitude={lat}&longitude={lon}"
  f"&daily=wave_height_max,wave_period_max,wind_speed_10m_max,visibility_mean"
  f"&wind_speed_unit=mph&length_unit=imperial&timezone=auto&forecast_days=7"
)
```
Return `daily_forecast` in the same response object as `sea_surface_temp`, `wave_height`, etc. The frontend MUST render all 7 forecast tiles immediately on page load — NO button click required. FORBIDDEN: `daily_forecast` fetched only when user clicks a button named "Load Forecast" or "Generate Marine Briefing".

---

### ROOT CAUSE: HAZARD CENTER MAP CONTAINER OVERFLOWS VIEWPORT — BOTTOM TILES PUSHED OUT OF VIEW
The Global Threat Map container uses `flex-grow: 1` or `height: calc(100vh - Npx)` causing it to expand and fill all remaining vertical space. The Active Tropical Storms, Wildfire Report, and Flood Warnings tiles that should appear below the map are pushed below the visible viewport with no scroll affordance. The page appears to end at the bottom of the map.

HAZARD CENTER MAP VIEWPORT OVERFLOW MANDATE: The Global Threat Map container MUST use a fixed pixel height (e.g., `style={{height: '520px', width: '100%'}}`) — NEVER `flex-grow: 1`, `h-full`, or `height: calc(100vh - ...)`. The outer view container MUST be a scrollable column using `overflowY: 'auto'` so the bottom hazard panels are reachable. The bottom three panels (Active Tropical Storms, Wildfire Report, Flood Warnings) MUST use a flex-row layout: `display: flex; flex-wrap: wrap; gap: 1rem` so they fill the space naturally below the map. FORBIDDEN: any layout where `<div ref={mapRef}>` uses `height: 100%`, `height: 100vh`, or inherits parent height without an explicit cap. The hazard center is a multi-section scrollable page — it MUST NOT behave like a fullscreen single-map application.

---

### ROOT CAUSE: AI LAB MODEL COMPARISON CHART RENDERS EMPTY — DATA NOT LOADED ON MOUNT
The Ensemble Forecast Divergence chart on the Model Comparison tab renders an empty dark rectangle on initial load. The `/ailab/models` endpoint returns real comparison data from multiple Open-Meteo models, but the chart data state is never populated because: (a) the useEffect fetch either never fires on mount, (b) the recharts component receives `undefined` or `null` instead of an array, or (c) the backend returns data but the frontend maps the wrong field names.

AI LAB MODEL COMPARISON AUTOLOAD MANDATE: The Model Comparison tab component MUST fetch `/ailab/models?lat={lat}&lon={lon}` inside a `useEffect(() => { fetchModels(); }, [lat, lon])` on mount — NEVER require a button click to populate the initial chart. The `/ailab/models` backend route MUST return a `comparison_points` array — one entry per forecast hour for the next 24 hours — with fields `{hour_label: str, gfs_temp: float, ecmwf_temp: float, icon_temp: float|null, hrrr_temp: float|null}` where missing model data uses `null`. The recharts `<LineChart>` MUST initialize its `data` prop as `[]` (not `null`/`undefined`) and render the chart as soon as `comparison_points` is populated. FORBIDDEN: chart container with `data={undefined}` or showing empty on initial render with real data available from the backend. The "Which Model Should I Trust?" button triggers an LLM synthesis of the chart data — it is SECONDARY to the chart itself loading automatically.

---

### ROOT CAUSE: PATTERN STUDIO ANOMALY NODE CLICK SHOWS NOTHING — NO DETAIL PANEL
The Pattern Studio topology diagram displays persona nodes (Dr. Lena Vance, Gale Hawthorne, etc.) with ANOMALY/NOMINAL status labels, but clicking any node produces no response. The user can see "1 of 7 Signals" anomaly count in the Synthesis Core but cannot read the actual anomaly description that triggered the ANOMALY status. The diagram is read-only and provides no drill-down.

PATTERN STUDIO NODE CLICK DETAIL MANDATE: Every domain persona node in the Pattern Studio topology MUST have an `onClick` handler. When clicked, it MUST render a detail panel (side panel or modal overlay) showing: (1) the persona's name and role title, (2) their domain report text from `precursorData.domain_reports[personaName]` — minimum 3 sentences, (3) a signal status badge (NOMINAL/ELEVATED/ANOMALY) with color, (4) the specific anomaly keywords detected (the keywords that elevated the node from NOMINAL to ANOMALY). The Convergence Core node MUST be clickable and show the full synthesis text from `precursorData.synthesis`. FORBIDDEN: any Pattern Studio topology where node clicks do nothing — every node is an interactive data point, not a decoration. The detail panel MUST be dismissible (click outside or × button) and MUST render inside a React portal to avoid `overflow:hidden` clipping.

---

### ROOT CAUSE: 14-DAY FORECAST EXPANDED CARD SHOWS SINGLE COMBINED DESCRIPTION — NO SEPARATE DAY/NIGHT PANELS
When a 14-day forecast card is expanded (clicked), the user sees a single description and a combined conditions grid with no visual distinction between daytime and nighttime conditions. The spec requires that clicking a day reveals separate Day and Night weather detail panels.

FORECAST DAY/NIGHT EXPANSION MANDATE: When a 14-day forecast card is expanded via click, it MUST reveal TWO clearly labeled sub-panels side by side (or stacked):
1. **DAY panel** — labeled "Daytime" with a Sun icon. Shows: daytime high (°F), day description, precipitation probability, UV index, wind speed/direction, sunrise time.
2. **NIGHT panel** — labeled "Overnight" with a Moon icon. Shows: overnight low (°F), night description, precipitation probability, humidity, wind speed, sunset and moonrise times.
Backend: The `/weather/daily` route MUST return `day_temp`, `night_temp`, `day_description`, `night_description`, `day_precip_pct`, `night_precip_pct`, `day_wind_speed`, `night_wind_speed`, `uvi`, `sunrise`, `sunset`, `moon_phase` for every day entry. Open-Meteo provides `temperature_2m_max` and `temperature_2m_min` separately; OWM One Call 3.0 provides `daily[i].temp.day` and `daily[i].temp.night`.
Frontend: Each day card MUST have `onClick` toggle. When expanded, ALWAYS render both panels. FORBIDDEN: `expanded && <div>Single combined description</div>` — two panels are MANDATORY.

---

### ROOT CAUSE: SEISMIC VIEW SHOWS 0 EARTHQUAKES DESPITE USGS RETURNING DATA — RESPONSE SHAPE MISMATCH
The Seismic view shows 0 earthquakes and "No recent events detected" even when USGS returns hundreds of events. Root cause: response-shape mismatch — the backend transforms USGS GeoJSON `features[]` but the frontend reads `data.features` instead of the transformed field name, OR the marker plot useEffect never fires because it keys on a state variable that was never updated.

SEISMIC DATA SHAPE CONTRACT: The `/seismic/feed` backend route MUST return `{"earthquakes": [...], "count": N}` where each item is `{lat, lon, magnitude, depth_km, place, time_str, magnitude_type}`. The frontend MUST read `data.earthquakes` (NOT `data.features`, `data.items`, or `data.results`). The Leaflet marker layer MUST iterate `data.earthquakes` and call `L.circleMarker([eq.lat, eq.lon], {...})` for EVERY item. The stat card MUST display `data.count ?? data.earthquakes?.length ?? 0` — NEVER a hardcoded 0. FORBIDDEN: frontend reading `data.features` from a backend route that does not return raw GeoJSON.

---

### ROOT CAUSE: AI LAB PERSONA DEBATE "AWAITING DOMAIN DATA" — DOMAIN REPORTS BOUND TO WRONG STATE
The Persona Debate tab shows "Awaiting domain data..." for all persona cards even when `/precursor/analysis` returns domain reports. Root cause: two separate state variables (`debateData` vs `precursorData`) that both fetch the same endpoint and never share results.

AI LAB PERSONA DEBATE DATA BINDING MANDATE: The Persona Debate tab MUST use the SAME state variable as the Pattern Studio tab for precursor analysis: `const [precursorData, setPrecursorData] = useState<any>(null)`. Both tabs read `precursorData?.domain_reports?.[persona.name]`. FORBIDDEN: a separate `setDebateData` / `debateData` state that duplicates the precursor fetch. The debate tab is a visualization of `/precursor/analysis` output — it MUST NOT call a separate `/ailab/debate` POST endpoint for the same per-persona reports that `/precursor/analysis` already returns.

---

## TOOLTIP / POPUP OVERFLOW MANDATE
Any UI element that renders a tooltip, hover popup, dropdown, or absolutely-positioned floating panel MUST NOT be clipped by an ancestor with `overflow:hidden`. Required:
1. The IMMEDIATE PARENT (and every ancestor up to the view root) of a tooltip-bearing element MUST set `overflow: visible` — OR the tooltip MUST render via a React portal (`createPortal(tip, document.body)`).
2. Pattern Studio / topology / synthesis-core diagrams that show "Anomaly Detected" labels MUST render the labels above the container (`zIndex >= 1000`) and outside any `overflow:hidden` ancestor.
3. A tooltip whose text is cut off by its container is REJECTED — every flagged anomaly tooltip MUST be fully readable.

---

### ROOT CAUSE: AI LAB MODEL COMPARE SHOWS "NO MODEL DATA AVAILABLE" — CHART NOT READING comparison_points

The Model Compare tab's Ensemble Forecast Divergence chart renders "No model data available" even though `/ailab/models` returns HTTP 200. Root cause: the frontend state setter receives `data` from the API but reads a wrong field name (e.g. `data.models`, `data.data`, or `data.chart`) instead of `data.comparison_points`.

AI LAB MODEL COMPARE CHART BINDING MANDATE: After fetching `/ailab/models`, the frontend MUST set chart state from `data.comparison_points` exclusively. The backend `/ailab/models` route MUST return `{"comparison_points": [{hour: str, gfs_temp: float, ecmwf_temp: float, icon_temp: float, hrrr_temp: float}, ...], "location": str}`. The Recharts `<LineChart>` MUST receive `comparison_points` as its `data` prop. Each temperature series MUST be a separate `<Line>` with a distinct color. FORBIDDEN: rendering an empty chart state when the API returns 200.

---

### ROOT CAUSE: OCEANIC INTELLIGENCE SHOWS "--" FOR WAVE HEIGHT AND SWELL — MARINE API NOT CALLED

The Oceanic Intelligence page header stat cards show "--" for Wave Height and Swell Direction because the backend `/ocean/current` route fetches only sea surface temperature (SST) and ocean currents but omits the Open-Meteo Marine API call for wave data.

OCEANIC WAVE DATA MANDATE: The backend `/ocean/current` route MUST call the Open-Meteo Marine API: `https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_period,swell_wave_height,swell_wave_direction,ocean_current_velocity,ocean_current_direction`. The response MUST include `wave_height` (meters), `wave_period` (seconds), `swell_direction` (degrees), `swell_direction_label` (compass string e.g. "NW"), `swell_height` (meters). The frontend MUST render `oceanData.wave_height` and `oceanData.swell_direction_label` in the stat cards. FORBIDDEN: displaying "--" when the API returns 200 with valid wave fields.

---

### ROOT CAUSE: RADAR SHOWS 0 FORECAST FRAMES — nowcast ARRAY IGNORED

The radar timeline shows "Past: 13 frames | Future: 0 frames" and caps at the current time because `radar.nowcast` from the RainViewer API is never merged into the frame array.

RADAR FORECAST FRAMES MANDATE: (see RULES section above — already defined at line ~657)

---

### ROOT CAUSE: "X IS NOT DEFINED" — SINGLE-LETTER LUCIDE ICON NOT IMPORTED

The Weather & Atmosphere view crashes with ErrorBoundary showing `X is not defined`. Root cause: the JSX component scanner uses regex `<([A-Z]\w+)` which requires at least two characters after `<`, silently excluding single-character uppercase component names like `<X />` (the lucide-react close/dismiss icon). As a result, `X` is never added to the undefined-component set and never injected into the lucide-react import during assembly.

SINGLE-CHARACTER LUCIDE ICON MANDATE: The JSX component scanner regex MUST use `[A-Z]\w*` (zero or more word chars) not `[A-Z]\w+` (one or more) so that single-character React components like `<X />`, `<I />`, and `<A />` are detected as used components. Any scanned uppercase component that is in the known lucide-react icon set MUST be injected into the lucide import block. FORBIDDEN: using `\w+` in any JSX component scan that is expected to catch all React component references including single-letter icons. Common single-letter lucide icons: `X` (close/dismiss), `I` (italic/info).

---

### ROOT CAUSE: "PLANETARY & STAR MAP" ERRORS ON RENDER — GEOLOCATION DENIED IN HEADLESS BROWSER

The Planetary & Star Map view reports an ErrorBoundary crash with message "Location access denied — enter your city above." in the render check functional tests. Root cause: Playwright is launched in headless mode without a browser context that grants geolocation permission. `navigator.geolocation.getCurrentPosition()` is denied immediately, and any component that throws on geolocation denial (instead of degrading gracefully) will be caught by the ErrorBoundary and reported as a crash — even though the component works correctly when geolocation is permitted.

RENDER CHECK GEOLOCATION MANDATE: The headless Playwright browser context MUST be created with `geolocation` permission granted and a default position (e.g., New York City: `latitude=40.7128, longitude=-74.0060`) so that components using `navigator.geolocation` receive a valid position during render validation. FORBIDDEN: launching `browser.new_page()` directly without a context that has `permissions=["geolocation"]` — this produces false-positive ErrorBoundary crash reports for any location-aware view. The default geolocation position MUST be a real city coordinate pair, not `{latitude: 0, longitude: 0}` (which sits in the ocean and may trigger edge cases in geographic APIs).
