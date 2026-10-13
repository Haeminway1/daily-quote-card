# Daily Quote Card

Twelve original reflections, photographic cards, and a private note for each thought. English by default, with an optional Korean interface. No account is required.

[Try the live app](https://daily-quote-card.pages.dev/)

## Features

- Draw all twelve cards before a card repeats.
- Save a card and write a note; both stay in this browser on this device.
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

All twelve English reflections were written for this app and are labeled “Original reflection.” The editorial photographs were created with AI. The older Korean GAS implementation remains in `src/` and `wrapper/`; the new public app has its own origin and does not change that deployment.

## License

MIT © 2026 Haemin Kim (Haeminway). See [LICENSE](LICENSE).
