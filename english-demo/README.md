# Daily Quote Card

A standalone, English-first (EN/KO) PWA: a moving deck of 103 original bilingual quotes with author and source on AI-created photographs. Pull a card down to draw it, then keep a private, dated note for each card. Live at https://daily-quote-card.pages.dev/

## Run

- Preview: `python3 -m http.server 4187 --directory english-demo` (localhost is a secure-context exception). Production requires HTTPS on its own origin.
- QA: `python qa.py --url http://localhost:4187 --out qa-out` — real headless-browser checks plus screenshots, writes `qa.json`, exits nonzero on failure.

## What it does

- Restored deck mechanics on the new photo design: seven portrait photo cards drift along the belt; drag one down past the threshold (or press Enter/Space on the deck, or the Draw a card button) to flip it over at stage centre. Sub-threshold drags snap back; the revealed card swipes down to dismiss.
- Non-repeat draws: every block of N draws contains each quote exactly once and never repeats the previous card across a block boundary. Custom quotes join the same bag and show a "Your quote" badge.
- Write your thought: each drawn card can hold a dated note (date, time, quote, author, thought, linked draw id).
- History calendar: days are marked for drawn cards and written thoughts; the day view lists every drawn card with its thoughts plus imported or unlinked notes. Month navigation and back-to-month included.
- Bookmark and share the revealed card; EN/KO switch localizes the whole UI (labels, dates, hints, toasts, aria) and the Korean quote text. Custom user input is never auto-translated.

## Storage and migration

- New records use namespaced keys: `daily-quote-card.quotes.v2` (custom quotes), `daily-quote-card.memos.v2` (thoughts), `daily-quote-card.drawn.v2` (draw history), plus `daily-quote-card.prefs.v2` (language and saved cards). Write failures surface an error and roll back; nothing claims a false success.
- The previous build's `daily-quote-card:v1` is left untouched. On first run, its per-card notes are imported as dated thought records using the import timestamp, labelled "Imported note · original date unavailable" — no fabricated original date. Prior language and saved-card choices carry over via the new prefs key.
- With the 103-quote deck, stored references to the old twelve cards (`q01`…`q12`) are idempotently remapped to their padded IDs (`q001`…`q012`) in saved cards and in default/imported memos and draws; custom IDs and historical text are untouched.

## Limits (stated accurately)

- Offline: the service worker (`daily-quote-card-shell-v4`) precaches the shell at install, then precaches each unique photograph used by the deck a few at a time; an image fetch failure does not block installation, and images delivered later are cached on the fly. Same-origin GET requests only; offline navigations fall back to the cached shell. The first visit must be online.
- Install: uses the browser's own flow (`beforeinstallprompt` when offered, otherwise a help dialog). On iPhone/iPad: Safari → Share → Add to Home Screen. Availability depends on the browser.
- Notifications: the button requests permission inside the click and posts one immediate local notification via `ServiceWorkerRegistration.showNotification`. No scheduled reminders, Web Push, VAPID, or app-closed delivery. iOS/iPadOS needs 16.4+ and a Home Screen install; OS settings still apply. This path is not verified on every OS/browser combination.

## Content and license

Texts are 103 curated quotes in English and Korean, each carrying its author and a work-or-source line shown when available. Photographs are AI-created and visually reviewed (`imageStatus` in `deck.json`). Released under the MIT License (see the repository LICENSE).

## Design contract

- Tokens: Aquila aliases (`--aq-*` in `aquila.css`, preset `aq-preset-toss-v2`) plus app aliases in `style.css`: spacing `--dqc-space-*`, type `--dqc-type-*`, and photo overlay tokens `--dqc-photo-ink` (#FFF), `--dqc-photo-ink-secondary`, `--dqc-photo-on-ink`, scrim `--dqc-photo-scrim` / `--dqc-photo-scrim-soft`.
- Type: Georgia serif 30px quote (25px Korean sans, 26/22px for long quotes), 32px heading, 16px body, 13px labels.
- Layout: `.shell` max-width 480px. `.stage` is a full-width 3:4 area with a 460px minimum height: `.deck` hosts seven overlapping 178×240 photo cards on a tilting arc above the drag hint; `#result` overlays the stage while a card is revealed. `#drawButton` sits below the stage.
- Revealed card: `#quoteCard` is a 3:4 portrait photo card — the drawn card's photograph under a gradient scrim that reaches .80 opacity, with the white quote near the bottom, theme/index metadata, attribution, a 13px source line when the deck provides one, a white Write your thought CTA, and bookmark/share icon buttons. Long quote/source text scrolls inside the card body instead of clipping or hiding the actions.
- Sheets: neutral Aquila bottom sheets (backdrop, Escape, Tab trap, focus restore) for adding a quote (120-char text + 40-char author with live counters and validation), writing a thought (300-char counter), and the month/day history calendar.
- Interaction: ≥44px targets, visible `:focus-visible` ring (white over the photo), `prefers-reduced-motion` honored (belt stops, reveals become instant).
- Responsive: 360px and 768px breakpoints adjust type scale and shell padding.

## Notes

This demo is deliberately separate from the Korean quotecard operating app; no GAS, src/, wrapper/ or deployment files are involved. The restored card mechanics are ported from that app's MIT-licensed front end. The PWA never caches or requests permissions on behalf of an external iframe.
