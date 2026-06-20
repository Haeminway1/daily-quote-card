# Architecture: quotecard

The app uses Apps Script backend files from `src/backend/` and HtmlService
frontend files from `src/frontend/`.

## Public Multi-User Model

The deployed app is safe to open to anonymous public users as a local-first
quote card app:

- `appsscript.json` exposes the web app as `ANYONE_ANONYMOUS` with
  `executeAs: USER_DEPLOYING`.
- `oauthScopes` is empty, and the current HtmlService client does not call
  `google.script.run`, `fetch`, or other write APIs.
- The default quote deck is bundled as static public data in
  `src/frontend/quote-data.js`.
- User-added quotes and memos are stored only in each visitor's browser
  `localStorage` under `jotcard.quotes.v1` and `jotcard.memos.v1`.

Because of that boundary, one visitor's added quotes and memos are not visible
to another visitor. They also do not sync across the same visitor's devices,
browsers, private browsing sessions, or cleared app storage.

## Frame Wrapper Handshake

The Cloudflare wrapper and GAS iframe exchange `GAS_WRAPPER_READY` and
`GAS_FRAME_VERIFIED` messages so the wrapper can tell when the embedded GAS app
is ready. The frontend keeps this non-blocking handshake but does not show a
visible "checking wrapper" banner to users.

## Future Shared Data Boundary

A future shared quote feed, shared memo feature, favorite sync, or admin review
queue must not reuse the current local-only assumptions. Before adding any
backend write path, decide and document:

- whether submissions are private, public, or owner-only;
- how users are warned before submitting public or owner-readable text;
- moderation rules for offensive content, spam, and personal information;
- rate limits and size limits for anonymous visitors;
- quota ownership, because anonymous visitors would otherwise consume the
  deploying owner's Apps Script quota;
- concurrency behavior for writes, including `LockService` or another storage
  strategy.
