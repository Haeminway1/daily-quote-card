# Frontend Handoff: 좋은생각카드

이 문서는 프론트 디자인과 모션만 다시 잡을 때 필요한 구조 설명이다. 프로덕션 로직을 바로 바꾸기 전에 `design/mockups/frontend-editable.html`을 먼저 수정해서 화면, 카드 질감, 드로우 모션, 시트 흐름을 확정하는 방식이 가장 안전하다.

## 바로 수정할 디자인 코드

- 편집 파일: `design/mockups/frontend-editable.html`
- 성격: GAS 런타임과 분리된 단일 HTML/CSS/JS 프로토타입
- 실행: 브라우저에서 파일을 직접 열면 된다.
- 외부 의존성: 없음. CDN, 원격 폰트, 원격 이미지, 외부 JS를 넣지 않는다.

파일 안에서 먼저 볼 곳:

1. `:root` CSS 변수: 색, 그림자, 카드 반경, easing, 폰트 스택
2. `.deck-stage`, `.deck-card`, `.motion-card`: 카드 더미와 뽑기 모션
3. `.quote-card`, `.quote-text`, `.quote-author`: 결과 카드
4. `.sheet-root`, `.sheet`: 명언 추가, 메모, 달력 bottom sheet
5. 아래쪽 `.prototype-tools`: ready, quote, long, custom 상태 전환용

## 실제 프론트 소스 구조

실제 GAS 앱은 `src/frontend/` 아래 세 파일이 중심이다.

- `src/frontend/index.html`: DOM 구조, GAS include, PWA frame guard, modal/sheet 마크업
- `src/frontend/css.html`: 실제 앱 스타일과 keyframes
- `src/frontend/js.html`: 카드 뽑기, 포인터 드래그, 키보드 입력, localStorage, bottom sheet, 달력 로직
- `src/frontend/quote-data.js`: 빌드 전에 생성된 공개 명언 데이터. 손수 편집하지 않는다.

빌드 흐름:

1. `compile_code.py`가 `src/frontend/index.html`을 읽는다.
2. `<?!= include('css') ?>` 자리에 `src/frontend/css.html`을 넣는다.
3. `src/frontend/quote-data.js`와 `src/frontend/js.html`을 런타임 HTML에 인라인한다.
4. 결과물은 `gas.project.json`의 `runtimeDir` 아래 `build/index.html`로 만들어진다.

## 유지해야 하는 DOM 계약

테스트와 기능 로직이 의존하는 값이다. 디자인을 바꿔도 이 selector는 유지한다.

- `data-test-id="app-shell"`
- `data-test-id="quote-deck"`
- `data-test-id="quote-card"`
- `data-test-id="quote-text"`
- `data-test-id="quote-author"`
- `data-test-id="quote-announcement"`
- `data-test-id="add-quote"`
- `data-test-id="add-quote-text"`
- `data-test-id="add-quote-author"`
- `data-test-id="save-quote"`
- `data-test-id="memo-open"`
- `data-test-id="memo-calendar"`

접근성 계약도 유지한다.

- 덱은 버튼처럼 동작해야 한다.
- Enter와 Space로 카드가 뽑혀야 한다.
- 새 명언은 polite live region에 들어가야 한다.
- bottom sheet는 `role="dialog"`와 `aria-modal="true"`를 유지한다.

## 현재 인터랙션 모델

카드 뽑기는 세 입력을 같은 결과로 연결한다.

- 탭/클릭: 중심 카드가 눌리고 아래로 빠지며 결과 카드가 열린다.
- 드래그: 덱 위 카드가 포인터를 따라가고, 기준 거리 이상이면 뽑힌다.
- 키보드: `quote-deck`에 포커스가 있을 때 Enter/Space로 뽑힌다.

실제 앱의 주요 JS 함수 위치:

- 덱 생성: `buildDeck()`
- 카드 위치 계산: `styleFor()`, `apply()`
- 포인터 잡기: `onDown()`, `onMove()`, `onUp()`
- 뽑기 실행: `doDraw()`
- 결과 표시: `reveal()`
- 결과 카드 내리기: `dismissQuote()`

모션을 바꿀 때는 `THRESHOLD`, `SPEED`, `CARD_W`, `CARD_H`, `GAP`, `styleFor()`, `doDraw()`의 transition 값을 함께 본다.

## 데이터와 저장소

- 기본 공개 명언은 `window.QUOTE_DECK`에서 온다.
- source-side 원본 후보는 104개이고, 브라우저 공개 덱은 103개다.
- 제외된 explicit source 항목은 UI와 빌드 결과에 절대 나오면 안 된다.
- 사용자가 추가한 명언 저장소 키: `jotcard.quotes.v1`
- 사용자가 저장한 메모 저장소 키: `jotcard.memos.v1`
- 첫 버전은 로그인과 서버 저장이 없고, 사용자 입력은 이 브라우저 localStorage에만 남는다.

## 프론트만 할 때 건드리지 않을 것

- `src/backend/`: GAS 서버 함수
- `data/processed/`: 명언 import 결과. 디자인 변경으로 직접 수정하지 않는다.
- `wrapper/`: Cloudflare Pages wrapper. 앱 iframe 껍데기이므로 화면 디자인 확정 전에는 건드리지 않는다.
- `appsscript.json`, `.deployment-id.*`, `.webapp-url.*`: 배포/런타임 경계
- `.clasprc.json`, `.env`: 인증/비밀 파일. 커밋하지 않는다.

## 포팅 순서

1. `design/mockups/frontend-editable.html`에서 시각과 모션을 수정한다.
2. 확정된 CSS 변수와 컴포넌트 스타일을 `src/frontend/css.html`로 옮긴다.
3. 필요한 DOM 구조 변경을 `src/frontend/index.html`에 반영한다.
4. 모션이 새 구조를 요구하면 `src/frontend/js.html`의 덱 관련 함수만 좁게 수정한다.
5. `data-test-id`와 localStorage 키를 유지한 채 빌드와 모바일 검증을 돌린다.

## 검증 명령

디자인 파일만 확인:

```bash
node tests/inline-resource-check.mjs design/mockups/frontend-editable.html
node tests/design-antipattern-check.mjs design/mockups/frontend-editable.html
```

실제 앱에 포팅한 뒤:

```bash
npm run build
npm run test:project-contract
npm run test:mobile:local
npm run test:adaptive:local
node tests/card-draw-check.mjs "$(node tests/runtime-path.mjs build/index.html)" --mode all
```

## 디자인 수정 체크리스트

- 390px 폭에서 가로 스크롤이 없다.
- 카드 더미, 결과 카드, bottom sheet가 같은 화면 언어를 쓴다.
- 버튼 반경은 작게 유지하고, 실제 종이 카드만 더 큰 반경을 쓴다.
- 명언이 길어져도 shell 폭이 흔들리지 않는다.
- `prefers-reduced-motion: reduce`에서 이동 모션이 사실상 사라진다.
- 앱 안에 구현 설명이나 키보드 단축키 설명이 보이지 않는다.
- 명언 추가 empty/error/saved 상태가 디자인에 포함된다.
