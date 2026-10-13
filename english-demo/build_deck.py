#!/usr/bin/env python3
"""Reproducible builder for the Daily Quote Card 103-quote original deck.

Usage:
    python3 build_deck.py --quotes PATH --assignment PATH --art-dir PATH \
        --fallback-dir PATH --out PATH --receipt PATH

Reads the bilingual source quote rows and the per-quote art assignment, then
converts the matching PNG art to RGB WebP (aspect preserved, capped at 1080px
on the tall side, Lanczos, quality 82, method 6):

    completed id  -> art-dir/<id>.png       -> <out>/images/<id>.webp
    otherwise     -> fallback-dir/<style>.png -> <out>/images/<style>.webp
                     (shared fallback art is converted once)

Writes:

    <out>/images/<id|style>.webp  one file per unique output, atomic replace
    <out>/deck.json               version 2, kind "original-quotes", input order,
                                  exact field mapping text_en->text,
                                  original_text->ko, author_en->author,
                                  original_author->author_ko, work_or_source,
                                  plus image/imageAvailable/style/imageStatus
    <out>/sw.js                   only the CACHE constant is restamped to
                                  daily-quote-card-shell-v4-<deck+asset digest>
    <receipt>                     build receipt JSON: timestamp, inputSHA,
                                  count, completed/pending ids, per-asset
                                  source path+SHA, output SHA, dimensions,
                                  bytes, assignment style, unique image bytes

Inputs are read-only. Only the generated image paths, deck.json, sw.js and the
receipt are written; no other files or images are touched. No cropping,
repainting or AI generation is performed.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import TypedDict

from PIL import Image

MAX_TALL_PX = 1080
WEBP_QUALITY = 82
WEBP_METHOD = 6
CACHE_PREFIX = 'daily-quote-card-shell-v4'
CACHE_RE = re.compile(r"(const\s+CACHE\s*=\s*['\"])([^'\"]+)(['\"])")

COMPLETED = {'completed', 'complete', 'done', 'ready', 'final', 'finished',
             'original', 'art', 'true', 'yes', '1'}
PENDING = {'pending', 'fallback', 'todo', 'wip', 'waiting', 'incomplete',
           'none', 'false', 'no', '0'}
STATUS_KEYS = ('status', 'state', 'imageStatus', 'artStatus', 'art_status')
STYLE_KEYS = ('style', 'fallback', 'fallbackStyle', 'fallback_style', 'artStyle')


class DeckQuote(TypedDict):
    id: str
    text: str
    ko: str
    author: str
    author_ko: str
    work_or_source: str
    image: str
    imageAvailable: bool
    style: str
    imageStatus: str


class AssetEntry(TypedDict):
    id: str
    style: str
    imageStatus: str
    sourcePath: str
    sourceSHA: str
    output: str
    outputSHA: str
    width: int
    height: int
    bytes: int


class Conversion(TypedDict):
    data: bytes
    width: int
    height: int
    sha: str
    src: Path


class BuildReceipt(TypedDict):
    timestamp: str
    inputSHA: str
    assignmentSHA: str
    count: int
    completed: list[str]
    pending: list[str]
    assets: list[AssetEntry]
    uniqueImages: list[str]
    uniqueImageBytes: int
    cache: str


class BuildError(Exception):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path: Path, data: bytes):
    """Write via a sibling temp file + os.replace so readers see all or nothing."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                             prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_quotes(path: Path):
    raw = path.read_bytes()
    try:
        rows = json.loads(raw)
    except Exception as e:
        raise BuildError(f'{path}: invalid JSON: {e}')
    if not isinstance(rows, list) or not rows:
        raise BuildError(f'{path}: expected a non-empty JSON array of quote rows')
    seen, out = set(), []
    for i, q in enumerate(rows):
        if not isinstance(q, dict):
            raise BuildError(f'{path}: row {i} is not an object')
        qid = q.get('id')
        if not isinstance(qid, str) or not qid.strip():
            raise BuildError(f'{path}: row {i} has no usable id')
        if qid in seen:
            raise BuildError(f'{path}: duplicate id {qid!r}')
        seen.add(qid)
        if not isinstance(q.get('text_en'), str) or not q['text_en'].strip():
            raise BuildError(f'{path}: {qid} missing text_en')
        out.append(q)
    return out, raw


def load_assignment(path: Path):
    """Accept a list of row objects, an id-keyed object, or a wrapper object
    holding such a list/dict under a conventional key."""
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
    except Exception as e:
        raise BuildError(f'{path}: invalid JSON: {e}')
    rows = data
    if isinstance(data, dict):
        rows = None
        for key in ('assignments', 'rows', 'quotes', 'items'):
            if isinstance(data.get(key), (list, dict)):
                rows = data[key]
                break
        if rows is None:
            rows = data
    if isinstance(rows, dict):
        rows = [{'id': k, **(v if isinstance(v, dict) else {'style': v})}
                for k, v in rows.items()]
    if not isinstance(rows, list) or not rows:
        raise BuildError(f'{path}: expected a non-empty list or id-keyed object '
                         'of assignment rows')
    out = {}
    for i, row in enumerate(rows):
        if isinstance(row, str):
            row = {'id': row}
        if not isinstance(row, dict):
            raise BuildError(f'{path}: row {i} is not an object')
        qid = row.get('id') or row.get('quote') or row.get('quote_id') or row.get('quoteId')
        if not isinstance(qid, str) or not qid.strip():
            raise BuildError(f'{path}: row {i} has no usable id')
        if qid in out:
            raise BuildError(f'{path}: duplicate assignment for {qid!r}')
        out[qid] = row
    return out, raw


def field(row, keys):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != '':
            return v
    return None


def safe_name(s: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '-', str(s)).strip('.-')


def convert_image(src: Path):
    """RGB WebP, aspect preserved, tall side capped at MAX_TALL_PX, Lanczos."""
    with Image.open(src) as im:
        rgb = im.convert('RGB')
        w, h = rgb.size
        if h > MAX_TALL_PX:
            rgb = rgb.resize((max(1, round(w * MAX_TALL_PX / h)), MAX_TALL_PX),
                             Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        rgb.save(buf, 'WEBP', quality=WEBP_QUALITY, method=WEBP_METHOD)
        return buf.getvalue(), rgb.size


def build(quotes_path: Path, assign_path: Path, art_dir: Path,
          fallback_dir: Path, out_dir: Path, receipt_path: Path) -> BuildReceipt:
    quotes, quotes_raw = load_quotes(quotes_path)
    assign, assign_raw = load_assignment(assign_path)
    qids = {q['id'] for q in quotes}
    missing = [q['id'] for q in quotes if q['id'] not in assign]
    if missing:
        raise BuildError(f'assignment incomplete: {len(missing)} quote ids '
                         f'have no assignment row: {missing[:5]}')
    extra = [i for i in assign if i not in qids]
    if extra:
        raise BuildError(f'assignment lists {len(extra)} unknown ids: {extra[:5]}')

    conversions: dict[str, Conversion] = {}  # out_name -> conversion record
    deck_quotes: list[DeckQuote] = []
    assets: list[AssetEntry] = []
    completed: list[str] = []
    pending: list[str] = []
    for q in quotes:
        qid = q['id']
        row = assign[qid]
        status = field(row, STATUS_KEYS)
        stok = str(status).strip().lower() if status is not None else None
        style = safe_name(field(row, STYLE_KEYS) or '')
        art = art_dir / f'{qid}.png'
        if stok is None:
            done = art.is_file()
        elif stok in COMPLETED:
            done = True
        elif stok in PENDING:
            done = False
        else:
            raise BuildError(f'{qid}: unknown assignment status {status!r}')
        if done:
            if not art.is_file():
                raise BuildError(f'{qid}: assignment marks completed but '
                                 f'{art} is missing')
            src, out_name, istatus = art, f'{qid}.webp', 'original'
            completed.append(qid)
        else:
            if not style:
                raise BuildError(f'{qid}: pending assignment has no fallback style')
            src = fallback_dir / f'{style}.png'
            if not src.is_file():
                raise BuildError(f'{qid}: fallback art {src} is missing')
            out_name, istatus = f'{style}.webp', 'fallback'
            pending.append(qid)
        if out_name not in conversions:
            data, (w, h) = convert_image(src)
            conversions[out_name] = {'data': data, 'width': w, 'height': h,
                                     'sha': sha256_bytes(data), 'src': src}
        conv = conversions[out_name]
        deck_quotes.append({
            'id': qid,
            'text': q['text_en'],
            'ko': q.get('original_text', ''),
            'author': q.get('author_en', ''),
            'author_ko': q.get('original_author', ''),
            'work_or_source': q.get('work_or_source', ''),
            'image': out_name,
            'imageAvailable': True,
            'style': style,
            'imageStatus': istatus,
        })
        assets.append({
            'id': qid,
            'style': style,
            'imageStatus': istatus,
            'sourcePath': str(src.resolve()),
            'sourceSHA': sha256_path(src),
            'output': f'images/{out_name}',
            'outputSHA': conv['sha'],
            'width': conv['width'],
            'height': conv['height'],
            'bytes': len(conv['data']),
        })

    img_dir = out_dir / 'images'
    for name in sorted(conversions):
        atomic_write(img_dir / name, conversions[name]['data'])

    deck = {'version': 2, 'kind': 'original-quotes', 'quotes': deck_quotes}
    deck_bytes = (json.dumps(deck, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    atomic_write(out_dir / 'deck.json', deck_bytes)

    digest = hashlib.sha256(deck_bytes)
    for name in sorted(conversions):
        digest.update(name.encode('utf-8'))
        digest.update(conversions[name]['data'])
    cache_name = f'{CACHE_PREFIX}-{digest.hexdigest()[:16]}'

    sw_src = out_dir / 'sw.js'
    if not sw_src.is_file():
        sw_src = Path(__file__).resolve().parent / 'sw.js'
    if not sw_src.is_file():
        raise BuildError('no sw.js found to restamp (looked in --out and '
                         'next to build_deck.py)')
    sw_text = sw_src.read_text()
    stamped, n = CACHE_RE.subn(rf'\g<1>{cache_name}\g<3>', sw_text, count=1)
    if n != 1:
        raise BuildError(f'{sw_src}: CACHE constant not found')
    atomic_write(out_dir / 'sw.js', stamped.encode('utf-8'))

    receipt: BuildReceipt = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'inputSHA': sha256_bytes(quotes_raw),
        'assignmentSHA': sha256_bytes(assign_raw),
        'count': len(deck_quotes),
        'completed': completed,
        'pending': pending,
        'assets': assets,
        'uniqueImages': sorted(conversions),
        'uniqueImageBytes': sum(len(c['data']) for c in conversions.values()),
        'cache': cache_name,
    }
    atomic_write(receipt_path,
                 (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='build_deck.py',
        description='Build the 103-quote original bilingual deck.json and WebP '
                    'art from supplied inputs, then restamp the service-worker '
                    'CACHE name with the deck+asset content digest.')
    ap.add_argument('--quotes', required=True, type=Path,
                    help='input quotes JSON (read-only)')
    ap.add_argument('--assignment', required=True, type=Path,
                    help='per-quote art assignment JSON (read-only)')
    ap.add_argument('--art-dir', required=True, type=Path,
                    help='directory of completed <id>.png art')
    ap.add_argument('--fallback-dir', required=True, type=Path,
                    help='directory of <style>.png fallback art')
    ap.add_argument('--out', required=True, type=Path,
                    help='output directory (deck.json, images/, sw.js)')
    ap.add_argument('--receipt', required=True, type=Path,
                    help='receipt JSON output path')
    args = ap.parse_args(argv)
    try:
        receipt = build(args.quotes, args.assignment, args.art_dir,
                        args.fallback_dir, args.out, args.receipt)
    except BuildError as e:
        print(f'build_deck: {e}', file=sys.stderr)
        return 2
    print(f"build_deck: {receipt['count']} quotes "
          f"({len(receipt['completed'])} original, {len(receipt['pending'])} fallback), "
          f"{len(receipt['uniqueImages'])} unique images, "
          f"{receipt['uniqueImageBytes']} bytes, cache={receipt['cache']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
