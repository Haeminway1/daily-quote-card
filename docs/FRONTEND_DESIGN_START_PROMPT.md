# Frontend Design Starting Prompt: 좋은생각카드

아래 프롬프트를 그대로 복사해서 Claude, Figma Make, v0, open_design 역할의 디자이너, 또는 프론트엔드 UI 생성 도구에 넣어라.

```md
You are designing the frontend for `좋은생각카드`, a mobile-first quote card app.

Design the actual usable app screen, not a landing page.

## Product

`좋은생각카드` is a public mobile app where a user draws one card from a deck and receives a random quote. The key feeling is physical: the user should feel like they are pulling one card from a small deck.

The app must also let the user add their own quotes. This requirement supersedes any previous non-goal that said user-added quotes are out of scope.

## Audience

- Korean mobile users.
- One-handed use.
- Short repeated visits.
- No login required for the first version.
- Calm, public-safe, simple enough for anyone to use.

## First Screen

The first viewport must immediately show the usable app:

- App identity: `좋은생각카드`
- A visible card deck
- A clear draw affordance
- A revealed quote area or ready state
- A way to add a quote

Do not make a marketing hero page.
Do not explain how the app works with long visible instructions.

## Core Interaction

### Draw A Card

The user can draw a card by:

- tapping/clicking the deck;
- dragging a card out of the deck;
- pressing Enter/Space when the deck control is focused.

The draw motion should feel tactile:

- deck compresses slightly on press;
- top card moves out from the stack;
- revealed quote settles into a readable card;
- below-threshold drag returns the card to the deck;
- no flashy infinite animation.

The app should avoid immediately repeating the previous quote when there is more than one quote available.

### Add A Quote

Design a complete quote-add flow.

The user must be able to:

- open an add quote surface from the main app;
- enter quote text;
- optionally enter author/source;
- save the quote;
- cancel without saving;
- see validation if the quote text is empty;
- draw from the combined deck after saving.

Recommended UI pattern:

- A compact icon or text button near the action row: `명언 추가`
- A bottom sheet or modal for adding a quote
- Fields:
  - `명언`
  - `작가 또는 출처`
- Primary action: `추가`
- Secondary action: `취소`

Saved custom quotes should feel like part of the deck, but the design should visually stay simple. Do not turn the app into an admin dashboard.

Include empty, error, saved, and editing states in the design.

## Content Rules

- Default quote deck has 103 public quotes.
- Source-side records are 104, but one explicit-profane source entry is excluded from browser-visible content.
- Never show excluded explicit content in the UI.
- Missing author should display as `미상`.
- User-added quotes should be local/private in the first version unless backend storage is later added.
- Do not include social sharing, accounts, likes, comments, or public feeds.

## Visual Direction

The app should feel:

- tactile;
- warm but not beige/brown-heavy;
- quiet and trustworthy;
- light enough for daily use;
- polished on mobile.

Avoid:

- generic SaaS dashboard look;
- purple/blue gradient hero styling;
- decorative orbs or bokeh blobs;
- cards inside cards;
- stock images;
- remote fonts;
- CDN assets;
- visible implementation notes or keyboard shortcut explanations.

Preferred palette direction:

- background: cool off-white or very light gray;
- card paper: soft ivory/yellow paper tone;
- accent: strong but restrained yellow;
- text: near-black ink;
- secondary: muted gray;
- small success/accent: green or teal.

You may revise the palette if the result is better, but it must not become one-note beige, purple, dark slate, or generic blue gradient.

## Typography

- Korean-safe system font stack only.
- No remote fonts.
- Letter spacing must be `0`.
- App title should be strong but not hero-sized.
- Quote text should be highly readable on mobile.
- Long quotes must wrap cleanly without horizontal overflow.
- Use `word-break: keep-all` behavior conceptually for Korean, with fallback for long English words.

## Layout

Mobile baseline:

- 375px and 390px widths must look intentional.
- Desktop should center a mobile shell with max width around 480px.
- No horizontal overflow.
- Stable deck and card dimensions so labels, hover, and long quotes do not resize the shell.
- Bottom controls should remain reachable.

Main layout order:

1. Header with `오늘의 카드` and `좋은생각카드`
2. Deck draw area
3. Revealed quote card or ready state
4. Actions: `다시 뽑기`, `명언 추가`, small status like `이전 카드와 겹치지 않게`
5. Add quote sheet/modal when opened

## Accessibility

Design for:

- semantic button for the deck;
- visible focus states;
- 44px+ touch targets;
- readable contrast;
- reduced motion mode;
- polite live announcement when a quote changes;
- modal/bottom-sheet focus management for quote adding.

## Required States To Show

Create design states for:

- initial ready deck;
- card being dragged;
- revealed quote;
- long quote;
- missing author;
- add quote sheet empty;
- add quote validation error;
- added quote saved confirmation;
- custom quote drawn from deck;
- reduced motion version or notes.

## Technical Constraints

This will be implemented in Google Apps Script HtmlService.

The design must be implementable with:

- local inline HTML/CSS/JS;
- no CDN;
- no remote CSS;
- no remote JS;
- no remote fonts;
- no external image dependency;
- no API-key media generation.

Cloudflare Pages is only a wrapper shell for the GAS app. Do not design a separate Cloudflare product surface.

## Output I Need

Return:

1. A concise design concept.
2. Mobile layout structure.
3. Component list.
4. Interaction details for drawing a card.
5. Complete add-quote flow.
6. Visual tokens: colors, spacing, radii, shadows, typography.
7. Accessibility notes.
8. Implementation notes for a GAS-safe frontend.
9. A 375px mockup description or HTML/CSS prototype if you can generate one.

The design should feel like a real mobile app someone can use immediately.
```

## Current Product Facts

- App name: `좋은생각카드`
- Runtime: Google Apps Script HtmlService
- Wrapper target: Cloudflare Pages project `gas-quotecard`
- Default public deck count: 103
- Source-side quote count: 104
- Excluded source line: 66
- Current key selectors:
  - `data-test-id="quote-deck"`
  - `data-test-id="quote-card"`
  - `data-test-id="quote-text"`
  - `data-test-id="quote-author"`
  - `data-test-id="draw-again"`
  - `data-test-id="quote-announcement"`

## Design Decision Change

The new frontend design must include user-added quotes. Treat this as a new product requirement and not as a future-only idea.
