# Assessment B — baseline technical evidence

Target: `D:/Football Prediction AI/apps/web/src/App.tsx` and the stored-provider fixture view at `http://127.0.0.1:5173/?view=provider&live_date=2026-10-25`.

This assessment was isolated from Assessment A. It reviews the baseline, not the parent's forthcoming changes. Read `reference/critique.md` Assessment B and `reference/audit.md`, `PRODUCT.md`, `DESIGN.md`, the supplied desktop/mobile screenshots, `detector-before.json`, and relevant React/CSS/API source. No source edits, application writes, provider requests, credential reads, or subagents were used. All authored files are inside `reports/impeccable/`.

## Provenance and limits

- Supplied baseline screenshots: desktop **1440 × 2542**, mobile **390 × 2917**, recorded 27 October 2026 at 14:43 local filesystem time.
- Independent browser measurements: headless Chromium through the repository's Playwright installation, fresh browser contexts at **1440 × 900**, **390 × 900**, and **320 × 900**, starting **2026-10-27T07:52:01Z**. Read-only DOM/computed-style evaluation and Tab traversal only; no injected markup, script tags, title changes, forced response mocks, or source mutations.
- Browser document heights at desktop and 390px matched the supplied screenshots exactly: 2542px and 2917px. The same hero, eight-item navigation, 16 fixtures, five league sections, and native-looking two-button subview switch were present. No live UI drift was observed during this measurement run.
- Complete DOM, keyboard, request, font, and resource evidence: `reports/impeccable/assessment-b-evidence.json`. Reproduction script: `assessment-b-probe.mjs`. Baseline SHA-256 hashes are recorded in the evidence file.
- Only localhost requests were allowed. All observed requests were GETs to the local Vite/API application. There were **zero external requests**, zero blocked external attempts, and zero uncaught page errors in the three baseline contexts.
- The native browser presentation/overlay workflow was skipped because this delegated assessment explicitly prohibits page mutation. No live-server was started and no user-visible overlay is claimed. The fallback is baseline screenshots plus computed DOM measurements and source evidence.
- A supplementary state-navigation probe (`assessment-b-states.mjs`) timed out after 30 seconds waiting for `networkidle` at `live_date=invalid`; it did not produce its planned JSON file. That failed probe is not treated as proof of a UI error or a performance regression. Missing/error-state conclusions below are explicitly source-based. Its pages were disposable; it made no application writes.
- Narrow viewport emulation is layout evidence, not synthesized-touch or physical-device evidence. Touch panning, 200% text zoom, screen-reader announcements, reduced-motion rendering, and modal keyboard trapping were not exercised. Production timing, field Core Web Vitals, and model behavior are outside this baseline technical assessment.

## Audit health

| Dimension | Score | Measured/source finding |
|---|---:|---|
| Accessibility | 2/4 | Native keyboard controls and useful labels exist; selected navigation state is visual-only, the brand lacks the authored focus style, and input boundaries are below 3:1. |
| Performance | 3/4 | Local baseline rendered without page errors; no heavy imagery or ongoing polling. All research modules load eagerly; production speed is not established by dev-server timings. |
| Theming | 1/4 | Dark palette is broadly consistent, but styles hard-code colors and roles rather than implement the documented tokens; no local webfont load exists. |
| Responsive design | 2/4 | Page stays within viewport, but fixture tables remain 640px wide inside 341/280px viewports, hiding status and analysis; target heights are below the documented 44px standard. |
| Implementation integrity | 2/4 | Real/mock and unknown-data caveats are preserved; operational hierarchy and shared components do not yet match the written product/design system. |
| **Total** | **10/20 — Acceptable** | Significant work remains in mobile fixtures, asynchronous state integrity, and consistent controls. |

These scores describe the inspected baseline, not a conformance certification.

## Deterministic scan

Reuse the supplied successful baseline detector artifact rather than run a second scan over potentially changing sources.

**Count: 1 warning, 0 other reported findings.** Rule: `side-tab` / “Side-tab accent border”, category `slop`, at `apps/web/src/style.css:3`, snippet `border-left:2px solid #a0b878`, imported by `main.tsx`.

Source verification: `.filter-protocol` has exactly that left border and is used in `FilteringPanel.tsx:27`. This is a real style occurrence, but **it is not present on the baseline provider screen**. Treat it as low-priority system drift against DESIGN.md's explicit no-side-tab rule, not a defect explaining the provider layout. The detector's generic claim about AI-generated appearance is not technical evidence. The one reported warning says nothing about contrast, responsive layout, keyboard behavior, or async correctness.

## Measured layout and readability

| Measurement | 1440px viewport | 390px viewport | 320px viewport |
|---|---:|---:|---:|
| Document horizontal width | 1440px | 390px | 320px |
| Provider page heading top | 776.8px | 800.0px | 860.2px |
| First league heading top | 1049.0px | 1256.5px | 1316.7px |
| First fixture table top | 1093.0px | 1300.5px | 1360.7px |
| First table visible content width | 1125px | 341px | 280px |
| First table scroll content width | 1125px | 640px | 640px |
| First analysis-action x position | 1043.4px | 587.8px | 583.6px |

At 390px, **299px of the table's width is outside its initial visible area**. At 320px, the hidden width is 360px. The first analysis action starts beyond the viewport in both narrow layouts. This matches the baseline mobile screenshot: the fixture identity is visible while API state and the analysis column are clipped inside each independently scrolling table. There is no whole-document horizontal overflow, so the problem must not be described as a page-width overflow.

Source: `style.css:1` applies `table{min-width:640px}` and `.table-wrap{overflow:auto}` globally. The provider view reuses these research-table rules rather than a dedicated fixture row. Data tables have a WCAG reflow exception; this is a major primary-flow usability failure and a DESIGN.md mismatch, not sufficient evidence by itself to assert an SC 1.4.10 violation.

Computed type sizes remain **12px for team names and analysis actions**, **10px for table headers**, **11px for date/select controls**, **9px for mobile metric supporting text**, and **9px for the footer**. The main marketing heading is 54px desktop, versus the documented page-title role of 28–32px. The documented 16px primary team/body, 14px controls, and 13px supporting roles are not implemented for fixture reading.

Control bounding boxes: date input **118 × 33px**; period select **134 × 35px**; league select **118 × 35px**; provider subview buttons **101.7 × 27px** and **94.8 × 27px**; first team button **177.6 × 16px**; repeated analysis button **60.1 × 16px**. Navigation buttons are 43px high desktop and 41px narrow. These miss the product's 44px ordinary-control target. Do **not** automatically claim SC 2.5.8 failure: several targets can qualify for inline-text or spacing exceptions, which were not fully audited.

## Contrast and keyboard evidence

Ratios below use computed CSS colors and their known solid surfaces; they are not a pixel-based overlay detector result.

| Pair | Ratio | Interpretation |
|---|---:|---|
| Intro supporting text `#91a59b` / body `#0c1513` | 7.12:1 | Passes AA normal text |
| Metric copy `#94aa9d` / surface `#111e18` | 6.95:1 | Passes AA normal text |
| Table heading `#93a895` / heading surface `#14231a` | 6.44:1 | Passes AA normal text |
| Footer `#6d8a76` / body `#0c1513` | 4.90:1 | Passes AA normal text; its 9px size remains a usability concern |
| Team action `#c6e8aa` / body `#0c1513` | 13.71:1 | Strong contrast |
| Authored focus `#c4e998` / body | 13.65:1 | Strong contrast |
| Control border `#36503f` / control fill `#16261e` | 1.79:1 | Below 3:1 non-text boundary target |
| Control border / surrounding body | 2.10:1 | Below 3:1 against outside as well |
| Brand's measured browser focus color `#101010` / body | 1.03:1 | Poor fallback focus visibility on this Chromium setup |

No sampled normal-text color was below 4.5:1. Do not report a generic low-text-contrast failure from the screenshot's small rendering.

Tab traversal reaches the brand link, all eight navigation buttons, date segments, both selects, both provider subview buttons, then the first team action. There was no trap in these first 18 Tab stops. Native date fields correctly occupy several internal segment stops; this is not repeated focus caused by application code. Controls other than the brand receive a 2px lime outline with 4px offset. The nav strip scrolls as later buttons receive focus.

Source gaps: `App.tsx:14` marks selection only with `.active`; all eight buttons have no `aria-current` or `aria-pressed`. The provider's two view buttons similarly expose no selected state. The repeated analysis actions all share the same accessible name “วิเคราะห์คู่จริง” with no team-specific context. `.brand` is an anchor, omitted from the `button,select,input,summary:focus-visible` selector in `centre.css:1`; its actual focus style was the browser's dark default. Native button semantics, visible text labels, Thai document language, a main landmark, and ordered h1/h2/h3 headings are positive evidence.

## Prioritized findings

### [P1] Primary fixture content and action require horizontal discovery on mobile

**Location:** `ProviderPreview.tsx:22` (provider table rendering), `style.css:1` (global table and text-button rules).

**Impact:** Status and analysis are outside the initial visible area; 12px team names and 16px-high actions compound the problem. The user must find and pan separate tables just to inspect a match. The desktop hero, caveat and metrics also push the first match table to y=1093; mobile reaches y=1301 before fixtures begin.

**Recommendation:** Use the documented fixture row: readable team identities stacked in a mobile row, kickoff/state/score adjacent, and a full-height analysis action. Retain horizontal research tables for actual multidimensional evidence. Move the compact date/filter toolbar and fixtures near the top; move research metrics to their relevant research screens.

**Commands:** `$impeccable adapt`, `$impeccable layout`, `$impeccable typeset`.

### [P1] Date/period changes can label previous data as the new round while the fetch is pending

**Location:** `ProviderPreview.tsx:8–13` (fixture effect), `:22` (date control and round label); `LiveDetail.tsx:10–11` has the same retained-detail pattern on filter changes.

**Evidence class:** Verified source behavior; no delayed-response injection was used.

**Impact:** A state change sets the new selected date immediately, but the fixture effect clears only `error`, not `data`; it has no loading state or pending label after the initial load. The old `data.items`, total, timestamp and forecast content remain while the heading uses the new `date`. The detail view similarly retains the old history while a new history scope/count is being fetched. This risks presenting mismatched football evidence as current.

**Recommendation:** Track request/loading state, keep the rendered data bound to its response date/scope, show an explicit updating status, and replace content only when the matching response succeeds. Reserve content space. Do not invent missing results or probabilities.

**Command:** `$impeccable harden`.

### [P1] Provider failures remove the recovery controls; daily HTTP errors lack validation

**Location:** `ProviderPreview.tsx:9–17`.

**Evidence class:** Source inspection, not a reproduced network failure. The supplementary invalid-URL networkidle timeout is inconclusive.

**Impact:** `if(error)return <p ...>` removes the provider section, including the date, period and league controls. A transient or date-specific failure leaves no retry or in-context recovery. The 409 fallback error exposes internal “API preflight” and “seed-provider-preview” setup commands. The daily-report fetch calls `r.json()` without checking `r.ok` or the expected data shape; a JSON error payload can reach code that immediately reads `daily.picks.filter`, creating a render failure. The main App also exposes a `seed-centre` instruction for quality-data failure.

**Recommendation:** Keep the page controls and selected date visible in the error state, provide retry and known-date recovery, distinguish unavailable recorded dates from an empty schedule, check status/shape for daily results, and give plain Thai guidance suitable for routine app use. Keep operator setup details in a secondary help surface.

**Command:** `$impeccable harden`, `$impeccable clarify`.

### [P1] Form boundaries have insufficient non-text contrast

**Location:** `centre.css:1` date input and `style.css:1` select rules.

**Impact/standard:** The custom boundaries needed to locate date/select controls measure 1.79:1 against their fill and 2.10:1 against their surrounding background, below SC 1.4.11's 3:1 target. The native arrows/calendar affordances were not separately pixel-tested. Text and focus colors are strong; preserve them.

**Recommendation:** Add a shared control boundary token that reaches 3:1 against the surface and keep consistent hover, focus, active and disabled states.

**Command:** `$impeccable colorize`, `$impeccable polish`.

### [P2] Keyboard and assistive selection state is incomplete

**Location:** `App.tsx:14`; provider subview buttons in `ProviderPreview.tsx:22`; focus selector in `centre.css:1`.

**Impact:** Selection is only visible through color/underline. The brand uses a barely visible browser-default outline. Repeated “วิเคราะห์คู่จริง” buttons do not identify the match by name when navigated out of table context. No skip link bypasses the hero/eight-item navigation.

**Recommendation:** Use clear link/navigation or button selection semantics, include the brand in the authored focus style, provide match-specific action names, and add a skip-to-fixtures path. Native dialog behavior exists for match details, but its full focus/escape cycle still requires browser verification after the redesign.

**Command:** `$impeccable harden`.

### [P2] Documented theme/typography system is not implemented in CSS

**Location:** `style.css:1–3`, `centre.css:1`, `index.html:1`.

**Impact:** Colors are repeated literal values instead of DESIGN.md tokens, and the incumbent CSS uses a different background/palette set. Many research and fixture roles share global rules, which produced the narrow table/text problem. IBM Plex Sans Thai is named in the CSS but no `@font-face`, font preload, or font stylesheet exists; `document.fonts` had zero loaded font-face entries and no font resource requests occurred. Typography therefore depends on fonts installed on the host. `document.fonts.check()` returning true is not proof that the requested family loaded.

**Recommendation:** Introduce the documented tokens and explicit type roles, load a local licensed Thai webfont with swap if available, and scope research table styles separately from fixtures. A light theme is not required by the product and its absence is not scored as a defect.

**Command:** `$impeccable typeset`, `$impeccable polish`.

### [P2] Recorded results and interface state are omitted from the main match flow

**Location:** `apps/api/live.ts:27` drops `Observation.score_90` when constructing `CentreFixture`; `packages/football/types.ts:1` has no score property; `ProviderPreview.tsx:22` prints only `f.status`. `ProviderPreview.tsx:15` writes date into the URL only when a match is opened.

**Impact:** The baseline contains finished/live states but no recorded score display. Missing scores are not falsely replaced with 0–0, which is good, yet users cannot see even recorded results in the fixture list. Date, period, league and provider subview changes are not consistently persisted to navigation state; refresh can restore a different selection. App navigation similarly writes `view` only for provider, so other research destinations are not durable links.

**Recommendation:** Carry nullable recorded scores with provenance into the display, render an explicit unknown state, translate status codes into consistent Thai labels, and serialize meaningful date/view/filter state. This is a display/data-contract change, not permission to recalculate model weights or backdate predictions.

**Command:** `$impeccable harden`, `$impeccable clarify`.

### [P3] Research-only side accent remains contrary to the written system

**Location:** `style.css:3`, `.filter-protocol`; deterministic `side-tab` warning.

**Impact:** Minor style drift in a secondary research view; no primary task failure. This is the only detector warning and must not displace the measurable issues above.

**Recommendation:** Replace the colored left border with a standard group divider/tonal surface if that research protocol block remains.

**Command:** `$impeccable polish`.

**Counts:** 0 P0, 4 P1, 3 P2, 1 P3. Related issues are grouped to avoid counting the same underlying mobile/global-style problem repeatedly.

## Missing/error states already handled well

The baseline explicitly warns that scores may have changed since the stored timestamp. Its empty fixture text says recorded data may be incomplete rather than asserting there are no games. The API reports source dates and partial completeness. Mock and real-provider views remain separate. Missing analysis is presented as missing, not as invented probabilities; live detail refuses to create a backdated prediction after kickoff. These distinctions are part of the product's integrity and must survive visual cleanup.

A league with zero recorded items still renders an empty header-only table (Championship in the screenshots). This is a secondary issue: use a compact truthful league-specific empty message instead of an empty table, and avoid making zero recorded rows look like confirmed absence.

## Performance observations

The local dev baseline had **0 uncaught page errors**. FCP was **568ms desktop**, **584ms at 390px**, and **404ms at 320px**; DOMContentLoaded was 324/424/265ms respectively. Completed local fixture/history requests took approximately **192–645ms** across these single runs. These are unthrottled local development measurements, not production or field claims.

The provider page loaded **zero images** and no fonts. That avoids image weight but also confirms that real team/league logo identity and the intended local font have not yet been implemented. No provider polling runs in these React effects; static cached data is read from local endpoints.

All research screens are statically imported by `App.tsx`, so Vite fetched their modules even on the provider route. Development script resource bodies total about **4.14MB**, dominated by the development React runtime, source maps and HMR; do not report that as a 4MB production bundle. The existing `dist/assets` at inspection contained a **310,245-byte JS file** and **12,077-byte CSS file**, with no freshness guarantee relative to this baseline. A production build was not run because the parent is editing the UI and this assignment is read-only outside reports.

`React.StrictMode` creates duplicate development fixture/history requests (one cancelled/zero-body attempt and one completed attempt for each endpoint). This is expected dev behavior, not proof of duplicate production fetching. No layout-reading loops, broad `will-change`, continuously running animation, or unbounded animated effect were found in the inspected source. The only baseline card transition is background color over 0.2s. There is no `prefers-reduced-motion` rule, but no observed task-blocking motion warrants declaring a motion accessibility failure. The research image elements lack width/height and lazy loading; this is a modest follow-up if retained, not the primary provider performance issue.

## Recommended order for the parent

1. `$impeccable adapt` / `$impeccable layout`: dedicated mobile fixture rows and earlier access to fixtures.
2. `$impeccable harden`: request-state consistency, resilient provider/daily errors, URL state, score nullability and keyboard semantics.
3. `$impeccable typeset` / `$impeccable colorize`: shared readable type/control roles, actual local font loading, and stronger control boundaries.
4. `$impeccable polish`: unify all legacy research screens with the shared tokens and remove the isolated detector warning.

Recheck these concrete measurements after changes. Preserve truthful unknown states, real/mock separation, frozen model policy, and before-kickoff restrictions.
