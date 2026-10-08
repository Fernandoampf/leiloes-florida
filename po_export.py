#!/usr/bin/env python3
"""PropertyOnion Premium CSV exports → left-enrich RealAuction items (+ PO-only upcoming).

Drop zone (outside the public repo): /workspace/auc/statewide/po_exports/
  Files: po_<county>_<YYYY-MM-DD>.csv   e.g. po_orange_2026-10-08.csv
  Newest file per county wins; county also read from the CSV "County" column when present.

build.py calls enrich() after rawdata.collect(). Raw CSVs are NEVER committed to the site repo.
"""
from __future__ import annotations
import csv, datetime as dt, glob, hashlib, os, re

SW = '/workspace/auc/statewide'
EXPORT_DIR = os.path.join(SW, 'po_exports')

# RealAuction hosts (clerk auction preview) by county slug + kind
HOST = {
    ('orange', 'FC'): 'myorangeclerk.realforeclose.com',
    ('orange', 'TD'): 'orange.realtaxdeed.com',
    ('seminole', 'FC'): 'seminole.realforeclose.com',
    ('seminole', 'TD'): 'seminole.realtaxdeed.com',
    ('osceola', 'FC'): 'osceola.realforeclose.com',
    ('osceola', 'TD'): 'osceola.realtaxdeed.com',
    ('lake', 'FC'): 'lake.realforeclose.com',
    ('lake', 'TD'): 'lake.realtaxdeed.com',
    ('volusia', 'FC'): 'volusia.realforeclose.com',
    ('volusia', 'TD'): 'volusia.realtaxdeed.com',
    ('brevard', 'FC'): 'brevard.realforeclose.com',
    ('brevard', 'TD'): 'brevard.realtaxdeed.com',
    ('polk', 'FC'): 'polk.realforeclose.com',
    ('polk', 'TD'): 'polk.realtaxdeed.com',
}

POV_CONF_MIN = 70
POV_COUNTY_BAND = 0.35  # |POV / county - 1| <= 35%


def money(v):
    try:
        if v is None or v == '' or v == '-': return None
        if isinstance(v, str): v = v.replace('$', '').replace(',', '').strip()
        v = float(v)
        if v != v or v <= 0 or v > 1e9: return None
        return v
    except Exception:
        return None


def ncase(s):
    s = (s or '').upper().strip()
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)
    s = re.sub(r'[.\s-]*MLTI\d*$', '', s, flags=re.I)
    s = re.sub(r'[^A-Z0-9]', '', s)
    s = re.sub(r'MLTI\d*$', '', s)
    return s


def digits(s):
    return re.sub(r'[^0-9]', '', s or '')


def nstreet(s):
    s = (s or '').upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\b(UNIT|APT|SUITE|STE|#)\s*[A-Z0-9-]+\b', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\b(ORLANDO|WINTER GARDEN|WINDERMERE|APOPKA|OCOEE|MAITLAND|WINTER PARK|'
               r'SANFORD|KISSIMMEE|CLERMONT|DAYTONA|MELBOURNE|LAKELAND|FL|FLORIDA)\b.*$', '', s).strip()
    return s


def nzip(s):
    m = re.search(r'\b(3\d{4})\b', s or '')
    return m.group(1) if m else ''


def county_slug(name):
    s = re.sub(r'[^a-z]', '', (name or '').lower().replace('county', ''))
    return {'myorangeclerk': 'orange', 'stlucie': 'stlucie', 'stjohns': 'stjohns',
            'miamidade': 'miamidade', 'palmbeach': 'palmbeach'}.get(s, s)


def parse_date(d):
    d = (d or '').strip()
    if re.match(r'\d{4}-\d{2}-\d{2}$', d):
        y, m, dd = d.split('-'); return f'{y}-{m}-{dd}', f'{m}/{dd}/{y}'
    if re.match(r'\d{1,2}/\d{1,2}/\d{4}$', d):
        m, dd, y = d.split('/'); return f'{y}-{int(m):02d}-{int(dd):02d}', f'{int(m):02d}/{int(dd):02d}/{y}'
    return None, None


def ocpa_parcel(row):
    """Normalize parcel to OCPA-style digit id when possible."""
    link = (row.get('Appraiser Link') or row.get('appraiser') or '').replace('%20', ' ')
    m = re.search(r'/([0-9]{10,})\s*$', link.rstrip('/'), re.I)
    if m: return m.group(1).zfill(15)
    p = row.get('Parcel Number') or row.get('parcel') or ''
    parts = re.findall(r'\d+', p)
    if len(parts) >= 6:
        sec, twp, rng, sub, blk, lot = (parts[0].zfill(2), parts[1].zfill(2), parts[2].zfill(2),
                                        parts[3].zfill(4), parts[4].zfill(2), parts[5].zfill(3))
        # Orange (and many FL) appraiser links use Range-Township-Section-…
        return f'{rng}{twp}{sec}{sub}{blk}{lot}'
    d = digits(p)
    return d.zfill(15) if d else ''


def _file_county_date(path):
    base = os.path.basename(path)
    m = re.match(r'po_([a-z0-9]+)_(\d{4}-\d{2}-\d{2})\.csv$', base, re.I)
    if m: return county_slug(m.group(1)), m.group(2)
    return None, None


def list_export_files(directory=None):
    """Newest file per county (by date in filename, then mtime)."""
    directory = directory or EXPORT_DIR
    if not os.path.isdir(directory): return []
    by = {}
    for path in sorted(glob.glob(os.path.join(directory, 'po_*.csv'))):
        co, date = _file_county_date(path)
        if not co or not date: continue
        prev = by.get(co)
        if not prev or date > prev[0] or (date == prev[0] and os.path.getmtime(path) >= os.path.getmtime(prev[1])):
            by[co] = (date, path)
    return [(co, d, p) for co, (d, p) in sorted(by.items())]


def _truthy_yes(v):
    return str(v or '').strip().lower() in ('yes', 'y', 'true', 'owner occupied', '1')


def _truthy_vacant(v):
    return str(v or '').strip().upper() in ('Y', 'YES', 'VACANT', 'TRUE', '1')


def normalize_row(row, file_county=None):
    lt = (row.get('Listing Type') or '').strip()
    kind = 'FC' if 'Foreclos' in lt else 'TD' if 'Tax' in lt else None
    if not kind: return None
    status = (row.get('Auction Status') or '').strip().lower()
    if status and status not in ('upcoming', 'scheduled', 'active', ''):
        return None
    iso, mdY = parse_date(row.get('Auction Date'))
    if not iso: return None
    street = (row.get('Street Address') or '').strip()
    city = (row.get('City') or '').strip()
    zip5 = (row.get('Zip') or '').strip()[:5]
    co = county_slug(row.get('County') or file_county or '')
    if not co: return None
    case = (row.get('Case Number') or '').strip()
    parcel = ocpa_parcel(row)
    parcel_raw = (row.get('Parcel Number') or '').strip()
    addr = f'{street} {city}, FL {zip5}'.strip() if street else (city + f', FL {zip5}').strip()
    rent = money(row.get('POV Rent') or row.get('Estimated Rent') or row.get('Estimated Rental Value')
                 or row.get('Rent') or row.get('POV rent'))
    return dict(
        kind=kind, county=co, case=case, case_n=ncase(case),
        parcel=parcel, parcel_raw=parcel_raw,
        street=street, city=city, zip=zip5, addr=addr,
        street_n=nstreet(street),
        date_iso=iso, date_mdY=mdY.replace('-', '/') if mdY and '-' in mdY else (mdY or ''),
        # date_mdY for RealAuction URLs: MM/DD/YYYY
        date_ra=f"{iso[5:7]}/{iso[8:10]}/{iso[:4]}",
        pov=money(row.get('POV')),
        pov_conf=money(row.get('Confidence Rating')),
        pov_rent=rent,
        cmv=money(row.get('County Market Value')),
        clv=money(row.get('County Land Value')),
        last_sale=money(row.get('Last Sale')),
        last_sale_date=(row.get('Last Sale Date') or '').strip(),
        prev_sale_type=(row.get('Previous Sale Type') or '').strip() or None,
        vacant=_truthy_vacant(row.get('Vacant Flag')),
        owner_occ=_truthy_yes(row.get('Owner Occupied')),
        liens_n=money(row.get('Total Liens')),
        liens_amt=money(row.get('Total Lien Amount')),
        owner=(row.get('Owner 1 Name') or '').strip() or None,
        prop_type=(row.get('Property Type') or '').strip() or None,
        beds=money(row.get('Bedrooms')), baths=money(row.get('Total Baths')),
        sqft=money(row.get('Area SQFT')), lot=money(row.get('Lot Size')),
        po_url=(row.get('Property Details Link') or '').strip() or None,
        appraiser=(row.get('Appraiser Link') or '').strip() or None,
        listing_type=lt,
    )


def load_exports(directory=None):
    """Load newest export per county → list of normalized rows (Upcoming only)."""
    out = []
    for co, date, path in list_export_files(directory):
        with open(path, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                n = normalize_row(row, file_county=co)
                if n: out.append(n)
    return out


def _index_items(items):
    by_case, by_parcel, by_addr = {}, {}, {}
    for it in items:
        x = it['raw']
        c = ncase(x.get('case'))
        if c: by_case.setdefault(c, []).append(it)
        p = digits(x.get('parcel') or '')
        if p:
            by_parcel.setdefault(p.zfill(15), []).append(it)
            by_parcel.setdefault(p.lstrip('0') or '0', []).append(it)
        st = nstreet(x.get('street') or x.get('addr') or '')
        z = nzip(x.get('addr') or '') or ''
        if st: by_addr.setdefault((st, z), []).append(it)
    return by_case, by_parcel, by_addr


def match_export_to_item(row, by_case, by_parcel, by_addr, used):
    """Primary case → parcel → address. Returns (item, how) or (None, None)."""
    def take(cands, how):
        for it in cands:
            if id(it) in used: continue
            return it, how
        return None, None

    if row['case_n'] and row['case_n'] in by_case:
        cands = by_case[row['case_n']]
        # prefer same parcel / street among case matches (MLTI)
        if row['parcel']:
            for it in cands:
                if id(it) in used: continue
                p = digits(it['raw'].get('parcel') or '')
                if p and (p.zfill(15) == row['parcel'] or p.lstrip('0') == row['parcel'].lstrip('0')):
                    return it, 'case+parcel'
        if row['street_n']:
            for it in cands:
                if id(it) in used: continue
                st = nstreet(it['raw'].get('street') or it['raw'].get('addr') or '')
                if st and st == row['street_n']:
                    return it, 'case+address'
        hit, how = take(cands, 'case')
        if hit: return hit, how
    if row['parcel']:
        for key in (row['parcel'], row['parcel'].lstrip('0') or '0'):
            if key in by_parcel:
                hit, how = take(by_parcel[key], 'parcel')
                if hit: return hit, how
    if row['street_n']:
        for z in (row['zip'], ''):
            hit, how = take(by_addr.get((row['street_n'], z), []), 'address')
            if hit: return hit, how
    return None, None


def pov_ok_for_arv(pov, conf, county_val):
    """True when POV may replace ARV: conf >= 70 and within 35% of county value."""
    if not pov or conf is None or conf < POV_CONF_MIN: return False
    if not county_val or county_val <= 0: return False
    return abs(pov / county_val - 1) <= POV_COUNTY_BAND


def apply_fields(it, row, how):
    """Attach export fields onto collected item (does not set ARV — build.py decides)."""
    it['poe'] = dict(
        how=how,
        pov=row['pov'], pov_conf=row['pov_conf'], pov_rent=row['pov_rent'],
        cmv=row['cmv'], clv=row['clv'],
        liens_n=row['liens_n'], liens_amt=row['liens_amt'],
        owner_occ=row['owner_occ'], vacant=row['vacant'],
        prev_sale_type=row['prev_sale_type'],
        po_url=row['po_url'], appraiser=row['appraiser'],
        beds=row['beds'], baths=row['baths'], sqft=row['sqft'], lot=row['lot'],
        owner=row['owner'], prop_type=row['prop_type'],
        case=row['case'], parcel_raw=row['parcel_raw'],
    )


def _po_aid(row):
    raw = '|'.join([row['county'], row['kind'], row['case_n'] or '', row['parcel'] or '', row['date_iso'], row['street_n'] or ''])
    return 'pox' + hashlib.sha1(raw.encode()).hexdigest()[:12]


def po_only_item(row):
    """Build a collect_items()-shaped dict for an unmatched upcoming PO listing (no RealAuction AID)."""
    aid = _po_aid(row)
    host = HOST.get((row['county'], row['kind']))
    date = row['date_ra']
    detail = list_url = None
    if host and date:
        list_url = f'https://{host}/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE={date}'
        detail = list_url  # no AID — clerk calendar for the day
    x = dict(
        county=row['county'], host=host, date=date, aid=aid,
        case=row['case'], parcel=row['parcel'] or row['parcel_raw'] or None,
        plink=row['appraiser'], street=row['street'],
        addr=row['addr'], av=row['cmv'],
        url=list_url, detail=detail,
        owner=row['owner'],
    )
    if row['kind'] == 'TD':
        x['ob'] = None
    else:
        x['fj'] = None; x['pmax'] = None
    it = dict(src=row['kind'], raw=x, known=None, avoid=None, po_only=True)
    apply_fields(it, row, 'po_only')
    return it


def enrich(items, directory=None, today=None):
    """Left-join newest PO exports onto items; append unmatched upcoming as po_only items.

    Returns (items, stats) where stats = {files, rows, matched, added, by_how}.
    Mutates `items` in place (adds it['poe']) and extends with PO-only entries.
    """
    today = today or dt.date.today().isoformat()
    files = list_export_files(directory)
    rows = load_exports(directory)
    by_case, by_parcel, by_addr = _index_items(items)
    used, how_c = set(), {}
    matched = 0
    unmatched = []
    for row in rows:
        if row['date_iso'] < today: continue
        hit, how = match_export_to_item(row, by_case, by_parcel, by_addr, used)
        if hit:
            used.add(id(hit))
            apply_fields(hit, row, how)
            how_c[how] = how_c.get(how, 0) + 1
            matched += 1
        else:
            unmatched.append(row)
    added = 0
    for row in unmatched:
        items.append(po_only_item(row))
        added += 1
        how_c['po_only'] = how_c.get('po_only', 0) + 1
    stats = dict(files=[{'county': c, 'date': d, 'path': p} for c, d, p in files],
                 rows=len(rows), matched=matched, added=added, by_how=how_c)
    return items, stats


def type_from_prop(prop_type, sqft, lot):
    if not prop_type: return None
    l = prop_type.lower()
    if 'single' in l or l == 'sfr': return 'Casa'
    if 'town' in l: return 'Townhouse'
    if 'condo' in l: return 'Condo'
    if 'mobile' in l or 'manufactured' in l: return 'Mobile'
    if 'multi' in l or 'duplex' in l or 'apartment' in l: return 'Multifamily'
    if 'vacant' in l or l == 'land' or 'lot' in l:
        acres = (lot / 43560) if lot else None
        return 'Lote' if acres is None or acres < 1 else 'Terreno'
    if any(k in l for k in ('commercial', 'retail', 'office', 'industrial')): return 'Comercial'
    return 'Outro' if sqft else None


if __name__ == '__main__':
    import collections, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rawdata
    items = [dict(src=k, raw=x, known=None) for k, x in rawdata.collect()]
    items, st = enrich(items)
    print(st)
    print('poe on items', sum(1 for it in items if it.get('poe')), 'po_only', sum(1 for it in items if it.get('po_only')))
    print(collections.Counter(it['src'] for it in items if it.get('po_only')))
