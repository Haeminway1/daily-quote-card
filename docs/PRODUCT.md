# 좋은생각카드 Product Context

Locale: ko-KR

`좋은생각카드`는 누구나 모바일에서 가볍게 카드 한 장을 뽑아 짧은 문장을 만나는 공개용 웹앱이다. 첫 화면은 설명형 랜딩 페이지가 아니라 바로 덱을 만지고 뽑을 수 있는 앱 화면이어야 한다.

## Audience

- Primary users: 출퇴근, 휴식, 대화 시작점이 필요할 때 짧은 명언을 보고 싶은 일반 사용자.
- Device baseline: 375-390px 모바일 viewport, 데스크톱에서는 최대 480px 중심 앱 셸.
- Context: 한 손 사용, 짧은 체류, 반복 사용. 로그인, 가입, 저장소 설정 없이 바로 동작한다.
- Accessibility baseline: 버튼으로 인식되는 덱, Enter/Space 키 동작, 충분한 터치 타깃, prefers-reduced-motion 대응.

## Product Intent

- Core feeling: 실제 카드 덱에서 한 장을 뽑는 느낌이 앱의 중심이다.
- Primary action: 사용자가 흐르는 카드 더미에서 가운데 카드를 탭하거나 아래로 드래그해 뽑으면 랜덤 명언이 열린다.
- Add action: 사용자는 상단 `＋` 버튼으로 자신만의 명언을 추가할 수 있고, 추가된 명언은 이 기기의 localStorage에 저장되어 기본 덱과 함께 뽑힌다.
- Memo action: 카드를 뽑은 뒤 `내 생각 메모`를 남기면 날짜별 달력에서 다시 볼 수 있다.
- Repeat behavior: 다시 뽑기는 즉시 이전 카드가 반복되지 않도록 한다.
- Tone: 공공장소에서도 보기에 부담 없는 차분하고 따뜻한 한국어 UI. 과한 감성 문구보다 짧고 직접적인 버튼과 상태 텍스트를 쓴다.
- First-screen rule: 앱 이름, 카드 덱, 뽑기 가능한 상태가 첫 viewport에 보여야 한다.

## Content Policy

- Default deck comes from the user-provided a plain-text source.
- Browser-visible payload includes only publish-safe quotes.
- Explicit profanity or public-use-risky entries are excluded from `src/frontend/quote-data.js` and compiled runtime HTML.
- Excluded records remain source-side only for audit metadata and parser verification.
- Quote output must not log or print the full deck in test output.
- Missing authors fall back to `미상`; the UI must not invent authors.

## Data And Auth Boundary

- No OAuth.
- No account system.
- No backend data store.
- User-added quotes and memos are local/private browser data in the first version.
- Quote data is compiled into the GAS HtmlService bundle as a static public default deck.
- User-added quotes and memos use localStorage keys `jotcard.quotes.v1` and `jotcard.memos.v1`.
- Public visitors do not share user-added quotes or memos with each other in
  this version.
- Local data may disappear if the visitor clears browser data, uses private
  mode, uninstalls the PWA wrapper, or if the browser evicts third-party iframe
  storage.
- Any future server sync/favorite feature requires a separate privacy and storage decision before implementation.
- Any future shared quote or shared memo feature also requires moderation,
  abuse limits, and explicit copy explaining who can read submitted text.

## Cloudflare Wrapper Boundary

- GAS remains the app implementation surface.
- Cloudflare Pages wrapper is only a per-project installable shell for `gas-quotecard`.
- Wrapper dry-run and local wrapper QA are allowed.
- Real Cloudflare deploy, project creation/deletion, or production deploy changes require explicit owner approval after local evidence.
- The wrapper must not reuse another app's localStorage keys, service worker cache names, manifest identity, or handshake naming.

## UX Principles

- Make the card draw feel tactile but not flashy.
- Use motion to explain state: deck resting, card lifting/drawing, revealed quote.
- Keep long quotes readable without changing shell width.
- Avoid decorative hero sections, CDN assets, remote fonts, generated network images, and purple/blue gradient decoration.
- Keep labels short: `오늘의 카드`, `명언 추가`, `내 생각 메모`, `메모 달력`.

## QA Gates

- Quote import contract proves full/source counts, public counts, explicit exclusion, IDs, and line provenance.
- Runtime build proves `window.QUOTE_DECK` is bundled before React code and explicit excluded text is absent.
- Mobile/adaptive tests cover 375px, 390px, and desktop centered shell behavior.
- Browser interaction QA covers click/tap, pointer drag threshold, below-threshold drag, keyboard Enter/Space, no-immediate-repeat, and profanity absence.
- Inline-resource and design-antipattern checks prove no external CSS, JavaScript, fonts, or CDN assets.
- Deploy guard and wrapper dry-run evidence prove no live GAS or Cloudflare production deploy happened.
