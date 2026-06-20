# PRD: 좋은생각카드

## Purpose

`좋은생각카드`는 모바일에서 흐르는 카드 더미에서 한 장을 뽑는 듯한 짧은 상호작용으로 랜덤 명언을 보여주는 공개용 GAS 웹앱이다. 사용자는 별도 계정 없이 앱을 열고, 카드 한 장을 뽑고, 자신만의 명언과 생각 메모를 이 기기에 저장할 수 있다.

## Goals

- 첫 화면에서 앱 이름, 회전하는 카드 더미, 뽑기 액션을 즉시 제공한다.
- 탭/클릭, 아래 방향 포인터 드래그, 키보드 Enter/Space로 동일한 카드 뽑기 결과를 만든다.
- 사용자가 직접 명언을 추가하고, 추가한 명언을 기본 덱과 함께 뽑을 수 있다.
- 카드를 뽑은 뒤 내 생각 메모를 저장하고, 메모 달력에서 날짜별로 다시 볼 수 있다.
- 기본 명언 덱은 제공된 텍스트 원본에서 생성하되, public payload는 publish-safe 항목만 포함한다.
- 명언이 길거나 저자 정보가 없어도 모바일 화면 폭이 흔들리지 않는다.
- GAS HtmlService와 Cloudflare Pages wrapper가 서로 분리된 책임을 유지한다.

## Non-Goals

- 회원가입, OAuth, 공유 추적, 서버 데이터 저장은 포함하지 않는다.
- 사용자 명언과 메모는 브라우저 localStorage에만 저장한다.
- 외부 폰트, CDN CSS/JS, 원격 이미지, API-key 기반 미디어 생성을 사용하지 않는다.

## Users And Scenarios

- 일반 사용자: 이동 중 휴대폰으로 앱을 열고 한 장을 뽑아 짧은 문장을 본다.
- 반복 사용자: 같은 세션에서 여러 번 뽑되, 바로 이전 카드가 반복되지 않기를 기대한다.
- 기록 사용자: 직접 추가한 명언과 뽑은 카드에 대한 생각 메모를 나중에 날짜별로 다시 보고 싶어 한다.
- 접근성 사용자: 키보드나 보조기술에서도 덱이 버튼으로 인식되고 활성화되기를 기대한다.
- 운영자/소유자: source-side metadata로 어떤 원본 라인이 제외되었는지 확인할 수 있어야 한다.

## Functional Requirements

- App title and visible UI name: `좋은생각카드`.
- Initial state shows a deck control with `data-test-id="quote-deck"`.
- Revealed state shows:
  - quote card with `data-test-id="quote-card"`;
  - quote text with `data-test-id="quote-text"`;
  - author/source with `data-test-id="quote-author"`;
  - memo action with `data-test-id="memo-open"`.
- Add quote flow:
  - opens from `data-test-id="add-quote"`;
  - quote text field uses `data-test-id="add-quote-text"`;
  - save action uses `data-test-id="save-quote"`;
  - empty quote text shows validation and does not save;
  - saved custom quotes join the current local deck.
- Memo flow:
  - after drawing, `내 생각 메모` opens a bottom sheet;
  - empty memo text shows validation and does not save;
  - saved memo appears on `메모 달력`.
- Draw input modes:
  - tap/click draws immediately;
  - pointer drag draws only after a downward pull from the deck;
  - below-threshold pointer movement does not reveal a card;
  - Enter and Space on the deck button draw.
- Random selection avoids immediate repeats when the public deck size is greater than 1.
- Test-only deterministic RNG hooks may exist under `window.GOOD_THOUGHT_CARD_TEST`; no debug UI is visible to users.

## Quote Data Requirements

- Parser reads the provided UTF-8 a plain-text source.
- Source-side full record count target: 104 quote candidates.
- Browser-visible public count target: 103 quote records.
- One explicit-profane entry from source line 66 is excluded from the browser-visible deck.
- `data/processed/quote-deck.full.json` preserves source spans, flags, exclusion status, IDs, and normalized author data.
- `src/frontend/quote-data.js` defines `window.QUOTE_DECK` and includes only publish-safe public records.
- Compiled runtime `index.html` must not contain the explicit excluded text.
- User-added quote storage key: `jotcard.quotes.v1`.
- Memo storage key: `jotcard.memos.v1`.

## Content And Voice

- Korean UI copy should be concise, calm, and public-use safe.
- The app may say `오늘의 카드`, `명언 추가`, `내 생각 메모`, `메모 달력`, and `미상`.
- Do not display technical explanations, keyboard shortcut instructions, parser details, or implementation notes in-app.
- If a quote has no author, show a simple fallback rather than a warning.

## Technical Requirements

- Source stays under `src/`.
- Runtime output stays under the `gas.project.json` runtime directory.
- GAS output must be self-contained: no CDN, remote fonts, external CSS/JS, or network media dependencies.
- Cloudflare wrapper project name remains `gas-quotecard`.
- Wrapper metadata, manifest identity, service worker cache naming, localStorage key, and app handshake must be project-specific.
- Deploy scripts may be run only in local build or dry-run modes unless the owner explicitly approves production deployment.

## Acceptance Gates

- Product/docs/design files are app-specific and non-placeholder.
- Quote import tests pass and record source/public/excluded counts.
- Build tests prove `window.QUOTE_DECK` is bundled before React app code.
- Card draw Playwright QA passes for click, drag, keyboard, threshold, no-repeat, add-quote, memo/calendar, and excluded-content absence.
- Mobile viewport and adaptive viewport tests pass.
- Inline resource and design antipattern tests pass.
- Wrapper build, Cloudflare live deploy, and wrapper live smoke tests pass when owner approval is given.
