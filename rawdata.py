#!/usr/bin/env python3
"""v4 raw auction collector: every pending item from the public RealAuction preview scans in /workspace/auc/statewide
(td/*.json tax deeds, fc/*.json foreclosures, area W = still scheduled) + Orange foreclosures (fc_all.json, scraped
separately) + extra land sources (extra_*.json). Returns normalized dicts (same shape as fc_all.json)."""
import time, glob, json, os, re

SW = '/workspace/auc/statewide'

def money(v):
    try: return float(str(v).replace('$', '').replace(',', '').strip())
    except Exception: return None

def norm(raw, county, host, date, kind):
    street = (raw.get('Property Address') or '').strip()
    a2 = (raw.get('addr2') or '').strip()
    if street and a2: addr = f'{street} {a2}'
    else: addr = street or a2
    case = re.sub(r'\s*\(\d+\)\s*$', '', raw.get('Case #') or '').strip()
    # Most counties use 'Parcel ID'; Hernando uses 'Parcel Key' and Citrus 'Alternate Key' (= DOR ALT_KEY).
    pkey = next((k for k in ('Parcel ID', 'Parcel Key', 'Alternate Key') if (raw.get(k) or '').strip()), 'Parcel ID')
    parcel = (raw.get(pkey) or '').strip()
    multi = bool(re.search(r'MULTIPLE', parcel, re.I))
    if not re.search(r'\d', parcel): parcel = None          # 'Property Appraiser' / 'PERSONAL PROPERTY' / 'MULTIPLE PARCELS'
    plink = raw.get(pkey + '_link')
    if plink and (re.search(r'[=/]$', plink) or re.search(r'MULTIPLE', plink, re.I)): plink = None    # link without the parcel id
    d = dict(county=county, host=host, date=date, aid=raw['AID'], case=case, parcel=parcel,
             plink=plink, street=street, addr=addr, multi=multi or None,
             av=money(raw.get('Assessed Value')) or money(raw.get('Property App. Market Value')),
             url=f'https://{host}/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE={date}',
             detail=f'https://{host}/index.cfm?zaction=auction&zmethod=details&AID={raw["AID"]}')
    if kind == 'TD':
        d['ob'] = money(raw.get('Opening Bid')); d['cert'] = raw.get('Certificate #')
    else:
        d['fj'] = money(raw.get('Final Judgment Amount')); d['pmax'] = raw.get('Plaintiff Max Bid') or raw.get('Plaintiff max bid')
    return d

def collect():
    """-> list of (src, item)"""
    out, seen = [], set()
    for kind, sub, dom in (('TD', 'td', 'realtaxdeed'), ('FC', 'fc', 'realforeclose')):
        for f in sorted(glob.glob(os.path.join(SW, sub, '*.json'))):
            base = os.path.basename(f)[:-5]
            county, date = base.rsplit('_', 1)
            if kind == 'FC' and county == 'myorangeclerk': continue     # Orange FC comes from fc_all.json (fco scrape)
            date = date.replace('-', '/')
            # host: tax deeds may live on the combined realforeclose site
            host = None
            try: rows = json.load(open(f))
            except Exception: continue
            for r in rows:
                if r.get('area') != 'W' or 'Case #' not in r: continue
                if kind == 'TD' and (r.get('Auction Type') or 'TAXDEED').upper() != 'TAXDEED': continue
                if host is None:
                    lk = r.get('Parcel ID_link') or ''
                    host = f"{ {'stjohns': 'saintjohns'}.get(county, county) if kind == 'FC' else county}.{dom}.com"
                key = (kind, r['AID'])
                if key in seen: continue
                seen.add(key)
                d = norm(r, county, host, date, kind)
                d['scan'] = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(f)))   # when this RealAuction list was read
                if r.get('Case #_link'): d['clink'] = r['Case #_link']
                out.append((kind, d))
    # tax deeds: real host from the RealAuction calendar (some counties run TD on the combined realforeclose site)
    evh = {}
    try:
        for h, d, k, n, t in json.load(open(os.path.join(SW, 'events.json'))):
            if k == 'Tax Deed': evh.setdefault((h.split('.')[0].replace('-', ''), d), h)
    except Exception: pass
    for k, x in out:
        if k != 'TD': continue
        h = evh.get((x['county'], x['date']))
        if h and h != x['host']:
            x['url'] = x['url'].replace(x['host'], h); x['detail'] = x['detail'].replace(x['host'], h); x['host'] = h
    for x in json.load(open(os.path.join(SW, 'fc_all.json'))):
        if x['county'] == 'myorangeclerk' and ('FC', x['aid']) not in seen:
            seen.add(('FC', x['aid'])); out.append(('FC', dict(x)))
    for f in sorted(glob.glob(os.path.join(SW, 'extra_*.json'))):
        for x in json.load(open(f)):
            out.append((x.get('src', 'OT'), x))
    return out

def closed_cases():
    """(case, ISO date) of RealAuction items no longer pending (area C: canceled, redeemed, sold) in the scanned
    preview lists – used to keep stale PropertyOnion export rows from re-adding them as PO-only items."""
    out = set()
    for sub in ('td', 'fc'):
        for f in glob.glob(os.path.join(SW, sub, '*.json')):
            date = os.path.basename(f)[:-5].rsplit('_', 1)[1]          # MM-DD-YYYY
            iso = date[6:] + '-' + date[:2] + '-' + date[3:5]
            try: rows = json.load(open(f))
            except Exception: continue
            for r in rows:
                if r.get('area') == 'C' and r.get('Case #'):
                    out.add((re.sub(r'\s*\(\d+\)\s*$', '', r['Case #']).strip(), iso))
    return out

if __name__ == '__main__':
    import collections
    c = collect()
    print(len(c), collections.Counter(k for k, _ in c))
    print(collections.Counter((k, x['county']) for k, x in c).most_common(100))
