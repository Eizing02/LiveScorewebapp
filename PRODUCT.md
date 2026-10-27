# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The owner reads football fixtures and model analysis in Thai on mobile and desktop. Public audience and monetization are undecided; current implementation is private local research.

## Product Purpose

Show upcoming football matches grouped by their actual league, let a person inspect one match, and summarize model selections and recorded outcomes. The owner defines a football day as 06:00 to 06:00 the following day in Asia/Bangkok.

Programme competitions follow the user-approved editorial order: five major European leagues, UEFA club cups, Championship, major domestic cups, other selected top divisions, then lower/unlisted competitions. Apply the order before pagination and share it across the sidebar, filter and programme. Within each competition, sort by kickoff; following a competition does not change its priority. This ordering does not express model confidence or league strength.

## Operating Context

React/TypeScript frontend, Cloudflare Worker/D1 read API, and Python data/model pipelines already exist. API-Football is the current-data provider; historical data is pinned separately. Frontend reads stored data and never carries the provider key. Display fixtures from all recorded competitions; model/history eligibility stays separate from the five-league provider research mapping. Source timestamps matter because refresh is budgeted rather than continuous live polling.

## Capabilities and Constraints

Program listing, league filters, future kickoff times, official provider logo references, H2H and form, probabilities, goal estimates, daily summaries and prospective result evaluation. Preserve separate real and mock data. An unavailable date is not an empty schedule. A missing score is not 0–0. No prediction can be created after kickoff. Model weights and frozen acceptance policy must not be changed to fill the UI. No production deployment, paid services or automatic model promotion in this task.

## Brand Commitments

Existing product name: สนามข้อมูล / Football Prediction AI. Thai is the primary interface language. Actual team and league identities and logos come from the provider. Use the user-approved white, blue and red football-programme theme and one-window workspace. Avoid invented football claims or assets presented as official.

## Evidence on Hand

See docs/USABLE_APP_PLAN_TH.md, reports/live-research/verification.json and reports/precision-v3/PRECISION_REPORT_TH.md. Previous software tests and retrospective accuracy are dated evidence, not fresh live performance. API responses under ignored data/processed contain real provider logo URLs. No future accuracy certification exists. External-forecast percentages must remain separate from our model.

## Product Principles

- Put the fixtures and the next useful action before research diagnostics.
- Preserve the difference between recorded facts, model estimates and unknown data.
- Give every empty/error state a truthful explanation and a useful recovery.
- Keep one consistent vocabulary and predictable navigation across screens.
- Make routine use possible without exposing setup commands or credentials.

## Accessibility & Inclusion

Thai text must remain readable and wrap correctly. Support keyboard navigation, visible focus, reduced motion, useful accessible names, sufficient contrast, and narrow mobile layouts. State must be understandable without color alone.
