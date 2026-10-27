disposition: fix

Unprovided provenance: concept-seed roll/corroboration; the parent confirms no roll was run. No approved comp, comp build state, or comp diffs apply to this code-led build. Primary source files were sampled; no browser, provider, API, database, or detector pass was run by this reviewer.

## persistence

Pass for product/design persistence: `PRODUCT.md` exists and records the broad programme, separate model eligibility, recorded-time truth, and white/blue/red workspace. `DESIGN.md` matches the rendered palette and three/two/one-pane world; final documenter handoff remains pending as declared. Code-led execution makes comp phases and approval records inapplicable.

Evidence pass: all fourteen required captures exist, show their claimed content and document top, and have sensible dimensions. `desktop.png`, `user-1366.png`, `tablet.png`, `user-768.png`, `mobile.png`, and `user-320.png` cover the six required viewports. The eight task/state captures are valid. `mobile-text-200.png` is valid evidence of a layout defect, not a malformed capture. The measurements corroborate document bounds; their preliminary visible-row counts were not used as proof of usable rows. Detector input is `[]`; the manual floor review still finds a contrast failure.

## fidelity

Composition authority: the user-approved written plan, `docs/SINGLE_PAGE_RED_WHITE_BLUE_PLAN_TH.md`; no image comp or decision-comp reference was supplied.

| Element / promise | State | Screenshot / source evidence |
|---|---|---|
| TYPE | match | Readable ordinary programme typography, with 16px team names and smaller controls/supporting data; `style.css:4`, `:304`, `:309`. The incumbent locally imported IBM Plex Sans Thai is the declared family. No invented display treatment. |
| MATERIAL | match | White panes, fine dividers, tonal selected surfaces, actual crests or neutral initials. No physical-material imitation or promised raster region is present. |
| GROUND | match | White content and cool light blue-grey fields match the approved `#ffffff`, `#f4f7fb`, `#eff6ff` roles; `desktop.png`, `all-competitions.png`, `style.css:5-8`, `:270-271`, `:301`, `:305`. No warm-ground drift. |
| Compact blue masthead and task navigation | match | All captures put the programme controls before research; `App.tsx:9`. Programme / daily / results remain within the workspace. |
| Desktop competition / programme / analysis topology | match | `desktop.png` and `user-1366.png` show all three panes together; `style.css:270`, `:278`, `:298`, `:346` give their own overflow. |
| Tablet two-pane topology | adaptation | `tablet.png` and `user-768.png` remove the competition rail while retaining programme and analysis, as expressly required by plan section 3; filters remain in the toolbar. |
| Mobile single active pane and Back | adaptation | `mobile.png` versus `mobile-analysis.png` use the single pane required by plan section 3; `ProviderPreview.tsx:29`, `:32-33` restore row focus/scroll and preserve URL state. |
| Selected fixture identity | contradicted | The chosen Cuarte–Girona row loses its time, team names and score dash against pale blue in `desktop.png`, `user-1366.png`, `tablet.png`, and `user-768.png`; the same happens to Barcelona–Real Madrid in `legacy-history.png`. `style.css:23` supplies `#f4f7fb` text for pressed buttons, while `:305` overrides only the row background to `#eff6ff`: approximately 1.01:1 contrast. |
| Enlarged-text reading | contradicted | `mobile-text-200.png` leaves only the league strip and a sliver of the scrolling programme, with no complete fixture visible. The fixed `100dvh`/hidden frame (`style.css:236`) and shrinking panes (`:270`, `:298`) have no text-enlargement fallback; `:431-435` applies only below 450px viewport height. This contradicts plan sections 3 and 10 and the QUALITY BAR's reading fallback. |
| League heading inventory | missing | Plan section 4 requires each group to show its match count and fold/unfold control. `all-competitions.png` and `mobile.png` show name/country/star only; `ProviderPreview.tsx:41` renders a static `h2` without count or collapse state. The desktop rail count does not supply the missing tablet/mobile group affordance. |
| Narrow-screen team size and wrapping | adaptation | `user-320.png` preserves team size, complete names through wrapping, score/action access, and document width rather than shrinking the font; responsive reflow is authorized by plan sections 3–4. Some long names break within words, but this does not replace their identities. |
| Four analysis tasks and short first read | match | `mobile-analysis.png`, `mobile-team-unknown.png`, and `legacy-history.png` show Summary, Form–H2H, Goals, Team; technical provenance stays behind disclosure. `LiveDetail.tsx:16`, `:32-38`. |
| Truth: coverage, unknowns, recorded facts, readiness | match | `all-competitions.png` exposes 332 stored fixtures; the source strip dates observations. `mobile-team-unknown.png` explicitly keeps unavailable injuries, lineups, xG and provider forecast unknown. `daily-empty.png` / `results-empty.png` present zero qualifying prospective predictions without filled-in selections. No contrary claim is visible. |
| THESIS | match | The first viewport is recognisably a football programme desk: date, competition, kickoff, teams, score/status, adjacent analysis. The memory test retains the fixture desk rather than a marketing dashboard. |
| OWN-WORLD | match | The visible white/blue/red, compact row-based programme and official/fallback identity follow the pinned user world. |
| STORY | match | Programme → selected match → four task tabs is maintained across desktop and mobile; empty/unknown data remains useful content. |
| FIRST VIEWPORT | contradicted | The normal-size desk composition is present, but the selected row is illegible and the 200% viewport loses the usable programme. |
| FORM provenance | missing | `.impeccable/direction/football-desk.md` contains the promises in prose but does not commit the five named blocks or a valid `seed:` reference. The parent explicitly confirms no concept-seed roll, rather than unavailable evidence; the reviewer's check 4 therefore remains unmet. The approved plan still governs composition. |

## ceiling

Unreached against `.impeccable/direction/quality-bar.md`: its explicit fully readable selection and enlarged-text reading promises fail in the supplied captures. The plan's foldable, counted league strip is an unused native programme device. The desk does not call for extra photographic material, ornamental depth, decorative lettering, or additional motion.

## material_fixes

1. Check 4 / FORM: commit the direction's five named blocks and resolve the unrun concept-seed requirement with genuine workflow provenance or an explicitly recorded applicable exception; do not fabricate a seed, claim unavailability, or replace the user-approved world.
2. Fidelity / enlarged-text reading: add a content-sensitive reading fallback so 200% text permits necessary document or adequately sized pane scrolling instead of collapsing the fixture viewport; recapture `mobile-text-200.png` showing readable fixture content and verify access to the last fixture and analysis tabs.
3. Fidelity / selection and floor contrast: set an explicit dark selected-row foreground (including time, names and score) against its pale-blue/background surfaces, meeting 4.5:1; recapture the existing desktop/tablet selected states and `legacy-history.png` with the selected identity fully visible.
4. Fidelity / approved plan section 4: add truthful per-group match counts and keyboard-accessible fold/unfold controls to league headers, preserving follow controls and list context; recapture `all-competitions.png` and a mobile programme state showing that inventory.

## keep

Keep the three/two/one-pane programme topology, 16px team identities, restored Back context, broad stored-competition coverage, and explicit recorded/unknown/model-unready truth while fixing.
