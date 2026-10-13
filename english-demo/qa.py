#!/usr/bin/env python3
"""Real-browser QA for the restored photo-deck Daily Quote Card app.

Usage: python3 qa.py --url http://localhost:4187 --out qa-out [--record]

Drives headless Chromium at 390x844 (mobile, touch, DPR 3) and 1280x900 with
prefers-reduced-motion disabled. Verifies the 7-card photo belt (render, photo
decode, motion), real pointer drag-to-draw above/below the 120px threshold,
button (#drawButton) and Enter/Space draws, pointer swipe and #quoteDismiss
dismissal, memo save + calendar persistence, custom-quote add and survival,
two full unique 12-card draw cycles, service-worker photo caching, manifest +
icons, installability errors, offline use, and legacy daily-quote-card:v1 note
migration when production supports it. Captures clean marketing screenshots at
both widths in dedicated fresh contexts; --record additionally writes two
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

LEGACY_KEY = 'daily-quote-card:v1'
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
NEXT_QUOTE = ("(t) => { const c = document.getElementById('quoteCard');"
              " const q = document.getElementById('quoteText');"
              " return !!(c && q && !c.hidden && c.dataset.state === 'revealed'"
              " && q.textContent.trim().length && q.textContent !== t); }")
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


def wait_next_quote(page, prev_text, timeout=9000):
    page.wait_for_function(NEXT_QUOTE, arg=prev_text, timeout=timeout)
    page.wait_for_function(SETTLED, timeout=timeout)


def button_draw(page) -> DrawResult:
    """Click #drawButton; waits for a genuinely new reveal + finished clone."""
    prev = quote_text(page)
    for _ in range(1):
        page.wait_for_function(SETTLED)
        page.click('#drawButton')
        try:
            wait_next_quote(page, prev, timeout=6000)
            return {'id': last_draw_id(page), 'text': quote_text(page)}
        except PWTimeout:
            continue
    raise AssertionError('#drawButton click produced no new draw')


def key_draw(page, key) -> DrawResult:
    prev = quote_text(page)
    page.wait_for_function(SETTLED)
    page.focus('#deck')
    assert page.evaluate("() => document.activeElement && document.activeElement.id") == 'deck', \
        '#deck did not take focus'
    page.keyboard.press(key)
    wait_next_quote(page, prev)
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
    prev = quote_text(page)
    pt = card_point(page)
    page.mouse.move(pt['x'], pt['y'])
    page.mouse.down()
    page.mouse.move(pt['x'], pt['y'] + dy, steps=8)
    grabbed = page.eval_on_selector('#drawCard', 'e => e.style.opacity')
    assert grabbed == '1', f'pointer-down did not grab a belt card (opacity={grabbed!r})'
    page.mouse.up()
    wait_next_quote(page, prev)
    return {'id': last_draw_id(page), 'text': quote_text(page)}


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
    assert page.locator('#drawButton').is_visible(), '#drawButton not visible'
    return f'7 photo belt cards; {len(srcs)} photo(s) decode; #drawButton visible'


def belt_motion(page):
    t0 = page.eval_on_selector('#belt .belt-card', 'e => e.style.transform')
    page.wait_for_function("(t) => { const c = document.querySelector('#belt .belt-card');"
                           " return c && c.style.transform !== t; }",
                           arg=t0, timeout=5000)
    return 'belt transforms change over time (motion on, reduced_motion=no-preference)'


def short_drag(page):
    prev = quote_text(page)
    pt = card_point(page)
    page.mouse.move(pt['x'], pt['y'])
    page.mouse.down()
    page.mouse.move(pt['x'], pt['y'] + 60, steps=6)
    grabbed = page.eval_on_selector('#drawCard', 'e => e.style.opacity')
    page.mouse.up()
    assert grabbed == '1', f'pointer-down did not grab a belt card (opacity={grabbed!r})'
    page.wait_for_function(SETTLED)
    assert quote_text(page) == prev, '60px drag unexpectedly drew a card'
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
    box = page.locator('#quoteText').bounding_box() or page.locator('#quoteCard').bounding_box()
    assert box, 'no quote card geometry'
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
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
    assert h1.get('totalQuoteCount') == 13, f"totalQuoteCount={h1.get('totalQuoteCount')}"
    return f"saved; counts {h1.get('customQuoteCount')}/{h1.get('totalQuoteCount')} (was 12)"


def add_quote_persist(page, st):
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function(BELT_READY)
    h = hook(page) or {}
    assert h.get('totalQuoteCount') == 13 and h.get('customQuoteCount', 0) >= 1, f'hook={h}'
    return 'custom quote survives reload (totalQuoteCount=13)'


def find_custom(page, st):
    text = st.get('custom_text')
    assert text, 'no custom text recorded'
    for i in range(13):
        d = button_draw(page)
        if d['text'] == text:
            return f'custom quote reached in {i + 1} real #drawButton draws (<=13)'
    raise AssertionError('custom quote not drawn within 13 real draws')


def quote_cycles(page):
    got = [button_draw(page)['text'] for _ in range(24)]
    adj = [f'{a}' for a, b in zip(got, got[1:]) if a == b]
    assert not adj, f'adjacent repeats: {adj}'
    b1, b2 = set(got[:12]), set(got[12:])
    assert len(set(got)) == 12 and len(b1) == 12 and len(b2) == 12 and b1 == b2, \
        f'blocks not unique full cycles: {len(b1)}+{len(b2)} unique'
    return '24 real draws = 2 unique 12-card cycles, no adjacent repeats'


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
    caches = page.evaluate(CACHE_DUMP)
    flat = sorted({u for c in caches for u in c['urls']})
    assert flat, 'no CacheStorage entries found'
    base = page.evaluate("() => new URL('./', location.href).pathname")
    if expected:
        assert len(expected) == 12, f'deck lists {len(expected)} images, expected 12'
        need = [s if s.startswith('/') else base + ('images/' if '/' not in s else '') + s
                for s in expected]
        missing = [u for u in need if u not in flat]
        assert not missing, f'not cached: {missing}'
        srcs = [('images/' + s) if '/' not in s else s for s in expected]
        label = f'12 deck photos present in {caches[0]["key"] if caches else "?"}'
    else:
        srcs = [u for u in flat
                if re.search(r'\.(webp|png|jpe?g|avif)$', u, re.I) and 'icon' not in u.lower()]
        assert len(srcs) >= 12, f'only {len(srcs)} photo-like cache entries (deck.json unavailable)'
        label = f'{len(srcs)} photo cache entries (deck.json unavailable)'
    bad = page.evaluate(DECODE, srcs)
    assert not bad, f'undecodable cached photos: {bad[:4]}'
    return f'{label}; all {len(srcs)} decode'


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


def shoot_set(r, browser, url, cfg, tag):
    """Clean marketing captures in a dedicated fresh context."""
    ctx = browser.new_context(**cfg)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    r.watch(page, f'shot-{tag}')
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
    finally:
        ctx.close()
    return '8 shots'


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

            print('== pwa / offline (fresh context)')
            pctx, ppage = new_page(r, browser, MOBILE, 'pwa')
            r.check('pwa_boot', lambda: boot(ppage, url))
            if r.ok():
                r.check('sw_control', lambda: sw_control(ppage))
                r.check('cache_photos', lambda: cache_photos(ppage))
                r.check('manifest_icons', lambda: manifest_icons(ppage))
                r.check('installability', lambda: installability(pctx, ppage))
                r.check('offline_flow', lambda: offline_flow(ppage, pctx))
            pctx.close()

            print('== legacy migration (fresh context)')
            r.check('legacy_migration', lambda: legacy_migration(r, browser, url))

            print('== marketing screenshots (fresh contexts)')
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
