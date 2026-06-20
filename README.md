# good-thought-card (좋은생각카드)

A tiny, polished **card-deck web app that runs entirely on Google Apps Script** —
no server, no monthly bill. Open the link, tap the deck, draw today's quote.

- **Live:** https://gas-quotecard.pages.dev
- **Write-up:** https://haeminway.com/ko/projects/good-thought-card

Built by [Haeminway](https://haeminway.com) to show two things: "apps built inside
a Google account look cheap" is a myth, and **you can build and serve a fun app for
yourself, for free.**

## What it is
- **Frontend:** a React card deck (vendored React, no build server) rendered by GAS HtmlService.
- **Backend:** Google Apps Script — `src/backend/*.gs`.
- **Hosting:** $0. It runs inside *your own* Google account. A thin Cloudflare Pages
  wrapper (`wrapper/`) gives it a clean URL + PWA install without renting a server.
- **Data:** each visitor's own added quotes/notes stay in their browser — no shared DB.

## Structure
```
src/frontend/   UI (app.jsx, css/js/index .html, vendored React)
src/backend/    GAS server (code.gs, api.gs, gas-backoff.gs)
src/frontend/quote-data.js   default deck (public-domain classics) — swap in your own
wrapper/        Cloudflare Pages PWA wrapper (config is placeholders, injected at deploy)
tools/          local build/deploy helpers (clasp)
docs/           architecture, deployment, design notes
```

## Build & deploy your own copy
1. `npm i -g @google/clasp && clasp login`
2. `./deploy.sh build` — compiles `src/` into the GAS payload.
3. Push & deploy with clasp. Keep the `/exec` URL stable by reusing the deployment id:
   `clasp deploy -i <deploymentId> -d "v1 $(git rev-parse --short HEAD)"`
   (details in `docs/DEPLOYMENT.md`; note `clasp push` ≠ `clasp deploy`).
4. (Optional) put it behind a clean URL + PWA install with the `wrapper/` (Cloudflare Pages).

## Make it yours
Edit `src/frontend/quote-data.js` and drop in your own lines. The default deck is
public-domain classical sayings, so it's safe to fork and ship.

> Note: `deploy.sh` / `compile_code.py` were adapted from the author's internal
> `gas_dev` harness; you may need to tweak paths for a standalone setup.

## License
MIT © 2026 Haemin Kim (Haeminway). See [LICENSE](LICENSE).
