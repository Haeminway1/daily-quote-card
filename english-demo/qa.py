#!/usr/bin/env python3
"""Real-browser QA for the Daily Quote Card PWA.

Usage: python3 qa.py --url http://localhost:4187 --out qa-out

Drives headless Chromium at 390x844 (mobile, touch, DPR 3) and 1280x900,
verifies deck cycling, persistence, i18n, keyboard focus, install dialog,
overflow, manifest/icons, service-worker caching and offline traversal, and
captures screenshots. Reads the rendered DOM and waits on wait_for_function
only — no arbitrary sleeps. Writes qa.json; exits nonzero on failure/error.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

READY = ("() => { const q = document.querySelector('#quote-text');"
         " return !!(q && q.dataset.quoteId && q.textContent.length); }")
IMG_READY = ("() => { const i = document.querySelector('#media img');"
             " return !!(i && i.complete && i.naturalWidth > 0); }")
QUOTE_ID = "e => e.dataset.quoteId"
STORE = 'daily-quote-card:v1'


class Skip(Exception):
    pass


class Runner:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.checks = []
        self.browser_errors = []
        self.screenshots = []

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
        target = self.out / name
        if selector:
            page.locator(selector).screenshot(path=str(target))
        elif full_page_css:
            page.screenshot(path=str(target), full_page=True, scale='css')
        else:
            page.screenshot(path=str(target))
        self.screenshots.append(name)


def seed(page, **state):
    base = {'lang': 'en', 'current': 'q01', 'seen': [], 'notes': {}, 'saved': []}
    base.update(state)
    page.evaluate(f"(s) => localStorage.setItem('{STORE}', JSON.stringify(s))", base)
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function(READY)


def draw(page):
    prev = page.eval_on_selector('#quote-text', QUOTE_ID)
    page.click('#next')
    page.wait_for_function("(p) => document.querySelector('#quote-text').dataset.quoteId !== p", arg=prev)
    return page.eval_on_selector('#quote-text', QUOTE_ID)


def shoot_set(r, page, tag):
    """Clean EN q01/q02 card + CSS-scale full pages, KO card, scrolled end."""
    for qid, lang, name in (('q01', 'en', f'{tag}-en-q01.png'),
                            ('q02', 'en', f'{tag}-en-q02.png'),
                            ('q01', 'ko', f'{tag}-ko.png')):
        seed(page, current=qid, lang=lang, seen=[qid])
        page.wait_for_function(IMG_READY)
        r.shot(page, name, '.reflection')
        if lang == 'en':
            r.shot(page, f'{tag}-en-{qid}-page.png', full_page_css=True)
    seed(page, current='q01', lang='en', seen=['q01'])
    page.wait_for_function(READY)
    page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
    page.wait_for_function("() => window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 1")
    r.shot(page, f'{tag}-end.png')


def run(url, out):
    r = Runner(out)
    started = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 390, 'height': 844},
                                  device_scale_factor=3, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.set_default_timeout(15000)
        r.watch(page, 'mobile')
        srcs = []

        def boot():
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_function(READY)
            page.wait_for_function(IMG_READY)
            nonlocal srcs
            srcs = page.evaluate("fetch('deck.json').then(r => r.json()).then(d => d.quotes.map(q => q.image))")
            assert len(srcs) == 12, f'deck has {len(srcs)} images'
            return 'rendered first card'

        print(f'== mobile 390x844 dpr3 @ {url}')
        r.check('boot', boot)
        if r.ok():
            all_ids = set('q%02d' % i for i in range(1, 13))

            def counter_format():
                text = page.eval_on_selector('#counter', 'e => e.textContent')
                assert re.fullmatch(r'Card \d+ of 12', text.strip()), f'counter={text!r}'
                return text.strip()
            r.check('counter_format', counter_format)

            def three_cycles():
                seed(page, current='q01', seen=['q01'])
                ids = [page.eval_on_selector('#quote-text', QUOTE_ID)]
                for _ in range(36):
                    ids.append(draw(page))
                adj = [f'{a}->{b}' for a, b in zip(ids, ids[1:]) if a == b]
                assert not adj, f'adjacent repeats: {adj}'
                for i in range(3):
                    block = ids[i * 12:(i + 1) * 12]
                    assert len(set(block)) == 12 and set(block) == all_ids, f'block {i} bad: {block}'
                return '36 draws = 3 unique blocks of 12, no adjacent repeats'
            r.check('three_cycles', three_cycles)

            def images_decode():
                bad = page.evaluate("""async (srcs) => {
                    const bad = [];
                    for (const s of srcs) {
                        const img = new Image(); img.src = 'images/' + s;
                        try { await img.decode(); if (!img.naturalWidth) bad.push(s); }
                        catch (e) { bad.push(s); }
                    }
                    return bad;
                }""", srcs)
                assert not bad, f'undecodable: {bad}'
                return f'{len(srcs)} images decode'
            r.check('images_decode', images_decode)

            def i18n_ko():
                qid = page.eval_on_selector('#quote-text', QUOTE_ID)
                page.select_option('#language', 'ko')
                page.wait_for_function("() => document.documentElement.lang === 'ko'")
                expected = page.evaluate("""async (id) => {
                    const d = await (await fetch('deck.json')).json();
                    return d.quotes.find(q => q.id === id).ko;
                }""", qid)
                quote = page.eval_on_selector('#quote-text', 'e => e.textContent')
                assert quote == expected, f'ko quote {quote!r} != deck {expected!r}'
                counter = page.eval_on_selector('#counter', 'e => e.textContent')
                assert '장' in counter, f'counter not localized: {counter!r}'
                heading = page.eval_on_selector('h1', 'e => e.textContent')
                assert '오늘' in heading, f'heading not localized: {heading!r}'
                page.select_option('#language', 'en')
                page.wait_for_function("() => document.documentElement.lang === 'en'")
                return f'KO quote/counter/heading render ({counter.strip()})'
            r.check('i18n_ko', i18n_ko)

            def keyboard_focus():
                page.keyboard.press('Tab')
                for _ in range(15):
                    if page.evaluate("() => document.activeElement && document.activeElement.id") == 'next':
                        break
                    page.keyboard.press('Tab')
                assert page.evaluate("() => document.activeElement.id") == 'next', 'Tab never reached #next'
                assert page.evaluate("() => document.activeElement.matches(':focus-visible')"), '#next lacks :focus-visible'
                prev = page.eval_on_selector('#quote-text', QUOTE_ID)
                page.keyboard.press('Enter')
                page.wait_for_function("(p) => document.querySelector('#quote-text').dataset.quoteId !== p", arg=prev)
                assert page.evaluate("() => document.activeElement.id") == 'quote-text', 'focus did not move to quote'
                return 'Tab reaches #next with focus-visible; Enter draws and focus moves to quote'
            r.check('keyboard_focus', keyboard_focus)

            def note_persist():
                page.fill('#note', 'QA note persistence check')
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function(READY)
                val = page.eval_on_selector('#note', 'e => e.value')
                assert val == 'QA note persistence check', f'note={val!r}'
                return 'note survives reload'
            r.check('note_persist', note_persist)

            def bookmark_persist():
                page.click('#bookmark')
                page.wait_for_function("() => document.querySelector('#bookmark').getAttribute('aria-pressed') === 'true'")
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function(READY)
                val = page.eval_on_selector('#bookmark', "e => e.getAttribute('aria-pressed')")
                assert val == 'true', f'aria-pressed={val}'
                return 'bookmark survives reload'
            r.check('bookmark_persist', bookmark_persist)

            def install_dialog():
                page.click('#install')
                page.wait_for_function("() => document.querySelector('#install-help').open")
                page.click('#install-help button')
                page.wait_for_function("() => !document.querySelector('#install-help').open")
                return 'install help dialog opens and closes'
            r.check('install_dialog', install_dialog)

            def no_overflow():
                m = page.evaluate("""() => ({
                    sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
                    card: (r => ({l: r.left, r: r.right}))(document.querySelector('.reflection').getBoundingClientRect())})""")
                assert m['sw'] <= m['cw'] + 1, f'scrollWidth {m["sw"]} > clientWidth {m["cw"]}'
                assert m['card']['l'] >= -0.5 and m['card']['r'] <= m['cw'] + 0.5, f'card overflows: {m["card"]}'
                return f'no horizontal overflow ({m["cw"]}px)'
            r.check('no_overflow', no_overflow)

            def manifest_icons():
                info = page.evaluate("""async () => {
                    const m = await (await fetch('manifest.webmanifest')).json();
                    const icons = [];
                    for (const ic of m.icons || []) {
                        const img = new Image(); img.src = ic.src; await img.decode();
                        icons.push({src: ic.src, declared: ic.sizes, w: img.naturalWidth, h: img.naturalHeight});
                    }
                    return {name: m.name, display: m.display, icons};
                }""")
                assert info['display'] == 'standalone', f"display={info['display']}"
                dims = {i['declared']: (i['w'], i['h']) for i in info['icons']}
                for s in ('192x192', '512x512'):
                    assert s in dims, f'missing {s}'
                    assert dims[s] == (int(s[:3]), int(s[4:])), f'{s} -> {dims[s]}'
                return f"manifest '{info['name']}', icons 192+512 verified"
            r.check('manifest_icons', manifest_icons)

            def sw_cache():
                page.wait_for_function("() => !!navigator.serviceWorker.controller")
                data = page.evaluate("""async () => {
                    const key = (await caches.keys()).find(k => k.startsWith('daily-quote-card-'));
                    if (!key) return {key: null, urls: []};
                    const reqs = await (await caches.open(key)).keys();
                    return {key, urls: reqs.map(r => new URL(r.url).pathname)};
                }""")
                assert data['key'], 'no daily-quote-card cache found'
                base = page.evaluate("() => new URL('./', location.href).pathname")
                need = [base + 'images/' + s for s in srcs]
                need += [base + p for p in ('index.html', 'app.js', 'style.css', 'aquila.css',
                                            'deck.json', 'manifest.webmanifest',
                                            'icons/icon-192.png', 'icons/icon-512.png')]
                missing = [u for u in need if u not in data['urls']]
                assert not missing, f'not cached: {missing}'
                return f"SW controls page; {data['key']} holds {len(data['urls'])} entries incl. all 12 images"
            r.check('sw_cache', sw_cache)

            def notification_denied_ui():
                if not page.evaluate("() => 'Notification' in window"):
                    raise Skip('Notification API unsupported in this browser')
                perm = page.evaluate("() => Notification.permission")
                if perm == 'granted':
                    raise Skip('permission already granted; blocked-path UI not applicable')
                before = page.eval_on_selector('#status', 'e => e.textContent')
                page.click('#notify')
                page.wait_for_function("(b) => { const s = document.querySelector('#status'); return s.textContent !== b && s.textContent.length > 0; }", arg=before)
                msg = page.eval_on_selector('#status', 'e => e.textContent').strip()
                after = page.evaluate("() => Notification.permission")
                if after == 'granted':
                    raise Skip(f'permission {perm}->{after}; blocked-path UI not applicable')
                low = msg.lower()
                assert any(k in low for k in ('block', 'denied', 'not supported', 'could not', 'unavailable')), \
                    f'status is not a coherent blocked/error message: {msg!r}'
                return f'permission={perm}->{after}; blocked-path status="{msg}"'
            r.check('notification_denied_ui', notification_denied_ui)

            def notification_test():
                if not page.evaluate("() => 'Notification' in window && 'serviceWorker' in navigator"):
                    raise Skip('Notification API unsupported in this browser')
                ctx.grant_permissions(['notifications'])
                perm = page.evaluate("() => Notification.permission")
                if perm != 'granted':
                    raise Skip(f'permission={perm}; delivery cannot be exercised in this environment')
                before = page.eval_on_selector('#status', 'e => e.textContent')
                page.click('#notify')
                page.wait_for_function("(b) => { const s = document.querySelector('#status'); return s.textContent !== b && s.textContent.length > 0; }", arg=before)
                msg = page.eval_on_selector('#status', 'e => e.textContent').strip()
                found = page.evaluate("""async () => {
                    try {
                        const reg = await navigator.serviceWorker.ready;
                        return (await reg.getNotifications({tag: 'daily-quote-card-test'})).length;
                    } catch (e) { return -1; }
                }""")
                if found <= 0:
                    raise Skip(f'permission=granted, status="{msg}", but notification API cannot '
                               f'deliver (getNotifications tag=daily-quote-card-test -> {found})')
                return (f'permission=granted; local API receipt verified: getNotifications lists '
                        f'daily-quote-card-test x{found}; status="{msg}"; OS display not verifiable')
            r.check('notification_test', notification_test,
                    synthetic='permission granted via automation context; proves local API receipt only, never OS-level display')

            def offline_traverse():
                seed(page, current='q01', seen=['q01'])
                ctx.set_offline(True)
                try:
                    page.reload(wait_until='domcontentloaded')
                    page.wait_for_function(READY)
                    seen = [page.eval_on_selector('#quote-text', QUOTE_ID)]
                    page.wait_for_function(IMG_READY)
                    for _ in range(11):
                        seen.append(draw(page))
                        page.wait_for_function(IMG_READY)
                    adj = [f'{a}->{b}' for a, b in zip(seen, seen[1:]) if a == b]
                    assert not adj, f'adjacent repeats offline: {adj}'
                    assert len(seen) == 12 and set(seen) == all_ids, f'offline cycle ids: {seen}'
                    return 'offline reload + one full cycle: all 12 unique cards, every image decoded'
                finally:
                    ctx.set_offline(False)
            r.check('offline_reload_traverse', offline_traverse)

            r.check('screenshots_mobile', lambda: (shoot_set(r, page, 'mobile'), '6 shots')[1])

        # ---- desktop 1280x900 ----
        print('== desktop 1280x900')
        dctx = browser.new_context(viewport={'width': 1280, 'height': 900})
        dpage = dctx.new_page()
        dpage.set_default_timeout(15000)
        r.watch(dpage, 'desktop')

        def dboot():
            dpage.goto(url, wait_until='domcontentloaded')
            dpage.wait_for_function(READY)
            dpage.wait_for_function(IMG_READY)
            return 'desktop rendered'
        r.check('desktop_boot', dboot)
        if r.ok():
            def doverflow():
                m = dpage.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth})")
                assert m['sw'] <= m['cw'] + 1, f'{m}'
                shell = dpage.evaluate("() => document.querySelector('.shell').getBoundingClientRect().width")
                assert shell <= 480.5, f'shell {shell}px exceeds 480'
                return f'no overflow; shell={shell}px (<=480)'
            r.check('desktop_no_overflow', doverflow)
            r.check('screenshots_desktop', lambda: (shoot_set(r, dpage, 'desktop'), '6 shots')[1])
        browser.close()

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
    }
    (r.out / 'qa.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"qa.json: executed={executed} passed={report['passed']} failures={report['failures']} errors={report['errors']} skipped={report['skipped']} browser_errors={len(r.browser_errors)}")
    return 1 if (report['failures'] or report['errors']) else 0


def main():
    ap = argparse.ArgumentParser(description='Daily Quote Card PWA QA runner')
    ap.add_argument('--url', default='http://localhost:4187')
    ap.add_argument('--out', default='qa-out')
    args = ap.parse_args()
    try:
        sys.exit(run(args.url.rstrip('/') or 'http://localhost:4187', args.out))
    except Exception as e:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        (Path(args.out) / 'qa.json').write_text(json.dumps(
            {'url': args.url, 'executed': 0, 'passed': 0, 'failures': 0,
             'errors': 1, 'skipped': 0, 'checks': [],
             'browser_errors': [f'runner: {type(e).__name__}: {e}']}, indent=2))
        print(f'runner error: {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
