#!/usr/bin/env python3
"""Local comparable sales (DOR NAL roll, offline): restrict comps to the subject's SUBDIVISION first, then to rings
around it, then fall back to the old ZIP comps.

Location without coordinates: NAL sales carry no lat/lon, but every parcel has its PLSS Township / Range / Section.
Sections are ~1 x 1 mile cells, so the section centroid places a parcel within ~0.5 mi. Rings are therefore
approximate: '≈0,5 mi' = same section, '≈1 mi' = section centres ≤ 1 mi apart (same + 4 adjacent), '≈3 mi'.

Subdivision: S_LEGAL (short legal) starts with the plat name ('SOUTHERN HILLS PLANTATION PH 2 ...'); we strip
phase/unit/lot/block tokens. NBRHD_CD (appraiser neighbourhood) is the fallback key when the legal is empty.
Cache: cache/local/<county>.json (re-scanned when the raw roll is newer or new subject parcels appear)."""
import csv, io, json, math, os, re, statistics, zipfile
import nal

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, 'cache', 'local')
MONTHS = 18                      # sales window
CUT = re.compile(r'\b(PH(ASE)?|UNIT|UNREC|REPLAT|ADD(ITION)?|SEC(TION)?|BLK|BLOCK|LOT|LOTS|TRACT|TR|PB|PG|ORB|OR|REV|AMENDED|AMD|FIRST|SECOND|THIRD|1ST|2ND|3RD|4TH)\b.*$')
CACHE_VER = 3
LANDBANK = re.compile(r'\b(LAND|LANDS|INVEST\w*|PROPERT\w*|HOLDINGS?|CAPITAL|FINANCIAL|REALTY|ACQUISITIONS?|FUNDS?|PARTNERS|VENTURES|ASSETS?|EQUITY|TRUST)\b')
# builders: national/regional brands + generic builder words (current owner of a vacant lot bought in the last 12 months)
BRANDS = [('D.R. Horton', r'\bD\s*R\s*HORTON|\bDR HORTON'), ('Lennar', r'LENNAR'), ('LGI Homes', r'\bLGI\b'), ('Adams Homes', r'ADAMS HOMES'),
          ('Maronda Homes', r'MARONDA'), ('Perry Homes', r'PERRY HOMES'), ('Meritage Homes', r'MERITAGE'), ('Taylor Morrison', r'TAYLOR MORRISON'),
          ('KB Home', r'\bKB HOME'), ('Pulte / Centex / Del Webb', r'PULTE|CENTEX|DEL WEBB'), ('Highland Homes', r'HIGHLAND HOMES'),
          ('Holiday Builders', r'HOLIDAY BUILDERS'), ('Dream Finders', r'DREAM FINDERS'), ('Mattamy Homes', r'MATTAMY'), ('Ryan Homes / NVR', r'RYAN HOMES|\bNVR\b'),
          ('Toll Brothers', r'TOLL BROTHERS|\bTOLL FL'), ('Ashton Woods', r'ASHTON WOODS'), ('Stanley Martin', r'STANLEY MARTIN'), ('William Ryan', r'WILLIAM RYAN'),
          ('Park Square', r'PARK SQUARE'), ('Starlight Homes', r'STARLIGHT HOMES'), ('Landsea Homes', r'LANDSEA'), ('Smart Homes', r'SMART HOMES'),
          ('Ryland', r'RYLAND'), ('GL Homes', r'\bG\s*L HOMES'), ('Clayton Homes', r'CLAYTON'), ('Dream Homes', r'DREAM HOMES')]
BRAND_RE = [(n, re.compile(r)) for n, r in BRANDS]
BLD_RE = re.compile(r'\b(HOMES|HOMEBUILDERS?|BUILDERS?|BUILDING|CONSTRUCTION|CONTRACTORS?|CONTRACTING|DEVELOPMENT|DEVELOPERS?|COMMUNITIES|RESIDENTIAL)\b')
NOT_BLD = re.compile(r'CONSERVANCY|PRESERVE|DISTRICT|AUTHORITY|CHURCH|MINISTR|SCHOOL|UNIVERSITY|HOMEOWNERS|ASSOCIATION|\bASSN\b|\bPOA\b|\bHOA\b|COUNTY|CITY OF|STATE OF|TRUSTEE|\bBANK\b|HABITAT')
CORP = re.compile(r'\b(LLC|INC|CORP|CORPORATION|LP|LTD|CO)\b')
def builder_name(own):
    o = re.sub(r'[^A-Z0-9 &]', ' ', (own or '').upper()); o = re.sub(r'\s+', ' ', o).strip()
    if not o or NOT_BLD.search(o): return None, o
    for n, rx in BRAND_RE:
        if rx.search(o): return n, o
    if BLD_RE.search(o) and CORP.search(o): return o.title(), o
    return None, o

GOLF = re.compile(r'GOLF|COUNTRY CLUB|\bG ?& ?CC\b|\bCC\b|PLANTATION|FAIRWAY|LINKS')

def subname(legal):
    s = re.sub(r'[^A-Z0-9 &]', ' ', str(legal or '').upper())
    s = re.sub(r'\s+', ' ', s).strip()
    if not s or re.match(r'^(\d|COM |BEG |N |S |E |W |THE [NSEW] |PARCEL|PT |PART |ALL |TRACT |SEC |SECTION )', s): return ''
    s = CUT.sub('', s).strip()
    s = re.sub(r'\s+\d+[A-Z]?$', '', s).strip()
    return s if len(s) >= 4 else ''

def trs_xy(twn, rng, sec):
    """approximate PLSS section centre in miles (x east, y north) from Township/Range/Section (Tallahassee meridian)."""
    mt = re.match(r'\s*0*(\d+)\s*([NS])', str(twn or '').upper()); mr = re.match(r'\s*0*(\d+)\s*([EW])', str(rng or '').upper())
    try: s = int(float(sec))
    except Exception: return None
    if not mt or not mr or not (1 <= s <= 36): return None
    t, ns = int(mt.group(1)), mt.group(2); r, ew = int(mr.group(1)), mr.group(2)
    row = (s - 1) // 6; k = (s - 1) % 6
    col = (5 - k) if row % 2 == 0 else k                                # sections run 1→6 east-to-west, then back
    west = (r - 1) * 6 if ew == 'E' else -r * 6
    north = -(t - 1) * 6 if ns == 'S' else t * 6
    return (round(west + col + 0.5, 2), round(north - row - 0.5, 2))

def _i(v):
    try: return int(float(v))
    except Exception: return None

def scan(county, zpath, targets, today):
    """targets: set of normalised parcel ids. Returns subjects, recent qualified sales and per-area counters."""
    z = zipfile.ZipFile(zpath); n = [x for x in z.namelist() if x.lower().endswith('.csv')][0]
    rd = csv.DictReader(io.TextIOWrapper(z.open(n), encoding='latin-1', newline=''))
    ty, tm = int(today[:4]), int(today[5:7]); lim = ty * 12 + tm - MONTHS
    subj, sales, area = {}, [], {}
    lotbuys, newc, lsale = [], {}, {}            # (owner, sub key, zip key) of vacant-lot sales in 12 months; new construction per area
    for row in rd:
        uc = (row.get('DOR_UC') or '').zfill(3)
        sub = subname(row.get('S_LEGAL')); nb = (row.get('NBRHD_CD') or '').strip().lstrip('0')
        xy = trs_xy(row.get('TWN'), row.get('RNG'), row.get('SEC'))
        jv = _i(row.get('JV')); lvg = _i(row.get('TOT_LVG_AREA')); lsq = _i(row.get('LND_SQFOOT')); ayb = _i(row.get('ACT_YR_BLT'))
        res = uc in ('000', '001', '002', '004', '005', '008')
        st = nal.nstreet(row.get('PHY_ADDR1') or ''); st = ('r:' + st + '|' + (row.get('PHY_ZIPCD') or '')[:5]) if st else None
        for key in (('s:' + sub) if sub else None, ('n:' + nb) if nb else None, st):
            if not key or not res: continue
            a = area.get(key)
            if a is None: a = area[key] = [0, 0, 0, []]
            a[0] += 1
            if uc == '000': a[1] += 1
            else:
                a[2] += 1
                if jv and uc in ('001', '004') and len(a[3]) < 400: a[3].append(jv)
        zk = 'z:' + (row.get('PHY_ZIPCD') or '')[:5] if row.get('PHY_ZIPCD') else None
        if uc in ('001', '002', '004', '007') and ayb and ayb >= int(today[:4]) - 2:
            for k in (('s:' + sub) if sub else None, zk):
                if k: newc[k] = newc.get(k, 0) + 1
        if uc == '000':
            for k in ('1', '2'):
                yr_ = _i(row.get('SALE_YR' + k)); mo_ = _i(row.get('SALE_MO' + k)) or 6; pr_ = _i(row.get('SALE_PRC' + k)) or 0
                if yr_ and yr_ * 12 + mo_ >= ty * 12 + tm - 12 and pr_ >= 1000 and row.get('VI_CD' + k) == 'V':
                    if not row.get('MULTI_PAR_SAL' + k):          # absorption: every single-parcel vacant-lot sale (any qualification code)
                        for kk in (('s:' + sub) if sub else None, ('n:' + nb) if nb else None, zk):
                            if kk: lsale[kk] = lsale.get(kk, 0) + 1
                    lotbuys.append(((row.get('OWN_NAME') or '').strip(), ('s:' + sub) if sub else None, zk)); break
        pid = nal.npid(row.get('PARCEL_ID')); ak = nal.npid(row.get('ALT_KEY'))
        hit = pid if pid in targets else (ak if ak and ak in targets else None)
        if hit:
            subj[hit] = dict(sub=sub, nb=nb, st=st, xy=xy, uc=uc, lsq=lsq, lvg=lvg, ayb=ayb, jv=jv, leg=(row.get('S_LEGAL') or '')[:80], pid=row.get('PARCEL_ID'))
        for k in ('1', '2'):
            prc = _i(row.get('SALE_PRC' + k)); yr = _i(row.get('SALE_YR' + k)); mo = _i(row.get('SALE_MO' + k)) or 6
            if not prc or not yr or yr * 12 + mo < lim: continue
            if prc < 1000 or row.get('QUAL_CD' + k) != '01' or row.get('MULTI_PAR_SAL' + k): continue
            if jv and (prc < 0.25 * jv or prc > 4 * jv): continue          # obvious non-market vs the parcel's own value
            sales.append([sub, nb, xy[0] if xy else None, xy[1] if xy else None, uc, prc, yr, mo, lvg, ayb, lsq,
                          (row.get('PHY_ADDR1') or '').strip().title(), (row.get('PHY_ZIPCD') or '')[:5], row.get('VI_CD' + k), pid])
            break
    out_area = {}
    for k, a in area.items():
        out_area[k] = [a[0], a[1], a[2], round(statistics.median(a[3])) if a[3] else None]
    # builders = known brands / builder words, or companies that bought ≥ 5 vacant lots in 12 months in this county
    cnt = {}
    for own, _, _ in lotbuys:
        _, o = builder_name(own); cnt[o] = cnt.get(o, 0) + 1
    bld, tops = {}, {}
    for own, sk, zk in lotbuys:
        n, o = builder_name(own)
        if not n and cnt.get(o, 0) >= 5 and CORP.search(o) and not NOT_BLD.search(o) and not LANDBANK.search(o): n = o.title()
        if not n: continue
        tops[n] = tops.get(n, 0) + 1
        for k in (sk, zk):
            if not k: continue
            b = bld.setdefault(k, [0, {}]); b[0] += 1; b[1][n] = b[1].get(n, 0) + 1
    out_bld = {k: [v[0], newc.get(k, 0), sorted(v[1].items(), key=lambda t: -t[1])[:5]] for k, v in bld.items()}
    for k, v in newc.items():
        if k not in out_bld and v >= 5: out_bld[k] = [0, v, []]
    return dict(subj=subj, sales=sales, area=out_area, bld=out_bld, btop=sorted(tops.items(), key=lambda t: -t[1])[:25], ls=lsale, ver=CACHE_VER)

def load(county, targets, today):
    zp = nal.zips().get(county)
    if not zp: return None
    os.makedirs(C, exist_ok=True)
    p = os.path.join(C, county + '.json')
    d = None
    if os.path.exists(p):
        try: d = json.load(open(p))
        except Exception: d = None
    if d is None or d.get('ver') != CACHE_VER or os.path.getmtime(zp) > os.path.getmtime(p) or not set(targets) <= set(d.get('tp', [])) or d.get('today', '')[:7] != today[:7]:
        tp = sorted(set(targets) | set((d or {}).get('tp', [])))
        d = scan(county, zp, set(tp), today); d['tp'] = tp; d['today'] = today
        json.dump(d, open(p, 'w'))
    return d

def _group(uc):
    return 'land' if uc == '000' else 'sfr' if uc in ('001', '007') else 'condo' if uc in ('004', '005') else 'mob' if uc == '002' else 'multi' if uc in ('003', '008') else None

LEVELS = [('sub', 'mesma subdivisão'), ('r05', '≈0,5 mi (mesma seção)'), ('r1', '≈1 mi'), ('r3', '≈3 mi')]
BASE = dict(sub=75, r05=65, r1=55, r3=40)

def estimate(d, pid, zh_of, today, ty_hint=None):
    """-> dict(lvl, lvlTxt, n, est, lo, hi, conf, confTxt, comps[], ctx{}) or None. zh_of(zip) -> Zillow ZHVI series."""
    s = d['subj'].get(pid) if d else None
    if not s: return None
    g = _group(s['uc'])
    if not g: return None
    land = g == 'land'
    size = s['lsq'] if land else s['lvg']
    ctx = dict(sub=s['sub'] or None, leg=s['leg'] or None)
    a = d['area'].get('s:' + s['sub']) if s['sub'] else None
    if not a and s['nb']: a = d['area'].get('n:' + s['nb']); ctx['by'] = 'bairro do PA'
    if a and a[0]:
        ctx.update(nTot=a[0], nVac=a[1], nBuilt=a[2], pctBuilt=round(100 * a[2] / a[0]), medBuilt=a[3])
    rs = d['area'].get(s.get('st')) if s.get('st') else None
    if rs and rs[0] >= 4: ctx.update(stTot=rs[0], stPct=round(100 * rs[2] / rs[0]))
    if s['sub'] and GOLF.search(s['sub']): ctx['golf'] = True
    B = d.get('bld') or {}
    bs = B.get('s:' + s['sub']) if s['sub'] else None
    zk = 'z:' + (s.get('st') or '|').split('|')[-1] if s.get('st') else None
    bz = B.get(zk) if zk else None
    if bs or bz: ctx['bld'] = dict(sub=bs, zip=bz, zk=zk[2:] if zk else None)
    big = bool(a and a[0] > 3000)
    # absorption: qualified sales in the last 12 months inside the same subdivision (or appraiser neighbourhood)
    ty_, tm_ = int(today[:4]), int(today[5:7]); nowm = ty_ * 12 + tm_
    keyf = (lambda r: r[0] == s['sub']) if s['sub'] else ((lambda r: r[1] == s['nb']) if s['nb'] else None)
    if keyf and a:
        sl = sb = 0
        for r in d['sales']:
            if nowm - (r[6] * 12 + r[7]) > 12 or not keyf(r): continue
            if r[4] == '000' and r[13] == 'V': sl += 1
            elif r[4] in ('001', '002', '004', '005', '007', '008') and r[13] != 'V': sb += 1
        LS = d.get('ls') or {}
        lk = ('s:' + s['sub']) if s['sub'] else ('n:' + s['nb'])
        if lk in LS: sl = LS[lk]
        ctx['abs'] = dict(lots=sl, built=sb, nVac=a[1], nBuilt=a[2],
                          rLots=round(sl / a[1], 4) if a[1] else None, rBuilt=round(sb / a[2], 4) if a[2] else None)
    ty, tm = int(today[:4]), int(today[5:7])
    def fac(z, yr, mo):
        zz = zh_of(z)
        if not zz or not zz.get('v'): return 1.0
        ends, vs = zz['end'], zz['v']; key = f'{yr}-{mo:02d}'
        at = next((v for e, v in zip(ends, vs) if e[:7] == key), None)
        if at is None: at = vs[0] if key < ends[0][:7] else None
        return max(0.85, min(1.15, vs[-1] / at)) if at else 1.0
    cand = []
    for r in d['sales']:
        sub, nb, x, y, uc, prc, yr, mo, lvg, ayb, lsq, addr, zp, vi, rpid = r
        if rpid == nal.npid(s['pid']) or _group(uc) != g: continue
        if land:
            if vi != 'V' or not lsq or not size or not (0.5 * size <= lsq <= 1.5 * size): continue
        else:
            if vi == 'V' or not lvg: continue
            if size and not (0.75 * size <= lvg <= 1.25 * size): continue
            if s['ayb'] and ayb and abs(ayb - s['ayb']) > 15: continue
        dist = math.hypot(x - s['xy'][0], y - s['xy'][1]) if (x is not None and s['xy']) else None
        f = fac(zp, yr, mo)
        imp = prc * f * ((size / lsq) ** 0.3 if land else (size / lvg if size else 1))
        cand.append(dict(addr=addr or '(sem endereço)', d=f'{yr}-{mo:02d}', p=prc, adj=round(imp), sz=lsq if land else lvg, yb=ayb,
                         mi=round(dist, 1) if dist is not None else None, sub=bool(s['sub'] and sub == s['sub']) or bool(not s['sub'] and s['nb'] and nb == s['nb']), age=(ty * 12 + tm) - (yr * 12 + mo)))
    pick = None
    for lv, txt in LEVELS:
        if lv == 'sub':
            L = [c for c in cand if c['sub'] and (not big or (c['mi'] is not None and c['mi'] <= 1.01))]
            if big: txt = 'mesma subdivisão (≤1 mi)'
        else:
            lim = {'r05': 0.01, 'r1': 1.01, 'r3': 3.01}[lv]
            L = [c for c in cand if c['mi'] is not None and c['mi'] <= lim]
        if len(L) >= 3: pick = (lv, txt, L); break
    if not pick: return dict(lvl=None, ctx=ctx, n=0)
    lv, txt, L = pick
    L.sort(key=lambda c: (c['mi'] if c['mi'] is not None else 9, c['age']))
    L = L[:12]
    vals = sorted(c['adj'] for c in L)
    est = statistics.median(vals)
    q = lambda p: vals[min(len(vals) - 1, int(p * (len(vals) - 1) + 0.5))]
    lo, hi = q(0.25), q(0.75)
    conf = BASE[lv] + min(15, 2 * (len(L) - 3))
    disp = (hi - lo) / est if est else 1
    conf -= 25 if disp > 0.6 else 12 if disp > 0.35 else 0
    if min(c['age'] for c in L) > 12: conf -= 5
    conf = max(0, min(100, conf))
    return dict(lvl=lv, lvlTxt=txt, n=len(L), est=round(est), lo=round(lo), hi=round(hi), conf=conf,
                confTxt='alta' if conf >= 70 else 'média' if conf >= 50 else 'baixa', g=g,
                comps=[[c['addr'], c['d'], c['p'], c['sz'], c['yb'], c['mi'], c['adj']] for c in L], ctx=ctx)
