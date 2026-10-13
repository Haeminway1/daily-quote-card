# Daily Quote Card

A standalone, English-first (EN/KO) PWA: twelve original reflections on AI-created illustrations, each with a private on-device note. Live at https://daily-quote-card.pages.dev/

## Run

- Preview: `python3 -m http.server 4187 --directory english-demo` (localhost is a secure-context exception). Production requires HTTPS on its own origin.
- QA: `python3 qa.py --url http://localhost:4187 --out qa-out` — real headless-browser checks plus screenshots, writes `qa.json`, exits nonzero on failure.

## What it does

- Deals one card at a time; every block of 12 draws contains each card exactly once and never repeats the previous card across a block boundary.
- Bookmark cards and keep a private note per card. English/Korean UI from the header selector.
- Share through the native share sheet with a clipboard fallback. Installable as a standalone app where the browser supports it.

## Limits (stated accurately)

- Storage: language, position, saved cards and notes live in this browser's `localStorage` under `daily-quote-card:v1`. Nothing leaves the device; clearing site data erases them. No sync.
- Offline: the service worker (`daily-quote-card-shell-v2`) precaches the shell and all 12 illustrations at install; install fails if any image is missing. Same-origin GET requests only; offline navigations fall back to the cached shell. The first visit must be online.
- Install: uses the browser's own flow (`beforeinstallprompt` when offered, otherwise a help dialog). On iPhone/iPad: Safari → Share → Add to Home Screen. Availability depends on the browser.
- Notifications: the button requests permission inside the click and posts one immediate local notification via `ServiceWorkerRegistration.showNotification`. No scheduled reminders, Web Push, VAPID, or app-closed delivery. iOS/iPadOS needs 16.4+ and a Home Screen install; OS settings still apply.

## Content and license

Texts are original reflections written for this app; no famous attribution is claimed. Illustrations are AI-created and visually reviewed (`imageStatus` in `deck.json`). Released under the MIT License (see the repository LICENSE).

## Design contract

- Tokens: Aquila aliases (`--aq-*` in `aquila.css`, preset `aq-preset-toss-v2`) plus app aliases in `style.css`: spacing `--dqc-space-*`, type `--dqc-type-*`, and photo overlay tokens `--dqc-photo-ink` (#FFF), `--dqc-photo-ink-secondary`, `--dqc-photo-on-ink`, scrim `--dqc-photo-scrim` / `--dqc-photo-scrim-soft`.
- Type: Georgia serif 30px quote (25px Korean sans), 32px heading, 16px body, 13px labels.
- Layout: `.shell` max-width 480px. `.reflection` is a CSS grid where `.media` (portrait, 3:4, min-height 460px) and `.card-body` share one cell; card-body anchors to the bottom over a gradient scrim that reaches .80 opacity by a quarter of its height and .88 at the bottom, so the white quote and .90-opacity secondary metadata stay readable over the brightest art while the upper photograph remains visible.
- States: image "pending" placeholder, saved bookmark via `aria-pressed`, draw button disabled if the deck fails to load, offline/ready status line.
- Interaction: ≥44px targets, visible `:focus-visible` ring (white over the photo), `prefers-reduced-motion` honored.
- Responsive: 360px and 768px breakpoints adjust type scale and shell padding.

## Notes

This demo is deliberately separate from the Korean quotecard operating app; no GAS, src/, wrapper/ or deployment files are involved. The PWA never caches or requests permissions on behalf of an external iframe.
