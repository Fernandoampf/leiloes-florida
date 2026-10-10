#!/usr/bin/env python3
"""Refresh RealAuction tax-deed snapshots against the CLERK's own records (never a RealAuction host):
- TaxSmart / TaxSmartWeb case pages (Citrus search.citrusclerk.org, Hernando or.hernandoclerk.com) -> current Opening Bid and Status;
- data/status_manual.json: statuses/opening bids Fernando verified by hand (county + case or parcel) -> redeemed/canceled removed, OB corrected.
Fetched once a day (1 request/second), cached in AUC/statewide/clerk_verify/<YYYY-MM-DD>.json; --offline uses the newest cache."""
import datetime as dt, glob, html, json, os, re, time, urllib.request
DIR = os.path.join('/workspace/auc', 'statewide', 'clerk_verify')
HERE = os.path.dirname(os.path.abspath(__file__))
UA = 'Mozilla/5.0 (ChallengeCapital daily refresh; 1 request/second)'
OK_HOSTS = ('search.citrusclerk.org', 'or.hernandoclerk.com')
DEAD = re.compile(r'REDEEM|CANCEL|WITHDRAW|VOID|STRUCK|DISMISS|BANKRUP|PAID', re.I)


def _money(s):
    try: return float(re.sub(r'[^0-9.]', '', s)) if s and re.search(r'\d', s) else None
    except Exception: return None


def parse_taxsmart(page):
    t = html.unescape(re.sub(r'<[^>]+>', ' | ', re.sub(r'<script.*?</script>|<style.*?</style>', '', page, flags=re.S)))
    t = re.sub(r'(\s*\|\s*)+', ' | ', re.sub(r'\s+', ' ', t))
    ob = re.search(r'(?:Opening|Base) Bid \| \$?([\d,]+\.\d\d)', t); st = re.search(r'\| Status \| ([A-Za-z][A-Za-z /-]+?) \|', t)
    ad = re.search(r'Assessed As \| ([A-Za-z ]+?) \|', t)
    return dict(ob=_money(ob.group(1)) if ob else None, status=(st.group(1).strip() if st else None), assessed=(ad.group(1).strip() if ad else None))


def refresh(items, offline=False, today=None):
    """items: list of (src, raw) from rawdata.collect(). Mutates raws; returns (kept items, stats)."""
    today = today or dt.date.today().isoformat()
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, f'{today}.json')
    cache = {}
    olds = sorted(glob.glob(os.path.join(DIR, '*.json')))
    if olds: cache = json.load(open(olds[-1]))
    todo = [x for s, x in items if s == 'TD' and any(h in (x.get('clink') or '') for h in OK_HOSTS)]
    fetched = 0
    if not offline and not os.path.exists(path):
        for x in todo:
            try:
                req = urllib.request.Request(x['clink'].replace('http://', 'https://'), headers={'User-Agent': UA})
                cache[x['clink']] = dict(parse_taxsmart(urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')), at=today)
                fetched += 1
            except Exception as e:
                cache.setdefault(x['clink'], {})['err'] = type(e).__name__
            time.sleep(1)
        json.dump(cache, open(path, 'w'))
    man = {}
    mp = os.path.join(HERE, 'data', 'status_manual.json')
    if os.path.exists(mp):
        for e in json.load(open(mp)).get('items', []):
            for k in ('case', 'parcel'):
                if e.get(k): man[(e['county'], k, re.sub(r'[^0-9A-Z]', '', e[k].upper()))] = e
    st = dict(checked=0, ob_changed=0, dropped=0, manual=0, fetched=fetched, by_county={})
    keep = []
    for s, x in items:
        c = cache.get(x.get('clink') or '') if s == 'TD' else None
        dead = None
        if c and (c.get('ob') or c.get('status')):
            st['checked'] += 1
            x['cver'] = dict(ob=c.get('ob'), status=c.get('status'), at=c.get('at'), src=x['clink'], ob0=x.get('ob'), assessed=c.get('assessed'))
            if c.get('status') and DEAD.search(c['status']): dead = c['status']
            elif c.get('ob') and x.get('ob') and abs(c['ob'] - x['ob']) > 1:
                st['ob_changed'] += 1; x['ob'] = c['ob']
        e = man.get((x['county'], 'case', re.sub(r'[^0-9A-Z]', '', str(x.get('case') or '').upper()))) or \
            man.get((x['county'], 'parcel', re.sub(r'[^0-9A-Z]', '', str(x.get('parcel') or '').upper())))
        if e:
            st['manual'] += 1
            if e.get('status') and DEAD.search(e['status']): dead = e['status'] + ' (verificado: ' + (e.get('source') or 'manual') + ')'
            if e.get('ob'):
                x['cver'] = dict(ob=e['ob'], status=e.get('status'), at=e.get('date'), src=e.get('source'), ob0=x.get('ob')); x['ob'] = e['ob']
        if dead:
            st['dropped'] += 1; st['by_county'][x['county']] = st['by_county'].get(x['county'], 0) + 1
            continue
        keep.append((s, x))
    return keep, st
