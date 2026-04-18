import asyncio
import logging
from typing import Dict, List
from persona_logger import narrate

logger = logging.getLogger("RenderCheck")

FUNCTIONAL_CHECK_JS = """() => {
    const results = {
        maps: { found: 0, rendered: 0, details: [] },
        buttons: { found: 0, with_handlers: 0, clicked: 0, errors: [], details: [] },
        nav_tabs: { found: 0, clickable: 0, switched: 0, details: [] },
        toggles: { found: 0, responsive: 0, details: [] },
        selects: { found: 0, with_options: 0, details: [] },
        inputs: { found: 0, typeable: 0, details: [] },
        data_sections: { found: 0, with_content: 0, empty: [], details: [] },
        images: { found: 0, loaded: 0, broken: [], details: [] },
    };

    // ── MAP CHECK ──
    const mapContainers = document.querySelectorAll(
        '.leaflet-container, [class*="map-container"], [class*="mapContainer"], [id*="map"], ' +
        '[class*="radar"], [class*="Radar"], [class*="seismic-map"], [class*="aurora-map"]'
    );
    results.maps.found = mapContainers.length;
    mapContainers.forEach((mc, i) => {
        const tiles = mc.querySelectorAll('.leaflet-tile, .leaflet-tile-loaded, img[src*="tile"]');
        const hasCanvas = mc.querySelector('canvas');
        const hasSvg = mc.querySelector('svg');
        // Don't count ErrorBoundary content or empty error divs as rendered maps
        const hasErrorUI = mc.innerHTML.includes('View Error') || mc.innerHTML.includes('View Module Error') || mc.innerHTML.includes('Cannot access');
        const rendered = !hasErrorUI && (tiles.length > 0 || !!hasCanvas || !!hasSvg || mc.innerHTML.length > 200);
        if (rendered) results.maps.rendered++;
        results.maps.details.push({
            index: i,
            rendered: rendered,
            tileCount: tiles.length,
            htmlLength: mc.innerHTML.length,
            hasCanvas: !!hasCanvas,
            visible: mc.offsetHeight > 0 && mc.offsetWidth > 0
        });
    });

    // ── BUTTON CHECK ──
    const buttons = document.querySelectorAll('button, [role="button"], a.btn, [class*="btn-"], input[type="button"], input[type="submit"]');
    results.buttons.found = buttons.length;
    buttons.forEach((btn, i) => {
        if (i >= 30) return;
        const label = (btn.textContent || btn.getAttribute('aria-label') || btn.getAttribute('title') || '').trim().substring(0, 60);
        const hasOnClick = !!btn.onclick;
        const listeners = typeof getEventListeners === 'function' ? getEventListeners(btn) : null;
        const hasListeners = listeners ? Object.keys(listeners).length > 0 : null;
        const reactFiber = Object.keys(btn).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
        const reactProps = Object.keys(btn).find(k => k.startsWith('__reactProps'));
        let hasReactHandler = false;
        if (reactProps) {
            const props = btn[reactProps];
            hasReactHandler = !!(props && (props.onClick || props.onChange || props.onSubmit || props.onMouseDown));
        }
        const hasHandler = hasOnClick || hasReactHandler || (hasListeners === true);
        if (hasHandler) results.buttons.with_handlers++;
        const isDisabled = btn.disabled || btn.getAttribute('aria-disabled') === 'true';
        results.buttons.details.push({
            index: i,
            label: label || `(unlabeled button #${i})`,
            hasHandler: hasHandler,
            hasReactHandler: hasReactHandler,
            disabled: isDisabled,
            visible: btn.offsetHeight > 0 && btn.offsetWidth > 0
        });
    });

    // ── NAV/TAB CHECK ──
    const navItems = document.querySelectorAll(
        'nav a, nav button, [role="tab"], [role="tablist"] > *, ' +
        '[class*="nav-"] button, [class*="nav-"] a, [class*="tab"] button, [class*="sidebar"] button, [class*="sidebar"] a, ' +
        '[class*="menu-item"], [class*="MenuItem"]'
    );
    results.nav_tabs.found = navItems.length;
    navItems.forEach((nav, i) => {
        if (i >= 20) return;
        const label = (nav.textContent || '').trim().substring(0, 40);
        const reactProps = Object.keys(nav).find(k => k.startsWith('__reactProps'));
        let clickable = !!nav.onclick;
        if (reactProps) {
            const props = nav[reactProps];
            clickable = clickable || !!(props && props.onClick);
        }
        if (nav.tagName === 'A' && nav.href) clickable = true;
        if (clickable) results.nav_tabs.clickable++;
        results.nav_tabs.details.push({ index: i, label: label, clickable: clickable });
    });

    // ── TOGGLE/SWITCH CHECK ──
    const toggles = document.querySelectorAll(
        'input[type="checkbox"], input[type="radio"], [role="switch"], [role="checkbox"], ' +
        '[class*="toggle"], [class*="Toggle"], [class*="switch"], [class*="Switch"]'
    );
    results.toggles.found = toggles.length;
    toggles.forEach((tog, i) => {
        if (i >= 20) return;
        const reactProps = Object.keys(tog).find(k => k.startsWith('__reactProps'));
        let responsive = !!tog.onchange || !!tog.onclick;
        if (reactProps) {
            const props = tog[reactProps];
            responsive = responsive || !!(props && (props.onChange || props.onClick));
        }
        if (responsive) results.toggles.responsive++;
        const label = (tog.getAttribute('aria-label') || tog.closest('label')?.textContent || '').trim().substring(0, 40);
        results.toggles.details.push({ index: i, label: label, responsive: responsive });
    });

    // ── SELECT/DROPDOWN CHECK ──
    const selects = document.querySelectorAll('select, [role="listbox"], [role="combobox"]');
    results.selects.found = selects.length;
    selects.forEach((sel, i) => {
        const optionCount = sel.querySelectorAll('option').length;
        if (optionCount > 0) results.selects.with_options++;
        results.selects.details.push({ index: i, optionCount: optionCount });
    });

    // ── INPUT CHECK ──
    const inputs = document.querySelectorAll('input[type="text"], input[type="search"], input[type="number"], input[type="email"], textarea');
    results.inputs.found = inputs.length;
    inputs.forEach((inp, i) => {
        if (i >= 15) return;
        const notDisabled = !inp.disabled && !inp.readOnly;
        if (notDisabled) results.inputs.typeable++;
    });

    // ── DATA SECTION CHECK (cards, tables, lists that should have dynamic content) ──
    const dataSections = document.querySelectorAll(
        '[class*="card"], [class*="Card"], table, [class*="grid"], [class*="Grid"], ' +
        '[class*="list"], [class*="List"], [class*="panel"], [class*="Panel"], ' +
        '[class*="section"], [class*="Section"], [class*="widget"], [class*="Widget"]'
    );
    results.data_sections.found = dataSections.length;
    dataSections.forEach((ds, i) => {
        if (i >= 40) return;
        const text = (ds.innerText || '').trim();
        const hasContent = text.length > 10;
        if (hasContent) {
            results.data_sections.with_content++;
        } else {
            const id = ds.id || ds.className?.toString().substring(0, 40) || `section_${i}`;
            results.data_sections.empty.push(id);
        }
    });

    // ── IMAGE CHECK ──
    const images = document.querySelectorAll('img');
    results.images.found = images.length;
    images.forEach((img, i) => {
        if (img.naturalWidth > 0 || img.complete) {
            results.images.loaded++;
        } else {
            results.images.broken.push((img.src || '').substring(0, 80));
        }
    });

    return results;
}"""

BUTTON_CLICK_TEST_JS = """async () => {
    const errors = [];
    const clicked = [];
    const buttons = document.querySelectorAll('button, [role="button"]');
    const testButtons = Array.from(buttons).slice(0, 10);

    for (let i = 0; i < testButtons.length; i++) {
        const btn = testButtons[i];
        const label = (btn.textContent || '').trim().substring(0, 40);
        if (btn.disabled) continue;
        if (!btn.offsetHeight || !btn.offsetWidth) continue;
        const beforeHTML = document.getElementById('root')?.innerHTML.length || 0;
        try {
            btn.click();
            await new Promise(r => setTimeout(r, 300));
            const afterHTML = document.getElementById('root')?.innerHTML.length || 0;
            if (afterHTML < 10 && beforeHTML > 50) {
                errors.push(`Button "${label}" crashed the page (root went from ${beforeHTML} to ${afterHTML} chars)`);
            } else {
                clicked.push(label);
            }
        } catch (e) {
            errors.push(`Button "${label}" threw: ${e.message}`);
        }
    }
    return { clicked: clicked.length, errors: errors };
}"""

PER_VIEW_TEST_JS = r"""async () => {
    const results = { switched: 0, errors: [], views_found: [], view_reports: [] };
    const navItems = document.querySelectorAll(
        'nav a, nav button, [role="tab"], [role="tablist"] > *, aside a, aside button, ' +
        '[class*="nav-"] button, [class*="nav-"] a, [class*="sidebar"] button, [class*="sidebar"] a, ' +
        '[class*="menu-item"], [class*="MenuItem"], [class*="nav-item"], [class*="NavItem"], ' +
        'header a, header button, [class*="navItem"], [class*="sidebarItem"]'
    );
    const items = Array.from(navItems).filter(el => el.offsetHeight > 0 && el.offsetWidth > 0).slice(0, 20);

    function checkReactHandlers(el) {
        const rp = Object.keys(el).find(k => k.startsWith('__reactProps'));
        if (!rp) return false;
        const props = el[rp];
        return !!(props && (props.onClick || props.onChange || props.onSubmit || props.onMouseDown));
    }

    for (let i = 0; i < items.length; i++) {
        const nav = items[i];
        const label = (nav.getAttribute('aria-label') || nav.innerText || nav.textContent || '').trim().replace(/\s+/g, ' ').substring(0, 40);
        if (!nav.offsetHeight || !nav.offsetWidth) continue;
        const beforeHTML = document.getElementById('root')?.innerHTML.length || 0;
        try {
            nav.click();
            await new Promise(r => setTimeout(r, 2500));
            const afterHTML = document.getElementById('root')?.innerHTML.length || 0;
            if (afterHTML < 10 && beforeHTML > 50) {
                results.errors.push(`Nav "${label}" crashed the page (root went from ${beforeHTML} to ${afterHTML} chars)`);
                continue;
            }
            results.switched++;
            results.views_found.push(label);

            const report = { view: label, issues: [] };

            const maps = document.querySelectorAll('.leaflet-container, [class*="map-container"], [class*="mapContainer"]');
            if (maps.length > 0) {
                let mapsRendered = 0;
                maps.forEach(mc => {
                    const tiles = mc.querySelectorAll('.leaflet-tile, .leaflet-tile-loaded');
                    const hasSvg = mc.querySelector('svg');
                    const hasCanvas = mc.querySelector('canvas');
                    if (tiles.length > 0 || hasSvg || hasCanvas || mc.innerHTML.length > 200) mapsRendered++;
                });
                if (mapsRendered === 0) {
                    report.issues.push(`VIEW "${label}": ${maps.length} map container(s) found but NONE rendered — no tiles loaded, no SVG/canvas content`);
                }
                maps.forEach(mc => {
                    if (mc.offsetHeight < 10 || mc.offsetWidth < 10) {
                        report.issues.push(`VIEW "${label}": Map container has 0 height/width — invisible. Needs explicit height style.`);
                    }
                });
            }

            const btns = document.querySelectorAll('button, [role="button"]');
            let viewBtns = 0, viewBtnsWithHandlers = 0;
            const deadBtnLabels = [];
            btns.forEach(btn => {
                if (!btn.offsetHeight || !btn.offsetWidth) return;
                viewBtns++;
                if (btn.onclick || checkReactHandlers(btn)) {
                    viewBtnsWithHandlers++;
                } else {
                    const bl = (btn.textContent || '').trim().substring(0, 30);
                    if (bl && deadBtnLabels.length < 3) deadBtnLabels.push(bl);
                }
            });
            if (viewBtns > 2 && viewBtnsWithHandlers === 0) {
                report.issues.push(`VIEW "${label}": ${viewBtns} visible button(s) but NONE have click handlers. Examples: ${deadBtnLabels.join(', ')}`);
            }

            const dataSections = document.querySelectorAll('[class*="card"], [class*="Card"], table, [class*="panel"], [class*="Panel"]');
            let withContent = 0, empty = 0;
            dataSections.forEach(ds => {
                if (!ds.offsetHeight || !ds.offsetWidth) return;
                const text = (ds.innerText || '').trim();
                if (text.length > 15) withContent++;
                else empty++;
            });
            if (dataSections.length > 3 && withContent === 0) {
                report.issues.push(`VIEW "${label}": ${dataSections.length} data section(s) found but ALL are empty — no data displayed`);
            }

            const toggles = document.querySelectorAll('input[type="checkbox"], input[type="radio"], [role="switch"]');
            if (toggles.length > 0) {
                let responsive = 0;
                toggles.forEach(t => { if (t.onchange || t.onclick || checkReactHandlers(t)) responsive++; });
                if (responsive === 0) {
                    report.issues.push(`VIEW "${label}": ${toggles.length} toggle(s) found but NONE have handlers`);
                }
            }

            // DATA DESERT CHECK: detect views showing only zeros, dashes, and N/A with no real data.
            // IMPORTANT: ALL-CAPS label text (e.g. "WIND DYNAMICS", "RECENT QUAKES (7D)") and
            // pure time strings (e.g. "12:00") must NOT count as real data — they are labels/fallbacks.
            const zeroPattern = /^(?:0|0\.0+|0°|0 mph|0 km\/h|0\.00|N\/A|--+|-+|none|null|undefined|Waiting.*|No .*found\.|Fetching.*|Calculating\.|Loading\.)$/i;
            const allCapsLabelPattern = /^[A-Z][A-Z\s\d\(\)\/\-\u2013&%°\.,:!]+$/;
            const pureTimePattern = /^\d{1,2}:\d{2}(\s*(AM|PM))?$/i;
            const statCells = document.querySelectorAll('[class*="card"] *, [class*="stat"] *, [class*="metric"] *, [class*="value"] *, td, [class*="panel"] *');
            let zeroValCount = 0, realDataCount = 0;
            statCells.forEach(el => {
                if (!el.offsetHeight || el.children.length > 0) return;
                const t = (el.innerText || '').trim();
                if (!t || t.length < 2) return;
                if (zeroPattern.test(t)) {
                    zeroValCount++;
                } else if (!allCapsLabelPattern.test(t) && !pureTimePattern.test(t) && /\d/.test(t)) {
                    // Has digits, not all-caps label, not just a time → real data value
                    realDataCount++;
                }
            });
            if (zeroValCount > 4 && realDataCount === 0) {
                report.issues.push(`VIEW "${label}": Data desert — ${zeroValCount} value cell(s) show only zeros/N/A/dashes with no real API data loaded`);
            }

            // ERROR BOUNDARY CRASH CHECK: detect if ErrorBoundary caught a crash in this view.
            // Check both headings AND any element with error-boundary-style text content.
            // ERROR BOUNDARY keyword set — matches any word-order variant the LLM may use.
            function isErrorBoundaryText(s) {
                return s.includes('Module View Error') || s.includes('View Module Error') ||
                       s.includes('View Render Error') || s.includes('Render Error') ||
                       s.includes('View Error') || s.includes('Something went wrong') ||
                       s.includes('Component Error') || s.includes('critical error') ||
                       s.includes('application shell has safely caught');
            }
            const allHeadings = document.querySelectorAll('h1, h2, h3, h4, h5');
            allHeadings.forEach(h => {
                const htext = (h.textContent || '').trim();
                if (isErrorBoundaryText(htext)) {
                    // Look for the error message near the heading (sibling, parent text, or code element)
                    const codeEl = h.closest('div')?.querySelector('code, pre, [class*="error"]');
                    const errMsg = (codeEl?.textContent || h.nextElementSibling?.textContent || '').trim().substring(0, 150);
                    report.issues.push(`VIEW "${label}": ErrorBoundary crash — "${errMsg || htext}". This view crashes on render and is non-functional.`);
                }
            });
            // Also check all leaf text nodes — ErrorBoundary may use <p>, <span>, or <div>
            const allLeafEls = document.querySelectorAll('p, span, div, code, pre');
            const seenErrors = new Set();
            allLeafEls.forEach(el => {
                if (el.children.length > 0) return;
                const t = (el.innerText || '').trim();
                if (t.length > 5 && t.length < 300) {
                    if (isErrorBoundaryText(t) && !seenErrors.has('boundary')) {
                        seenErrors.add('boundary');
                        const nextSib = el.nextElementSibling;
                        const codeEl = el.closest('div')?.querySelector('code, pre');
                        const errMsg = (codeEl?.textContent || nextSib?.innerText || '').trim().substring(0, 150);
                        report.issues.push(`VIEW "${label}": ErrorBoundary crash — "${errMsg || t}". This view crashes on render.`);
                    }
                    // Catch raw JS runtime errors shown in DOM (e.g. "Lucide is not defined")
                    if ((t.includes('is not defined') || t.includes('Cannot access') || t.includes('before initialization')) && !seenErrors.has(t)) {
                        seenErrors.add(t);
                        report.issues.push(`VIEW "${label}": Runtime JS error in DOM — "${t}". Component crashed.`);
                    }
                }
            });

            if (report.issues.length > 0) {
                results.view_reports.push(report);
                report.issues.forEach(iss => results.errors.push(iss));
            }
        } catch (e) {
            results.errors.push(`Nav "${label}" threw: ${e.message}`);
        }
    }
    return results;
}"""


async def check_module_renders(module_name: str, port: int = 8000, timeout_ms: int = 8000) -> Dict:
    result = {
        "rendered": False,
        "root_html_length": 0,
        "console_errors": [],
        "error_summary": "",
        "page_title": "",
        "functional": {},
        "functional_failures": [],
    }
    url = f"http://127.0.0.1:{port}/static/built/modules/{module_name}/index.html"
    narrate("Dr. Mira Kessler", f"Render check: loading {url} in headless browser...")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        narrate("Dr. Mira Kessler", "Render check SKIPPED — playwright not installed.")
        result["error_summary"] = "playwright not installed"
        return result

    pw = None
    browser = None
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        console_errors = []

        def _on_console(msg):
            if msg.type in ("error", "warning"):
                console_errors.append(f"[{msg.type}] {msg.text}")

        def _on_page_error(error):
            console_errors.append(f"[uncaught] {error.message if hasattr(error, 'message') else str(error)}")

        page.on("console", _on_console)
        page.on("pageerror", _on_page_error)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as nav_err:
            result["error_summary"] = f"Navigation failed: {nav_err}"
            result["console_errors"] = console_errors
            narrate("Dr. Mira Kessler", f"Render check FAILED: could not load page — {nav_err}")
            return result

        await page.wait_for_timeout(3000)

        root_info = await page.evaluate("""() => {
            const root = document.getElementById('root');
            if (!root) return { exists: false, childCount: 0, htmlLength: 0, text: '' };
            return {
                exists: true,
                childCount: root.children.length,
                htmlLength: root.innerHTML.length,
                text: root.innerText.substring(0, 500)
            };
        }""")

        result["root_html_length"] = root_info.get("htmlLength", 0)
        result["console_errors"] = console_errors
        result["page_title"] = await page.title()

        if not root_info.get("exists"):
            result["error_summary"] = "No #root element found in DOM"
            narrate("Dr. Mira Kessler", "Render check FAILED: #root element missing from DOM.")
            return result
        elif root_info.get("htmlLength", 0) < 50:
            error_msgs = [e for e in console_errors if "[uncaught]" in e or "[error]" in e]
            summary = "; ".join(error_msgs[:5]) if error_msgs else "No console errors captured — component returned empty JSX"
            result["error_summary"] = f"Blank render (root innerHTML={root_info['htmlLength']} chars). Errors: {summary}"
            narrate("Dr. Mira Kessler", f"Render check FAILED: blank page detected ({root_info['htmlLength']} chars in #root). {len(console_errors)} console error(s).")
            return result

        result["rendered"] = True
        narrate("Dr. Mira Kessler", f"Render check PASSED: page rendered ({root_info['htmlLength']} chars, {root_info['childCount']} children). Running functional tests...")

        # ── FUNCTIONAL SMOKE TESTS ──
        functional_failures = []

        try:
            func_results = await page.evaluate(FUNCTIONAL_CHECK_JS)
            result["functional"] = func_results

            maps = func_results.get("maps", {})
            if maps.get("found", 0) > 0 and maps.get("rendered", 0) == 0:
                functional_failures.append(
                    f"MAPS: {maps['found']} map container(s) found but NONE rendered (no tiles, no canvas, no SVG). "
                    f"Likely: Leaflet not initialized, missing MapContainer/TileLayer, or map container has 0 height."
                )
            elif maps.get("found", 0) > 0:
                not_visible = [d for d in maps.get("details", []) if not d.get("visible")]
                if not_visible:
                    functional_failures.append(
                        f"MAPS: {len(not_visible)}/{maps['found']} map(s) have 0 height/width — invisible to user. "
                        f"Likely: parent container needs explicit height style."
                    )

            btns = func_results.get("buttons", {})
            if btns.get("found", 0) > 0 and btns.get("with_handlers", 0) == 0:
                functional_failures.append(
                    f"BUTTONS: {btns['found']} button(s) found but NONE have click handlers. "
                    f"All buttons are non-functional. Likely: onClick props missing or not bound."
                )
            elif btns.get("found", 0) > 3:
                dead_pct = 1 - (btns.get("with_handlers", 0) / btns["found"])
                if dead_pct > 0.5:
                    dead_labels = [d["label"] for d in btns.get("details", []) if not d.get("hasHandler") and d.get("label")][:5]
                    functional_failures.append(
                        f"BUTTONS: {btns['found'] - btns['with_handlers']}/{btns['found']} buttons have NO click handlers. "
                        f"Examples: {', '.join(dead_labels)}. Likely: onClick not bound to these buttons."
                    )

            navs = func_results.get("nav_tabs", {})
            if navs.get("found", 0) > 0 and navs.get("clickable", 0) == 0:
                functional_failures.append(
                    f"NAVIGATION: {navs['found']} nav/tab items found but NONE are clickable. "
                    f"Users cannot switch between pages/views."
                )

            toggles = func_results.get("toggles", {})
            if toggles.get("found", 0) > 0 and toggles.get("responsive", 0) == 0:
                functional_failures.append(
                    f"TOGGLES: {toggles['found']} toggle/switch elements found but NONE have onChange/onClick handlers. "
                    f"All toggles are non-functional."
                )

            data = func_results.get("data_sections", {})
            if data.get("found", 0) > 5 and data.get("with_content", 0) == 0:
                functional_failures.append(
                    f"DATA SECTIONS: {data['found']} card/panel/section elements found but ALL are empty. "
                    f"No data is being displayed. Likely: API calls failing or data not rendered."
                )

            imgs = func_results.get("images", {})
            if imgs.get("found", 0) > 0 and imgs.get("loaded", 0) == 0:
                broken_srcs = imgs.get("broken", [])[:3]
                functional_failures.append(
                    f"IMAGES: {imgs['found']} image(s) found but NONE loaded. "
                    f"Broken sources: {', '.join(broken_srcs) if broken_srcs else 'unknown'}"
                )

        except Exception as func_err:
            narrate("Dr. Mira Kessler", f"Functional static analysis error (non-fatal): {func_err}")

        # ── INTERACTIVE TESTS (click buttons, navigate tabs) ──
        pre_click_errors = len(console_errors)
        try:
            btn_test = await page.evaluate(BUTTON_CLICK_TEST_JS)
            result["functional"]["button_click_test"] = btn_test
            if btn_test.get("errors"):
                for e in btn_test["errors"]:
                    functional_failures.append(f"BUTTON CRASH: {e}")
            if btn_test.get("clicked", 0) > 0:
                narrate("Dr. Mira Kessler", f"Button click test: {btn_test['clicked']} button(s) clicked without crash.")
        except Exception as btn_err:
            narrate("Dr. Mira Kessler", f"Button click test error (non-fatal): {btn_err}")

        post_btn_errors = console_errors[pre_click_errors:]
        crash_errors = [e for e in post_btn_errors if "[uncaught]" in e]
        if crash_errors:
            functional_failures.append(
                f"BUTTON RUNTIME ERRORS: {len(crash_errors)} uncaught error(s) after clicking buttons: "
                + "; ".join(crash_errors[:3])
            )

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(2000)
            nav_test = await page.evaluate(PER_VIEW_TEST_JS)
            result["functional"]["nav_click_test"] = nav_test
            if nav_test.get("errors"):
                for e in nav_test["errors"]:
                    functional_failures.append(e)
            if nav_test.get("switched", 0) > 0:
                narrate("Dr. Mira Kessler", f"Per-view test: {nav_test['switched']} view(s) tested: {', '.join(nav_test.get('views_found', []))}")
            view_reports = nav_test.get("view_reports", [])
            if view_reports:
                narrate("Dr. Mira Kessler", f"Per-view test: {len(view_reports)} view(s) have functional issues.")
                for vr in view_reports:
                    for iss in vr.get("issues", []):
                        narrate("Dr. Mira Kessler", f"  VIEW FAIL: {iss[:200]}")
                        functional_failures.append(iss)
        except Exception as nav_err:
            narrate("Dr. Mira Kessler", f"Per-view test error (non-fatal): {nav_err}")

        result["functional_failures"] = functional_failures

        if functional_failures:
            result["rendered"] = False
            summary = "; ".join(functional_failures[:5])
            result["error_summary"] = f"Page renders but has {len(functional_failures)} functional issue(s): {summary}"
            narrate("Dr. Mira Kessler", f"Functional test FAILED: {len(functional_failures)} issue(s) found.")
            for ff in functional_failures:
                narrate("Dr. Mira Kessler", f"  FAIL: {ff[:200]}")
        else:
            narrate("Dr. Mira Kessler", f"Functional tests PASSED: maps={func_results.get('maps',{}).get('rendered',0)}, "
                     f"buttons={func_results.get('buttons',{}).get('with_handlers',0)}, "
                     f"navs={func_results.get('nav_tabs',{}).get('clickable',0)}, "
                     f"toggles={func_results.get('toggles',{}).get('responsive',0)}")

    except Exception as e:
        result["error_summary"] = f"Render check exception: {e}"
        narrate("Dr. Mira Kessler", f"Render check ERROR: {e}")
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if pw:
            try:
                await pw.stop()
            except Exception:
                pass

    return result
