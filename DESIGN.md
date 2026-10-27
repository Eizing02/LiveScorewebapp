---
name: สนามข้อมูล
description: A Thai football programme desk in white, blue and red, grounded in recorded data.
colors:
  background: "#f4f7fb"
  surface: "#ffffff"
  surface-raised: "#eff6ff"
  border: "#7e8da1"
  divider: "#d7dfeb"
  text: "#101828"
  text-muted: "#475467"
  accent: "#1d4ed8"
  warning: "#b42318"
  error: "#b42318"
  info: "#1d4ed8"
  win-surface: "#eff6ff"
  loss-surface: "#fef3f2"
  scrim: "#10182866"
  header-hover: "#ffffff24"
  header-border: "#bfdbfe"
typography:
  headline:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-.02em"
  title:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.5
  section:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
  analysis-body:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: ".875rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: ".875rem"
    fontWeight: 400
    lineHeight: 1.65
  supporting:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: ".8125rem"
    fontWeight: 400
    lineHeight: 1.65
  probability:
    fontFamily: "IBM Plex Sans Thai, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 500
    lineHeight: 1.65
rounded:
  square: "0"
  score: "5px"
  tag: "6px"
  control: "8px"
  container: "12px"
spacing:
  tight: "4px"
  inline: "6px"
  compact: "8px"
  row: "12px"
  pane: "16px"
  section: "24px"
  roomy: "32px"
components:
  button-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 13px"
  button-default-hover:
    backgroundColor: "{colors.surface-raised}"
  button-selected:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.background}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 13px"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "8px 0"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 13px"
  navigation-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.accent}"
    typography: "{typography.label}"
    rounded: "{rounded.tag}"
    padding: "8px 16px"
  source-tag:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.accent}"
    typography: "{typography.supporting}"
    rounded: "{rounded.tag}"
    padding: "6px 10px"
  empty-state:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.container}"
    padding: "20px 24px"
  fixture-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.square}"
    padding: "8px 12px"
  fixture-row-selected:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
  analysis-tab:
    backgroundColor: "transparent"
    textColor: "{colors.text-muted}"
    typography: "{typography.supporting}"
    rounded: "{rounded.square}"
    padding: "8px 4px"
---

# Design System: สนามข้อมูล

## Overview

**Creative North Star: "Football programme desk"**

Compact, ordered and calm: white panes sit below a blue masthead, with red qualifying significant recorded states and the pitch mark. Thai text, full team identities, aligned scores and fine dividers carry the interface. Research shares the same materials and remains a secondary task.

This is the finished system extracted from the application, refreshing the incumbent document under the user's approved white/blue/red direction. It preserves the product name, local Thai type, provider identities and explicit distinction between recorded facts, estimates and unknown data. A competition being visible never implies that the model can analyse it. A recorded status never implies a current live guarantee. The approved written plan and the named FORM contract establish the direction; no generated seed or raster comp exists.

**Key Characteristics:**

- White content, cool blue-grey structure, blue navigation and restrained red state.
- Readable Thai text and full team names, with tabular scores and times.
- Flat, divider-led panes and small curved controls.
- Context-preserving selection, task tabs and truthful unavailable states.

## Colors

The palette is cool, clear and functional; frontmatter values are normative and map to the CSS custom properties in `apps/web/src/style.css`.

### Primary

- **Programme Blue** (`accent`, `info`; CSS `--accent`, `--info`): masthead, links, current navigation, selected filters, focus and probability bars.
- **Selection Wash** (`surface-raised`, `win-surface`; CSS `--raised`, `--win-surface`): selected rows, current task tabs, tags and explicit W form labels.
- **Masthead Hover** (`header-hover`): translucent white hover treatment over the blue navigation.
- **Masthead Border** (`header-border`): the secondary research button's outline.

### Secondary

- **Recorded Red** (`warning`, `error`; CSS `--warning`, `--error`): stale/partial-data notices, recorded live/cancelled/abandoned states, errors, explicit L form labels and the pitch centre mark. It accompanies words or shape.
- **Loss Wash** (`loss-surface`; CSS `--loss-surface`): the pale backing of L form badges.

### Neutral

- **Cool Field** (`background`; CSS `--bg`): page ground, league strips, score backing and secondary fields.
- **White Pane** (`surface`; CSS `--surface`): programme, competition and analysis panes, fields, notices and crest backing.
- **Pitch Ink** (`text`; CSS `--text`): names, selected-row text, scores and headings.
- **Supporting Slate** (`text-muted`; CSS `--muted`): countries, timestamps, supporting copy and neutral fallback initials.
- **Control Stroke** (`border`; CSS `--border`): input/button outlines and scrollbar thumb.
- **Pane Divider** (`divider`; CSS `--divider`): thin row, group and pane boundaries.
- **Research Scrim** (`scrim`; CSS `--scrim`): legacy research dialog/drawer backdrop only.

### Named Rules

**The Readable Selection Rule.** A selected fixture keeps Pitch Ink on Selection Wash, including time, team names and score. The generic blue pressed-button foreground must not leak into the pale programme row.

**The Named State Rule.** Red qualifies an explicit recorded state or problem; it never supplies the meaning alone. W/D/L form badges retain their letters.

## Typography

**Body and heading font:** locally served IBM Plex Sans Thai, with `system-ui, sans-serif` fallback. Local WOFF2 subsets supply weights (400, 500, 600), loaded with `font-display: swap`; `font-synthesis: none` is declared. There is no separate display face or ornamental display role.

**Character:** a single Thai sans keeps names, labels and analysis in the same voice. The root size is (16px), with default line height (1.65). Paragraphs normally use (1.8); the compact analysis body uses (1.7). Headings use (1.5), weight (600), and balanced wrapping.

### Hierarchy

- **Headline** (`headline`): research page headings (2rem / 32px), reducing to (1.75rem / 28px) at (600px) and below; letter spacing (-.02em).
- **Title** (`title`): programme pane and selected-match heading (1.125rem / 18px); the mobile programme title becomes (1rem / 16px). The brand is also (1.125rem), weight (600), with its inherited body line height.
- **Section:** analysis section headings (1rem / 16px); general research section headings use (1.25rem / 20px).
- **Body:** programme team identities (1rem / 16px) with row-specific line height (1.45); compact analysis prose (14px).
- **Label:** controls and kickoff time (14px). Competition/country labels, recorded status, source notes and task tabs use the supporting role (13px); the competition row uses line height (1.45), recorded fixture state (1.35), and source strip (1.5).
- **Probability:** compact analysis percentages and expected goals (1.375rem / 22px), weight (500). Research metric sizes remain contextual (20–28px), without a second type system.

### Named Rules

**The Full Identity Rule.** Team names remain (16px) and wrap, including at narrow widths; do not shrink them to preserve a one-line row. Scores, times and probability values use tabular numerals. Dates and recorded times use the Thai locale with the Asia/Bangkok timezone; the shared date helpers explicitly use the Gregorian calendar.

## Layout

The main desk uses the full available width. A compact masthead precedes date/search/filter controls; pane titles, source state and pagination stay outside their pane's scrolling body. The research area scrolls within the frame and centres its content at a maximum (1240px). Spacing is compact and contextual: common gaps and insets are (4, 6, 8, 12, 16, 24, 32px), with (1px) dividers. This is an extracted vocabulary, not an enforced arithmetic scale.

- **Desktop, width at least (1280px):** competition rail (210px), flexible programme (`minmax(0,1fr)`), analysis (400px), separated by (1px) gaps. The masthead minimum height is (64px); toolbar padding is (10px 16px). Competition, fixture list and analysis content have their own overflow.
- **Tablet, (768–1279px):** the competition rail is hidden. The grid becomes `minmax(0,1fr) minmax(320px,44%)`; competitions remain available in filters. Supplementary round/header status is hidden.
- **Mobile, width below (768px):** one active pane. The masthead has a second row of three equal task buttons and minimum height (88px). The toolbar puts dates across the first row and search/filter across the second. Selecting a match replaces the programme and toolbar with analysis; Back restores filters, URL state, row focus and list position. Both team identities and score remain in one grid row; long names wrap within their cells.
- **Results:** the competition rail and programme filters/scopes are hidden, leaving the flexible results pane and (400px) analysis pane until the single-pane mobile breakpoint.

Programme rows have a minimum height (60px), padding (8px 12px), and columns `2.875rem minmax(0,1fr) 2.5rem minmax(0,1fr) 1.125rem`. Recorded state sits below the two identities and score. Below (768px), padding becomes (8px), the gap (5px), and fixed columns become (2.75rem), (2.125rem), and (1rem); team text stays (16px). League headings contain real counts, a separately named collapse button and a follow star. Subset/total counts distinguish a page's visible group from its stored total.

The frame uses `height: 100dvh` and a text-relative minimum (40rem). Normal captures at (1440×900), (1366×768), (1024×900), (768×900), (390×844) and (320×900) have no document overflow. Enlarged text may exceed viewport height: at 200% text in the recorded mobile case the frame is (1280px), permitting necessary outer scrolling while preserving the programme pane. At viewport heights (450px) and below, the frame explicitly uses auto height, visible overflow and a minimum of (100dvh); workspace/grid minimum heights are (580px)/(460px). Reading takes precedence over fitting everything in one window.

Ordinary interactive controls have a minimum target height (44px). Pane scroll regions are keyboard focusable; pane focus outlines are inset to avoid clipping. Tables use their own horizontal scrolling container when their data cannot fit. The research stylesheet's additional (800px) and (600px) adaptations remain local to its older layouts; they do not change the main desk's three/two/one-pane thresholds.

## Elevation & Depth

There are no authored box shadows, blurs or decorative gradients. Fine borders, cool grounds and selected washes establish hierarchy. The filter popover is elevated by position, border and stacking order, with a (12px) radius and no shadow; it closes on outside pointer interaction or Escape. Legacy research dialogs/drawers use a scrim, while match inspection occupies the adjacent or active analysis pane.

**The Flat Desk Rule.** Establish groups with dividers and tonal surfaces. Reserve overlays for existing filter and research tasks; do not add ornamental depth to fixture rows.

## Shapes

Pane boundaries, fixture rows, scope tabs and analysis tabs are square. Curves belong to controls (8px), tags/masthead buttons/neutral logo fallback (6px), score and form cells (5px), and contained notices, research cards, tables or filters (12px). A desktop masthead current tab is rounded (6px); mobile masthead tabs become square.

Logo slots have fixed geometry and `object-fit: contain`, preserving each official mark. Programme and competition slots are (24px) with (22px) images; mobile fixture slots are (22px) with (20px) images. Selected-match identity uses (26px) slots with (24px) images. General and large research slots remain (32px)/(28px) and (56px)/(48px). Neutral initials substitute for unavailable media; they are never presented as an official crest. Authored outline SVGs use roughly (18–20px) geometry with (1.6–1.7px) strokes; the pitch mark is (32px), becoming (28px) on mobile.

## Components

### Buttons

Compact, bordered and explicit. The default is White Pane/Pitch Ink with Control Stroke, padding (9px 13px), radius (8px), and minimum height (44px). Hover uses Selection Wash and a blue border. Generic pressed controls use blue/Cool Field; date and scope controls deliberately use pale selection instead. Disabled buttons use Supporting Slate and opacity (.6). Text actions have blue text, transparent background, no border, padding (8px 0), and an underline on hover.

Background and border changes transition in (160ms ease-out). Visible focus is a blue (2px) outline with (4px) offset; the masthead uses a white outline. The date field's containing label uses (2px) offset. Reduced-motion preference sets animation/transition duration to (.01ms) and disables smooth scrolling. No authored entrance, scale or decorative movement is part of this system.

### Chips

Source tags use blue text on Selection Wash, radius (6px), supporting type and padding (6px 10px); the compact analysis top line uses (4px 8px). These identify recorded data or experimental models. W/D/L badges use explicit letters in square-ish cells; compact analysis cells are (24px), with (5px) corners and state-specific washes.

### Cards / Containers

Main panes are flat, square white surfaces separated by dividers. Empty/error notices use a bordered (12px) container with (20px 24px) general padding; list-pane notices use (16px) padding and (18px) margins, while the mobile general notice uses (18px). Error states retain explanatory copy and a retry control. The model-unavailable message uses Cool Field, a divider border, radius (8px) and padding (12px). Loading placeholders reserve space without shimmering. Research match cards retain a (12px) radius and padding (20px 24px), becoming (16px) at narrow widths; they do not replace dense programme rows.

### Inputs / Fields

Inputs/selects share the default control border, radius, height and type. Search uses Cool Field; its width flexes up to (360px) and becomes full width on mobile. Placeholder text remains Supporting Slate at full opacity; caret and focus use blue. The date field presents a formatted label with a real native date input over it; keyboard focus reveals the input. The filter panel groups country, competition, recorded status and period in two columns, with maximum width `calc(100vw - 24px)`.

### Navigation

The blue masthead contains Programme, Daily Picks and Prediction Results, with Research as a secondary entry. Desktop buttons use white text, padding (8px 16px), radius (6px) and minimum height (44px); current navigation uses white/blue. Mobile gives the three main tasks equal widths and square corners. Current state uses `aria-current`; follow/scope/row state uses native buttons and `aria-pressed` or an explicit current marker. Skip links appear on focus.

### Programme and analysis

A whole fixture row is a named button. Hover and selection use Selection Wash with explicit dark foreground; score cells use tabular figures on Cool Field, and an unknown score remains a dash. Source strips show the actual recorded timestamp and qualify score/status as recorded; stale or incomplete coverage is named. Reading cache is an explicit action, not a promise of a provider refresh.

Analysis retains four tasks: Summary, Form–H2H, Goals and Team. Tabs have a minimum height (44px), are square and muted by default, and use blue on Selection Wash when selected, with a blue (2px) bottom indicator. The tablist supports Left/Right/Home/End, keeps one tab in the tab sequence, and labels its scrollable panel. Detail headings remain stable while task content scrolls. Model provenance stays in a disclosure. Model and provider forecasts keep separate headings and source times; broad programme visibility is independent of model readiness. Empty Daily Picks and Results retain their truthful explanations.

### Brand identity

Provider IDs select genuine crest media. The current local index contains (47) static crest files with embedded origin metadata and URL/hash provenance in `apps/web/public/media/sources.json`. The manifest preserves download hashes/byte counts alongside current hashes/byte counts; the metadata addition leaves image payloads visually unchanged, as recorded in `reports/one-page/raster-provenance.json`. Other known IDs use the fixed-CDN `/api/media/{teams|leagues}/{id}.png` cache, subject to its feature flag and recorded-ID checks. Offscreen API images wait for intersection; images load lazily and failed/unknown media retain a stable neutral initials fallback. There is no new decorative raster or generated official branding in this world.

## Do's and Don'ts

### Do:

- **Do** show the actual recorded timestamp and distinguish unavailable data from an empty schedule.
- **Do** keep the selected fixture's text dark, team names readable and complete, and target heights at least 44px.
- **Do** preserve list context on selection/Back and allow necessary scrolling for enlarged text or short windows.
- **Do** distinguish programme coverage, model eligibility and provider forecasts with explicit text.
- **Do** retain evidence and sample size in research views, with technical provenance behind useful disclosures.
- **Do** use genuine provider crests or the stable neutral initials fallback.

### Don't:

- **Don't** put a marketing hero, large research metrics or repeated warnings before the working programme.
- **Don't** manufacture probabilities, scores, availability, official logos or live accuracy claims to fill a state.
- **Don't** expose setup commands as the standard user recovery.
- **Don't** add decorative gradients, glow, blur, hard offset shadows, invented eyebrow/kicker labels or glyph/emoji UI icons.
- **Don't** use a decorative system display face or motion that competes with reading.

Not canonized: the incumbent document's centred main workspace, stacked mobile team identities, 28–32px primary desk title, merely intended local font, and text-coloured crest backing were stale descriptions. The build uses a full-width desk, same-row identities, 18/16px pane title, locally loaded fonts and white crest backing; those descriptions are reconciled here. Legacy research layouts remain contextual variants, not a mandate to reproduce their card density in the programme. No unresolved craft-floor defect is adopted as a reusable rule, and no application code is repaired by this documentation pass.
