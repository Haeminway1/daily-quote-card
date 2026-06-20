# Design Direction: 좋은생각카드

Status: T2 baseline for mockup and JSX implementation.

Advisor: Claude print-mode `open_design` bounded review returned
`APPROVE_WITH_NOTES` in
`.advisor/responses/20260614-175645-open-design-good-thought-card-bounded.md`.
The notes below are implementation requirements, not optional polish.

## Design System Basis

Selected vendored system: `library/design-systems/professional`.

Rationale: `좋은생각카드` is a public mobile utility, not an enterprise dashboard, but it still needs a restrained, trustworthy frame. The professional system provides clear contrast, compact mobile spacing, and a strong yellow accent that can make the physical card-draw action feel tactile without relying on purple/blue gradients, remote imagery, or decorative blobs.

Adaptation rule: use the local design-system direction only as a source of token discipline. Do not import external fonts, CDN CSS, remote assets, or generated network media.

## Visual Tone

- Calm public-use app with a tactile paper/card feeling.
- Not a landing page: the first viewport is the usable card deck screen.
- The app surface should feel light, focused, and repeatable.
- Avoid one-note palettes. The dominant frame is ink/white with a pale cool background, yellow card accent, and a small teal success accent.
- Avoid beige/brown-heavy warmth, purple gradients, oversized hero copy, nested cards, and decorative orbs.

## Token Map

Implementation should define these CSS variables in `src/frontend/css.html` and may mirror them in `design/mockups/main.html`.

```css
:root {
  --qc-bg: #f5f7fb;
  --qc-surface: #ffffff;
  --qc-paper: #fff8d8;
  --qc-paper-edge: #f0c84b;
  --qc-ink: #111827;
  --qc-muted: #566070;
  --qc-subtle: #e2e8f0;
  --qc-accent: #fece14;
  --qc-accent-ink: #111827;
  --qc-teal: #0f766e;
  --qc-danger: #b42318;
  --qc-focus: #2563eb;
  --qc-radius-sm: 8px;
  --qc-radius-md: 10px;
  --qc-radius-lg: 14px;
  --qc-space-1: 4px;
  --qc-space-2: 8px;
  --qc-space-3: 12px;
  --qc-space-4: 16px;
  --qc-space-5: 20px;
  --qc-space-6: 24px;
  --qc-shadow-card: 0 16px 38px rgba(17, 24, 39, 0.14);
  --qc-shadow-soft: 0 8px 22px rgba(17, 24, 39, 0.08);
  --qc-font: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", "Segoe UI", sans-serif;
}
```

## Typography

- Use the Korean-safe system stack from `--qc-font`; never load remote fonts.
- Letter spacing stays `0`.
- App title: 24-28px, 700, line-height 1.25.
- Quote text: 22-26px depending on available space, 700, line-height 1.62, `word-break: keep-all`, `overflow-wrap: anywhere` fallback.
- Body/support text: 14-16px, line-height at least 1.6.
- Metadata and author: 13-14px, 600, muted ink.
- Keep line length around 28-40 Korean characters where possible.

## Layout

- Body: full viewport, no horizontal overflow.
- App shell: `width: min(100%, 480px)`, centered on desktop, min-height 100dvh.
- Safe padding: 18px on 375px, 20px on 390px, 24px above 420px.
- First viewport order:
  1. compact app header with `좋은생각카드`;
  2. deck area with stacked cards;
  3. revealed quote area or ready state;
  4. redraw/action row.
- The deck and revealed card need stable dimensions so hover, motion, long quotes, and labels cannot resize the shell.
- Cards may be individual framed objects; do not place UI cards inside another card.

## Core Components

### Deck Button

- Semantic `button`.
- Visual: 3-5 stacked cards with slight offsets, yellow paper face, ink border, and soft shadow.
- Minimum touch target: 56px high, preferably 160px card footprint.
- States: resting, pressed, dragging, disabled only if deck data is empty.
- Focus-visible: 3px outline using `--qc-focus` with offset.

### Revealed Quote Card

- Single card with fixed responsive width and min-height.
- Paper surface `--qc-paper`, subtle edge color, and strong readable quote text.
- Long quote handling: card grows vertically within shell but never exceeds viewport without scroll.
- Missing author: show `미상`.
- Excluded source records must never appear in this UI.

### Action Row

- `다시 뽑기` button uses yellow accent with ink text.
- Secondary metadata stays quiet; no implementation instructions or keyboard shortcut text.
- Buttons use 8px radius or less unless a true card object needs larger physical-paper rounding.

## Motion

- Motion must communicate a card being drawn from a deck.
- Tap/click: short press compression then card lift/reveal, 180-260ms.
- Drag: follow pointer enough to feel direct, reveal after 48px movement threshold.
  Horizontal movement is the preferred draw gesture. Vertical movement may still
  draw only when it starts on the deck and is captured by the deck control; tests
  must guard against accidental scroll-style vertical drags.
- Below-threshold drag: card settles back, no reveal.
- Reduced motion: skip travel transforms and use opacity/state change only.
- No decorative infinite animation.
- Deck size 1 disables anti-repeat rather than faking a different result. Deck
  size 2 alternates away from the previous card when possible.

## Accessibility

- Deck control has an accessible name such as `명언 카드 뽑기`.
- Enter and Space activate draw.
- Focus ring is visible on deck and redraw controls.
- Quote text contrast must meet WCAG AA against paper surface.
- Touch targets should be at least 44px.
- App state changes should not trap focus; after redraw, focus remains on the activated control unless the browser naturally moves it.
- Revealed quote changes must be announced through a polite live region without
  adding visible implementation instructions.

## GAS And Wrapper Constraints

- HtmlService output must be self-contained.
- No external CSS, JavaScript, CDN assets, remote fonts, API-key media, or remote image dependencies.
- CSS lives inline through the project build system.
- Cloudflare wrapper remains a shell for `gas-quotecard`; no production deploy or project mutation is part of design implementation.
- Wrapper must keep project-specific storage keys, manifest identity, cache prefix, and frame handshake name.

## QA Gates

- `node tests/inline-resource-check.mjs design/mockups/main.html`
- `node tests/design-antipattern-check.mjs design/mockups/main.html`
- `npm run test:inline-resources`
- `npm run test:design:antipatterns`
- Browser screenshot at 390x844 for the mockup and implemented app.
- Card-draw Playwright checks for click, drag threshold, keyboard, no-repeat, and excluded-content absence.
- Runtime payload checks must reconcile 104 source-side records to 103 public
  records and assert the explicit source line 66 text is absent from compiled
  runtime HTML.
