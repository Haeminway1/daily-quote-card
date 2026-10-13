# Daily Quote Card

103 quotes from the original deck, illustrated card art, and a private calendar of your thoughts. English by default, with the original Korean text and authors available through the language switch. No account is required.

[Try the live app](https://daily-quote-card.pages.dev/)

## Features

- Pull a photo card down from the spinning deck, or use the draw button or keyboard.
- Draw all 103 cards before a card repeats; swipe a revealed card down to dismiss it.
- Write a dated thought for a drawn card. Browse marked calendar days to revisit that day's cards and thoughts.
- Add your own quote to the deck. Quotes, thoughts, history and bookmarks stay in this browser on this device.
- Share a reflection through your browser's native sharing or clipboard support.
- Read cached cards offline after the first complete online visit.
- Install on supported browsers using the browser's app or Home Screen controls.

The optional notification button sends an immediate local test. There is no scheduled reminder, server Web Push subscription, or cross-device sync. Physical-device installation and operating-system notification display depend on browser and device settings.

## Run locally

The current public app lives in `english-demo/` and needs no build step or backend.

```sh
python3 -m http.server 4187 --directory english-demo
```

Open `http://localhost:4187/`. Production service workers and notifications require HTTPS. Clearing browser storage removes saved notes and cards.

The deck preserves the original quote IDs and includes English authors and work-or-source lines. The illustrations were created with AI; unfinished individual artwork uses the matching approved style sample. The older Korean GAS implementation remains in `src/` and `wrapper/`; the new public app has its own origin and does not change that deployment.

## License

MIT © 2026 Haemin Kim (Haeminway). See [LICENSE](LICENSE).
