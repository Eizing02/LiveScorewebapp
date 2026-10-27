Method: independent Assessment A (design review; agent /root/impeccable_design_review). No detector or Assessment B output was read.

# Assessment A — สนามข้อมูล / Football Prediction AI

Review date: 27 October 2026, Asia/Bangkok. Scope: the current fixture entry and match-detail flow, using PRODUCT.md, DESIGN.md, docs/USABLE_APP_PLAN_TH.md, before-desktop.png (1440px), before-mobile.png (390px), a fresh browser tab at http://127.0.0.1:5173/?view=provider&live_date=2026-10-25, and limited source inspection of App.tsx, ProviderPreview.tsx, LiveDetail.tsx and the two existing stylesheets. The frozen screenshots define the baseline if implementation changes during the wider task. No provider requests, credentials, application edits, or automated detectors were used.

## Design specificity verdict

The pine and lime palette, Thai brand, actual competitions, Bangkok football-day boundary and explicit separation of model versus provider data already belong to this product. Preserve them. The composition is less specific: a promotional headline, three retrospective metrics, repeated warning strips and eight equal navigation choices precede the actual football desk. Much of the opening screen could be reused for an unrelated analytics prototype without changing its structure.

The strongest opportunity is to make the 06:00–06:00 fixture round the organizing idea: date and coverage, league, teams, kickoff, recorded state and a clear analysis action. This creates product character through football work rather than decoration. No extra hero, glow or animated scoreboard is needed.

## Overall impression

The app communicates conscientious research, but routine use feels like entering the research lab before reaching the fixtures. On the live desktop viewport (approximately 1265 × 712), the first screen ends at the navigation; no match is visible. In the 390px baseline, the first fixture is approximately 1,350px down the page. The user should see what can be inspected immediately and then choose how much evidence to open.

## Design health

Scores describe the reviewed surfaces, not a claim about every project page. All ten heuristics apply to this operational app.

| # | Heuristic | Score / 4 | Evidence |
|---|---|---:|---|
| 1 | Visibility of system status | 2 | Captured time and model limitations are visible, but stale rows still say “live”; the two fixture/summary buttons lack an active treatment. |
| 2 | Match between system and real world | 2 | Thai league/fixture framing and Bangkok day are useful; API status words, source dates, identity jargon and mixed calendar formats require translation. |
| 3 | User control and freedom | 2 | The detail dialog has a close control and native Escape behavior. Opening it replaces the current history entry, so normal Back behavior does not represent the drill-down. |
| 4 | Consistency and standards | 2 | Palette and borders are coherent; browser-default white buttons sit beside styled selects and tiny text actions, and daily/summary labels overlap. |
| 5 | Error prevention | 2 | The interface explicitly refuses retrospective predictions and distinguishes real/demo data, but default mock entry and old “live” labels still invite misreading. |
| 6 | Recognition rather than recall | 2 | League grouping helps recognition. Missing logos, horizontally separated row actions and hidden navigation choices make it harder on mobile. |
| 7 | Flexibility and efficiency | 1 | Date and league controls exist. No team search or Today/Tomorrow shortcuts are visible, and routine browsing starts after a long introduction. |
| 8 | Aesthetic and minimalist design | 1 | The restrained colors work, but hero, research totals and repeated cautions occupy the most valuable space. |
| 9 | Error recognition and recovery | 2 | Several messages honestly explain missing data. Source shows a failure path replacing the whole fixture section and suggesting internal preflight/seed commands instead of an in-app recovery. |
| 10 | Help and documentation | 2 | The 06:00 boundary and experimental status are explained. Other explanations are dense and technical rather than short, contextual assistance. |
| **Total** | **Poor — major usability work needed** | **18 / 40** | **The principal weaknesses are task hierarchy, mobile reading and navigation.** |

## What is working

1. **Honest evidence language.** The captured timestamp, separate provider forecast heading, missing-data explanations and explicit refusal to create a prediction after kickoff protect the meaning of the numbers. Keep these distinctions while shortening their presentation.
2. **A coherent quiet identity.** Dark pine, lime, fine dividers and the Thai wordmark suit an evening football desk. The product does not need a new visual brand.
3. **Useful domain structure.** Actual league grouping, fixture counts, Bangkok time and 5/10/20-match history choices support the real workflow. The detail view contains genuine comparison material rather than empty dashboard metrics.

## Priority issues

No P0 blocker was established in the reviewed fixture flow: team-name buttons provide a working path into a detail dialog. The following issues materially hinder the intended routine use.

### [P1] The opening hierarchy privileges research over tonight’s football

**Evidence:** Both baseline screenshots place the two-line headline, real/demo explanation and retrospective 17,027 / 2,705 / 06:00 metric strip ahead of eight main tabs. Source initializes the root view to the simulated MatchCentre unless view=provider is supplied. The screenshot’s real-data route is therefore already a more direct path than the ordinary entry.

**Impact:** A returning Thai reader cannot answer “มีคู่ไหนจะเตะและดูวิเคราะห์ตรงไหน” from the first viewport. Large historical counts also command more attention than the available fixture round.

**Fix:** Make stored real fixtures the default. Use a compact brand header, three primary destinations — โปรแกรม / คู่เด่น / ผลการทำนาย — and one secondary research entry. Put round controls, coverage and the first league immediately below. Move historical totals, old filters and mock data into research. Keep one short experimental-model label adjacent to predictions.

**Suggested commands:** impeccable distill, impeccable layout, impeccable clarify.

**Acceptance:** At 390px and ordinary desktop height, the first viewport exposes the current round, its source state and at least the first fixture or a truthful empty state.

### [P1] Mobile presents a cut-off desktop table as the main match interface

**Evidence:** At 390px, the baseline fixture tables show time and teams while state/analysis columns extend past the visible right edge. Long Bundesliga and Serie A team names wrap inside narrow table cells. Main row text is styled at 12px; table headings at 10px. Team-name and analysis actions have zero-padding text-button styling. The first fixture/summary switch uses small browser-default white buttons.

**Impact:** A person must swipe sideways and remember which teams belong to the state or analysis action. The app loses its core comparison at the size where it is meant to be most useful. Dense type and small targets particularly affect Thai reading, low vision and one-handed use.

**Fix:** Build one shared fixture-row component. On mobile, show kickoff/state, two stacked team identities with fixed logo slots, and a visible ดูวิเคราะห์ action in the same viewport. Use 16px main text, 14px controls and 13px supporting text, with at least 44px ordinary control targets. Keep horizontal scrolling for genuine research tables, not the primary fixture list.

**Suggested commands:** impeccable adapt, impeccable typeset, impeccable harden.

**Acceptance:** At 360px and 390px, every fixture’s teams, kickoff, state and action are readable without horizontal swiping. Long names wrap without shrinking.

### [P1] Cached status still resembles a current live feed

**Evidence:** The selected round is 2026-10-25; the notice says the cache was captured on 26/10/69 at 03:27 and is not refreshed automatically. Rows nevertheless display bare English “live” and “finished”. The Barcelona–Real Madrid and Udinese–AC Milan rows are “live” in the archive. Finished rows do not show a recorded score in the listing. The careful coverage explanation is separated from those rows and uses “source” and “response” terminology.

**Impact:** The reader can mistake a recorded state for the present match state, particularly when landing directly on an old round. A warning above the table does not explain the meaning of each old status as well as a local label would.

**Fix:** Place an explicit “ข้อมูลบันทึกเมื่อ …” indicator beside the round controls. Translate state labels and qualify old ones as recorded state, for example “กำลังแข่ง ณ เวลาบันทึก”. Show actual recorded scores only when present; use a clear unknown state otherwise. Distinguish complete-empty, not fetched, denied and failed date states with separate short messages. Let a refresh read the local cache only; it must not imply a provider poll or change the real captured time.

**Suggested commands:** impeccable clarify, impeccable harden.

**Acceptance:** An old round cannot be read as a current live feed. Empty data never silently means no matches, and unavailable scores never become 0–0.

### [P1] Match analysis behaves like an overlay instead of a navigable destination

**Evidence:** Live inspection opens Barcelona–Real Madrid in a large scrolling dialog. Its header leads with PRIVATE RESEARCH, mapping_status=reviewed and identity caveats; kickoff and recorded match state are absent from the heading area. ProviderPreview.open uses history.replaceState, while date, period and league remain mostly local component state. There is no popstate synchronization in the reviewed component.

**Impact:** Browser Back does not naturally undo the drill-down, a shared URL does not preserve the whole list context, and a long mobile evidence read has an uncertain exit. The first impression is technical caution before match context.

**Fix:** Give main match analysis an inline, addressable detail view. Keep teams, league, Bangkok kickoff and recorded state at the top, then our-model summary or a specific unavailable explanation, then form/H2H. Put detailed mapping, model version, cutoff and enrichment provenance in a concise expandable section. Use navigation history for opening/closing detail and retain round, league, search, period and list position.

**Suggested commands:** impeccable layout, impeccable harden, impeccable clarify.

**Acceptance:** Open match → Back returns to the same filtered list and position; a direct match link works; keyboard users can identify and return from the detail view.

### [P2] Labels, identity and small controls do not yet form one product vocabulary

**Evidence:** The navigation mixes สรุปประจำวัน with the in-view สรุปวิจัยคู่จริง. The fixture/summary buttons have no visible selected state. โปรแกรม API จริง and API-FOOTBALL · PRIVATE RESEARCH expose implementation vocabulary as primary wayfinding. Team and league logos are absent from the baseline despite provider references being a product requirement. Team names are used as bare green text links and a second analysis action repeats alongside them.

**Impact:** Users must learn multiple names for related destinations and infer what is clickable. Repeated text and plain lists obscure the distinct identities of clubs and competitions.

**Fix:** Apply a single Thai vocabulary across navigation and content. Give the active view a persistent visual and accessible state. Style all buttons from the same tokens. Use official provider ID-bound logo references with fixed-size neutral fallbacks and no invented crests. Keep one obvious analysis action per fixture; make the whole row behavior predictable.

**Suggested commands:** impeccable polish, impeccable clarify.

**Acceptance:** The same concept uses the same Thai label everywhere; users can identify the active destination and the match action without reading provider jargon.

## Cognitive load

The checklist flags **6 failures out of 8**, a high load for a task that should be a quick fixture lookup.

| Check | Result | Specific observation |
|---|---|---|
| Single focus | Fail | Hero, evidence totals, warnings and research navigation precede fixtures. |
| Chunking | Fail | Eight equally presented navigation destinations mix everyday and specialist work. |
| Grouping | Pass | Leagues and match history comparisons are grouped coherently. |
| Visual hierarchy | Fail | The largest type and numbers describe the project rather than the current round. |
| One decision at a time | Pass with concern | Date, period and league are sensibly related controls; their explanations still compete with the list. |
| Minimal choices | Fail | Eight top-level tab choices appear together on desktop; mobile hides part of that same row. |
| Working memory | Fail | Mobile requires remembering teams while horizontally reaching state/action columns; browser history does not preserve the drill-down. |
| Progressive disclosure | Fail | Repeated research cautions and retrospective metrics are always expanded before the task. |

The navigation is the clear decision point with more than four simultaneous options. The league selector has six choices when opened, but a native grouped selector is reasonable here; do not replace it merely to meet a numerical rule. A league can also legitimately list more than four matches: ordered records are content, not eight competing task destinations.

## Emotional journey

**Arrival:** The dark identity is calm and credible, but the large headline delays the promised useful information.

**Valley:** Several caution strips and historical totals create doubt before the user has inspected a match. A mobile user then discovers that the row’s state and action are outside the visible table.

**Useful peak:** Opening a real match reveals concrete 10-match form and home/away comparison. Explicit “no retrospective prediction” language is reassuring when no model estimate exists.

**Ending:** Closing the dialog is possible, but the absence of a normal detail/back route weakens the sense of having completed a purposeful investigation. A short match summary, clear available/unavailable states and predictable Back would create a confident endpoint without implying certified accuracy.

## Persona red flags

**Alex — returning analyst checking tonight’s fixtures:** The root route starts at mock fixtures, the first viewport contains no games, and no team search or Today/Tomorrow controls are visible. Alex must navigate the research-heavy tabs and manually set the round before useful inspection. The relevant accelerator is a direct current-round path and retained filters; adding decorative keyboard shortcuts is lower priority.

**Jordan — first-time Thai reader:** “โปรแกรม API จริง”, “source”, “response”, “snapshot” and “reviewed” require technical interpretation. สรุปประจำวัน and สรุปวิจัยคู่จริง appear to promise similar outcomes. A bare “live” label in an old cache is especially easy to interpret literally.

**Sam — low-vision or keyboard reader:** The visible 10–12px table typography and small text actions increase effort; horizontal reading divides a fixture into disconnected pieces. Source does contain focus-visible styling and a native dialog, so missing focus support or broken focus trapping is not asserted. Still verify focus return after closing, accessible active state and narrow/zoomed layouts during implementation.

No project-specific Design Context persona was added because AGENTS.md has no such section.

## Minor observations

- The empty Championship group renders a table header without a contextual empty explanation. Use “ไม่มีคู่ในข้อมูลรอบนี้” only when coverage supports it; otherwise report unavailable coverage.
- Native date input formatting, Thai Buddhist-year short dates and ISO source dates appear together. Choose one display convention for the reader and reserve ISO dates for detailed provenance.
- The full date repeats for each match even within one round. A compact Bangkok time with a clear next-day date cue would scan faster.
- Logos should aid recognition, with accessible treatment avoiding repetition of adjacent team names. Their absence should never stop a fixture from rendering.
- A general fetch error currently returns only a notice, removing the date/league controls. Keep the task context visible and offer a retry that reads stored data.

## Questions for synthesis

- If the reader has 30 seconds before kickoff, which three facts and one action should the first viewport guarantee?
- Can every “no prediction” or “no fixtures” state explain its exact cause without exposing an internal command?
- What would the football desk feel like if the 06:00 round, coverage and fixtures defined the page, and the research remained one step away?

## Evidence limitations

Mobile judgments are grounded in the frozen 390px screenshot and source, not a separate live mobile emulation. Live inspection confirmed the desktop entry composition and the Barcelona–Real Madrid dialog. Scores, contrast ratios, future-date access and provider completeness were not independently verified; no claim about live API entitlement is made. The review tab was closed after restoring the fixture view. The report intentionally contains no automated findings.


