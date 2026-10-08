#!/usr/bin/env python3
"""Fill Final Judgment / Opening Bid for PropertyOnion-only listings from public RealAuction previews.

- Reuses /workspace/auc/statewide/{fc,td}/*.json when present (all areas, not only W).
- Otherwise fetches the public RealAuction preview AJAX (polite, cached). Lake/Osceola FC
  currently return a login page → skipped (no bypass).
- Cache: challenge-capital/cache/po_bids.json (persists across builds).
"""
from __future__ import annotations
import glob, html, json, os, re, time, requests
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache', 'po_bids.json')
SW = '/workspace/auc/statewide'
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
PAUSE = 1.1  # seconds between host hits

# counties known to require login for foreclosure list (skip network fetch)
LOGIN_WALL = {'lake.realforeclose.com', 'osceola.realforeclose.com'}

def money(v):
    try:
        if v is None or v == '' or v == '-': return None
        if isinstance(v, (int, float)): return float(v) if float(v) > 0 else None
        v = float(str(v).replace('$', '').replace(',', '').strip())
        return v if v > 0 else None
    except Exception:
        return None

def ncase(s):
    s = (s or '').upper().strip()
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)
    s = re.sub(r'[.\s-]*MLTI\d*$', '', s, flags=re.I)
    s = re.sub(r'[^A-Z0-9]', '', s)
    s = re.sub(r'MLTI\d*$', '', s)
    return s

def nstreet(s):
    s = (s or '').upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\b(UNIT|APT|SUITE|STE|#)\s*[A-Z0-9-]+\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def digits(s):
    return re.sub(r'[^0-9]', '', s or '')

def load_cache():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {'bids': {}, 'fetched': {}, 'meta': {}}

def save_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    c['meta'] = dict(c.get('meta') or {}, updated=datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'))
    json.dump(c, open(CACHE, 'w'), indent=1)

def _dec(rH):
    for a, b in [('@A', '<div class="'), ('@B', '</div>'), ('@C', 'class="'), ('@D', '<div>'),
                 ('@E', 'AUCTION'), ('@F', '</td><td'), ('@G', '</td></tr>'), ('@H', '<tr><td '),
                 ('@I', 'table'), ('@J', 'p_back="NextCheck='), ('@K', 'style="Display:none"'),
                 ('@L', '/index.cfm?zaction=auction&zmethod=details&AID=')]:
        rH = rH.replace(a, b)
    return rH

def parse_preview_html_items(h):
    out = []
    for aid, body in re.findall(r'<div id="AITEM_(\d+)"(.*?)(?=<div id="AITEM_|\Z)', h, re.S):
        rows = re.findall(r'<td[^>]*class="AD_LBL"[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>', body, re.S)
        rec = {'AID': aid}
        for k, v in rows:
            k = re.sub(r'<[^>]+>', '', k).strip().rstrip(':')
            v = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', v))).strip()
            if not k: k = 'addr2'
            if k in rec: k = k + '2'
            rec[k] = v
        out.append(rec)
    return out

def fetch_day(host, date_mdY, sess=None):
    """date_mdY like 10/09/2026. Returns list of auction dicts (all areas) or None on failure/login."""
    if host in LOGIN_WALL:
        return None
    s = sess or requests.Session()
    s.headers['User-Agent'] = UA
    base = f'https://{host}'
    try:
        s.get(f'{base}/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE={date_mdY}', timeout=30)
    except Exception:
        return None
    out, seen = [], set()
    for area in ('W', 'C'):
        pd = 0
        for _ in range(12):
            try:
                r = s.get(
                    f'{base}/index.cfm?zaction=AUCTION&Zmethod=UPDATE&FNC=LOAD&AREA={area}&PageDir={pd}&doR=1&tx={int(time.time()*1000)}&bypassPage=0',
                    headers={'X-Requested-With': 'XMLHttpRequest'}, timeout=30)
                ctype = (r.headers.get('content-type') or '')
                if 'json' not in ctype and not r.text.strip().startswith('{'):
                    return None  # login HTML
                d = r.json()
            except Exception:
                return None
            h = _dec(d.get('retHTML') or '')
            items = parse_preview_html_items(h)
            new = 0
            for rec in items:
                if rec['AID'] in seen: continue
                seen.add(rec['AID']); new += 1
                rec['area'] = area
                out.append(rec)
            if new == 0: break
            pd = 1
    return out

def local_day_files(host, date_iso, kind):
    """Yield paths of existing scrape JSON for host/date/kind."""
    slug = host.split('.')[0]
    md = f"{date_iso[5:7]}-{date_iso[8:10]}-{date_iso[:4]}"
    sub = 'fc' if kind == 'FC' else 'td'
    cands = [os.path.join(SW, sub, f'{slug}_{md}.json')]
    if 'orange' in slug or slug == 'myorangeclerk':
        cands += [os.path.join(SW, sub, f'myorangeclerk_{md}.json'), os.path.join(SW, sub, f'orange_{md}.json')]
    for p in cands:
        if os.path.exists(p):
            yield p

def load_day_rows(host, date_iso, kind, cache, fetch=True, sess=None):
    key = f'{host}|{date_iso}|{kind}'
    rows = []
    for p in local_day_files(host, date_iso, kind):
        try:
            rows.extend(json.load(open(p)))
        except Exception:
            pass
    if rows:
        return rows, 'local'
    fetched = (cache.get('fetched') or {}).get(key)
    if fetched and fetched.get('rows') is not None:
        return fetched['rows'], 'cache'
    if not fetch:
        return [], 'skip'
    if host in LOGIN_WALL:
        cache.setdefault('fetched', {})[key] = dict(rows=None, status='login_wall', at=datetime.now().isoformat(timespec='seconds'))
        return [], 'login_wall'
    mdY = f"{date_iso[5:7]}/{date_iso[8:10]}/{date_iso[:4]}"
    time.sleep(PAUSE)
    got = fetch_day(host, mdY, sess=sess)
    if got is None:
        cache.setdefault('fetched', {})[key] = dict(rows=None, status='blocked', at=datetime.now().isoformat(timespec='seconds'))
        return [], 'blocked'
    cache.setdefault('fetched', {})[key] = dict(rows=got, status='ok', at=datetime.now().isoformat(timespec='seconds'), n=len(got))
    return got, 'fetch'

def match_row(want, rows):
    """want has case_n, parcel digits, street_n. Prefer case, then parcel, then street."""
    wc, wp, ws = want.get('case_n'), want.get('parcel'), want.get('street_n')
    for r in rows:
        if wc and ncase(r.get('Case #')) == wc:
            return r, 'case'
    if wp:
        for r in rows:
            p = digits(r.get('Parcel ID') or '')
            if p and (p.zfill(15) == wp.zfill(15) or p.lstrip('0') == wp.lstrip('0')):
                return r, 'parcel'
    if ws:
        for r in rows:
            st = nstreet(r.get('Property Address') or '')
            if st and (st == ws or st.startswith(ws) or ws.startswith(st)):
                return r, 'address'
    return None, None

def bid_from_row(row, kind):
    if kind == 'TD':
        return money(row.get('Opening Bid')), 'ob'
    return money(row.get('Final Judgment Amount')), 'fj'

def host_from_item(it):
    x = it.get('raw') or {}
    if x.get('host'): return x['host']
    # from poe / links later
    return None

def fill_po_bids(items, fetch=True):
    """Mutate po_only items' raw fj/ob when found. Returns stats."""
    cache = load_cache()
    sess = requests.Session(); sess.headers['User-Agent'] = UA
    need = [it for it in items if it.get('po_only')]
    stats = dict(need=len(need), filled=0, by_src={}, by_county={}, skipped_login=0, blocked=0, unmatched=0)
    # group by host|date|kind
    groups = {}
    for it in need:
        x = it['raw']
        host = x.get('host')
        if not host: continue
        date_iso = None
        # raw date is MM/DD/YYYY
        d = x.get('date') or ''
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}$', d):
            m, dd, y = d.split('/'); date_iso = f'{y}-{int(m):02d}-{int(dd):02d}'
        kind = it['src']
        if not date_iso: continue
        groups.setdefault((host, date_iso, kind), []).append(it)

    for (host, date_iso, kind), its in sorted(groups.items()):
        rows, src = load_day_rows(host, date_iso, kind, cache, fetch=fetch, sess=sess)
        if src == 'login_wall': stats['skipped_login'] += len(its)
        elif src == 'blocked': stats['blocked'] += len(its)
        stats['by_src'][src] = stats['by_src'].get(src, 0) + 1
        for it in its:
            x = it['raw']
            want = dict(case_n=ncase(x.get('case')), parcel=digits(x.get('parcel') or ''),
                        street_n=nstreet(x.get('street') or x.get('addr') or ''))
            # also try cache by id
            cid = f"{kind}:{x.get('aid')}"
            prev = (cache.get('bids') or {}).get(cid)
            row, how = None, None
            if prev and prev.get('ref'):
                # reuse
                ref = prev['ref']; how = prev.get('how') or 'cache'
            else:
                row, how = match_row(want, rows) if rows else (None, None)
                if not row:
                    stats['unmatched'] += 1
                    continue
                ref, rkind = bid_from_row(row, kind)
                if not ref:
                    stats['unmatched'] += 1
                    continue
                cache.setdefault('bids', {})[cid] = dict(
                    ref=ref, kind=rkind, how=how, aid=row.get('AID'),
                    case=row.get('Case #'), area=row.get('area'),
                    host=host, date=date_iso, at=datetime.now().isoformat(timespec='seconds'))
            if kind == 'TD':
                x['ob'] = ref
            else:
                x['fj'] = ref
            if row and row.get('AID'):
                # upgrade detail link to real AID when we have it
                x['aid_ra'] = row['AID']
                x['detail'] = f"https://{host}/index.cfm?zaction=auction&zmethod=details&AID={row['AID']}"
            it['bid_fill'] = dict(ref=ref, how=how or 'cache', src=src)
            stats['filled'] += 1
            co = x.get('county', '?')
            stats['by_county'][co] = stats['by_county'].get(co, 0) + 1

    save_cache(cache)
    return stats

if __name__ == '__main__':
    import sys
    sys.path.insert(0, HERE)
    import rawdata, po_export
    items = [dict(src=k, raw=x, known=None) for k, x in rawdata.collect()]
    items, _ = po_export.enrich(items)
    st = fill_po_bids(items, fetch=True)
    print(json.dumps(st, indent=2))
    print('now with fj/ob', sum(1 for it in items if it.get('po_only') and (it['raw'].get('fj') or it['raw'].get('ob'))))
