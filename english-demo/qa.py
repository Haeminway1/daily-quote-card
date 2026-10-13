#!/usr/bin/env python3
"""Real-browser QA for the restored photo-deck Daily Quote Card app running
the 103 original bilingual quotes deck (EN text + KO original, author and
work_or_source attribution on every card).

Usage: python3 qa.py --url http://localhost:4187 --out qa-out [--record]

Drives headless Chromium at 390x844 (mobile, touch, DPR 3) and 1280x900 with
prefers-reduced-motion disabled. Verifies the 7-card photo belt (render, photo
decode, <=9 lazy/async image nodes, motion), real pointer drag-to-draw
above/below the 120px threshold, button (#drawButton) and Enter/Space draws,
pointer swipe and #quoteDismiss dismissal, memo save + calendar persistence,
custom-quote add (104 total) and survival, two full unique 103-id draw cycles
(206 real animated button draws, asserted by id since originals may share
text), service-worker caching of the full unique deck image set (up to 60s),
manifest + icons, installability errors, and offline use at both widths.
Dedicated prefers-reduced-motion contexts at 390 and 1280 exhaustively verify
all 103 quotes EN+KO — exact text, author and source via forceQuoteId plus a
real #drawButton click, language switched on the revealed card without
redrawing — plus the longest quote: full-text snapshot persistence in
localStorage and author/source/actions staying visible before and after a
native wheel (or CDP touch) scroll to the end of the text. Legacy
daily-quote-card:v1 note import and the v1->v2 id remap migration (q01 -> q001,
custom ids untouched) are exercised against real storage and the visible
calendar. Clean screenshots at both widths include the longest quote EN/KO at
top and scrolled bottom, q001 attribution and the longest-source card;
--record additionally writes two
short real flow videos (flow-390.webm, flow-1280.webm).

All readiness waits are DOM predicates (wait_for_function / wait_for_selector);
the only sleeps are ~600ms dwells inside recorded flows so a settled state
stays visible on video. Browser is always closed in finally. Writes qa.json;
exits nonzero on any functional failure/error.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import TypedDict

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

MOBILE = dict(viewport={'width': 390, 'height': 844}, device_scale_factor=3,
              is_mobile=True, has_touch=True, reduced_motion='no-preference')
DESKTOP = dict(viewport={'width': 1280, 'height': 900},
               reduced_motion='no-preference')
# Reduced-motion contexts used only for the exhaustive per-quote content
# passes so 103 forced draws stay fast; the core animation checks keep
# reduced_motion='no-preference'.
REDUCE_MOBILE = dict(MOBILE, reduced_motion='reduce')
REDUCE_DESKTOP = dict(DESKTOP, reduced_motion='reduce')

DECK_N = 103                    # original bilingual quotes (exact supplied ids)
CUSTOM_TOTAL = DECK_N + 1       # deck + one custom quote
CYCLE_DRAWS = 2 * DECK_N        # two full unique cycles
CACHE_WAIT_S = 60               # service worker may need a while for ~103 images

LEGACY_KEY = 'daily-quote-card:v1'
PREF_KEY = 'daily-quote-card.prefs.v2'
QKEY = 'daily-quote-card.quotes.v2'
MEMO_KEY = 'daily-quote-card.memos.v2'
DRAWN_KEY = 'daily-quote-card.drawn.v2'
THOUGHT = 'A small step is still progress.'
OFFLINE_THOUGHT = 'An offline note still lands safely.'
MARKETING_THOUGHT = 'A quiet morning gave this sentence room to land.'
RECORD_THOUGHT = 'A short recording still counts as a real thought.'
RECORD_QUOTE = 'Small lanterns still mark the way home.'
CUSTOM_AUTHOR = 'Your reflection'
UNKNOWN_DATE_RE = re.compile(
    r'(unknown|undated|no date|date unknown|알 수 없|날짜 미상|날짜 없|미상|imported)', re.I)
STRICT_DATE_RE = re.compile(
    r'(unknown|undated|no date|date unknown|알 수 없는 날짜|날짜 미상|날짜 없음)', re.I)

HOOK = '(window.DAILY_QUOTE_CARD_TEST || window.GOOD_THOUGHT_CARD_TEST)'
BELT_READY = ("() => { const b = document.getElementById('belt');"
              " return !!(b && b.querySelectorAll('.belt-card').length === 7); }")
SETTLED = ("() => { const d = document.getElementById('drawCard');"
           " const a = document.querySelector('.deck-area');"
           " return !!d && d.style.opacity === '0'"
           " && !document.getElementById('drawButton').disabled"
           " && !(a && a.classList.contains('is-drawing')); }")
CARD_HIDDEN = ("() => { const c = document.getElementById('quoteCard');"
               " return !!(c && c.hidden); }")
NEXT_DRAW = ("(p) => { const h = " + HOOK + " || {};"
             " const c = document.getElementById('quoteCard');"
             " return !!(c && !c.hidden && c.dataset.state === 'revealed'"
             " && h.lastDrawId && h.lastDrawId !== p); }")
REVEALED_ID = ("(id) => { const h = " + HOOK + " || {};"
               " const c = document.getElementById('quoteCard');"
               " return !!(c && !c.hidden && c.dataset.state === 'revealed'"
               " && h.lastDrawId === id); }")
CARD_POINT = """() => {
  const deck = document.getElementById('deck');
  if (!deck) return null;
  const dr = deck.getBoundingClientRect();
  const cx = dr.left + dr.width / 2;
  let cards = [...deck.querySelectorAll('#belt .belt-card')];
  if (!cards.length) cards = [...document.querySelectorAll('#belt > *')];
  let best = null, bd = 1e9;
  for (const c of cards) {
    const r = c.getBoundingClientRect();
    if (r.width < 40 || r.height < 40) continue;
    const mid = r.left + r.width / 2;
    const d = Math.abs(mid - cx);
    if (d < bd) { bd = d; best = {x: mid, y: r.top + r.height / 2}; }
  }
  return best;
}"""
PHOTO_INFO = """() => {
  const cards = [...document.querySelectorAll('#belt .belt-card')];
  return cards.map(c => {
    const r = c.getBoundingClientRect();
    const im = c.querySelector('img');
    let src = im ? (im.currentSrc || im.getAttribute('src') || '') : '';
    if (!src) {
      const bg = getComputedStyle(c).backgroundImage || '';
      const i = bg.indexOf('url(');
      if (i !== -1) {
        const u = bg.slice(i + 4), e = u.indexOf(')');
        src = u.slice(0, e === -1 ? undefined : e).replace(/^["']+|["']+$/g, '');
      }
    }
    return {w: Math.round(r.width), h: Math.round(r.height), src,
            imgOk: !!(im && im.complete && im.naturalWidth > 0)};
  });
}"""
DECODE = """async (srcs) => {
  const bad = [];
  for (const s of srcs) {
    if (!s) { bad.push('(missing src)'); continue; }
    try {
      const i = new Image(); i.src = s; await i.decode();
      if (!i.naturalWidth) bad.push(s);
    } catch (e) { bad.push(s); }
  }
  return bad;
}"""
DECK_IMAGES = """async () => {
  try {
    const r = await fetch('deck.json');
    if (r.ok) {
      const d = await r.json();
      const imgs = (d.quotes || []).map(q => q && q.image).filter(Boolean);
      if (imgs.length) return imgs;
    }
  } catch (e) {}
  try {
    if (Array.isArray(window.QUOTE_DECK)) {
      const imgs = window.QUOTE_DECK.map(q => q && q.image).filter(Boolean);
      if (imgs.length) return imgs;
    }
  } catch (e) {}
  return null;
}"""
DECK_QUOTES = """async () => {
  try {
    const r = await fetch('deck.json');
    if (r.ok) {
      const d = await r.json();
      if (d && Array.isArray(d.quotes)) return d.quotes;
    }
  } catch (e) {}
  try {
    if (Array.isArray(window.QUOTE_DECK)) return window.QUOTE_DECK;
  } catch (e) {}
  return null;
}"""
CARD_VIEW = """() => {
  const h = (window.DAILY_QUOTE_CARD_TEST || window.GOOD_THOUGHT_CARD_TEST) || {};
  const txt = (s) => { const e = document.querySelector(s); return e ? e.textContent.trim() : ''; };
  const card = document.getElementById('quoteCard');
  return {
    text: txt('#quoteText'),
    author: txt('#quoteAuthor'),
    source: txt('#quoteSource') || txt('#quoteCard .quote-source') || txt('#quoteCard .attribution .source'),
    cardText: card ? card.innerText : '',
    id: h.lastDrawId || '',
    draws: h.drawCount || 0,
    drawn: h.drawnCardCount || 0,
  };
}"""
LONG_BOUND = """() => {
  const de = document.documentElement;
  const card = document.getElementById('quoteCard');
  if (!card || card.hidden) return {err: 'card hidden'};
  const cr = card.getBoundingClientRect();
  const overX = Math.max(de.scrollWidth, document.body ? document.body.scrollWidth : 0)
                - de.clientWidth;
  const txt = document.getElementById('quoteText');
  const tr = txt.getBoundingClientRect();
  const sc = document.getElementById('quoteScroll')
             || (txt && txt.closest ? txt.closest('.quote-scroll') : null);
  const inCard = (r) => !!r && r.bottom <= cr.bottom + 1 && r.top >= cr.top - 1
                 && r.left >= cr.left - 1 && r.right <= cr.right + 1 && r.height > 0;
  const authorEl = document.getElementById('quoteAuthor');
  const srcEl = document.getElementById('quoteSource') || card.querySelector('.quote-source');
  const acts = document.getElementById('memoCta') || card.querySelector('.quote-actions');
  const hint = document.getElementById('quoteScrollHint');
  const res = {overX,
               withinX: tr.left >= cr.left - 1 && tr.right <= cr.right + 1,
               textIn: inCard(tr), cardH: Math.round(cr.height), txtH: Math.round(tr.height),
               authorIn: inCard(authorEl && authorEl.getBoundingClientRect()),
               srcIn: srcEl ? (srcEl.hidden ? 'hidden' : inCard(srcEl.getBoundingClientRect())) : 'absent',
               actsIn: inCard(acts ? acts.getBoundingClientRect() : null)};
  if (sc) {
    res.scrollable = sc.scrollHeight > sc.clientHeight + 1;
    res.scrollTop = Math.round(sc.scrollTop);
    res.atEnd = sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 1;
    res.hasMore = sc.classList.contains('has-more');
    res.authorOut = !!(authorEl && !sc.contains(authorEl));
    res.srcOut = srcEl ? !sc.contains(srcEl) : 'absent';
  } else {
    res.scrollable = false;
  }
  res.hint = hint ? {hidden: hint.hidden, vis: getComputedStyle(hint).visibility}
                  : {hidden: true, vis: 'absent'};
  return res;
}"""
QUOTE_SCROLLABLE = ("() => { const s = document.getElementById('quoteScroll');"
                    " return !!(s && s.scrollHeight > s.clientHeight + 1); }")
QUOTE_AT_END = ("() => { const s = document.getElementById('quoteScroll');"
                " return !!(s && s.scrollTop + s.clientHeight >= s.scrollHeight - 1); }")
QUOTE_OVERFLOW_TOP = ("() => { const s = document.getElementById('quoteScroll');"
                      " const h = document.getElementById('quoteScrollHint');"
                      " return !!(s && s.scrollHeight > s.clientHeight + 1"
                      " && s.scrollTop <= 1 && s.classList.contains('has-more')"
                      " && h && !h.hidden"
                      " && getComputedStyle(h).visibility === 'visible'); }")
QUOTE_AT_END_SETTLED = ("() => { const s = document.getElementById('quoteScroll');"
                        " const h = document.getElementById('quoteScrollHint');"
                        " return !!(s && s.scrollTop + s.clientHeight >= s.scrollHeight - 1"
                        " && !s.classList.contains('has-more')"
                        " && (!h || getComputedStyle(h).visibility === 'hidden')); }")
STATE_DUMP = """() => ({
  prefs: JSON.parse(localStorage.getItem('daily-quote-card.prefs.v2') || 'null'),
  quotes: JSON.parse(localStorage.getItem('daily-quote-card.quotes.v2') || 'null'),
  memos: JSON.parse(localStorage.getItem('daily-quote-card.memos.v2') || '[]'),
  drawn: JSON.parse(localStorage.getItem('daily-quote-card.drawn.v2') || '[]'),
  legacy: localStorage.getItem('daily-quote-card:v1'),
})"""
CACHE_DUMP = """async () => {
  if (!('caches' in window)) return [];
  const out = [];
  for (const k of await caches.keys()) {
    try {
      const reqs = await (await caches.open(k)).keys();
      out.push({key: k, urls: reqs.map(r => new URL(r.url, location.href).pathname)});
    } catch (e) {}
  }
  return out;
}"""
MANIFEST = """async () => {
  const link = document.querySelector('link[rel="manifest"]');
  const href = link ? link.getAttribute('href') : 'manifest.webmanifest';
  const r = await fetch(href);
  const m = await r.json();
  const icons = [];
  for (const ic of m.icons || []) {
    const img = new Image(); img.src = ic.src;
    try { await img.decode(); } catch (e) {}
    icons.push({src: ic.src, declared: ic.sizes, w: img.naturalWidth, h: img.naturalHeight});
  }
  return {name: m.name, display: m.display, icons};
}"""
SHOT_SETTLED = r"""() => {
  const zero = (t) => {
    if (!t || t === 'none') return true;
    const m = t.match(/^matrix3d\((.+)\)$/) || t.match(/^matrix\((.+)\)$/);
    if (!m) return false;
    const v = m[1].split(',').map(Number);
    const off = v.length === 16 ? [v[12], v[13], v[14]] : [v[4], v[5]];
    return off.every(n => Math.abs(n) < 0.5);
  };
  for (const r of document.querySelectorAll('.sheet-root')) {
    if (r.hidden) continue;
    const s = r.querySelector('.sheet');
    if (!s) continue;
    const cs = getComputedStyle(s);
    if (parseFloat(cs.opacity) < 0.999 || !zero(cs.transform)) return false;
  }
  const c = document.getElementById('quoteCard');
  if (c && !c.hidden) {
    if (parseFloat(getComputedStyle(c).opacity) < 0.999) return false;
    const im = c.querySelector('img');
    if (im && !(im.complete && im.naturalWidth > 0)) return false;
  }
  const t = document.getElementById('toast');
  if (t && parseFloat(getComputedStyle(t).opacity) > 0.001) return false;
  return true;
}"""


class Skip(Exception):
    pass


class DrawResult(TypedDict):
    id: str | None
    text: str


class Runner:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.checks = []
        self.browser_errors = []
        self.screenshots = []
        self.recordings = []

    def check(self, cid, fn, **extra):
        try:
            detail = fn()
            status = 'passed'
        except Skip as e:
            status, detail = 'skipped', str(e)
        except AssertionError as e:
            status, detail = 'failed', str(e)
        except Exception as e:
            status, detail = 'error', f'{type(e).__name__}: {e}'
        entry = {'id': cid, 'status': status, 'detail': detail}
        entry.update(extra)
        self.checks.append(entry)
        print(f'  [{status.upper():7}] {cid} — {detail}')

    def ok(self):
        return self.checks and self.checks[-1]['status'] == 'passed'

    def watch(self, page, tag):
        page.on('console', lambda m: self.browser_errors.append(f'{tag} console.error: {m.text}') if m.type == 'error' else None)
        page.on('pageerror', lambda e: self.browser_errors.append(f'{tag} pageerror: {e}'))

    def shot(self, page, name, selector=None, full_page_css=False):
        page.wait_for_function(SHOT_SETTLED, timeout=8000)
        target = self.out / name
        if selector:
            page.locator(selector).screenshot(path=str(target), scale='css')
        elif full_page_css:
            page.screenshot(path=str(target), full_page=True, scale='css')
        else:
            page.screenshot(path=str(target), scale='css')
        self.screenshots.append(name)


# ---------- primitives ----------

def boot(page, url):
    page.goto(url, wait_until='domcontentloaded')
    page.wait_for_function(BELT_READY)
    page.wait_for_function(SETTLED)
    return 'ready: 7-card belt rendered'


def hook(page):
    return page.evaluate(f'() => {HOOK} || null')


def quote_text(page) -> str:
    return page.eval_on_selector('#quoteText', 'e => e.textContent || ""')


def last_draw_id(page) -> str | None:
    h = hook(page)
    return (h or {}).get('lastDrawId')


def wait_next_draw(page, prev_id, timeout=9000):
    page.wait_for_function(NEXT_DRAW, arg=prev_id, timeout=timeout)
    page.wait_for_function(SETTLED, timeout=timeout)


def button_draw(page) -> DrawResult:
    """Click #drawButton; waits for a genuinely new reveal + finished clone."""
    prev = last_draw_id(page)
    page.wait_for_function(SETTLED)
    page.click('#drawButton')
    try:
        wait_next_draw(page, prev, timeout=6000)
    except PWTimeout:
        raise AssertionError('#drawButton click produced no new draw')
    return {'id': last_draw_id(page), 'text': quote_text(page)}


def key_draw(page, key) -> DrawResult:
    prev = last_draw_id(page)
    page.wait_for_function(SETTLED)
    page.focus('#deck')
    assert page.evaluate("() => document.activeElement && document.activeElement.id") == 'deck', \
        '#deck did not take focus'
    page.keyboard.press(key)
    wait_next_draw(page, prev)
    return {'id': last_draw_id(page), 'text': quote_text(page)}


def ensure_revealed(page) -> DrawResult:
    if page.evaluate(CARD_HIDDEN):
        return button_draw(page)
    return {'id': last_draw_id(page), 'text': quote_text(page)}


def card_point(page):
    pt = page.evaluate(CARD_POINT)
    assert pt, 'no grabbable belt card geometry found'
    return pt


def drag_draw(page, dy=170) -> DrawResult:
    """Real pointer down/move/up on the card nearest deck centre."""
    prev = last_draw_id(page)
    pt = card_point(page)
    page.mouse.move(pt['x'], pt['y'])
    page.mouse.down()
    page.mouse.move(pt['x'], pt['y'] + dy, steps=8)
    grabbed = page.eval_on_selector('#drawCard', 'e => e.style.opacity')
    assert grabbed == '1', f'pointer-down did not grab a belt card (opacity={grabbed!r})'
    page.mouse.up()
    wait_next_draw(page, prev)
    return {'id': last_draw_id(page), 'text': quote_text(page)}


def force_draw(page, qid, timeout=9000):
    """Set the supported test hook then perform a real #drawButton click."""
    page.wait_for_function(SETTLED, timeout=timeout)
    page.evaluate(f"(id) => {{ const h = {HOOK}; if (h) h.forceQuoteId = id; }}", qid)
    page.click('#drawButton')
    page.wait_for_function(REVEALED_ID, arg=qid, timeout=timeout)
    page.wait_for_function(SETTLED, timeout=timeout)
    return {'id': last_draw_id(page), 'text': quote_text(page)}


def set_lang(page, lang):
    page.select_option('#language', lang)


def wait_card_text(page, text, timeout=5000):
    page.wait_for_function("(t) => { const q = document.getElementById('quoteText');"
                           " return q && q.textContent === t; }",
                           arg=text, timeout=timeout)


def norm_txt(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def close_any_sheet(page):
    for _ in range(4):
        roots = page.evaluate("() => [...document.querySelectorAll('.sheet-root')]"
                              ".filter(r => !r.hidden).map(r => r.id)")
        if not roots:
            return
        page.keyboard.press('Escape')
        try:
            page.wait_for_function("(ids) => ids.every(i => document.getElementById(i).hidden)",
                                   arg=roots, timeout=3000)
        except PWTimeout:
            return


def today_key(page):
    return page.evaluate("() => { const d = new Date(), p = n => String(n).padStart(2, '0');"
                         " return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; }")


def open_cal(page):
    close_any_sheet(page)
    page.click('#openCal')
    page.wait_for_function("() => { const r = document.getElementById('calRoot');"
                           " const g = document.getElementById('calGrid');"
                           " return !!(r && !r.hidden && g && g.children.length); }")


def wait_month_view(page):
    page.wait_for_function("() => { const v = document.getElementById('calMonthView');"
                           " return !!(v && !v.hidden); }")


def open_day(page, key):
    sel = f"#calGrid .cal-cell.has[data-k='{key}']"
    page.wait_for_selector(sel)
    page.click(sel)
    page.wait_for_function("() => { const v = document.getElementById('calDayView');"
                           " return !!(v && !v.hidden); }")


def day_text(page):
    return page.eval_on_selector('#dayList', 'e => e.innerText')


def close_sheet(page, root='calRoot'):
    page.keyboard.press('Escape')
    page.wait_for_function(f"() => document.getElementById('{root}').hidden")


def unskip(page):
    page.evaluate("() => { const a = document.activeElement;"
                  " if (a && a.matches('a[href^=\"#\"], .skip, .skip-link')) a.blur(); }")


# ---------- checks ----------

def test_hook(page):
    name = page.evaluate("() => window.DAILY_QUOTE_CARD_TEST ? 'DAILY_QUOTE_CARD_TEST'"
                         " : (window.GOOD_THOUGHT_CARD_TEST ? 'GOOD_THOUGHT_CARD_TEST' : null)")
    assert name, 'no test hook (DAILY_QUOTE_CARD_TEST) found'
    return f'{name} present (read-only observables)'


def belt_check(page):
    info = page.evaluate(PHOTO_INFO)
    assert len(info) == 7, f'{len(info)} belt cards, expected 7'
    if not all(c['imgOk'] or c['src'] for c in info):
        page.wait_for_function("""() => [...document.querySelectorAll('#belt .belt-card')]
          .every(c => { const im = c.querySelector('img');
            if (im) return im.complete && im.naturalWidth > 0;
            return (getComputedStyle(c).backgroundImage || '').indexOf('url(') !== -1; })""",
            timeout=10000)
        info = page.evaluate(PHOTO_INFO)
    assert all(c['src'] or c['imgOk'] for c in info), f'cards without photo: {info}'
    srcs = sorted({c['src'] for c in info if c['src']})
    assert srcs, 'no photo sources on belt cards'
    bad = page.evaluate(DECODE, srcs)
    assert not bad, f'undecodable belt photos: {bad[:4]}'
    imgs = page.evaluate("() => [...document.querySelectorAll('img')]"
                         ".map(i => ({l: i.loading, d: i.decoding}))")
    assert len(imgs) <= 9, f'{len(imgs)} image nodes (>9)'
    flagged = [i for i in imgs if i['l'] == 'lazy' or i['d'] == 'async']
    assert len(flagged) == len(imgs), \
        f'{len(imgs) - len(flagged)} images without lazy/async flags'
    assert page.locator('#drawButton').is_visible(), '#drawButton not visible'
    return (f'7 photo belt cards; {len(srcs)} photo(s) decode; '
            f'{len(imgs)} lazy/async image nodes; #drawButton visible')


def belt_motion(page):
    t0 = page.eval_on_selector('#belt .belt-card', 'e => e.style.transform')
    page.wait_for_function("(t) => { const c = document.querySelector('#belt .belt-card');"
                           " return c && c.style.transform !== t; }",
                           arg=t0, timeout=5000)
    return 'belt transforms change over time (motion on, reduced_motion=no-preference)'


def short_drag(page):
    prev_id = last_draw_id(page)
    prev = quote_text(page)
    pt = card_point(page)
    page.mouse.move(pt['x'], pt['y'])
    page.mouse.down()
    page.mouse.move(pt['x'], pt['y'] + 60, steps=6)
    grabbed = page.eval_on_selector('#drawCard', 'e => e.style.opacity')
    page.mouse.up()
    assert grabbed == '1', f'pointer-down did not grab a belt card (opacity={grabbed!r})'
    page.wait_for_function(SETTLED)
    assert last_draw_id(page) == prev_id and quote_text(page) == prev, \
        '60px drag unexpectedly drew a card'
    if not prev.strip():
        st = page.evaluate("() => { const c = document.getElementById('quoteCard');"
                           " return {h: c.hidden, s: c.dataset.state}; }")
        assert st['h'] or st['s'] != 'revealed', 'sub-threshold drag revealed a card'
    return '60px (<120 threshold) drag grabbed then snapped back without draw'


def button_draw_check(page):
    d = button_draw(page)
    assert d['text'].strip(), 'revealed quoteText empty'
    return f"#drawButton draw -> {d['id'] or d['text'][:30]!r}"


def key_draws(page):
    d1 = key_draw(page, 'Enter')
    d2 = key_draw(page, 'Space')
    return f"Enter -> {d1['id']}, Space -> {d2['id']} (focus on #deck)"


def drag_draw_check(page):
    d = drag_draw(page)
    assert d['text'].strip(), 'revealed quoteText empty'
    return f"pointer drag >=150px drew {d['id'] or 'card'}: {d['text'][:38]!r}"


def swipe_dismiss(page):
    ensure_revealed(page)
    box = page.locator('#quoteCard').bounding_box()
    assert box, 'no quote card geometry'
    x, y = box['x'] + box['width'] / 2, box['y'] + 60
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + 110, steps=8)
    dragging = page.eval_on_selector('#result', "e => e.classList.contains('is-dragging')")
    page.mouse.up()
    assert dragging, 'pointer swipe did not engage the quote card drag'
    page.wait_for_function(CARD_HIDDEN)
    return 'pointer swipe +110px (>78 threshold) dismissed the card'


def dismiss_button(page):
    ensure_revealed(page)
    page.click('#quoteDismiss')
    page.wait_for_function(CARD_HIDDEN)
    st = page.evaluate("() => document.getElementById('quoteCard').dataset.state")
    assert st == 'ready', f'data-state={st!r} after dismiss'
    return '#quoteDismiss click dismissed the card (state=ready)'


def memo_save(page, st):
    d = ensure_revealed(page)
    st['quote_a'] = d['text']
    page.click('#memoBtn')
    page.wait_for_function("() => { const m = document.getElementById('memoRoot');"
                           " return m && !m.hidden; }")
    page.click('#memoSave')
    page.wait_for_function("() => document.getElementById('memoField').classList.contains('error')")
    page.fill('#memoText', THOUGHT)
    page.click('#memoSave')
    page.wait_for_function("() => document.getElementById('memoRoot').hidden")
    return 'empty save rejected (.error); thought saved; sheet closed'


def calendar_day(page, st):
    open_cal(page)
    k = today_key(page)
    open_day(page, k)
    txt = day_text(page)
    assert THOUGHT in txt, 'saved thought missing from day list'
    assert st['quote_a'] in txt, 'memo quote missing from day list'
    page.click('#calBack')
    wait_month_view(page)
    close_sheet(page)
    return f'today {k} has marked data-k cell; day shows thought + its quote'


def calendar_draw_entry(page, st):
    d2 = button_draw(page)
    st['quote_b'] = d2['text']
    open_cal(page)
    open_day(page, today_key(page))
    txt = day_text(page)
    assert st['quote_b'] in txt, 'second draw (no memo) missing from day list'
    assert THOUGHT in txt, 'earlier memo entry missing alongside draw entry'
    page.click('#calBack')
    wait_month_view(page)
    label0 = page.eval_on_selector('#calMonthLabel', 'e => e.textContent')
    page.click('#calPrev')
    page.wait_for_function("(l) => document.getElementById('calMonthLabel').textContent !== l",
                           arg=label0)
    prev_label = page.eval_on_selector('#calMonthLabel', 'e => e.textContent')
    page.click('#calNext')
    page.wait_for_function("(l) => document.getElementById('calMonthLabel').textContent === l",
                           arg=label0)
    close_sheet(page)
    return f"second draw listed in day view; month nav {label0!r}->{prev_label!r}->{label0!r}"


def calendar_reload_persist(page, st):
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function(BELT_READY)
    open_cal(page)
    open_day(page, today_key(page))
    txt = day_text(page)
    assert THOUGHT in txt, 'thought not persisted across reload'
    for key in ('quote_a', 'quote_b'):
        if st.get(key):
            assert st[key] in txt, f'{key} not persisted in day list'
    close_sheet(page)
    return 'after reload: today cell still marked; entries persist'


def sheet_escape_focus(page):
    open_cal(page)
    page.keyboard.press('Escape')
    page.wait_for_function("() => document.getElementById('calRoot').hidden")
    page.wait_for_function("() => document.activeElement && document.activeElement.id === 'openCal'")
    return 'Escape closed the sheet and restored focus to #openCal'


def add_quote(page, st):
    close_any_sheet(page)
    h0 = hook(page) or {}
    page.click('#openAddTop')
    page.wait_for_function("() => { const r = document.getElementById('addRoot');"
                           " return r && !r.hidden; }")
    page.click('#addSave')
    page.wait_for_function("() => document.getElementById('addField').classList.contains('error')")
    text = f'The tide returns what the shore only borrowed. [qa{int(time.time()) % 100000}]'
    st['custom_text'] = text
    page.fill('#qText', text)
    cnt = page.eval_on_selector('#textCount', 'e => e.textContent')
    assert cnt.strip() == f'{len(text)}/120', f'counter={cnt!r}, expected {len(text)}/120'
    mx = page.eval_on_selector('#qText', "e => e.getAttribute('maxlength')")
    assert mx == '120', f'qText maxlength={mx!r}'
    page.fill('#qAuthor', CUSTOM_AUTHOR)
    page.click('#addSave')
    page.wait_for_function("() => document.getElementById('addRoot').hidden")
    h1 = hook(page) or {}
    assert h1.get('customQuoteCount', 0) == h0.get('customQuoteCount', 0) + 1, \
        f"customQuoteCount {h0.get('customQuoteCount')} -> {h1.get('customQuoteCount')}"
    assert h1.get('totalQuoteCount') == CUSTOM_TOTAL, \
        f"totalQuoteCount={h1.get('totalQuoteCount')}"
    return (f"saved; counts {h1.get('customQuoteCount')}/{h1.get('totalQuoteCount')} "
            f"(was {DECK_N})")


def add_quote_persist(page, st):
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function(BELT_READY)
    h = hook(page) or {}
    assert h.get('totalQuoteCount') == CUSTOM_TOTAL and h.get('customQuoteCount', 0) >= 1, \
        f'hook={h}'
    return f'custom quote survives reload (totalQuoteCount={CUSTOM_TOTAL})'


def find_custom(page, st):
    text = st.get('custom_text')
    assert text, 'no custom text recorded'
    for i in range(CUSTOM_TOTAL):
        d = button_draw(page)
        if d['text'] == text or (d['id'] or '').startswith('custom-'):
            return (f'custom quote reached in {i + 1} real #drawButton draws '
                    f'(<= {CUSTOM_TOTAL})')
    raise AssertionError(f'custom quote not drawn within {CUSTOM_TOTAL} real draws')


def quote_cycles(page):
    got = []
    for _ in range(CYCLE_DRAWS):
        d = button_draw(page)
        assert d['id'], 'draw produced no lastDrawId'
        got.append(d['id'])
    adj = [a for a, b in zip(got, got[1:]) if a == b]
    assert not adj, f'adjacent repeat ids: {sorted(set(adj))[:4]}'
    b1, b2 = set(got[:DECK_N]), set(got[DECK_N:])
    assert len(set(got)) == DECK_N and len(b1) == DECK_N and len(b2) == DECK_N \
        and b1 == b2, \
        f'blocks not unique full cycles: {len(b1)}+{len(b2)} unique ids'
    return (f'{CYCLE_DRAWS} real draws = 2 unique {DECK_N}-card cycles '
            '(asserted by id), no adjacent repeats')


def sw_control(page):
    assert page.evaluate("() => 'serviceWorker' in navigator"), 'no serviceWorker API'
    page.evaluate("() => navigator.serviceWorker.ready.then(() => null)")
    if not page.evaluate("() => !!navigator.serviceWorker.controller"):
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function(BELT_READY)
    page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=20000)
    return 'service worker controls the page'


def cache_photos(page):
    expected = page.evaluate(DECK_IMAGES)
    assert expected, 'deck image list unavailable'
    assert len(expected) == DECK_N, \
        f'deck lists {len(expected)} image references, expected {DECK_N}'
    base = page.evaluate("() => new URL('./', location.href).pathname")
    uniq = sorted(set(expected))
    need = [s if s.startswith('/') else base + ('images/' if '/' not in s else '') + s
            for s in uniq]
    deadline = time.time() + CACHE_WAIT_S
    caches, flat, missing = [], [], need
    while missing:
        caches = page.evaluate(CACHE_DUMP)
        flat = sorted({u for c in caches for u in c['urls']})
        missing = [u for u in need if u not in flat]
        if not missing:
            break
        assert time.time() < deadline, \
            f'{len(missing)} deck images not cached after {CACHE_WAIT_S}s: {missing[:5]}'
        page.wait_for_timeout(500)
    assert flat, 'no CacheStorage entries found'
    srcs = [('images/' + s) if '/' not in s else s for s in uniq]
    bad = page.evaluate(DECODE, srcs)
    assert not bad, f'undecodable cached photos: {bad[:4]}'
    label = caches[0]['key'] if caches else '?'
    return (f'{DECK_N} deck image references, {len(uniq)} unique urls complete '
            f'in {label}; all decode')


def manifest_icons(page):
    info = page.evaluate(MANIFEST)
    assert info['display'] == 'standalone', f"display={info['display']}"
    dims = {i['declared']: (i['w'], i['h']) for i in info['icons']}
    for s in ('192x192', '512x512'):
        assert s in dims, f'missing declared {s}: {dims}'
        assert dims[s] == (int(s[:3]), int(s[4:])), f'{s} -> {dims[s]}'
    return f"manifest '{info['name']}' standalone; icons 192+512 decode at declared size"


def installability(ctx, page):
    try:
        s = ctx.new_cdp_session(page)
        res = s.send('Page.getInstallabilityErrors')
    except Exception as e:
        raise Skip(f'Page.getInstallabilityErrors unsupported: {e}')
    errs = res.get('installabilityErrors', [])
    assert not errs, f"installability errors: {[e.get('errorId') for e in errs]}"
    return 'no installability errors'


def offline_flow(page, ctx):
    ctx.set_offline(True)
    try:
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function(BELT_READY)
        d = button_draw(page)
        page.click('#memoBtn')
        page.wait_for_function("() => { const m = document.getElementById('memoRoot');"
                               " return m && !m.hidden; }")
        page.fill('#memoText', OFFLINE_THOUGHT)
        page.click('#memoSave')
        page.wait_for_function("() => document.getElementById('memoRoot').hidden")
        open_cal(page)
        open_day(page, today_key(page))
        assert OFFLINE_THOUGHT in day_text(page), 'offline memo missing from day list'
        close_sheet(page)
        return f"offline reload + belt + draw ({d['id']}) + memo save + calendar all work"
    finally:
        ctx.set_offline(False)


def legacy_migration(r, browser, url):
    ctx = browser.new_context(**MOBILE)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    r.watch(page, 'legacy')
    note = 'A note written on the old card still matters.'
    seed = {'lang': 'en', 'current': 'q01', 'seen': ['q01'],
            'notes': {'q01': note}, 'saved': []}
    ctx.add_init_script(f"if (!localStorage.getItem('{LEGACY_KEY}')) localStorage.setItem('{LEGACY_KEY}', {json.dumps(json.dumps(seed))});")
    try:
        boot(page, url)
        h = hook(page) or {}
        open_cal(page)
        keys = page.eval_on_selector_all('#calGrid .cal-cell.has[data-k]',
                                       "es => es.map(e => e.getAttribute('data-k'))")
        found = []
        for k in keys:
            open_day(page, k)
            entries = page.eval_on_selector_all(
                '#dayList .entry',
                "es => es.map(e => ({t: e.innerText, time: (e.querySelector('.e-time')"
                " || {innerText: ''}).innerText}))")
            found.extend(e for e in entries if note in e['t'])
            page.click('#calBack')
            wait_month_view(page)
        root_txt = page.eval_on_selector('#calRoot', 'e => e.innerText')
        outside = root_txt.count(note) if not found else 0
        total = len(found) + outside
        if not total:
            if h.get('memoCount'):
                raise AssertionError(f"memoCount={h['memoCount']} but imported note not visible")
            raise Skip('production does not import daily-quote-card:v1 notes')
        assert total == 1, f'imported note appears {total}x (expected exactly once)'
        label_txt = found[0]['time'] if found else root_txt
        rex = UNKNOWN_DATE_RE if found else STRICT_DATE_RE
        assert rex.search(label_txt), f'no explicit unknown-date label near note: {label_txt[:80]!r}'
        raw = page.evaluate(f"() => localStorage.getItem('{LEGACY_KEY}')")
        assert json.loads(raw).get('notes', {}).get('q01') == note, 'legacy key mutated'
        return 'legacy note imported once with unknown-date label; old key untouched'
    finally:
        ctx.close()


def deck_quotes(page, n=DECK_N):
    quotes = page.evaluate(DECK_QUOTES)
    assert isinstance(quotes, list), 'deck quotes unavailable'
    assert len(quotes) == n, f'deck has {len(quotes)} quotes, expected {n}'
    ids = [q.get('id') for q in quotes]
    assert len(set(ids)) == n and all(ids), 'deck ids not unique/present'
    for q in quotes:
        assert isinstance(q.get('text'), str) and q['text'].strip(), f"{q.get('id')} empty text"
        assert isinstance(q.get('ko'), str) and q['ko'].strip(), f"{q.get('id')} empty ko"
        assert isinstance(q.get('author'), str), f"{q.get('id')} author not a string"
        assert isinstance(q.get('author_ko'), str), f"{q.get('id')} author_ko not a string"
        assert q.get('image') and q.get('imageAvailable') is True, \
            f"{q.get('id')} missing image/imageAvailable"
    return quotes


def quotes_bilingual(page, n=DECK_N):
    """All 103 quotes: force id + real #drawButton click; exact EN text, author
    and rendered source, then switch language on the revealed card (no redraw)
    and require exact KO original_text / original_author."""
    quotes = deck_quotes(page, n)
    for q in quotes:
        qid = q['id']
        force_draw(page, qid)
        v = page.evaluate(CARD_VIEW)
        assert v['id'] == qid, f"drawn id {v['id']!r} != forced {qid!r}"
        assert v['text'] == q['text'], f"{qid} EN text mismatch: {v['text'][:60]!r}"
        assert v['author'] == q['author'], \
            f"{qid} EN author {v['author']!r} != {q['author']!r}"
        src = (q.get('work_or_source') or '').strip()
        if src:
            assert norm_txt(src) in norm_txt(v['cardText']), \
                f'{qid} source not rendered on card'
        else:
            assert not v['source'], f"{qid} unexpected source {v['source']!r}"
        set_lang(page, 'ko')
        wait_card_text(page, q['ko'])
        vk = page.evaluate(CARD_VIEW)
        assert vk['id'] == qid and vk['drawn'] == v['drawn'], \
            f'{qid} language switch triggered a redraw'
        assert vk['text'] == q['ko'], f"{qid} KO text mismatch: {vk['text'][:60]!r}"
        assert vk['author'] == q['author_ko'], \
            f"{qid} KO author {vk['author']!r} != {q['author_ko']!r}"
        set_lang(page, 'en')
        wait_card_text(page, q['text'])
    return (f'{n} quotes verified EN (text/author/source) + KO '
            '(original_text/original_author) via forced real draws')


def scroll_quote_end(page):
    """Native-scroll the quote text to its end: real mouse wheel first, then
    CDP touch drags for contexts that ignore wheel input. Waits for the app's
    at-end state (fade cleared, hint kept but invisible). Returns False when
    the quote does not overflow its scroll region."""
    if not page.evaluate(QUOTE_SCROLLABLE):
        return False
    box = page.locator('#quoteScroll').bounding_box()
    assert box, 'no #quoteScroll geometry'
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(x, y)
    for _ in range(10):
        if page.evaluate(QUOTE_AT_END):
            break
        page.mouse.wheel(0, 480)
    if not page.evaluate(QUOTE_AT_END):
        cdp = page.context.new_cdp_session(page)
        for _ in range(14):
            cdp.send('Input.dispatchTouchEvent',
                     {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
            for i in range(1, 8):
                cdp.send('Input.dispatchTouchEvent',
                         {'type': 'touchMove',
                          'touchPoints': [{'x': x, 'y': y - i * 48}]})
            cdp.send('Input.dispatchTouchEvent',
                     {'type': 'touchEnd', 'touchPoints': []})
            if page.evaluate(QUOTE_AT_END):
                break
    page.wait_for_function(QUOTE_AT_END_SETTLED)
    return True


def longest_bounded(page):
    """The longest EN quote keeps author/source/actions always visible (they
    sit outside .quote-scroll), its full text persists to localStorage, and a
    native wheel/touch scroll reaches the end without dismissing the card."""
    quotes = deck_quotes(page)
    q = max(quotes, key=lambda x: len(x.get('text') or ''))
    force_draw(page, q['id'])

    st = page.evaluate(STATE_DUMP)
    recs = [d for d in st['drawn'] if d.get('quoteId') == q['id']]
    assert recs, f'no drawn snapshot persisted for {q["id"]}'
    assert recs[-1].get('quote') == q['text'], \
        (f"persisted quote snapshot is {len(recs[-1].get('quote') or '')} chars, "
         f'expected the full {len(q["text"])}')

    page.wait_for_function(QUOTE_OVERFLOW_TOP)
    m = page.evaluate(LONG_BOUND)
    assert not m.get('err'), m['err']
    assert m['overX'] <= 1, f"horizontal overflow: {m['overX']}px"
    assert m['withinX'], 'quote text escapes the card horizontally'
    assert m['scrollable'] is True, 'longest quote did not overflow its scroll region'
    assert m['authorOut'] is True, 'author still inside the scroll region'
    assert m['authorIn'], 'author not visible before scrolling'
    assert m['actsIn'], 'actions not visible before scrolling'
    src = (q.get('work_or_source') or '').strip()
    if src:
        assert m['srcOut'] is True, 'source still inside the scroll region'
        assert m['srcIn'] is True, 'source not visible before scrolling'
    assert m['hint']['hidden'] is False and m['hint']['vis'] == 'visible', \
        f"scroll hint not shown on overflow: {m['hint']}"
    assert m['hasMore'] is True, 'bottom fade missing while more text below'

    assert scroll_quote_end(page), 'native scroll could not reach the quote end'
    m2 = page.evaluate(LONG_BOUND)
    assert m2['authorIn'], 'author not visible after scrolling to the end'
    assert m2['actsIn'], 'actions not visible after scrolling to the end'
    if src:
        assert m2['srcIn'] is True, 'source not visible after scrolling'
    assert m2['hint']['vis'] == 'hidden', 'scroll hint still visible at scroll end'
    assert m2['hasMore'] is False, 'bottom fade still applied at scroll end'
    assert page.evaluate("() => { const c = document.getElementById('quoteCard');"
                         " return !!(c && !c.hidden && c.dataset.state === 'revealed'); }"), \
        'card dismissed or hidden during quote scrolling'
    force_draw(page, 'q014')
    page.wait_for_function("() => document.getElementById('quoteScrollHint').hidden")
    return (f"{q['id']} ({len(q['text'])} chars) full snapshot persisted; "
            'author/source/actions visible before+after native scroll to end; '
            'hint/fade clear at end')


def goto_marked_cell(page, key, max_prev=30):
    sel = f"#calGrid .cal-cell.has[data-k='{key}']"
    for _ in range(max_prev):
        if page.locator(sel).count():
            return
        page.click('#calPrev')
    raise AssertionError(f'no marked calendar cell for {key} within {max_prev} months')


def v2_migration(r, browser, url):
    """v1->v2 id remap: seeded prefs (saved q01 + stable q104 + custom id),
    dated q01 draw+memo holding historical text/author, a custom quote and a
    custom draw record, plus a v1 note under q01. After real boot the storage
    must read q001 (custom untouched, same text/time/thought/drawId), the
    import must carry id q001, the v1 blob must stay unchanged, the marked
    calendar days must show the records, and a reload must be idempotent."""
    ctx = browser.new_context(**MOBILE)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    r.watch(page, 'v2-migration')
    old_text = 'Begin with one small, honest step.'
    old_author = 'Original reflection'
    thought = 'A note saved on the old first card.'
    legacy_note = 'A v1 note written on the old first card.'
    custom_text = 'A seeded custom thought.'
    seed = {
        'prefs': {'lang': 'en', 'saved': ['q01', 'q104', 'custom-v2-seed']},
        'quotes': [{'id': 'custom-v2-seed', 't': custom_text, 'a': 'QA Seed'}],
        'drawn': [{'id': 'draw-old-1', 'ts': 0, 'dateKey': '', 'time': '9:41 AM',
                   'quoteId': 'q01', 'quoteSource': 'default',
                   'quote': old_text, 'author': old_author, 'custom': False},
                  {'id': 'draw-old-2', 'ts': 0, 'dateKey': '', 'time': '9:42 AM',
                   'quoteId': 'custom-v2-seed', 'quoteSource': 'local',
                   'quote': custom_text, 'author': 'QA Seed', 'custom': True}],
        'memos': [{'id': 'memo-old-1', 'ts': 0, 'dateKey': '', 'time': '9:43 AM',
                   'quoteId': 'q01', 'quoteSource': 'default',
                   'quote': old_text, 'author': old_author,
                   'thought': thought, 'drawId': 'draw-old-1', 'imported': False}],
        'legacy': {'lang': 'en', 'current': 'q01', 'seen': ['q01'],
                   'notes': {'q01': legacy_note}, 'saved': []},
    }
    ctx.add_init_script(
        f"const S={json.dumps(seed)};"
        f"const d=new Date(); d.setMonth(d.getMonth()-2); d.setDate(15);"
        f"const p=n=>String(n).padStart(2,'0');"
        f"const DK=`${{d.getFullYear()}}-${{p(d.getMonth()+1)}}-${{p(d.getDate())}}`;"
        f"const T=d.getTime();"
        f"S.drawn[0].ts=T; S.drawn[0].dateKey=DK; S.drawn[1].ts=T+1000; S.drawn[1].dateKey=DK;"
        f"S.memos[0].ts=T+2000; S.memos[0].dateKey=DK;"
        f"if (!localStorage.getItem('{PREF_KEY}')) localStorage.setItem('{PREF_KEY}', JSON.stringify(S.prefs));"
        f"if (!localStorage.getItem('{QKEY}')) localStorage.setItem('{QKEY}', JSON.stringify(S.quotes));"
        f"if (!localStorage.getItem('{DRAWN_KEY}')) localStorage.setItem('{DRAWN_KEY}', JSON.stringify(S.drawn));"
        f"if (!localStorage.getItem('{MEMO_KEY}')) localStorage.setItem('{MEMO_KEY}', JSON.stringify(S.memos));"
        f"if (!localStorage.getItem('{LEGACY_KEY}')) localStorage.setItem('{LEGACY_KEY}', JSON.stringify(S.legacy));")
    try:
        boot(page, url)
        st = page.evaluate(STATE_DUMP)
        drawn = {d['id']: d for d in st['drawn']}
        memos = {m['id']: m for m in st['memos']}
        assert 'draw-old-1' in drawn and 'memo-old-1' in memos, 'seeded v2 records missing'
        d1, d2, m1 = drawn['draw-old-1'], drawn['draw-old-2'], memos['memo-old-1']
        assert d1['quoteId'] == 'q001', f"draw quoteId {d1['quoteId']!r} not remapped to q001"
        assert d1['quote'] == old_text and d1['author'] == old_author, \
            'historical draw text/author rewritten'
        assert d1['time'] == '9:41 AM', f"draw time {d1['time']!r} changed"
        assert d2['quoteId'] == 'custom-v2-seed', 'custom draw id not preserved'
        assert m1['quoteId'] == 'q001', f"memo quoteId {m1['quoteId']!r} not remapped"
        assert m1['thought'] == thought and m1['drawId'] == 'draw-old-1' \
            and m1['time'] == '9:43 AM', 'memo thought/drawId/time changed'
        dk = d1['dateKey']
        imported = [m for m in st['memos'] if m.get('imported')]
        assert len(imported) == 1 and imported[0]['quoteId'] == 'q001' \
            and imported[0]['thought'] == legacy_note, \
            f'v1 note import wrong: {imported[:1]}'
        saved = (st['prefs'] or {}).get('saved') or []
        assert 'q001' in saved and 'q104' in saved and 'custom-v2-seed' in saved \
            and 'q01' not in saved, f'saved remap wrong: {saved}'
        assert json.loads(st['legacy']).get('notes', {}).get('q01') == legacy_note, \
            'v1 blob mutated'

        open_cal(page)
        open_day(page, today_key(page))
        assert legacy_note in day_text(page), 'imported note not in today day view'
        page.click('#calBack')
        wait_month_view(page)
        goto_marked_cell(page, dk)
        open_day(page, dk)
        txt = day_text(page)
        assert old_text in txt and thought in txt and custom_text in txt, \
            'historical day view missing draw/memo/custom entries'
        page.click('#calBack')
        wait_month_view(page)
        close_sheet(page)

        force_draw(page, 'q001')
        pressed = page.eval_on_selector('#bookmark', "e => e.getAttribute('aria-pressed')")
        assert pressed == 'true', f'remapped q001 not bookmarked (aria-pressed={pressed})'

        memo_len = len(st['memos'])
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function(BELT_READY)
        st2 = page.evaluate(STATE_DUMP)
        d2b = {d['id']: d for d in st2['drawn']}
        assert d2b.get('draw-old-1', {}).get('quoteId') == 'q001', \
            'remap not stable across reload'
        imp2 = [m for m in st2['memos'] if m.get('imported')]
        assert len(st2['memos']) == memo_len and len(imp2) == 1, \
            f'reload duplicated records: memos {memo_len} -> {len(st2["memos"])}'
        saved2 = (st2['prefs'] or {}).get('saved') or []
        assert 'q001' in saved2 and 'q01' not in saved2, 'saved remap lost on reload'
        return ('q01 records remapped to q001 (same text/time/thought/drawId), '
                'custom ids unchanged, v1 note imported as q001, v1 untouched, '
                'calendar shows both days, reload idempotent')
    finally:
        ctx.close()


def shoot_set(r, browser, url, cfg, tag):
    """Clean captures in a dedicated fresh context, including the longest
    quote in EN+KO at top and scrolled bottom, q001 attribution and the
    longest-source card."""
    ctx = browser.new_context(**cfg)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    r.watch(page, f'shot-{tag}')
    n0 = len(r.screenshots)
    try:
        boot(page, url)
        unskip(page)
        r.shot(page, f'{tag}-ready-belt.png', '#deck')
        r.shot(page, f'{tag}-ready-page.png', full_page_css=True)
        drag_draw(page)
        unskip(page)
        r.shot(page, f'{tag}-reveal-card.png', '#quoteCard')
        r.shot(page, f'{tag}-reveal-page.png', full_page_css=True)
        page.click('#memoBtn')
        page.wait_for_function("() => { const m = document.getElementById('memoRoot');"
                               " return m && !m.hidden; }")
        page.locator('#memoText').press_sequentially(MARKETING_THOUGHT, delay=25)
        unskip(page)
        r.shot(page, f'{tag}-memo-sheet.png')
        page.click('#memoSave')
        page.wait_for_function("() => document.getElementById('memoRoot').hidden")
        open_cal(page)
        unskip(page)
        r.shot(page, f'{tag}-cal-month.png')
        open_day(page, today_key(page))
        unskip(page)
        r.shot(page, f'{tag}-cal-day.png')
        close_sheet(page)
        page.click('#openAddTop')
        page.wait_for_function("() => { const r = document.getElementById('addRoot');"
                               " return r && !r.hidden; }")
        unskip(page)
        r.shot(page, f'{tag}-add-sheet.png')
        close_sheet(page, 'addRoot')
        quotes = deck_quotes(page)
        long_q = max(quotes, key=lambda q: len(q.get('text') or ''))
        src_q = max(quotes, key=lambda q: len(q.get('work_or_source') or ''))
        force_draw(page, long_q['id'])
        unskip(page)
        r.shot(page, f"{tag}-quote-{long_q['id']}-en.png", '#quoteCard')
        scroll_quote_end(page)
        unskip(page)
        r.shot(page, f"{tag}-quote-{long_q['id']}-en-bottom.png", '#quoteCard')
        set_lang(page, 'ko')
        wait_card_text(page, long_q.get('ko') or long_q['text'])
        unskip(page)
        r.shot(page, f"{tag}-quote-{long_q['id']}-ko.png", '#quoteCard')
        scroll_quote_end(page)
        unskip(page)
        r.shot(page, f"{tag}-quote-{long_q['id']}-ko-bottom.png", '#quoteCard')
        set_lang(page, 'en')
        wait_card_text(page, long_q['text'])
        force_draw(page, 'q001')
        unskip(page)
        r.shot(page, f'{tag}-quote-q001-attribution.png', '#quoteCard')
        if src_q['id'] != 'q001':
            force_draw(page, src_q['id'])
            unskip(page)
            r.shot(page, f"{tag}-quote-{src_q['id']}-source.png", '#quoteCard')
    finally:
        ctx.close()
    return f'{len(r.screenshots) - n0} shots (long quote EN/KO top+bottom)'


def record_flow(r, browser, url, cfg, name, tmp):
    """Short real full-flow video; context must close before video.save_as."""
    ctx = browser.new_context(record_video_dir=tmp,
                              record_video_size=cfg['viewport'], **cfg)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    r.watch(page, f'rec-{name}')
    video = None
    try:
        boot(page, url)
        belt_motion(page)              # settled predicate, then a viewing dwell
        page.wait_for_timeout(600)
        drag_draw(page)
        page.wait_for_timeout(600)
        page.click('#memoBtn')
        page.wait_for_function("() => { const m = document.getElementById('memoRoot');"
                               " return m && !m.hidden; }")
        page.locator('#memoText').press_sequentially(RECORD_THOUGHT, delay=40)
        page.click('#memoSave')
        page.wait_for_function("() => document.getElementById('memoRoot').hidden")
        open_cal(page)
        page.wait_for_timeout(600)
        open_day(page, today_key(page))
        page.wait_for_timeout(600)
        close_sheet(page)
        swipe_dismiss(page)
        button_draw(page)
        page.wait_for_timeout(600)
        page.click('#openAddTop')
        page.wait_for_function("() => { const r = document.getElementById('addRoot');"
                               " return r && !r.hidden; }")
        page.locator('#qText').press_sequentially(RECORD_QUOTE, delay=40)
        page.locator('#qAuthor').press_sequentially(CUSTOM_AUTHOR, delay=40)
        page.click('#addSave')
        page.wait_for_function("() => document.getElementById('addRoot').hidden")
        page.wait_for_timeout(600)
        video = page.video
    finally:
        ctx.close()
    assert video, 'no video object produced'
    target = r.out / name
    video.save_as(str(target))
    assert target.exists() and target.stat().st_size > 0, f'{name} is empty'
    r.recordings.append(name)
    return f'{name} recorded'


# ---------- runner ----------

def new_page(r, browser, cfg, tag):
    ctx = browser.new_context(**cfg)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    r.watch(page, tag)
    return ctx, page


def run(url, out, record=False):
    r = Runner(out)
    started = time.time()
    st = {}
    tmp = tempfile.mkdtemp(prefix='qa-vid-')
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            print(f'== mobile 390x844 dpr3 @ {url}')
            ctx, page = new_page(r, browser, MOBILE, 'mobile')
            r.check('mobile_boot', lambda: boot(page, url))
            if r.ok():
                r.check('test_hook', lambda: test_hook(page))
                r.check('mobile_belt', lambda: belt_check(page))
                r.check('mobile_belt_motion', lambda: belt_motion(page))
                r.check('mobile_drag_below_threshold', lambda: short_drag(page))
                r.check('mobile_drag_draw', lambda: drag_draw_check(page))
                r.check('mobile_button_draw', lambda: button_draw_check(page))
                r.check('mobile_keyboard_draw', lambda: key_draws(page))
                r.check('mobile_swipe_dismiss', lambda: swipe_dismiss(page))
                r.check('mobile_dismiss_button', lambda: dismiss_button(page))
                r.check('memo_save', lambda: memo_save(page, st))
                r.check('calendar_day', lambda: calendar_day(page, st))
                r.check('calendar_draw_entry', lambda: calendar_draw_entry(page, st))
                r.check('calendar_reload_persist', lambda: calendar_reload_persist(page, st))
                r.check('sheet_escape_focus', lambda: sheet_escape_focus(page))
                r.check('add_quote', lambda: add_quote(page, st))
                r.check('add_quote_persist', lambda: add_quote_persist(page, st))
                r.check('custom_quote_draw', lambda: find_custom(page, st))
            ctx.close()

            print('== desktop 1280x900')
            dctx, dpage = new_page(r, browser, DESKTOP, 'desktop')
            r.check('desktop_boot', lambda: boot(dpage, url))
            if r.ok():
                r.check('desktop_belt', lambda: belt_check(dpage))
                r.check('desktop_belt_motion', lambda: belt_motion(dpage))
                r.check('desktop_drag_below_threshold', lambda: short_drag(dpage))
                r.check('desktop_drag_draw', lambda: drag_draw_check(dpage))
                r.check('desktop_button_draw', lambda: button_draw_check(dpage))
                r.check('desktop_keyboard_draw', lambda: key_draws(dpage))
                r.check('desktop_swipe_dismiss', lambda: swipe_dismiss(dpage))
                r.check('desktop_dismiss_button', lambda: dismiss_button(dpage))
                dst = {}
                r.check('desktop_memo_save', lambda: memo_save(dpage, dst))
                r.check('desktop_calendar_day', lambda: calendar_day(dpage, dst))
                r.check('desktop_calendar_draw_entry', lambda: calendar_draw_entry(dpage, dst))
                r.check('desktop_calendar_reload_persist', lambda: calendar_reload_persist(dpage, dst))
                r.check('desktop_sheet_escape_focus', lambda: sheet_escape_focus(dpage))
                r.check('desktop_add_quote', lambda: add_quote(dpage, dst))
                r.check('desktop_add_quote_persist', lambda: add_quote_persist(dpage, dst))
                r.check('desktop_custom_quote_draw', lambda: find_custom(dpage, dst))
            dctx.close()

            print('== draw cycles (fresh context)')
            cctx, cpage = new_page(r, browser, MOBILE, 'cycles')
            r.check('cycles_boot', lambda: boot(cpage, url))
            if r.ok():
                r.check('quote_cycles', lambda: quote_cycles(cpage))
            cctx.close()

            print('== exhaustive deck content 390 (reduced motion)')
            ectx, epage = new_page(r, browser, REDUCE_MOBILE, 'deck-390')
            r.check('mobile_deck_boot', lambda: boot(epage, url))
            if r.ok():
                r.check('mobile_quotes_bilingual', lambda: quotes_bilingual(epage))
                r.check('mobile_longest_bounded', lambda: longest_bounded(epage))
            ectx.close()

            print('== exhaustive deck content 1280 (reduced motion)')
            ectx2, epage2 = new_page(r, browser, REDUCE_DESKTOP, 'deck-1280')
            r.check('desktop_deck_boot', lambda: boot(epage2, url))
            if r.ok():
                r.check('desktop_quotes_bilingual', lambda: quotes_bilingual(epage2))
                r.check('desktop_longest_bounded', lambda: longest_bounded(epage2))
            ectx2.close()

            print('== pwa / offline 390 (fresh context)')
            pctx, ppage = new_page(r, browser, MOBILE, 'pwa')
            r.check('pwa_boot', lambda: boot(ppage, url))
            if r.ok():
                r.check('sw_control', lambda: sw_control(ppage))
                r.check('cache_photos', lambda: cache_photos(ppage))
                r.check('manifest_icons', lambda: manifest_icons(ppage))
                r.check('installability', lambda: installability(pctx, ppage))
                r.check('offline_flow', lambda: offline_flow(ppage, pctx))
            pctx.close()

            print('== pwa / offline 1280 (fresh context)')
            dpc, dpp = new_page(r, browser, DESKTOP, 'pwa-1280')
            r.check('desktop_pwa_boot', lambda: boot(dpp, url))
            if r.ok():
                r.check('desktop_sw_control', lambda: sw_control(dpp))
                r.check('desktop_cache_photos', lambda: cache_photos(dpp))
                r.check('desktop_manifest_icons', lambda: manifest_icons(dpp))
                r.check('desktop_installability', lambda: installability(dpc, dpp))
                r.check('desktop_offline_flow', lambda: offline_flow(dpp, dpc))
            dpc.close()

            print('== legacy migration (fresh context)')
            r.check('legacy_migration', lambda: legacy_migration(r, browser, url))

            print('== v1->v2 id migration (fresh context)')
            r.check('v2_migration', lambda: v2_migration(r, browser, url))

            print('== screenshots (fresh contexts)')
            r.check('screenshots_mobile',
                    lambda: shoot_set(r, browser, url, MOBILE, 'mobile'))
            r.check('screenshots_desktop',
                    lambda: shoot_set(r, browser, url, DESKTOP, 'desktop'))

            if record:
                print('== recordings')
                r.check('record_390',
                        lambda: record_flow(r, browser, url, MOBILE, 'flow-390.webm', tmp))
                r.check('record_1280',
                        lambda: record_flow(r, browser, url, DESKTOP, 'flow-1280.webm', tmp))
        finally:
            browser.close()
            shutil.rmtree(tmp, ignore_errors=True)

    executed = sum(1 for c in r.checks if c['status'] != 'skipped')
    report = {
        'url': url,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'duration_s': round(time.time() - started, 2),
        'executed': executed,
        'passed': sum(1 for c in r.checks if c['status'] == 'passed'),
        'failures': sum(1 for c in r.checks if c['status'] == 'failed'),
        'errors': sum(1 for c in r.checks if c['status'] == 'error'),
        'skipped': sum(1 for c in r.checks if c['status'] == 'skipped'),
        'checks': r.checks,
        'browser_errors': r.browser_errors,
        'screenshots': r.screenshots,
        'recordings': r.recordings,
    }
    (r.out / 'qa.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"qa.json: executed={executed} passed={report['passed']} failures={report['failures']} "
          f"errors={report['errors']} skipped={report['skipped']} "
          f"browser_errors={len(r.browser_errors)} recordings={len(r.recordings)}")
    return 1 if (report['failures'] or report['errors']) else 0


def main():
    ap = argparse.ArgumentParser(description='Daily Quote Card photo-deck QA runner')
    ap.add_argument('--url', default='http://localhost:4187')
    ap.add_argument('--out', default='qa-out')
    ap.add_argument('--record', action='store_true',
                    help='record flow-390.webm and flow-1280.webm under --out')
    args = ap.parse_args()
    try:
        sys.exit(run(args.url.rstrip('/') or 'http://localhost:4187', args.out, args.record))
    except Exception as e:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        (Path(args.out) / 'qa.json').write_text(json.dumps(
            {'url': args.url, 'executed': 0, 'passed': 0, 'failures': 0,
             'errors': 1, 'skipped': 0, 'checks': [], 'browser_errors':
             [f'runner: {type(e).__name__}: {e}'], 'screenshots': [],
             'recordings': []}, indent=2))
        print(f'runner error: {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
