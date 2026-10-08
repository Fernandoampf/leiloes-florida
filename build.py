#!/usr/bin/env python3
"""
CHALLENGE CAPITAL – Leilões Flórida :: dashboard builder
=========================================================
Regenerates  leiloes-florida.html  (single self-contained file, base64 thumbnails embedded)
from the auction scans in /workspace/auc and /workspace/auc/statewide.

Usage
  python3 build.py                 # offline rebuild from data + ./cache (PropertyOnion details / photos)
  python3 build.py --fetch         # also fetch missing PropertyOnion detail pages + photos into ./cache
  python3 build.py --no-images     # no embedded photos (small file)
  python3 build.py --data-date 2026-10-15 --budget 150000
  python3 build.py --site           # GitHub Pages: writes index.html + manifest.webmanifest + icons/ + robots.txt
                                   # index.html is password-protected with StaticCrypt (password read from
                                   # --password-file, kept OUTSIDE the repo); plaintext goes to .plain/ (git-ignored)

Weekly refresh: re-run the statewide scan scripts in /workspace/auc/statewide (cal.py, fetch.py, po.py,
score.py) so td_scored.json / fc_*.json are current, then:  python3 build.py --fetch --data-date YYYY-MM-DD

Nothing is invented: every number comes from RealAuction (county clerk auction sites), PropertyOnion or the
county Property Appraiser data already in the scan files; missing values are shown as '—'. Repairs are an
explicit, labelled estimate (age x size rule below).
"""
import argparse, ast, base64, csv, datetime as dt, gzip, io, json, math, os, re, sys, time, html

HERE = os.path.dirname(os.path.abspath(__file__))
AUC = '/workspace/auc'
SW = os.path.join(AUC, 'statewide')
CACHE = os.path.join(HERE, 'cache')
ORLANDO = (28.5383, -81.3792)

# ----------------------------------------------------------------------------- parameters (shown in the HTML)
# Max bid = highest bid that still yields the minimum return (default 10%) after all costs.
# These are the defaults of the editable "Premissas" panel in the HTML (the page recomputes everything client-side).
P = dict(
    ret=10.0,               # minimum target return on cash invested (%)  -> "lance máx." / floor bid
    flip=18.0,              # ROI at the reference bid needed for verdict FLIP (BidToFlip-style 'below 18%')
    budget=150000,          # all-in budget (US$): bid + purchase costs + fees + repairs + holding
    clerk=1.5,              # clerk / title / recording fees on purchase (% of bid)
    docb=0.70,              # FL documentary stamp tax on the certificate/deed (% of bid)
    fee=200,                # auction site / flat fees (US$)
    qt=2500,                # quiet title (US$, tax deeds only)
    qtm=3,                  # extra months for tax deeds (quiet title before resale)
    ev=2500,                # eviction / cash-for-keys estimate (US$) when owner-occupied or tenant likely
    evm=2,                  # extra months when eviction likely
    months=6,               # base months until resale
    hold=2.5,               # holding: property tax, insurance, utilities (% of resale value per year)
    list=2.5, buyc=2.5, title=1.5, docs=0.70,   # sell side (% of resale): listing, buyer agent, title/escrow, doc stamps
    yld=9.0,                # gross yield (rent x 12 / value) considered 'aluguel forte' (%)
    rebuild=175, depr=1.0,  # replacement cost: US$/sqft, depreciation %/year of age (max 60%)
    refi=7.0, ltv=75, tax=1.8, ins=1.5, vac=10, mgmt=8,   # BRRRR: refi rate %, LTV %, tax %/yr, insurance %/yr, vacancy+maint % rent, mgmt % rent
    min_value=10000,        # junk filter
)

def bid_calc(val, repairs, is_td, ref=None):
    """Return-based max bid. Same formula as calc() in template.html (keep in sync).
    invested = bid*(1+buy) + fees + quiet title + repairs + holding ; profit = val*(1-sell) - invested ; return = profit/invested"""
    c = (P['clerk'] + P['docb']) / 100
    months = P['months'] + (P['qtm'] if is_td else 0)
    K = P['fee'] + (P['qt'] if is_td else 0) + repairs + val * P['hold'] / 100 / 12 * months
    sell = (P['list'] + P['buyc'] + P['title'] + P['docs']) / 100
    mb = (val * (1 - sell) / (1 + P['ret'] / 100) - K) / (1 + c)
    cap = (P['budget'] - K) / (1 + c)
    return mb, cap
# repair estimate US$/sqft by year built (when no better info). Mobile homes use their own rate.
REPAIR_RATES = [(2010, 8), (2000, 15), (1990, 20), (1975, 25), (1960, 30), (0, 35)]
REPAIR_UNKNOWN_YEAR = 30
REPAIR_MOBILE = 20
REPAIR_MIN = 8000
DEFAULT_SQFT = 1300

# Bad foreclosures identified in the earlier review (junior lien / HOA foreclosure – senior mortgage survives,
# or judgment far above budget). Shown with red EVITAR flag and score capped.
AVOID = {
    '15531 CITRUS HARVEST': 'Revisão anterior: excluído – lance/julgamento ~US$193k (acima do orçamento) e risco de hipoteca sênior.',
    '897 TARAMUNDI': 'Revisão anterior: execução de valor baixo (provável HOA/2ª hipoteca) – hipoteca sênior sobrevive.',
    '2294 ALOHA BAY': 'Revisão anterior: execução de hipoteca júnior – 1ª hipoteca (~US$184k, 2019) sobrevive ao leilão.',
    '81 JAKE CT': 'Revisão anterior: execução de hipoteca júnior (Capital One) – 1ª hipoteca (~US$298k, 2019) sobrevive.',
}

COUNTY_NAMES = {'palmbeach': 'Palm Beach', 'miamidade': 'Miami-Dade', 'stlucie': 'St. Lucie', 'stjohns': 'St. Johns',
                'indianriver': 'Indian River', 'santarosa': 'Santa Rosa', 'myorangeclerk': 'Orange', 'desoto': 'DeSoto'}
# approximate county centres (used only when the property has no coordinates; distance then marked "~")
COUNTY_LL = {
 'alachua': (29.67, -82.36), 'baker': (30.33, -82.28), 'bay': (30.24, -85.63), 'bradford': (29.95, -82.17),
 'brevard': (28.26, -80.73), 'broward': (26.15, -80.45), 'calhoun': (30.41, -85.20), 'charlotte': (26.90, -81.94),
 'citrus': (28.85, -82.52), 'clay': (29.98, -81.86), 'collier': (26.11, -81.40), 'columbia': (30.22, -82.62),
 'desoto': (27.19, -81.81), 'dixie': (29.58, -83.19), 'duval': (30.33, -81.66), 'escambia': (30.61, -87.34),
 'flagler': (29.47, -81.28), 'franklin': (29.81, -84.80), 'gadsden': (30.58, -84.61), 'gilchrist': (29.72, -82.80),
 'glades': (26.95, -81.19), 'gulf': (29.90, -85.24), 'hamilton': (30.49, -82.95), 'hardee': (27.49, -81.81),
 'hendry': (26.55, -81.17), 'hernando': (28.55, -82.43), 'highlands': (27.34, -81.34), 'hillsborough': (27.90, -82.35),
 'holmes': (30.87, -85.81), 'indianriver': (27.70, -80.57), 'jackson': (30.80, -85.21), 'jefferson': (30.42, -83.89),
 'lafayette': (29.99, -83.18), 'lake': (28.76, -81.71), 'lee': (26.56, -81.85), 'leon': (30.46, -84.28),
 'levy': (29.28, -82.78), 'liberty': (30.24, -84.88), 'madison': (30.45, -83.47), 'manatee': (27.47, -82.32),
 'marion': (29.21, -82.06), 'martin': (27.08, -80.40), 'miamidade': (25.61, -80.50), 'monroe': (24.70, -81.20),
 'nassau': (30.61, -81.77), 'okaloosa': (30.66, -86.59), 'okeechobee': (27.39, -80.89), 'orange': (28.51, -81.32),
 'osceola': (28.06, -81.15), 'palmbeach': (26.65, -80.45), 'pasco': (28.30, -82.44), 'pinellas': (27.90, -82.74),
 'polk': (27.95, -81.70), 'putnam': (29.61, -81.74), 'santarosa': (30.69, -86.98), 'sarasota': (27.18, -82.37),
 'seminole': (28.71, -81.24), 'stjohns': (29.91, -81.41), 'stlucie': (27.38, -80.44), 'sumter': (28.70, -82.08),
 'suwannee': (30.19, -82.99), 'taylor': (30.02, -83.62), 'union': (30.04, -82.37), 'volusia': (29.06, -81.16),
 'wakulla': (30.15, -84.38), 'walton': (30.63, -86.18), 'washington': (30.61, -85.67)}

JUNK_RE = re.compile(r'RETENTION|DETENTION|DRAINAGE|STORM ?WATER|\bPOND\b|COMMON AREA|COMMON ELEMENT|LIFT STATION|'
                     r'CONSERVATION|\bBUFFER\b|INGRESS|EGRESS|\bEASEMENT\b|OPEN SPACE|LANDSCAPE', re.I)
HOA_RE = re.compile(r'HOMEOWNER|HOME OWNERS|CONDOMINIUM|PROPERTY OWNERS|COMMUNITY ASSOC|OWNERS ASSOC|MASTER ASSOC|'
                    r'\bHOA\b|\bPOA\b|\bCOA\b|COMMUNITY DEVELOPMENT|CLUB ASSOC|VILLAS? ASSOC|ESTATES ASSOC', re.I)
DECEASED_RE = re.compile(r'(?<!REAL )\bESTATE\b(?! (LLC|INC|HOLD|GROUP|INVEST|TRUST|PARTNER|CORP|CO\b))|\bEST OF\b|\bHEIRS?\b|DECEASED|\bDEC\'?D\b', re.I)
CODE_RE = re.compile(r'CODE ENFORCEMENT|\bCITY OF\b|\bTOWN OF\b|\bVILLAGE OF\b', re.I)

# ----------------------------------------------------------------------------- helpers
def jload(p, default=None):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return default

def num(v):
    """Number or None. PropertyOnion uses -2147483648 / 0 for 'unknown'."""
    try:
        if isinstance(v, str): v = v.replace('$', '').replace(',', '').strip()
        v = float(v)
        if v != v or v <= 0 or v > 1e9: return None
        return v
    except Exception: return None

def dictval(v):
    if isinstance(v, dict): return v.get('value')
    return v

def hav(a, b):
    R = 3958.8
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def iso(mdY):
    m, d, y = mdY.split('/'); return f'{y}-{m}-{d}'

def county_name(slug):
    return COUNTY_NAMES.get(slug, slug.replace('-', ' ').title())

def norm_street(s):
    s = (s or '').upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s); return re.sub(r'\s+', ' ', s).strip()

# ----------------------------------------------------------------------------- PropertyOnion fetch (optional)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
EXTRA = ['id','seo_url','images','prop_cntypicurl','prop_thumbnail','googlestreet_pic','prop_appraiserlink',
 'usps_vacancy','vacantFlag','homesteadInd','ownerOccupied','landUseCode','mobileHomeInd','lbcs_structure_desc',
 'lbcs_function_desc','lbcs_activity_desc','lbcs_site_desc','propertyClassID','countyLandUseCode','bedrooms','bathTotalCalc','sumLivingAreaSqFt',
 'yearBuilt','effectiveYearBuilt','lotSizeAcres','lotSizeSqFt','zoning','marketTotalValue','marketValueLand','marketValueImprovement','currentAVMValue','vlowValue','vhighValue',
 'vconfidenceScore','estimatedRentalValue','mtg1LoanAmt','mtg1Lender','mtg1RecordingDate','mtg2LoanAmt','mtg2Lender','mtg2RecordingDate',
 'totalOpenLienNbr','totalOpenLienAmt','currentSalesPrice','currentSaleRecordingDate','ownerNAME1FULL','ownerNAME2FULL',
 'mailingFullStreetAddress','mailingCity','mailingState','situsFullStreetAddress','situsCity','situsZIP5','situsLatitude','situsLongitude',
 'fema_flood_zone','legalDescription','subdivisionName','buildingConditionCode','poolCode','apn','taxDeliquentYear']
AUC_KEYS = ['auction_date','auction_status','listing_type','auction_openingbid','auction_fj','auction_caseno','auction_url',
 'auction_plaintiffs','auction_defend','ownerOccupied']
_S = None
def session():
    global _S
    if _S is None:
        import requests
        _S = requests.Session(); _S.headers['User-Agent'] = UA
    return _S

def po_full(pid, slug, fetch=False):
    p = os.path.join(CACHE, 'po_full', f'p_{pid}.json')
    d = jload(p)
    if d is not None or not fetch: return d
    try:
        h = session().get(f'https://propertyonion.com/property_search/properties/{slug}/{pid}', timeout=45).text
        m = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>', h, re.S)
        if not m: return None          # transient – not cached, retried next run
        pl = (json.loads(m.group(1)).get(f'property-detail-{pid}') or {}).get('payload') or {}
        d = {k: pl.get(k) for k in EXTRA}
        d['auctions'] = [{k: a.get(k) for k in AUC_KEYS} for a in (pl.get('auctionDetails') or [])]
        d['fetched'] = time.strftime('%Y-%m-%d')
        json.dump(d, open(p, 'w')); time.sleep(0.2)
        return d
    except Exception:
        return None

def po_search(street, zips, fetch=False):
    q = re.sub(r'\s+3\d{4}$', '', street.strip()); q = re.sub(r'\s+(UNIT|APT|#|LT|LOT)\b.*$', '', q, flags=re.I).strip()
    if not q or not re.match(r'^\d', q): return None, None
    name = 's_' + re.sub(r'\W', '_', q) + '.json'
    res = jload(os.path.join(CACHE, 'search', name))
    if res is None: res = jload(os.path.join(SW, 'po', name))
    if res is None and fetch:
        try:
            res = session().get('https://propertyonion.com/api/search/api/search-by-keywords', params={'keyword': q}, timeout=30).json()
            json.dump(res, open(os.path.join(CACHE, 'search', name), 'w'))
        except Exception: res = None
    cands = [r['value'] for r in (res or []) if r.get('type') == 'Address']
    for c in cands:
        if zips and c.get('situsZIP5') == zips[-1]:
            return c.get('propertyId') or c.get('id'), c.get('seoUrl') or c.get('seo_url')
    if len(cands) == 1:
        c = cands[0]; return c.get('propertyId') or c.get('id'), c.get('seoUrl') or c.get('seo_url')
    return None, None

def thumb(pid, url, fetch=False, width=400, height=300, quality=60):
    p = os.path.join(CACHE, 'img', f'{pid}.jpg')
    if os.path.exists(p): return p if os.path.getsize(p) > 0 else None
    if not fetch or not url: return None
    try:
        from PIL import Image
        r = session().get(url, timeout=40)
        if r.status_code != 200 or len(r.content) < 500: raise Exception('http %s' % r.status_code)
        im = Image.open(io.BytesIO(r.content)).convert('RGB')
        w, h = im.size; tr = width / height
        if w / h > tr: nw = int(h * tr); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else: nh = int(w / tr); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        im = im.resize((width, height), Image.LANCZOS)
        im.save(p, 'JPEG', quality=quality, optimize=True, progressive=True)
        return p
    except Exception:
        open(p, 'wb').close(); return None   # negative cache; delete empty file to retry

# ----------------------------------------------------------------------------- calendar (auction time)
def load_calendar():
    cal = jload(os.path.join(SW, 'calendars.json'), {})
    out = {}
    for host, days in cal.items():
        for d, txt in days:
            for kind, active, total, tm, tz in re.findall(r'(Foreclosure|Tax Deed)\s+(\d+)\s*/\s*(\d+)\s*(?:FC|TD)\s+(\d{1,2}:\d{2} [AP]M) (ET|CT)', txt):
                out[(host, d, 'FC' if kind == 'Foreclosure' else 'TD')] = dict(active=int(active), total=int(total), time=tm, tz=tz)
    return out

def et_time(c):
    if not c: return None
    t = dt.datetime.strptime(c['time'], '%I:%M %p')
    if c['tz'] == 'CT':
        t2 = t + dt.timedelta(hours=1)
        return f"{t2.strftime('%H:%M')} ET ({t.strftime('%H:%M')} CT)"
    return f"{t.strftime('%H:%M')} ET"

# ----------------------------------------------------------------------------- raw item collection
def collect(args):
    items = []
    td = jload(os.path.join(SW, 'td_scored.json'), [])
    ocpa = jload(os.path.join(SW, 'ocpa_td.json'), {})
    orange_en = jload(os.path.join(AUC, 'orange_enriched.json'), {})
    lake_en = jload(os.path.join(AUC, 'lake_enriched.json'), {})
    stats = dict(td_total=len(td), td_noval=0, td_lowval=0)
    for x in td:
        po = x.get('po') or {}
        if 'err' in po or 'nomatch' in po: po = {}
        items.append(dict(src='TD', raw=x, po=po, ocpa=ocpa.get(x['aid']) or orange_en.get(x['aid']), lake=lake_en.get(x['aid'])))
    fc_all = jload(os.path.join(SW, 'fc_all.json'), [])
    fc_cand = {y['aid'] for y in jload(os.path.join(SW, 'fc_cand2.json'), [])}
    fc_po = jload(os.path.join(SW, 'fc_po.json'), {})
    stats['fc_total'] = len(fc_all); stats['fc_cand'] = len(fc_cand)
    for x in fc_all:
        a = x['addr'].upper()
        avoid = next((k for k in AVOID if k in a), None)
        if x['aid'] not in fc_cand and not avoid: continue
        po = fc_po.get(x['aid']) or {}
        if 'err' in po or 'nomatch' in po or not po.get('id'): po = {}
        items.append(dict(src='FC', raw=x, po=po, avoid=avoid))
    return items, stats

# ----------------------------------------------------------------------------- per-item enrichment & scoring
def classify(it, full, po):
    lu = dictval((full or {}).get('landUseCode'))
    sqft = num((full or po).get('sumLivingAreaSqFt'))
    if lu:
        m = {'Single Family': 'Casa', 'Townhouse': 'Townhouse', 'Condominium': 'Condo', 'Mobile': 'Mobile',
             'Multifamily': 'Multifamiliar', 'Land': 'Lote'}.get(lu)
        if m == 'Lote' and sqft:   # PO says land but has living area – unclear
            return 'Condo' if re.search(r'#|\bUNIT\b|\bAPT\b', it['raw'].get('addr', '').upper()) else 'Indefinido'
        if m: return m
        return 'Outro'
    o = it.get('ocpa')
    if o and o.get('dor'):
        d = o['dor'][:2]
        return {'00': 'Lote', '01': 'Casa', '02': 'Mobile', '04': 'Condo', '08': 'Multifamiliar', '03': 'Multifamiliar'}.get(d, 'Outro')
    lk = it.get('lake')
    if lk and isinstance(lk.get('land'), str):
        if 'VACANT' in lk['land'].upper(): return 'Lote'
    pc = (po or {}).get('propertyClassID')
    if pc == 'V': return 'Lote'
    if pc in ('C', 'I', 'O', 'E', 'F', 'A'): return 'Outro'
    if sqft: return 'Casa'
    addr = it['raw'].get('addr', '').upper()
    if re.search(r'#|\bUNIT\b|\bAPT\b', addr): return 'Condo'
    return 'Indefinido'

def repairs_for(cat, sqft, yr):
    if cat == 'Lote': return 0, 'lote – sem obra (limpeza/levantamento não incluídos)'
    s = sqft or DEFAULT_SQFT
    if cat == 'Mobile': rate = REPAIR_MOBILE
    elif yr: rate = next(r for y, r in REPAIR_RATES if yr >= y)
    else: rate = REPAIR_UNKNOWN_YEAR
    est = max(REPAIR_MIN, round(s * rate / 500) * 500)
    why = f"US${rate}/sqft × {int(s):,} sqft" + ('' if sqft else ' (área desconhecida: 1.300 sqft assumidos)') + ('' if yr or cat == 'Mobile' else ' (ano desconhecido)')
    return est, why

def build_items(args):
    cal = load_calendar()
    items, stats = collect(args)
    picks = {x['aid'] for x in jload(os.path.join(SW, 'final_picks_raw.json'), [])}
    today = args.data_date
    out, dropped = [], {}
    def drop(reason): dropped[reason] = dropped.get(reason, 0) + 1
    seen = set()
    for it in items:
        x, po = it['raw'], it['po']
        src = it['src']
        if x['aid'] in seen: continue
        seen.add(x['aid'])
        d_iso = iso(x['date'])
        if d_iso < today: drop('leilão já passou'); continue
        c = cal.get((x['host'], x['date'], src))
        if d_iso == today and c and c['active'] == 0: drop('leilão de hoje já encerrado'); continue
        if not x.get('addr', '').strip(): drop('sem endereço (timeshare / múltiplas parcelas)'); continue
        # PropertyOnion detail (cached) – also try search match for FC items without match
        pid, slug = po.get('id'), po.get('seo_url')
        if not pid and x.get('street'):
            pid, slug = po_search(x['street'], re.findall(r'\b(3\d{4})\b', x['addr']), fetch=args.fetch)
        full = po_full(pid, slug, fetch=args.fetch) if pid else None
        if full and full.get('err'): full = None
        P0 = full or po or {}
        has_po = bool(pid and (full or po))
        av = num(x.get('av'))
        mkt = num(P0.get('marketTotalValue'))
        o = it.get('ocpa')
        ocpa_mkt = None
        if o and o.get('vals'):
            ocpa_mkt = num(o['vals'][0].get('marketValue'))
        lk = it.get('lake'); lake_mv = num(lk.get('mv')) if lk else None
        avm = num(P0.get('currentAVMValue'))
        cat = classify(it, full, po)
        best = max([v for v in [av, mkt, ocpa_mkt, lake_mv, avm] if v] or [0])
        if best == 0: drop('sem nenhum valor (avaliação/mercado/AVM)'); continue
        if best < P['min_value']: drop('valor < US$10 mil'); continue
        if cat == 'Outro': drop('comercial/industrial/outro (fora do foco casa/lote)'); continue
        legal = (P0.get('legalDescription') or x.get('legal') or '')
        lbcs = ' '.join(str(P0.get(k) or '') for k in ('lbcs_site_desc', 'lbcs_function_desc'))
        if JUNK_RE.search(legal + ' ' + lbcs) and cat in ('Lote', 'Indefinido'): drop('lixo: retenção/drenagem/área comum/faixa'); continue
        acres = num(P0.get('lotSizeAcres'))
        if acres is None and num(P0.get('lotSizeSqFt')): acres = num(P0.get('lotSizeSqFt')) / 43560
        if cat == 'Lote' and acres is not None and acres < 0.05: drop('lixo: lote-faixa (< 0,05 acre)'); continue
        sqft = num(P0.get('sumLivingAreaSqFt')); yr = num(P0.get('yearBuilt'))
        if yr and yr < 1800: yr = None
        beds = num(P0.get('bedrooms')); baths = num(P0.get('bathTotalCalc'))
        if cat == 'Lote': beds = baths = sqft = yr = None
        # ---- value used for resale (conservative)
        mvals = [v for v in [av, mkt, ocpa_mkt, lake_mv] if v]
        base = max(mvals) if mvals else None
        if cat == 'Lote':
            val = base or avm; vsrc = 'maior entre avaliação do condado e valor de mercado' if base else 'AVM'
        elif base and avm:
            val = min(base, avm); vsrc = 'menor entre (valor de mercado/avaliação) e AVM'
        else:
            val = base or avm; vsrc = 'somente avaliação do condado' if (base and not mkt and not ocpa_mkt) else ('somente AVM' if not base else 'valor de mercado (sem AVM)')
        ref = num(x.get('ob')) if src == 'TD' else num(x.get('fj'))
        repairs, rwhy = repairs_for(cat, sqft, yr)
        mb, cap = bid_calc(val, repairs, src == 'TD')
        sugg = max(0.0, min(mb, cap))
        capped = mb > cap
        fits = ref is not None and sugg >= ref and sugg > 0
        # ---- location / distance
        lat, lon = num(P0.get('situsLatitude')), P0.get('situsLongitude')
        try: lon = float(lon) if lon is not None else None
        except Exception: lon = None
        if lat and lon and 24 < lat < 31.2 and -88 < lon < -79.8:
            dist = hav(ORLANDO, (lat, lon)); dapprox = False
        else:
            lat = lon = None
            cc = COUNTY_LL.get(x['county'].replace('myorangeclerk', 'orange'))
            dist = hav(ORLANDO, cc) if cc else None; dapprox = True
        # ---- auctions in PO for same date
        same = [a for a in (P0.get('auctions') or []) if (a.get('auction_date') or '').startswith(d_iso)]
        plaint = ' '.join(str(a.get('auction_plaintiffs') or '') for a in same)
        defend = ' '.join(str(a.get('auction_defend') or '') for a in same)
        status = [a.get('auction_status') for a in same]
        # ---- flags
        flags, notes = [], []
        occ_v = str(dictval(P0.get('ownerOccupied')) or '').lower()
        owner = (P0.get('ownerNAME1FULL') or (o or {}).get('owner') or (lk or {}).get('owner') or x.get('owner') or '').strip()
        owner2 = P0.get('ownerNAME2FULL') or ''
        mail = norm_street(P0.get('mailingFullStreetAddress')); situs = norm_street(P0.get('situsFullStreetAddress'))
        occupied = occ_v in ('yes', 'owner occupied') or P0.get('homesteadInd') is True or (bool(mail) and mail == situs)
        absentee = occ_v == 'absentee' or (bool(mail) and bool(situs) and mail != situs)
        if cat == 'Lote': occupied = False; absentee = False
        if occupied: flags.append('occ'); notes.append('Dono mora no imóvel: possível despejo (eviction) após a compra.')
        if DECEASED_RE.search(owner + ' ' + owner2) or (src == 'FC' and re.search(r'DECEASED|ESTATE OF|UNKNOWN HEIRS', defend, re.I)):
            flags.append('dec'); notes.append('Dono falecido/espólio: herdeiros podem contestar; checar título.')
        usps_vac = P0.get('usps_vacancy') == 'Y' or str(dictval(P0.get('vacantFlag')) or '').upper() in ('Y', 'YES')
        if absentee and not occupied and cat != 'Lote' and not usps_vac:
            flags.append('ten'); notes.append('Dono não reside (correspondência em outro endereço): inquilino provável.')
        if src == 'FC' and CODE_RE.search(defend):
            flags.append('code'); notes.append('Município é réu na ação: possível multa/lien de code enforcement.')
        mtg_surv = False
        if src == 'FC':
            m1 = num(P0.get('mtg1LoanAmt')); m1d = (P0.get('mtg1RecordingDate') or '')[:4]
            hoa_pl = bool(HOA_RE.search(plaint))
            if it.get('avoid'): mtg_surv = True
            elif hoa_pl and (m1 or 0) > 0: mtg_surv = True
            elif m1 and ref and m1d and m1d >= '2012' and m1 > 1.3 * ref:
                lender_tok = set(re.findall(r'[A-Z]{4,}', (P0.get('mtg1Lender') or '').upper())) - {'BANK', 'MORTGAGE', 'NATIONAL', 'ASSOCIATION', 'TRUST', 'FINANCIAL', 'LOAN', 'CORP', 'CORPORATION', 'COMPANY', 'SERVICES', 'HOME', 'FUNDING'}
                if not (lender_tok & set(re.findall(r'[A-Z]{4,}', plaint.upper()))): mtg_surv = True
            if mtg_surv:
                flags.append('mtg'); notes.append(f"Hipoteca sênior pode sobreviver (1ª hipoteca {('US$' + format(int(m1), ',')) if m1 else '?'} {m1d} > julgamento): confirmar no processo.")
            if hoa_pl: flags.append('hoa'); notes.append('Autor da execução é associação (HOA/condomínio).')
        if 'hoa' not in flags and cat == 'Condo':
            flags.append('hoa'); notes.append('Condomínio/HOA: taxas mensais e possíveis débitos de associação.')
        fz = (P0.get('fema_flood_zone') or '').upper().strip()
        if fz and re.match(r'^(A|V)', fz): flags.append('flood'); notes.append(f'Zona de enchente FEMA {fz}: seguro obrigatório se financiado.')
        if occupied and ref and val and ref < (0.10 if src == 'TD' else 0.25) * val:
            flags.append('red'); notes.append('Dívida pequena vs. valor e dono no imóvel: alta chance de resgate/cancelamento antes do leilão.')
        unverified = not has_po or not (avm or mkt or ocpa_mkt)
        if unverified: flags.append('unv'); notes.append('Dados não verificados (sem registro PropertyOnion ou valor só da avaliação do condado).')
        if any(s and s.lower().startswith('cancel') for s in status):
            flags.append('cxl'); notes.append('PropertyOnion marca este leilão como cancelado – confirmar no site do leilão.')
        if usps_vac and cat != 'Lote': flags.append('vac')
        if it.get('avoid'): flags.insert(0, 'avoid'); notes.insert(0, AVOID[it['avoid']])
        if x['aid'] in picks: flags.append('pick')
        if src == 'TD':
            notes.append('Tax deed: hipotecas são extintas, mas o título normalmente exige quiet title (~US$2–3k, incluído nos custos).' if cat != 'Lote' else 'Tax deed de lote: verifique zoneamento, acesso e se é edificável.')
        else:
            notes.append('Foreclosure: lance de abertura não publicado – o banco costuma dar lance até o valor do julgamento.')
        # ---- score
        margin = (mb - ref) / val if (ref is not None and val) else 0
        equity = (mb - ref) if ref is not None else 0
        s_spread = 3.0 * min(1.0, max(0.0, margin) / 0.45) + 1.5 * min(1.0, max(0.0, equity) / 60000)
        s_budget = 0.0 if not fits else (2.0 if not capped else (1.0 if mb <= 1.5 * cap else 0.5))
        # (the 'imóvel caro p/ o orçamento' note is rendered by the page, since it depends on the editable premissas)
        if d_iso == today:
            notes.insert(0, 'Leilão HOJE – provavelmente já encerrado; confirme no site.')
        if dist is None: s_prox = 0
        else: s_prox = 1.5 if dist <= 25 else 1.2 if dist <= 50 else 0.9 if dist <= 75 else 0.6 if dist <= 100 else 0.3 if dist <= 150 else 0.0
        conf = 0.0
        if has_po: conf += 0.5
        if avm or (cat == 'Lote' and (mkt or ocpa_mkt)): conf += 0.5
        if (cat == 'Lote' and acres) or (cat != 'Lote' and sqft and yr): conf += 0.5
        two = [v for v in [base, avm] if v] if cat != 'Lote' else [v for v in [av, mkt or ocpa_mkt or lake_mv] if v]
        if len(two) == 2 and max(two) / min(two) <= 1.35: conf += 0.5
        PEN = dict(occ=1.0, dec=0.75, ten=0.5, code=1.0, mtg=4.0, hoa=0.5, flood=0.5, red=1.0, unv=1.5, cxl=2.0)
        pen = sum(PEN.get(f, 0) for f in flags)
        score = max(0.0, min(10.0, s_spread + s_budget + s_prox + conf - pen))
        if 'avoid' in flags or 'mtg' in flags: score = min(score, 1.5 if 'avoid' not in flags else 1.0)
        # ---- links / photo
        po_url = f'https://propertyonion.com/property_search/properties/{slug}/{pid}' if (pid and slug) else None
        pa = (full or {}).get('prop_appraiserlink') or x.get('plink')
        if pa and ('key=&' in pa or pa.endswith('/parcel/') or 'MULTIPLE' in pa): pa = None
        img = None
        if not args.no_images and pid:
            imgs = (full or {}).get('images') or []
            url = imgs[0] if imgs else None
            pth = thumb(pid, url, fetch=args.fetch)
            if pth:
                img = 'data:image/jpeg;base64,' + base64.b64encode(open(pth, 'rb').read()).decode()
            elif url:
                img = url   # remote fallback
        addr = re.sub(r',\s*FL-?\s*', ', FL ', x['addr']).replace(' ,', ',').strip()
        # ---- extra intel (only real fields; None when missing)
        def plist(sv):
            try:
                v = ast.literal_eval(sv) if sv.strip().startswith('[') else [sv]
                return ', '.join(str(i).strip() for i in v if str(i).strip())
            except Exception: return sv.strip()
        plaintiff = ' | '.join(plist(str(a.get('auction_plaintiffs'))) for a in same if a.get('auction_plaintiffs')) or None
        hist = sorted([dict(d=(a.get('auction_date') or '')[:10], t=a.get('listing_type'), s=a.get('auction_status'),
                            b=num(a.get('auction_openingbid')) or num(a.get('auction_fj')))
                       for a in (P0.get('auctions') or []) if (a.get('auction_date') or '')[:10] and not (a.get('auction_date') or '').startswith(d_iso)],
                      key=lambda h: h['d'], reverse=True)
        zip5 = str(P0.get('situsZIP5') or '') or (re.findall(r'\b(3\d{4})\b', x['addr']) or [''])[-1] or None
        city = dictval(P0.get('situsCity'))
        tdy = num(P0.get('taxDeliquentYear')); tdy = int(tdy) if tdy and 1990 < tdy <= int(today[:4]) else None
        lsp = num(P0.get('currentSalesPrice')); lsd = (P0.get('currentSaleRecordingDate') or '')[:10] or None
        hoa_pl = bool(src == 'FC' and HOA_RE.search(plaint))
        cond = dictval(P0.get('buildingConditionCode')); pool = dictval(P0.get('poolCode'))
        rec = dict(
            id=x['aid'], t=src, cat=cat, co=county_name(x['county']), cs=x['county'].replace('myorangeclerk', 'orange'),
            date=d_iso, time=et_time(c), addr=addr, owner=owner or None, case=x.get('case'), parcel=x.get('parcel'),
            ref=ref, av=av, mkt=mkt or ocpa_mkt or lake_mv, avm=avm, avmLo=num(P0.get('vlowValue')), avmHi=num(P0.get('vhighValue')),
            rent=num(P0.get('estimatedRentalValue')), val=round(val), vsrc=vsrc,
            beds=beds, baths=baths, sqft=sqft, yr=int(yr) if yr else None, ac=round(acres, 3) if acres else None,
            zon=P0.get('zoning') or None, fz=fz or None, lat=lat, lon=lon,
            dist=round(dist) if dist is not None else None, dap=dapprox,
            rep=repairs, repw=rwhy, mb=round(mb), sug=round(sugg), cap=capped, fits=fits,
            sc=round(score, 1), sp=round(margin * 100) if ref is not None else None,
            eq=round(equity) if ref is not None else None, parts=dict(spread=round(s_spread, 2), budget=s_budget, prox=s_prox, conf=conf, pen=-pen),
            fl=flags, note=' '.join(notes[:4]), links=dict(auc=x.get('detail'), po=po_url, pa=pa), img=img,
            zip=zip5, city=str(city).title() if city else None, plaint=plaintiff, hist=hist[:8], tdy=tdy, lsp=lsp, lsd=lsd,
            m1=num(P0.get('mtg1LoanAmt')), m1d=(P0.get('mtg1RecordingDate') or '')[:10] or None, m1l=P0.get('mtg1Lender') or None,
            m2=num(P0.get('mtg2LoanAmt')), m2d=(P0.get('mtg2RecordingDate') or '')[:10] or None,
            olA=num(P0.get('totalOpenLienAmt')), olN=num(P0.get('totalOpenLienNbr')), hoaPl=hoa_pl,
            cond=cond, pool=pool, eyb=int(num(P0.get('effectiveYearBuilt'))) if num(P0.get('effectiveYearBuilt')) and num(P0.get('effectiveYearBuilt')) > 1800 else None,
            pa_only=(vsrc == 'somente AVM'), hasPO=has_po, ap=P0.get('apn') or None,
        )
        out.append(rec)
    return out, stats, dropped

# ----------------------------------------------------------------------------- ZIP market data (free public bulk files)
MKT = os.path.join(CACHE, 'market')
REDFIN_URL = 'https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz'
ZHVI_URL = 'https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv'

def fetch_market():
    """Download Redfin Data Center ZIP tracker (~1.5 GB gz, streamed, FL rows kept) and Zillow ZHVI by ZIP."""
    import requests
    os.makedirs(MKT, exist_ok=True)
    with requests.get(REDFIN_URL, stream=True, timeout=120) as r, open(os.path.join(MKT, 'redfin_zip_fl.tsv'), 'w') as out:
        r.raise_for_status(); first = True
        for line in io.TextIOWrapper(gzip.GzipFile(fileobj=r.raw), encoding='utf-8'):
            if first or ('\tFL\t' in line or '\t"FL"\t' in line) and 'All Residential' in line: out.write(line)
            first = False
    with requests.get(ZHVI_URL, timeout=120) as r:
        open(os.path.join(MKT, 'zillow_zhvi_zip.csv'), 'wb').write(r.content)

def _f(v):
    try:
        v = float(str(v).replace('"', '')); return None if v != v else v
    except Exception: return None

def load_market():
    """Compact FL ZIP market dict {zip: {rf:{...}, zh:{...}}} (cached in cache/market/market_fl.json)."""
    comp = os.path.join(MKT, 'market_fl.json')
    rf_raw, zh_raw = os.path.join(MKT, 'redfin_zip_fl.tsv'), os.path.join(MKT, 'zillow_zhvi_zip.csv')
    raws = [p for p in (rf_raw, zh_raw) if os.path.exists(p)]
    if os.path.exists(comp) and all(os.path.getmtime(comp) >= os.path.getmtime(p) for p in raws):
        return jload(comp, {})
    out, src = {}, {}
    if os.path.exists(rf_raw):
        series = {}
        with open(rf_raw, encoding='utf-8') as f:
            rd = csv.reader(f, delimiter='\t'); h = [c.strip('"').upper() for c in next(rd)]; ix = {k: i for i, k in enumerate(h)}
            for row in rd:
                g = lambda k: row[ix[k]].strip('"') if k in ix and ix[k] < len(row) else ''
                if g('PERIOD_DURATION') != '90' or g('PROPERTY_TYPE') != 'All Residential' or g('IS_SEASONALLY_ADJUSTED').lower() == 'true': continue
                z = re.sub(r'\D', '', g('REGION'))[-5:]
                if len(z) != 5: continue
                series.setdefault(z, []).append(dict(end=g('PERIOD_END'), price=_f(g('MEDIAN_SALE_PRICE')), price_yoy=_f(g('MEDIAN_SALE_PRICE_YOY')),
                    ppsf=_f(g('MEDIAN_PPSF')), ppsf_yoy=_f(g('MEDIAN_PPSF_YOY')), sold=_f(g('HOMES_SOLD')), sold_yoy=_f(g('HOMES_SOLD_YOY')),
                    dom=_f(g('MEDIAN_DOM')), dom_yoy=_f(g('MEDIAN_DOM_YOY')), stl=_f(g('AVG_SALE_TO_LIST')), above=_f(g('SOLD_ABOVE_LIST')),
                    off2w=_f(g('OFF_MARKET_IN_TWO_WEEKS')), mos=_f(g('MONTHS_OF_SUPPLY')), inv=_f(g('INVENTORY')), upd=g('LAST_UPDATED')[:10]))
        last_end = ''
        for z, rows in series.items():
            rows.sort(key=lambda r: r['end']); rows = rows[-13:]
            last_end = max(last_end, rows[-1]['end'])
            out.setdefault(z, {})['rf'] = rows
        src['redfin'] = dict(end=last_end, name='Redfin Data Center – ZIP market tracker (janelas de 90 dias, todos residenciais)', url='https://www.redfin.com/news/data-center/')
    if os.path.exists(zh_raw):
        with open(zh_raw, encoding='utf-8') as f:
            rd = csv.reader(f); h = next(rd); months = [c for c in h if re.match(r'\d{4}-\d{2}-\d{2}$', c)]
            mi = [h.index(c) for c in months[-13:]]
            for row in rd:
                if row[h.index('State')] != 'FL': continue
                z = row[h.index('RegionName')].zfill(5)
                out.setdefault(z, {})['zh'] = dict(end=months[-13:], v=[_f(row[i]) for i in mi])
        src['zillow'] = dict(end=months[-1], name='Zillow Research – ZHVI por ZIP (casas+condos, faixa média, ajustado sazonalmente)', url='https://www.zillow.com/research/data/')
    out['_src'] = src
    if out: json.dump(out, open(comp, 'w'))
    return out

def resale_temp(rf):
    """Resale temperature 0-100 from the latest Redfin ZIP window (rule documented in the page)."""
    if not rf: return None
    r = rf[-1]
    if r.get('dom') is None and r.get('stl') is None: return None
    cl = lambda v: max(0.0, min(1.0, v))
    pts = 0.0
    pts += 40 * cl((120 - (r['dom'] if r.get('dom') is not None else 120)) / 100)
    pts += 25 * cl(((r['stl'] or 0.93) - 0.93) / 0.07)
    pts += 20 * cl((r['off2w'] or 0) / 0.5)
    pts += 15 * cl(((r['price_yoy'] if r.get('price_yoy') is not None else -0.10) + 0.10) / 0.20)
    sc = round(pts)
    lab = 'HOT' if sc >= 70 else 'WARM' if sc >= 50 else 'COOL' if sc >= 30 else 'COLD'
    return dict(sc=sc, lab=lab, dom=r.get('dom'), sold=r.get('sold'), end=r.get('end'), thin=(r.get('sold') or 0) < 5)

# ----------------------------------------------------------------------------- HTML
def render(items, stats, dropped, args):
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    mk = load_market()
    zips = {}
    for it in items:
        z = it.get('zip')
        if z and z in mk and z not in zips:
            zips[z] = dict(mk[z]); zips[z]['rt'] = resale_temp(mk[z].get('rf'))
    meta = dict(dataDate=args.data_date, built=time.strftime('%Y-%m-%d %H:%M'), params=P, zips=zips, mktSrc=mk.get('_src', {}),
                repairRates=REPAIR_RATES, repairUnknown=REPAIR_UNKNOWN_YEAR, repairMobile=REPAIR_MOBILE,
                repairMin=REPAIR_MIN, stats=stats, dropped=dropped, orlando=ORLANDO)
    data = json.dumps(dict(meta=meta, items=items), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return tpl.replace('/*__DATA__*/null', data)

# ----------------------------------------------------------------------------- site / PWA assets (GitHub Pages)
THEME = '#0d1b2a'          # header navy (template.html --navy); keep in sync with <meta name="theme-color">
NAVY2, GOLD = '#1b2d45', '#c9a227'
MANIFEST = {
    'name': 'LEILÃO – Leilões Flórida', 'short_name': 'LEILÃO',
    'description': 'Leilões de tax deed e foreclosure na Flórida – CHALLENGE CAPITAL',
    'lang': 'pt-BR', 'start_url': './', 'scope': './', 'display': 'standalone',
    'background_color': THEME, 'theme_color': THEME,
    'icons': [
        {'src': 'icons/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
        {'src': 'icons/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
        {'src': 'icons/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ],
}

def make_icon(size, path):
    """Gold 'CC' badge on dark navy (same look as the header logo). Badge stays inside the maskable safe zone."""
    from PIL import Image, ImageDraw, ImageFont
    S = size * 4                                     # supersample then downscale for smooth edges
    hx = lambda c: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    a, b = hx(THEME), hx(NAVY2)
    im = Image.new('RGB', (S, S), a); d = ImageDraw.Draw(im)
    for y in range(S):                               # subtle diagonal-ish vertical gradient like the header
        t = y / (S - 1); d.line([(0, y), (S, y)], fill=tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    m = int(S * 0.20); r = int(S * 0.11)
    d.rounded_rectangle([m, m, S - m, S - m], radius=r, fill=hx(GOLD))
    font = None
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'):
        if os.path.exists(f): font = ImageFont.truetype(f, int(S * 0.30)); break
    font = font or ImageFont.load_default()
    d.text((S / 2, S / 2), 'CC', font=font, fill=a, anchor='mm')
    im.resize((size, size), Image.LANCZOS).save(path, 'PNG', optimize=True)

def write_site_assets(outdir):
    os.makedirs(os.path.join(outdir, 'icons'), exist_ok=True)
    for size, name in ((192, 'icon-192.png'), (512, 'icon-512.png'), (180, 'apple-touch-icon.png')):
        make_icon(size, os.path.join(outdir, 'icons', name))
    with open(os.path.join(outdir, 'manifest.webmanifest'), 'w', encoding='utf-8') as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2); f.write('\n')
    with open(os.path.join(outdir, 'robots.txt'), 'w') as f:
        f.write('User-agent: *\nDisallow: /\n')
    open(os.path.join(outdir, '.nojekyll'), 'w').close()

PASSWORD_FILE = '/workspace/challenge-capital-secrets/site_password.txt'
STATICRYPT_LOCAL = '/workspace/tools/staticrypt/node_modules/.bin/staticrypt'

def encrypt_page(plain, outdir, password_file):
    """StaticCrypt (AES-256 + PBKDF2, decrypted in the browser). Password via env var, never on the command line."""
    import subprocess
    pw = open(password_file, encoding='utf-8').read().strip()
    if not pw: sys.exit(f'empty password file: {password_file}')
    cmd = [STATICRYPT_LOCAL] if os.path.exists(STATICRYPT_LOCAL) else ['npx', '--yes', 'staticrypt@3.5.4']
    cmd += [plain, '-d', outdir, '-c', '.staticrypt.json', '-t', 'password_template.html',
            '--short', '--remember', '365',
            '--template-title', 'LEILÃO – Leilões Flórida', '--template-instructions', 'Acesso restrito. Digite a senha para abrir o painel.',
            '--template-placeholder', 'Senha', '--template-button', 'Entrar', '--template-remember', 'Lembrar neste aparelho',
            '--template-error', 'Senha incorreta.', '--template-toggle-show', 'Mostrar senha', '--template-toggle-hide', 'Ocultar senha',
            '--template-color-primary', '#0d1b2a', '--template-color-secondary', '#1b2d45']
    env = dict(os.environ, STATICRYPT_PASSWORD=pw)
    r = subprocess.run(cmd, env=env, cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0: sys.exit('staticrypt failed: ' + (r.stderr or r.stdout)[-2000:])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true', help='fetch missing PropertyOnion details/photos into ./cache')
    ap.add_argument('--no-images', action='store_true')
    ap.add_argument('--fetch-market', action='store_true', help='download Redfin + Zillow ZIP market files into ./cache/market')
    ap.add_argument('--data-date', default='2026-10-08')
    ap.add_argument('--budget', type=float, default=P['budget'])
    ap.add_argument('--out', default=None, help='output HTML (default leiloes-florida.html, or index.html with --site)')
    ap.add_argument('--site', action='store_true', help='GitHub Pages build: encrypted index.html + manifest/icons/robots.txt next to build.py')
    ap.add_argument('--password-file', default=PASSWORD_FILE, help='StaticCrypt password file (keep outside the repo)')
    ap.add_argument('--no-encrypt', action='store_true', help='with --site: write plaintext index.html (NOT for publishing)')
    args = ap.parse_args()
    encrypt = args.site and not args.no_encrypt
    if encrypt and not os.path.exists(args.password_file):
        sys.exit(f'password file not found: {args.password_file} (refusing to build an unprotected site; use --no-encrypt for local tests)')
    if args.out is None:
        args.out = os.path.join(HERE, '.plain', 'index.html') if encrypt else os.path.join(HERE, 'index.html' if args.site else 'leiloes-florida.html')
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    P['budget'] = args.budget
    for d in ('po_full', 'img', 'search', 'market'): os.makedirs(os.path.join(CACHE, d), exist_ok=True)
    if args.fetch_market: fetch_market()
    items, stats, dropped = build_items(args)
    items.sort(key=lambda r: (-r['sc'], r['date']))
    html_s = render(items, stats, dropped, args)
    open(args.out, 'w', encoding='utf-8').write(html_s)
    if args.site:
        write_site_assets(HERE)
        if encrypt:
            encrypt_page(args.out, HERE, args.password_file)
            print(f"encrypted -> {os.path.join(HERE, 'index.html')}  {os.path.getsize(os.path.join(HERE, 'index.html'))/1e6:.1f} MB (StaticCrypt)")
    print(f"wrote {args.out}  {os.path.getsize(args.out)/1e6:.1f} MB  items={len(items)}  with_photo={sum(1 for i in items if i['img'])}")
    print('dropped:', json.dumps(dropped, ensure_ascii=False))
    for r in items[:10]:
        print(f"{r['sc']:4}  {r['t']} {r['cat']:<8} {r['date']} {r['addr'][:45]:<45} ref={r['ref']} val={r['val']} sug={r['sug']} fl={r['fl']}")

if __name__ == '__main__':
    main()
