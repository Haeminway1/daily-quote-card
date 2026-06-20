const DRAW_THRESHOLD = 48;
const CLICK_MOVE_TOLERANCE = 4;

function createSeededRandom(seed) {
  let state = Number.isFinite(seed) ? Math.trunc(seed) : Date.now();
  state = (state >>> 0) || 1;
  return function nextRandom() {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function displayAuthor(author) {
  return author && author !== 'Unknown' ? author : '미상';
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

window.initializeGoodThoughtCard = function initializeGoodThoughtCard() {
  const root = document.querySelector('[data-test-id="good-thought-card"]');
  if (!root || root.dataset.initialized === 'true') return;
  root.dataset.initialized = 'true';

  const deck = Array.isArray(window.QUOTE_DECK) ? window.QUOTE_DECK : [];
  const testHook = window.GOOD_THOUGHT_CARD_TEST = window.GOOD_THOUGHT_CARD_TEST || {};
  const random = createSeededRandom(Number(testHook.seed));
  const deckButton = root.querySelector('[data-test-id="quote-deck"]');
  const card = root.querySelector('[data-test-id="quote-card"]');
  const quoteText = root.querySelector('[data-test-id="quote-text"]');
  const quoteAuthor = root.querySelector('[data-test-id="quote-author"]');
  const drawAgain = root.querySelector('[data-test-id="draw-again"]');
  const announcement = root.querySelector('[data-test-id="quote-announcement"]');
  const deckCount = root.querySelector('[data-test-id="deck-count"]');
  const quoteLabel = root.querySelector('[data-test-id="quote-label"]');
  const quoteState = root.querySelector('[data-test-id="quote-state"]');
  let lastId = '';
  let pointer = null;
  let suppressClick = false;

  if (deckCount) deckCount.textContent = `${deck.length}장`;
  if (!deck.length) {
    if (deckButton) deckButton.disabled = true;
    if (drawAgain) drawAgain.disabled = true;
    return;
  }

  function chooseQuote() {
    const rawIndex = Math.floor(random() * deck.length);
    let index = Math.max(0, Math.min(deck.length - 1, rawIndex));
    if (deck.length > 1 && deck[index].id === lastId) index = (index + 1) % deck.length;
    return deck[index];
  }

  function resetDrag() {
    if (!deckButton) return;
    deckButton.style.setProperty('--qc-drag-x', '0px');
    deckButton.style.setProperty('--qc-drag-y', '0px');
    deckButton.classList.remove('is-dragging');
  }

  function reveal(quote) {
    if (!quote || !card || !quoteText || !quoteAuthor) return;
    lastId = quote.id;
    testHook.lastDrawId = quote.id;
    testHook.drawCount = (testHook.drawCount || 0) + 1;
    card.dataset.state = 'revealed';
    card.classList.remove('is-ready');
    card.classList.add('is-revealed');
    quoteText.textContent = quote.text;
    quoteAuthor.textContent = displayAuthor(quote.author);
    if (quoteLabel) quoteLabel.textContent = '펼쳐진 카드';
    if (quoteState) quoteState.textContent = '준비됨';
    if (announcement) announcement.textContent = `${quote.text} ${displayAuthor(quote.author)}`;
    resetDrag();
    window.setTimeout(() => {
      if (typeof window.updateMobileViewportStatus === 'function') window.updateMobileViewportStatus();
    }, 0);
  }

  function drawQuote() {
    reveal(chooseQuote());
  }

  function handlePointerDown(event) {
    pointer = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      moved: 0,
    };
    deckButton.classList.add('is-dragging');
    try {
      deckButton.setPointerCapture(event.pointerId);
    } catch (_) {}
  }

  function handlePointerMove(event) {
    if (!pointer || pointer.id !== event.pointerId) return;
    const dx = event.clientX - pointer.x;
    const dy = event.clientY - pointer.y;
    pointer.moved = Math.max(pointer.moved, Math.abs(dx), Math.abs(dy));
    deckButton.style.setProperty('--qc-drag-x', `${clamp(dx, -84, 84)}px`);
    deckButton.style.setProperty('--qc-drag-y', `${clamp(dy, -54, 54)}px`);
  }

  function handlePointerUp(event) {
    if (!pointer || pointer.id !== event.pointerId) return;
    const moved = pointer.moved;
    pointer = null;
    try {
      deckButton.releasePointerCapture(event.pointerId);
    } catch (_) {}

    if (moved >= DRAW_THRESHOLD) {
      suppressClick = true;
      drawQuote();
    } else {
      if (moved > CLICK_MOVE_TOLERANCE) suppressClick = true;
      resetDrag();
    }
    window.setTimeout(() => {
      suppressClick = false;
    }, 0);
  }

  function handlePointerCancel() {
    pointer = null;
    suppressClick = true;
    resetDrag();
    window.setTimeout(() => {
      suppressClick = false;
    }, 0);
  }

  function handleClick(event) {
    if (suppressClick) {
      event.preventDefault();
      return;
    }
    drawQuote();
  }

  deckButton.addEventListener('pointerdown', handlePointerDown);
  deckButton.addEventListener('pointermove', handlePointerMove);
  deckButton.addEventListener('pointerup', handlePointerUp);
  deckButton.addEventListener('pointercancel', handlePointerCancel);
  deckButton.addEventListener('click', handleClick);
  drawAgain.addEventListener('click', drawQuote);
};

window.App = function App() {
  const deck = Array.isArray(window.QUOTE_DECK) ? window.QUOTE_DECK : [];
  window.setTimeout(window.initializeGoodThoughtCard, 0);

  return (
    <section className="quote-app" data-test-id="good-thought-card" aria-label="좋은생각카드">
      <header className="app-header">
        <div className="title-group">
          <p className="kicker">오늘의 카드</p>
          <h1>좋은생각카드</h1>
        </div>
        <span className="deck-count" data-test-id="deck-count" aria-label={`공개 카드 ${deck.length}장`}>{deck.length}장</span>
      </header>

      <div className="deck-zone">
        <button
          type="button"
          className="deck-button"
          data-test-id="quote-deck"
          aria-label="명언 카드 뽑기"
        >
          <span className="deck-card" aria-hidden="true"></span>
          <span className="deck-card" aria-hidden="true"></span>
          <span className="deck-card deck-card-top" aria-hidden="true">
            <span className="deck-face">
              <span className="deck-mark"></span>
              <span className="deck-label">뽑기</span>
            </span>
          </span>
        </button>
        <span className="draw-affordance" aria-hidden="true"></span>
      </div>

      <article
        className="quote-card is-ready"
        data-test-id="quote-card"
        data-state="ready"
      >
        <div className="quote-meta">
          <span data-test-id="quote-label">준비된 카드</span>
          <span className="quote-state" data-test-id="quote-state">대기</span>
        </div>
        <p className="quote-text" data-test-id="quote-text"></p>
        <p className="quote-author" data-test-id="quote-author"></p>
        <div className="ready-mark" aria-hidden="true">
          <span></span>
          <span></span>
        </div>
      </article>

      <div className="actions">
        <button type="button" className="redraw-button" data-test-id="draw-again">다시 뽑기</button>
        <p className="repeat-note">이전 카드와 겹치지 않게</p>
      </div>

      <p className="sr-only" data-test-id="quote-announcement" aria-live="polite"></p>
    </section>
  );
};
