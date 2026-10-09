#!/usr/bin/env python3
"""
CHALLENGE CAPITAL – Leilões Flórida :: dashboard builder (v4)
==============================================================
Builds the single-file dashboard from the public auction scans in /workspace/auc/statewide plus free public data:
  - RealAuction (county clerk auction sites) previews: tax deeds (td/), foreclosures (fc/), past results (results/)
  - Tranzon / U.S. Treasury land & property auctions (extra_*.json, extra_sources.py)
  - PropertyOnion public property pages (details, AVM, rent, occupancy, mortgages, FEMA, photos)   -> po_fetch.py
  - PropertyOnion Premium CSV exports (POV, liens, occupancy) in /workspace/auc/statewide/po_exports/ -> po_export.py
  - Florida DOR tax roll (NAL 2026P): use code, values, last sales, homestead + qualified sales for comps -> nal.py
  - Florida Dept. of Health FLWMI: water (public/well) and wastewater (sewer/septic) per parcel     -> flwmi.py
  - Redfin Data Center ZIP tracker, Zillow ZHVI and ZORI by ZIP (market, days on market, rents)

Usage
  python3 build.py                     # offline rebuild from data + ./cache  -> leiloes-florida.html
  python3 build.py --fetch             # also fetch missing PropertyOnion pages, FLWMI utilities (polite, cached)
  python3 build.py --data-date 2026-10-15
  python3 build.py --site              # GitHub Pages: encrypted index.html + manifest.webmanifest + icons/ + robots.txt
                                       # (password read from --password-file OUTSIDE the repo; plaintext -> .plain/)
  python3 build.py --site --no-encrypt --out .plain/index.html   # local test copy (never commit)
  python3 build.py --fetch-market      # refresh Redfin / Zillow ZIP files

Refresh of the raw auction lists (weekly): in /workspace/auc/statewide run cal.py, fetch_more.py (or fetch.py per day),
results.py (past results), extra_sources.py; NAL files: /workspace/auc/nal/dl.py. Then build.py --fetch.

Nothing is invented: every number comes from the sources above; missing values are '—' and alerts say 'não verificado'.
Repairs, holding, comps value and expected auction price are explicit, labelled estimates.
"""
import argparse, ast, base64, csv, datetime as dt, gzip, io, json, math, os, re, statistics, sys, time, html

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rawdata, po_fetch, nal, flwmi, po_export, po_bids

AUC = '/workspace/auc'
SW = os.path.join(AUC, 'statewide')
CACHE = os.path.join(HERE, 'cache')
ORLANDO = (28.5383, -81.3792)

# ----------------------------------------------------------------------------- parameters (defaults of the editable "Premissas")
P = dict(
    ret=17.0,               # minimum target return on cash invested (%)  -> "lance máx." (Fernando)
    tdxp=1,                 # tax deed: NET/ROI at the expected auction price (1) or at the opening bid (0)
    flip=25.0,              # ROI at the reference bid for verdict FLIP (%); CONSIDERAR between ret and flip
    lownet=25000,           # BidToFlip-style category 'lucro baixo' when NET below this (US$)
    # ---- deductions: BidToFlip structure, realistic defaults (all editable in the page) ----
    clerk1=3.0, clerk2=1.5,  # clerk fee: 3% of the first US$500 of the bid + 1.5% of the remainder
    docb=0.70,              # FL documentary stamp tax on the deed (% of bid)
    fee=0,                  # extra flat auction fees (US$)
    qt=2500,                # quiet title (US$) – built tax deeds
    qtm=0,                  # extra holding months for quiet title
    ev=2500,                # eviction / cash-for-keys (US$) when occupied/tenant likely
    evm=0,                  # extra months when eviction likely
    rhb20=5, rhb15=10, rhb05=20, rhb95=30, rhbOld=40,   # rehab US$/sqft by year built (2020+, 2015-19, 2005-14, 1995-2004, older)
    rhbMin=8000, rhbUnk=35000, rhbSqft=1500, rhbPool=5000, # minimum, unknown year, assumed sqft when unknown, pool
    cont=10,                # rehab contingency (% of rehab)
    months=5,               # holding months (built)
    monthsLot=3,            # holding months (land)
    usedom=0,               # 1 = exit time from Redfin ZIP days on market instead of fixed months
    closem=1,               # closing months after an accepted offer (only when usedom=1)
    htax=1.8,               # property tax %/yr of value when the real annual tax bill is unknown
    hins=1.0,               # insurance %/yr of value while holding (built)
    hutil=350,              # utilities / maintenance US$/month while holding (built)
    hutilLot=50,            # US$/month for land (mowing)
    clear=500,              # land: mowing / clean-up (US$); survey is normally the buyer's cost on a lot sale
    qtLot=1200,             # land: title certification for resale (US$) instead of a US$ 2.5k quiet-title suit
    list=2.5, buyc=2.5, docs=0.70, misc=1000, wra=399,   # sell side: brokers % of ARV, seller doc stamps, closing/misc US$, flat sale fee (BidToFlip; built only)
    titleP=100,             # owner's title policy on resale: % of the FL promulgated rate (seller pays; buyer-pays counties = 0)
    dep=5.0,                # deposit due at the auction (% of the bid) – RealAuction standard; confirm per county
    yld=9.0,                # gross yield considered 'aluguel forte' (%)
    rebuild=175, depr=1.0,  # replacement cost: US$/sqft, depreciation %/year of age (max 60%)
    refi=7.0, ltv=75, tax=1.8, ins=1.5, vac=10, mgmt=8,   # BRRRR
)
# BidToFlip-style age-tiered rehab (flat US$), used when there is no better estimate; +pool
REHAB_TIERS = [(2020, 8000), (2015, 12000), (2005, 20000), (1995, 30000), (0, 40000)]
REHAB_UNKNOWN = 25000
REHAB_POOL = 5000

AVOID = {
    '15531 CITRUS HARVEST': 'Revisão anterior: lance/julgamento ~US$193k e risco de hipoteca sênior.',
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

# ----------------------------------------------------------------------------- DOR use codes (Florida DOR, Rule 12D-8.008)
DOR_DESC = {'000': 'Terreno vago residencial', '001': 'Casa unifamiliar', '002': 'Mobile home', '003': 'Multifamiliar (10+ unid.)', '004': 'Condomínio',
 '005': 'Cooperativa', '006': 'Residência p/ aposentados', '007': 'Residencial diverso', '008': 'Multifamiliar (<10 unid.)', '009': 'Área comum residencial',
 '010': 'Terreno vago comercial', '011': 'Loja', '012': 'Loja/escritório/residência', '013': 'Loja de departamento', '014': 'Supermercado', '015': 'Shopping regional',
 '016': 'Centro comercial', '017': 'Escritório (1 andar)', '018': 'Escritório (vários andares)', '019': 'Consultórios/clínica', '020': 'Terminal (aeroporto/marina/ônibus)',
 '021': 'Restaurante', '022': 'Fast food / drive-in', '023': 'Banco', '024': 'Seguradora', '025': 'Serviços / reparos', '026': 'Posto de gasolina', '027': 'Concessionária / oficina',
 '028': 'Estacionamento / parque de mobile homes', '029': 'Atacado / distribuição', '030': 'Floricultura / estufa', '031': 'Cinema drive-in', '032': 'Teatro / auditório',
 '033': 'Bar / casa noturna', '034': 'Boliche / arena', '035': 'Atração turística', '036': 'Camping', '037': 'Hipódromo / pista', '038': 'Golfe', '039': 'Hotel / motel',
 '040': 'Terreno vago industrial', '041': 'Indústria leve', '042': 'Indústria pesada', '043': 'Madeireira', '044': 'Processamento de alimentos', '045': 'Engarrafadora',
 '046': 'Outros alimentos', '047': 'Mineração', '048': 'Armazém / depósito', '049': 'Pátio aberto / sucata', '050': 'Agrícola melhorado', '051': 'Lavoura', '052': 'Lavoura',
 '053': 'Lavoura', '054': 'Silvicultura', '055': 'Silvicultura', '056': 'Silvicultura', '057': 'Silvicultura', '058': 'Silvicultura', '059': 'Silvicultura', '060': 'Pastagem',
 '061': 'Pastagem', '062': 'Pastagem', '063': 'Pastagem', '064': 'Pastagem', '065': 'Pastagem', '066': 'Pomar / citros', '067': 'Aves / abelhas / peixes', '068': 'Laticínio',
 '069': 'Plantas ornamentais', '070': 'Terreno vago institucional', '071': 'Igreja', '072': 'Escola privada', '073': 'Hospital privado', '074': 'Asilo', '075': 'Beneficente',
 '076': 'Funerária / cemitério', '077': 'Clube / associação', '078': 'Sanatório', '079': 'Cultural', '080': 'Governo – vago', '081': 'Militar', '082': 'Floresta / parque público',
 '083': 'Escola pública', '084': 'Faculdade', '085': 'Hospital público', '086': 'Condado', '087': 'Estado', '088': 'Federal', '089': 'Municipal', '090': 'Arrendamento de terra pública',
 '091': 'Utilidade pública', '092': 'Mineração / petróleo', '093': 'Direitos de subsolo', '094': 'Faixa de domínio (rua/via)', '095': 'Rio / lago / submerso',
 '096': 'Esgoto / aterro / brejo', '097': 'Recreação / parque', '098': 'Avaliação central (ferrovia/utilidade)', '099': 'Gleba não agrícola'}
TYPES = ['Lote', 'Terreno', 'Casa', 'Townhouse', 'Condo', 'Mobile', 'Multifamily', 'Comercial', 'Outro']
JUNK_UC = {'009', '094', '095', '096'}

def type_from_dor(uc, acres, po_lu):
    u = int(uc) if uc and uc.isdigit() else -1
    if u < 0: return None
    if u == 0: return 'Lote' if (acres is None or acres < 1) else 'Terreno'
    if u == 1: return 'Townhouse' if po_lu == 'Townhouse' else 'Casa'
    if u == 2: return 'Mobile'
    if u in (3, 8): return 'Multifamily'
    if u in (4, 5): return 'Townhouse' if po_lu == 'Townhouse' else 'Condo'
    if u in (10, 40, 70, 80, 99) or 50 <= u <= 69: return 'Terreno'
    if 11 <= u <= 39 or 41 <= u <= 49: return 'Comercial'
    return 'Outro'

def type_from_po(lu, acres, sqft, addr):
    if not lu: return None
    l = lu.lower()
    if 'single' in l: return 'Casa'
    if 'town' in l: return 'Townhouse'
    if 'condo' in l: return 'Condo'
    if 'mobile' in l or 'manufactured' in l: return 'Mobile'
    if 'multi' in l or 'duplex' in l or 'apartment' in l: return 'Multifamily'
    if l == 'land' or 'vacant' in l:
        if sqft: return 'Condo' if re.search(r'#|\bUNIT\b|\bAPT\b', addr.upper()) else 'Outro'
        return 'Lote' if (acres is None or acres < 1) else 'Terreno'
    if 'agri' in l or 'farm' in l or 'timber' in l: return 'Terreno'
    if any(k in l for k in ('commercial', 'retail', 'office', 'industrial', 'hotel', 'warehouse', 'business')): return 'Comercial'
    return 'Outro'

def type_fallback(it, po, sqft, acres):
    o = it.get('ocpa')
    if o and o.get('dor'): return type_from_dor(o['dor'][:2].zfill(3), acres, None)
    lk = it.get('lake')
    if lk and isinstance(lk.get('land'), str) and 'VACANT' in lk['land'].upper(): return 'Lote' if (acres is None or acres < 1) else 'Terreno'
    pc = (po or {}).get('propertyClassID')
    if pc == 'V': return 'Lote' if (acres is None or acres < 1) else 'Terreno'
    if pc in ('C', 'I', 'O'): return 'Comercial'
    if pc in ('E', 'F', 'A'): return 'Terreno' if pc == 'A' else 'Outro'
    if sqft: return 'Casa'
    if re.search(r'#|\bUNIT\b|\bAPT\b', it['raw'].get('addr', '').upper()): return 'Condo'
    return 'Outro'

def rehab_for(ty, yr, pool, units):
    if ty in ('Lote', 'Terreno'): return 0, 'terreno – sem obra (limpeza/levantamento topográfico não incluídos)'
    base = next(v for y, v in REHAB_TIERS if yr and yr >= y) if yr else REHAB_UNKNOWN
    why = (f'faixa por idade (constr. {yr})' if yr else 'ano desconhecido') + f': US${base:,}'
    mult = 1
    if ty == 'Multifamily' and units and units > 1: mult = min(int(units), 4); why += f' × {mult} unid.'
    if ty == 'Comercial': why += ' (comercial: estimativa fraca – vistoriar)'
    est = base * mult
    if pool: est += REHAB_POOL; why += f' + piscina US${REHAB_POOL:,}'
    return est, why

def use_group(uc):
    return {'001': 'sfr', '004': 'condo', '005': 'condo', '002': 'mob', '003': 'multi', '008': 'multi', '000': 'land'}.get(uc, 'other' if uc else None)

def comps_for(sales_by_zip, zp, uc, sqft, yr, lsq, addr_norm, ty):
    """comparable qualified sales (DOR NAL) in the same ZIP + use group; estimate is clearly labelled."""
    g = use_group(uc) if uc else {'Casa': 'sfr', 'Townhouse': 'sfr', 'Condo': 'condo', 'Mobile': 'mob', 'Multifamily': 'multi', 'Lote': 'land', 'Terreno': 'land'}.get(ty)
    if not zp or not g or g == 'other': return None
    rows = [s for s in sales_by_zip.get(zp, []) if use_group(s[1]) == g and nal.nstreet(s[8]) != addr_norm]
    land = g == 'land'
    if land:
        rows = [s for s in rows if (s[10] == 'V') and s[7]]
        if lsq: rows = [s for s in rows if 0.4 * lsq <= s[7] <= 2.5 * lsq]
        rows.sort(key=lambda s: (abs(math.log((s[7] or 1) / (lsq or s[7] or 1))), -(s[3] * 12 + (s[4] or 0))))
    else:
        rows = [s for s in rows if s[5] and s[5] > 300 and s[10] != 'V']
        if sqft: rows = [s for s in rows if 0.7 * sqft <= s[5] <= 1.4 * sqft]
        if yr: rows = [s for s in rows if not s[6] or abs(s[6] - yr) <= 20]
        rows.sort(key=lambda s: (abs((s[5] or 0) - (sqft or s[5] or 0)) / 100 + (abs((s[6] or yr or 0) - (yr or s[6] or 0)) / 10), -(s[3] * 12 + (s[4] or 0))))
    sel = rows[:8]
    if not sel: return None
    out = dict(n=len(rows), g=g, l=[[s[8].title(), s[2], f'{s[3]}-{(s[4] or 0):02d}', s[5], s[6], s[7]] for s in sel])
    if len(sel) >= 3:
        if land:
            pps = [s[2] / s[7] for s in sel if s[7]]
            out['ppsf'] = statistics.median(pps); out['est'] = round(out['ppsf'] * lsq) if lsq else round(statistics.median([s[2] for s in sel]))
        else:
            pps = [s[2] / s[5] for s in sel]
            out['ppsf'] = statistics.median(pps)
            out['est'] = round(out['ppsf'] * sqft) if sqft else round(statistics.median([s[2] for s in sel]))
    return out

# ----------------------------------------------------------------------------- auction results (RealAuction past dates)
def load_results():
    """-> (stats dict, recent 3rd-party sales list). Basis: RealAuction 'Assessed Value' shown on the auction listing."""
    import glob
    rows = []
    for f in glob.glob(os.path.join(SW, 'results', '*.json')):
        host, date = os.path.basename(f)[:-5].rsplit('_', 1)
        co = host.split('.')[0].replace('-', '').replace('myorangeclerk', 'orange')
        try: data = json.load(open(f))
        except Exception: continue
        for r in data:
            res = r.get('res') or {}
            at = (r.get('Auction Type') or '').upper()
            if not at: continue
            t = 'TD' if 'TAX' in at else 'FC'
            if 'realtaxdeed' in host and t != 'TD': continue
            m = lambda k: rawdata.money(r.get(k))
            ref = m('Opening Bid') if t == 'TD' else m('Final Judgment Amount')
            av = m('Assessed Value') or m('Property App. Market Value')
            st = 'sold' if res.get('A') == 'Auction Sold' else ('cxl' if re.search(r'cancel|bankrupt|redeem|postpon|reset|stay', str(res.get('B') or ''), re.I) else 'other')
            sold = rawdata.money(res.get('D')) if st == 'sold' else None
            to = res.get('ST') or ''
            rows.append(dict(co=co, t=t, d=date.replace('-', '/'), addr=((r.get('Property Address') or '') + ' ' + (r.get('addr2') or '')).strip(),
                             ref=ref, av=av, sold=sold, to=('3P' if '3rd' in to else 'PL' if 'Plaintiff' in to else ''), st=st, why=str(res.get('B') or '')[:60] if st != 'sold' else ''))
    stats = {}
    def add(key, r):
        s = stats.setdefault(key, dict(n=0, sold=0, p3=0, pl=0, cxl=0, rav=[], rref=[]))
        s['n'] += 1
        if r['st'] == 'cxl': s['cxl'] += 1
        if r['st'] == 'sold':
            s['sold'] += 1
            if r['to'] == '3P':
                s['p3'] += 1
                if r['av'] and r['sold']: s['rav'].append(r['sold'] / r['av'])
                if r['ref'] and r['sold']: s['rref'].append(r['sold'] / r['ref'])
            elif r['to'] == 'PL': s['pl'] += 1
    for r in rows:
        add(r['co'] + '|' + r['t'], r); add('*|' + r['t'], r)
    def q(v, p):
        v = sorted(v); return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else None
    for k, s in stats.items():
        s['rav_med'], s['rav_p25'], s['rav_p75'] = q(s['rav'], .5), q(s['rav'], .25), q(s['rav'], .75)
        s['rref_med'] = q(s['rref'], .5)
        s['nrav'] = len(s['rav']); s['nrref'] = len(s['rref']); del s['rav']; del s['rref']
        for kk in ('rav_med', 'rav_p25', 'rav_p75', 'rref_med'):
            if s[kk] is not None: s[kk] = round(s[kk], 3)
    dates = sorted({r['d'] for r in rows}, key=lambda d: (d[6:], d[:5]))
    recent = sorted([r for r in rows if r['st'] == 'sold'], key=lambda r: (r['d'][6:], r['d'][:5]), reverse=True)
    recent = [[r['co'], r['t'], iso(r['d']), r['addr'].title()[:60], r['ref'], r['av'], r['sold'], r['to']] for r in recent[:3000]]
    return stats, recent, dict(rows=len(rows), first=iso(dates[0]) if dates else None, last=iso(dates[-1]) if dates else None)

# ----------------------------------------------------------------------------- collection + enrichment
def collect_items(fetch_bids=False):
    known = {}
    for f in ('td_po.json', 'fc_po.json'):
        for k, v in (jload(os.path.join(SW, f), {}) or {}).items():
            if v and v.get('id'): known[k] = v
    ocpa = jload(os.path.join(SW, 'ocpa_td.json'), {})
    orange_en = jload(os.path.join(AUC, 'orange_enriched.json'), {})
    lake_en = jload(os.path.join(AUC, 'lake_enriched.json'), {})
    items = []
    for src, x in rawdata.collect():
        it = dict(src=src, raw=x, known=known.get(x['aid']))
        if src == 'TD':
            it['ocpa'] = ocpa.get(x['aid']) or orange_en.get(x['aid']); it['lake'] = lake_en.get(x['aid'])
        a = x.get('addr', '').upper()
        it['avoid'] = next((k for k in AVOID if k in a), None)
        items.append(it)
    items, po_st = po_export.enrich(items, closed=rawdata.closed_cases())
    # RealAuction is often blocked (HTTP 403). Default is cache/local files only.
    # Pass fetch_bids=True (--fetch-bids or --fetch, and not --offline) to hit the network.
    bid_st = po_bids.fill_po_bids(items, fetch=bool(fetch_bids))
    po_st = dict(po_st, bids=bid_st)
    collect_items._po_stats = po_st
    return items

def zips_of(x): return re.findall(r'\b(3\d{4})\b', x.get('addr', ''))
def street_of(x): return x.get('street') or re.sub(r'\s+3\d{4}\b.*$', '', x.get('addr', ''))

def prefetch_all(items, args):
    print(f'PropertyOnion: {len(items)} itens (somente os que faltam no cache são baixados)…', flush=True)
    po_fetch.prefetch([dict(street=street_of(it['raw']), zips=zips_of(it['raw']), known=it['known']) for it in items], threads=args.threads)

def county_slug(c): return c.replace('myorangeclerk', 'orange').replace('-', '')

def pid_variants(parcel):
    """normalised parcel ids to try against the DOR roll. Pinellas lists SS-TT-RR-… (section first) on RealAuction
    while the DOR roll stores RR TT SS …; without the swap those lots fell back to a street-name match (wrong parcel)."""
    out = []
    p = nal.npid(parcel)
    if p: out.append(p)
    m = re.match(r'\s*(\d{2})-(\d{2})-(\d{2})-(.+)$', str(parcel or ''))
    if m:
        q = nal.npid(m.group(3) + m.group(2) + m.group(1) + m.group(4))
        if q and q not in out: out.append(q)
    return out

MTG_RATE = [(2025, 6.6), (2023, 6.8), (2022, 5.3), (2020, 3.0), (2013, 4.1), (2011, 4.2), (2008, 5.2), (2001, 6.3), (0, 7.5)]   # avg 30-yr fixed, %/yr

def mtg_balance(orig, rec_date, today):
    """estimated balance of a 30-year fixed loan today -> (balance, explanation). No date: the original amount (conservative)."""
    if not orig: return None, ''
    m = re.match(r'(\d{4})-(\d{2})', str(rec_date or ''))
    if not m: return orig, f'Saldo: sem data de registro, usando o valor original US$ {orig:,.0f} (conservador).'
    y, mo = int(m.group(1)), int(m.group(2))
    ty, tm = int(today[:4]), int(today[5:7])
    k = max(0, (ty - y) * 12 + (tm - mo))
    rate = next(r for yy, r in MTG_RATE if y >= yy) / 100 / 12
    n = 360
    if k >= n: return 0.0, f'Saldo: hipoteca de {y} já quitada pelo prazo de 30 anos.'
    bal = orig * ((1 + rate) ** n - (1 + rate) ** k) / ((1 + rate) ** n - 1)
    return bal, f'Saldo estimado US$ {bal:,.0f}: original US$ {orig:,.0f} de {y}, amortizado 30 anos a {rate * 1200:.1f}% a.a. ({k} meses).'

def nal_index(items, today):
    """match every item to the DOR roll of its county; returns (parcel facts by aid, sales by zip, county numbers)"""
    by_c = {}
    for it in items:
        x = it['raw']; c = county_slug(x.get('county') or '')
        if not c: continue
        d = by_c.setdefault(c, dict(p=set(), a=set(), its=[]))
        for pid in pid_variants(x.get('parcel')): d['p'].add(pid)
        zs = zips_of(x)
        st = nal.nstreet(re.sub(r'\s+(UNIT|APT|#)\s*\S+$', '', street_of(x)))
        # street name without a house number matches an arbitrary parcel on that street: parcel only
        if st and zs and re.match(r'\d', st): d['a'].add(st + '|' + zs[-1])
        d['its'].append(it)
    facts, sales, cono = {}, {}, {}
    zfiles = nal.zips()
    for c, d in sorted(by_c.items()):
        if c not in zfiles: continue
        m = re.search(r'_(\d{2})_', os.path.basename(zfiles[c])); cono[c] = m.group(1) if m else None
        cd = nal.load(c, d['p'], d['a'])
        if not cd: continue
        P_ = cd['parcels']
        for it in d['its']:
            x = it['raw']; zs = zips_of(x)
            st = nal.nstreet(re.sub(r'\s+(UNIT|APT|#)\s*\S+$', '', street_of(x)))
            f = next((P_['p:' + p] for p in pid_variants(x.get('parcel')) if ('p:' + p) in P_), None)
            how = 'parcela'
            if not f and st and zs and re.match(r'\d', st): f = P_.get('a:' + st + '|' + zs[-1]); how = 'endereço'
            if f: f = dict(f); f['how'] = how; facts[x['aid']] = f
        for s in cd['sales']: sales.setdefault(s[0], []).append(s)
    return facts, sales, cono

def build_items(args):
    cal = load_calendar()
    offline = bool(getattr(args, 'offline', False)) or os.environ.get('LEILOES_OFFLINE', '').strip().lower() in ('1', 'true', 'yes', 'on')
    if offline and args.fetch:
        print('offline: sem rede (PropertyOnion/FLWMI/RealAuction) — usando só cache local', flush=True)
        args.fetch = False
    fetch_bids = (not offline) and bool(getattr(args, 'fetch_bids', False) or args.fetch)
    items = collect_items(fetch_bids=fetch_bids)
    if args.fetch: prefetch_all(items, args)
    today = args.data_date
    facts, sales_by_zip, cono = nal_index(items, today)
    ares, _, _ = load_results()
    seen = jload(os.path.join(CACHE, 'seen_v4.json'), {})
    baseline = not seen                      # first v4 run: nothing is 'new'
    mk = load_market()
    zcounty = zip_county_map()
    out, dropped, done, fw_jobs = [], {}, set(), []
    def drop(reason): dropped[reason] = dropped.get(reason, 0) + 1
    for it in items:
        x, src = it['raw'], it['src']
        key = src + x['aid']
        if key in done: continue
        done.add(key)
        d_iso = iso(x['date'])
        if d_iso < today: drop('leilão já passou'); continue
        c = cal.get((x.get('host'), x['date'], src)) if src in ('TD', 'FC') else None
        if d_iso == today and c and c['active'] == 0: drop('leilão de hoje já encerrado'); continue
        poe0 = it.get('poe') or {}
        if not x.get('parcel') and poe0.get('parcel'):
            x['parcel'] = poe0.get('parcel_raw') or poe0['parcel']
        if not x.get('addr', '').strip() and poe0.get('addr'):
            x['addr'] = poe0['addr']; x['street'] = poe0.get('street') or ''
            x['addr_src'] = 'PropertyOnion (o RealAuction ainda não publicou o endereço)'
        addr0 = x.get('addr', '').strip()
        if re.search(r'TIMESHARE', str(x.get('parcel') or ''), re.I) or re.search(r'\(ct\s', x.get('case') or ''):
            drop('timeshare'); continue
        if x.get('multi') and not addr0:
            drop('múltiplas parcelas (sem endereço)'); continue
        if not addr0 and not x.get('parcel'):
            drop('RealAuction ainda sem endereço e sem parcela (só o processo)'); continue
        if not addr0:
            x['addr'] = 'Parcela ' + str(x['parcel']) + ' (' + county_name(county_slug(x.get('county') or '')) + ')'
            x['street'] = ''; x['addr_src'] = 'RealAuction sem endereço — identificado pela parcela'
        elif not re.search(r'\d', x['addr']) and not x.get('parcel'):
            drop('rua sem número e sem parcela'); continue
        st0 = street_of(x)
        known0 = it['known'] if (it['known'] and it['known'].get('id')) else None
        if re.match(r'\s*\d', st0 or '') or known0:
            pid, slug, full = po_fetch.resolve(st0, zips_of(x), None, it['known'], fetch=False)
        else:
            pid = slug = full = None      # street name only: PO search would pick a random parcel on the street
        P0 = full or it['known'] or {}
        has_po = bool(pid and P0) or bool(it.get('poe'))
        nf = facts.get(x['aid'])
        cs = county_slug(x.get('county') or '') or zcounty.get((zips_of(x) or [''])[-1], '')
        if not cs: drop('condado desconhecido'); continue
        # ---- values
        av = num(x.get('av')); mkt = num(P0.get('marketTotalValue'))
        o = it.get('ocpa'); ocpa_mkt = num(o['vals'][0].get('marketValue')) if (o and o.get('vals')) else None
        lk = it.get('lake'); lake_mv = num(lk.get('mv')) if lk else None
        jv = num(nf.get('jv')) if nf else None
        avm = num(P0.get('currentAVMValue'))
        acres = num(P0.get('lotSizeAcres'))
        if acres is None and num(P0.get('lotSizeSqFt')): acres = num(P0.get('lotSizeSqFt')) / 43560
        if acres is None and nf and nf.get('lsq'): acres = nf['lsq'] / 43560
        sqft = num(P0.get('sumLivingAreaSqFt')) or (num(nf.get('lvg')) if nf else None)
        yr = num(P0.get('yearBuilt')) or (num(nf.get('ayb')) if nf else None)
        if yr and yr < 1800: yr = None
        lu = dictval(P0.get('landUseCode'))
        uc = (nf or {}).get('uc')
        ty = type_from_dor(uc, acres, lu) if uc else None
        tsrc = 'DOR (código de uso do condado)' if ty else None
        if not ty:
            ty = type_from_po(lu, acres, sqft, x.get('addr', ''))
            tsrc = 'PropertyOnion' if ty else None
        if not ty:
            ty = type_fallback(dict(it, raw=x), P0, sqft, acres); tsrc = 'inferido (dados incompletos)'
        if src == 'PV' and x.get('desc'):
            dsc = x['desc'].upper()
            if re.search(r'WAREHOUSE|COMMERCIAL|LAUNDRY|OFFICE|RETAIL', dsc): ty = 'Comercial'
            elif re.search(r'\bAC\b.*(DEVELOPMENT|PARCEL|SITE)|ACRE (WATERFRONT )?PARCEL|LAND', dsc) and not re.search(r'\d\s*BR', dsc): ty = 'Terreno' if (acres or 0) >= 1 or re.search(r'(\d+\.?\d*)\s*(\+/-|±)?\s*AC', dsc) else 'Lote'
            elif re.search(r'\d\s*BR', dsc): ty = ty if ty in ('Casa', 'Mobile', 'Condo', 'Townhouse') else 'Casa'
            tsrc = tsrc or 'descrição do leilão'
        land = ty in ('Lote', 'Terreno')
        poe = it.get('poe') or {}
        if not ty and poe.get('prop_type'):
            ty = po_export.type_from_prop(poe.get('prop_type'), num(poe.get('sqft')), num(poe.get('lot')))
            if ty: tsrc = 'PropertyOnion (export)'; land = ty in ('Lote', 'Terreno')
        if not acres and poe.get('lot'):
            acres = num(poe.get('lot')) / 43560
        beds = num(P0.get('bedrooms')) or num(poe.get('beds'))
        baths = num(P0.get('bathTotalCalc')) or num(poe.get('baths'))
        if not sqft and poe.get('sqft'): sqft = num(poe.get('sqft'))
        if land: beds = baths = sqft = yr = None
        if poe.get('cmv') and not mkt: mkt = num(poe.get('cmv'))
        mvals = [v for v in [av, mkt, ocpa_mkt, lake_mv, jv] if v]
        base = max(mvals) if mvals else None
        legal = (P0.get('legalDescription') or x.get('legal') or (nf or {}).get('leg') or '')
        lbcs = ' '.join(str(P0.get(k) or '') for k in ('lbcs_site_desc', 'lbcs_function_desc'))
        junk = bool((uc in JUNK_UC) or (land and JUNK_RE.search(legal + ' ' + lbcs)) or (land and acres is not None and acres < 0.05))
        # comps (DOR qualified sales)
        zip5 = str(P0.get('situsZIP5') or '') or (nf or {}).get('zip') or (zips_of(x) or [''])[-1] or None
        lsq = (nf or {}).get('lsq') or (acres * 43560 if acres else None)
        cp = comps_for(sales_by_zip, zip5, uc, sqft, int(yr) if yr else None, lsq, nal.nstreet((nf or {}).get('addr') or street_of(x)), ty) if zip5 else None
        cest = cp.get('est') if cp else None
        def _usd(v):
            return f"US$ {v:,.0f}"
        named = []
        if av: named.append(('avaliação no leilão', av))
        if mkt: named.append(('mercado (condado/PO)', mkt))
        if ocpa_mkt: named.append(('mercado OCPA', ocpa_mkt))
        if lake_mv: named.append(('mercado Lake', lake_mv))
        if jv: named.append(('just value DOR', jv))
        base_lbl = None
        if named:
            topn = max(named, key=lambda kv: kv[1])
            bits = ', '.join(f"{n} {_usd(v)}" for n, v in named)
            base_lbl = (f"{topn[0]} {_usd(topn[1])}" if len(named) == 1 else f"maior valor oficial = {topn[0]} {_usd(topn[1])} [{bits}]")
        if land:
            if base:
                val, vsrc = base, f"maior valor oficial do condado — {base_lbl}"
            elif avm:
                val, vsrc = avm, f"AVM PropertyOnion {_usd(avm)} (terreno, sem valor de condado)"
            else:
                val, vsrc = None, None
        elif base and avm:
            chosen = min(base, avm)
            which = 'o valor do condado' if base <= avm else 'o AVM PropertyOnion'
            val = chosen
            vsrc = f"menor entre {base_lbl} e AVM PropertyOnion {_usd(avm)} → vale {which} {_usd(chosen)}"
        elif base:
            val, vsrc = base, f"valor do condado, sem AVM — {base_lbl}"
        elif avm:
            val, vsrc = avm, f"AVM PropertyOnion {_usd(avm)} (sem valor de condado)"
        else:
            val, vsrc = None, None
        if not val and cest:
            val = cest; vsrc = 'comps DOR (estimativa)'
        pov = num(poe.get('pov')); pov_conf = num(poe.get('pov_conf'))
        county_for_pov = next((v for v in [mkt, ocpa_mkt, lake_mv, jv, av] if v), None)
        pov_as_arv = False
        if po_export.pov_ok_for_arv(pov, pov_conf, county_for_pov):
            val = pov
            vsrc = f"POV PropertyOnion {_usd(pov)} (confiança {int(pov_conf)}; dentro de ~35% do condado {_usd(county_for_pov)}) — usado como ARV"
            pov_as_arv = True
        elif not val and pov:
            val = pov
            vsrc = f"POV PropertyOnion {_usd(pov)} (sem valor de condado para comparar) — usado como ARV"
            pov_as_arv = True
        jv85 = None
        if (val and base and val == base and not pov_as_arv and not avm and not (cp and (cp.get('n') or 0) >= 3 and cest)):
            # Florida just value is set ~15% under market (cost-of-sale deduction, F.S. 193.011(8)); with nothing better, gross it up
            jv85 = val; val = base / 0.85
            vsrc = f"{vsrc} ÷ 0,85 = {_usd(val)} (só valor do condado: o just value fica ~15% abaixo do mercado, F.S. 193.011(8))"
        if val and val < 1000: val = None
        ref = num(x.get('ob')) if src == 'TD' else num(x.get('fj')) if src == 'FC' else num(x.get('ref'))
        nobid = bool(it.get('po_only') and not ref)
        if it.get('bid_fill') and ref:
            notes.append(f"Julgamento/lance obtido no RealAuction ({it['bid_fill'].get('how')}).")
        pool = bool(dictval(P0.get('poolCode')))
        units = (nf or {}).get('nu') or num(P0.get('sumResidentialUnits'))
        repairs, rwhy = rehab_for(ty, int(yr) if yr else None, pool, units)
        # ---- location
        lat, lon = num(P0.get('situsLatitude')), P0.get('situsLongitude')
        try: lon = float(lon) if lon is not None else None
        except Exception: lon = None
        util = None; gsrc = 'PropertyOnion'
        co_no = cono.get(cs)
        if nf and co_no:
            util = flwmi.get_by_parcel(co_no, nf.get('pid'))
            if util is not None and not util.get('_n'): util = None
            if args.fetch and util is None: fw_jobs.append(('p', co_no, nf.get('pid')))
        if not (lat and lon and 24 < lat < 31.2 and -88 < lon < -79.8):
            lat = lon = None
            if util and util.get('_lat'): lat, lon = round(util['_lat'], 6), round(util['_lon'], 6); gsrc = 'FDOH/DOR (centro da parcela)'
        if util is None and lat and lon:
            util = flwmi.get(lat, lon)
            if util is not None and not util.get('_n'): util = None
            if util is not None: util['_pt'] = 1
            if args.fetch and util is None: fw_jobs.append(('g', lat, lon))
        if lat and lon:
            dist = hav(ORLANDO, (lat, lon)); dapprox = False
        else:
            cc = COUNTY_LL.get(cs); dist = hav(ORLANDO, cc) if cc else None; dapprox = True
        # ---- PO auctions for same date
        same = [a for a in (P0.get('auctions') or []) if (a.get('auction_date') or '').startswith(d_iso)]
        plaint_raw = ' '.join(str(a.get('auction_plaintiffs') or '') for a in same)
        defend = ' '.join(str(a.get('auction_defend') or '') for a in same)
        status = [a.get('auction_status') for a in same]
        # ---- flags
        flags, notes = [], []
        occ_v = str(dictval(P0.get('ownerOccupied')) or '').lower()
        owner = (P0.get('ownerNAME1FULL') or (nf or {}).get('own') or (o or {}).get('owner') or (lk or {}).get('owner') or (poe.get('owner') if poe else None) or x.get('owner') or '').strip()
        owner2 = P0.get('ownerNAME2FULL') or ''
        mail = norm_street(P0.get('mailingFullStreetAddress') or (nf or {}).get('oa')); situs = norm_street(P0.get('situsFullStreetAddress') or (nf or {}).get('addr'))
        homestead = P0.get('homesteadInd') is True or bool((nf or {}).get('hm'))
        occupied = occ_v in ('yes', 'owner occupied') or homestead or (bool(mail) and mail == situs)
        absentee = occ_v == 'absentee' or (bool(mail) and bool(situs) and mail != situs)
        if poe.get('owner_occ'): occupied, absentee = True, False
        if poe.get('vacant') and not land: occupied, absentee = False, False
        if land: occupied = absentee = False
        if occupied: flags.append('occ')
        if DECEASED_RE.search(owner + ' ' + owner2) or (src == 'FC' and re.search(r'DECEASED|ESTATE OF|UNKNOWN HEIRS', defend, re.I)): flags.append('dec')
        usps_vac = P0.get('usps_vacancy') == 'Y' or str(dictval(P0.get('vacantFlag')) or '').upper() in ('Y', 'YES') or bool(poe.get('vacant'))
        if absentee and not occupied and not land and not usps_vac: flags.append('ten')
        if src == 'FC' and CODE_RE.search(defend): flags.append('code')
        hoa_pl = bool(src == 'FC' and HOA_RE.search(plaint_raw))
        m1 = num(P0.get('mtg1LoanAmt')); m1d = (P0.get('mtg1RecordingDate') or '')[:4]
        mtg_surv = False
        if src == 'FC':
            if it.get('avoid'): mtg_surv = True
            elif hoa_pl and (m1 or 0) > 0: mtg_surv = True
            elif m1 and ref and m1d and m1d >= '2012' and m1 > 1.3 * ref:
                lender_tok = set(re.findall(r'[A-Z]{4,}', (P0.get('mtg1Lender') or '').upper())) - {'BANK', 'MORTGAGE', 'NATIONAL', 'ASSOCIATION', 'TRUST', 'FINANCIAL', 'LOAN', 'CORP', 'CORPORATION', 'COMPANY', 'SERVICES', 'HOME', 'FUNDING'}
                if not (lender_tok & set(re.findall(r'[A-Z]{4,}', plaint_raw.upper()))): mtg_surv = True
            if mtg_surv: flags.append('mtg')
            if hoa_pl: flags.append('hoa')
            if ref and val and ref < 0.5 * val: flags.append('jr')
        if 'hoa' not in flags and ty in ('Condo', 'Townhouse'): flags.append('hoa')
        # Surviving-lien estimate (PropertyOnion + plaintiff heuristics). Deducts the ESTIMATED CURRENT BALANCE of the 1st
        # mortgage (original amount amortised over 30 years from its recording date); without a date, the original amount.
        # 'Judgment < 50% of value' alone no longer implies a surviving 1st (old, mostly paid loans look the same): it stays a warning.
        surv_amt = None; surv_why = None; surv_orig = None
        olA_v = num(P0.get('totalOpenLienAmt')) or (num(poe.get('liens_amt')) if poe else None)
        m1_bal, m1_how = mtg_balance(m1, P0.get('mtg1RecordingDate'), today)
        if src == 'FC':
            if hoa_pl and (m1 or olA_v):
                surv_amt = m1_bal if m1 else olA_v; surv_orig = m1 if m1 else None
                surv_why = 'Execução de HOA/condomínio: a 1ª hipoteca (ou liens PO) provavelmente SOBREVIVE ao leilão. ' + (m1_how if m1 else 'Valor: liens em aberto do PropertyOnion.')
                if 'mtg' not in flags: flags.append('mtg')
                if 'surv' not in flags: flags.append('surv')
            elif mtg_surv and m1:
                surv_amt = m1_bal; surv_orig = m1
                surv_why = 'Indício de execução júnior: 1ª hipoteca recente (PO) maior que o julgamento e autor ≠ credor da 1ª. ' + m1_how
                if 'surv' not in flags: flags.append('surv')
        elif src == 'TD':
            if CODE_RE.search(defend or '') or (olA_v and not m1 and 'code' in flags):
                surv_why = 'Tax deed: hipotecas privadas costumam ser extintas, mas liens municipais/code enforcement podem sobreviver – confirmar title search.'
                if 'surv' not in flags: flags.append('surv')
                surv_amt = None
        fz = (P0.get('fema_flood_zone') or '').upper().strip()
        if fz and re.match(r'^(A|V)', fz): flags.append('flood')
        if occupied and ref and val and ref < (0.10 if src == 'TD' else 0.25) * val: flags.append('red')
        if not has_po and not nf and not poe: flags.append('unv')
        if any(s and s.lower().startswith('cancel') for s in status): flags.append('cxl')
        if nobid: flags.append('nobid'); notes.append('Sem julgamento/lance inicial (fonte PropertyOnion export) – ROI no preço esperado do condado quando houver histórico.')
        if usps_vac and not land: flags.append('vac')
        if junk: flags.append('junk')
        if homestead and src == 'TD': flags.append('hmtd')
        if it.get('avoid'): flags.insert(0, 'avoid'); notes.insert(0, AVOID[it['avoid']])
        if d_iso == today: notes.insert(0, 'Leilão HOJE – provavelmente já encerrado; confirme no site.')
        # ---- photos (remote URLs, lazy-loaded; nothing embedded)
        imgs = []
        for k in ('images', 'manual_img', 'prop_cntypicurl', 'googlestreet_pic', 'googlemap_pic', 'prop_hudpicurl', 'wholesaler_pic1', 'wholesaler_pic2', 'wholesaler_pic3'):
            v = P0.get(k)
            for u in (v if isinstance(v, list) else [v]):
                if isinstance(u, str) and u.startswith('http') and u not in imgs and not re.search(r'maps\.googleapis\.com', u): imgs.append(u)
        if x.get('img'): imgs.insert(0, x['img'])
        # ---- links
        po_url = f'https://propertyonion.com/property_search/properties/{slug}/{pid}' if (pid and slug) else None
        if not po_url and poe.get('po_url'): po_url = poe['po_url']
        pa = P0.get('prop_appraiserlink') or x.get('plink') or (poe.get('appraiser') if poe else None)
        if pa and ('key=&' in pa or pa.endswith('/parcel/') or 'MULTIPLE' in pa): pa = None
        addr = re.sub(r',\s*FL-?\s*', ', FL ', x['addr']).replace(' ,', ',').strip()
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
        city = dictval(P0.get('situsCity')) or (nf or {}).get('city')
        tdy = num(P0.get('taxDeliquentYear')); tdy = int(tdy) if tdy and 1990 < tdy <= int(today[:4]) else None
        lsp = num(P0.get('currentSalesPrice')); lsd = (P0.get('currentSaleRecordingDate') or '')[:10] or None
        if not lsp and nf and nf.get('s1') and nf['s1'][0] and nf['s1'][1]:
            lsp = nf['s1'][0]; lsd = f"{nf['s1'][1]}-{(nf['s1'][2] or 1):02d}"
        taxamt = num(P0.get('taxAmt')); taxamt = taxamt if taxamt and taxamt > 10 else None
        front = num(P0.get('lotSizeFrontageFeet')); front = front if front and front > 5 else None
        sewer = dictval(P0.get('sewerCode'))
        # ---- expected auction price from county history (3rd-party sales, sold / assessed value)
        st_c = ares.get(cs + '|' + src) if src in ('TD', 'FC') else None
        st_s = ares.get('*|' + src) if src in ('TD', 'FC') else None
        rs = st_c if (st_c and st_c.get('nrav', 0) >= 5) else st_s
        xp = None
        if rs and rs.get('rav_med') and av:
            xp = dict(v=round(max(ref or 0, rs['rav_med'] * av)), va=round(rs['rav_med'] * av), r=rs['rav_med'], n=rs['nrav'], lvl='condado' if rs is st_c else 'estado',
                      lo=round(max(ref or 0, (rs.get('rav_p25') or rs['rav_med']) * av)), hi=round(max(ref or 0, (rs.get('rav_p75') or rs['rav_med']) * av)))
        # foreclosures: 3rd parties often win BELOW the judgment (the bank accepts less) -> sold/judgment ratio
        rj = None
        if src == 'FC':
            rj_c = st_c if (st_c and st_c.get('nrref', 0) >= 5 and st_c.get('rref_med')) else None
            rj_s = rj_c or (st_s if (st_s and st_s.get('rref_med')) else None)
            if rj_s: rj = dict(r=rj_s['rref_med'], n=rj_s.get('nrref'), lvl='condado' if rj_s is rj_c else 'estado')
        zm = mk.get(zip5) if zip5 else None
        dom = None
        if zm and zm.get('rf') and zm['rf'][-1].get('dom') is not None and (zm['rf'][-1].get('sold') or 0) >= 3: dom = zm['rf'][-1]['dom']
        zori = (zm or {}).get('zr')
        rent = num(P0.get('estimatedRentalValue')); rsrc = 'PropertyOnion' if rent else None
        if not rent and poe.get('pov_rent'): rent = num(poe.get('pov_rent')); rsrc = 'PropertyOnion (export)'
        if not rent and zori and not land and ty != 'Comercial': rent = zori; rsrc = 'Zillow ZORI (mediana do ZIP)'
        first = seen.get(key) or ('0000-00-00' if baseline else today)
        seen[key] = first
        rec = dict(
            id=key, t=src, ty=ty, tsrc=tsrc, uc=uc, ucd=DOR_DESC.get(uc) if uc else None, co=county_name(cs), cs=cs,
            date=d_iso, time=et_time(c) if c else x.get('time'), addr=addr, owner=owner or None, case=x.get('case'), parcel=x.get('parcel'),
            ref=ref, av=av, mkt=mkt or ocpa_mkt or lake_mv, jv=jv, avm=avm, avmLo=num(P0.get('vlowValue')), avmHi=num(P0.get('vhighValue')),
            rent=rent, rsrc=rsrc, val=round(val) if val else None, vsrc=vsrc,
            pov=round(pov) if pov else None, povConf=int(pov_conf) if pov_conf else None,
            povAsArv=pov_as_arv or None, clv=num(poe.get('clv')) if poe else None,
            prevSale=poe.get('prev_sale_type') if poe else None,
            nobid=nobid or None, poeHow=(poe.get('how') if poe else None),
            survAmt=round(surv_amt) if surv_amt else None, survWhy=surv_why, survOrig=round(surv_orig) if surv_orig else None,
            rj=rj, jv85=round(jv85) if jv85 else None,
            survDeduct=True if (surv_amt and hoa_pl and src=='FC') else None,
            beds=beds, baths=baths, sqft=sqft, yr=int(yr) if yr else None, ac=round(acres, 3) if acres else None,
            zon=P0.get('zoning') or None, fz=fz or None, lat=lat, lon=lon, gsrc=gsrc if lat else None,
            dist=round(dist) if dist is not None else None, dap=dapprox, rep=repairs, repw=rwhy,
            fl=flags, note=' '.join(notes[:3]) or None, links=dict(auc=x.get('detail'), po=po_url, pa=pa, list=x.get('url')),
            imgs=imgs[:8], zip=zip5, city=str(city).title() if city else None, plaint=plaintiff, hist=hist[:8], tdy=tdy, lsp=lsp, lsd=lsd,
            m1=m1, m1d=(P0.get('mtg1RecordingDate') or '')[:10] or None, m1l=P0.get('mtg1Lender') or None,
            m2=num(P0.get('mtg2LoanAmt')), m2d=(P0.get('mtg2RecordingDate') or '')[:10] or None,
            olA=num(P0.get('totalOpenLienAmt')) or num(poe.get('liens_amt')),
            olN=num(P0.get('totalOpenLienNbr')) or num(poe.get('liens_n')),
            olSrc=('PropertyOnion' if (num(P0.get('totalOpenLienAmt')) or num(poe.get('liens_amt'))) else None),
            hoaPl=hoa_pl, hm=homestead,
            pool=pool, eyb=int(num(P0.get('effectiveYearBuilt'))) if num(P0.get('effectiveYearBuilt')) and num(P0.get('effectiveYearBuilt')) > 1800 else None,
            hasPO=has_po, nalm=(nf or {}).get('how'), tax=taxamt, front=front, sewer=sewer, units=units,
            util=({k: util.get(k) for k in ('WW', 'WW_UPD', 'WW_SRC_TYP', 'DW', 'DW_UPD', 'DW_SRC_TYP', 'PARCELNO', 'LANDUSE', 'BLT_STATUS', 'GIS_ACRE')} | {'pt': util.get('_pt', 0)}) if util else None,
            comps=cp, xp=xp, dom=dom, desc=x.get('desc'),
            plat=('PropertyOnion' if it.get('po_only') else x.get('platform')),
            pmax=x.get('pmax') if x.get('pmax') not in (None, 'Hidden') else None,
            new=first == today, first=first if first != '0000-00-00' else None, muni=dictval(P0.get('municipality')),
        )
        rec = {k: v for k, v in rec.items() if v not in (None, '', [], {})}
        rec.setdefault('fl', []); rec.setdefault('links', {})
        out.append(rec)
    if args.fetch and fw_jobs:
        import requests
        from concurrent.futures import ThreadPoolExecutor
        print(f'FLWMI (água/esgoto): {len(fw_jobs)} consultas…', flush=True)
        def job(j):
            s = requests.Session(); s.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) leiloes-florida dashboard (personal research)'
            if j[0] == 'p': flwmi.get_by_parcel(j[1], j[2], fetch=True, sess=s)
            else: flwmi.get(j[1], j[2], fetch=True, sess=s)
        with ThreadPoolExecutor(3) as ex: list(ex.map(job, fw_jobs))
        print('  (utilidades baixadas – rode o build de novo sem --fetch para incorporá-las, ou elas entram na próxima execução)', flush=True)
    json.dump(seen, open(os.path.join(CACHE, 'seen_v4.json'), 'w'))
    po_st = getattr(collect_items, '_po_stats', {}) or {}
    stats = dict(total=len(items), kept=len(out), nal=sum(1 for r in out if r.get('nalm')), po=sum(1 for r in out if r.get('hasPO')),
                 poExport=po_st, pov=sum(1 for r in out if r.get('pov')), povArv=sum(1 for r in out if r.get('povAsArv')),
                 poOnly=sum(1 for r in out if r.get('plat') == 'PropertyOnion'))
    return out, stats, dropped

def zip_county_map():
    """ZIP -> county slug from the Zillow files (CountyName column)."""
    out = {}
    for fn in ('zillow_zori_zip.csv', 'zillow_zhvi_zip.csv'):
        p = os.path.join(CACHE, 'market', fn)
        if not os.path.exists(p): continue
        with open(p, encoding='utf-8') as f:
            rd = csv.reader(f); h = next(rd)
            try: iz, ist, ic = h.index('RegionName'), h.index('State'), h.index('CountyName')
            except ValueError: continue
            for row in rd:
                if row[ist] != 'FL': continue
                out.setdefault(row[iz].zfill(5), re.sub(r'[^a-z]', '', row[ic].lower().replace(' county', '')))
    return out

# ----------------------------------------------------------------------------- ZIP market data (free public bulk files)
MKT = os.path.join(CACHE, 'market')
REDFIN_URL = 'https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz'
ZORI_URL = 'https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv'
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
    with requests.get(ZORI_URL, timeout=120) as r:
        open(os.path.join(MKT, 'zillow_zori_zip.csv'), 'wb').write(r.content)

def _f(v):
    try:
        v = float(str(v).replace('"', '')); return None if v != v else v
    except Exception: return None

def load_market():
    """Compact FL ZIP market dict {zip: {rf:{...}, zh:{...}}} (cached in cache/market/market_fl.json)."""
    comp = os.path.join(MKT, 'market_fl.json')
    rf_raw, zh_raw = os.path.join(MKT, 'redfin_zip_fl.tsv'), os.path.join(MKT, 'zillow_zhvi_zip.csv')
    zr_raw = os.path.join(MKT, 'zillow_zori_zip.csv')
    raws = [p for p in (rf_raw, zh_raw, zr_raw) if os.path.exists(p)]
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
    if os.path.exists(zr_raw):
        with open(zr_raw, encoding='utf-8') as f:
            rd = csv.reader(f); h = next(rd); months = [c for c in h if re.match(r'\d{4}-\d{2}-\d{2}$', c)]
            for row in rd:
                if row[h.index('State')] != 'FL': continue
                z = row[h.index('RegionName')].zfill(5)
                v = next((_f(row[h.index(c)]) for c in reversed(months[-6:]) if _f(row[h.index(c)])), None)
                if v: out.setdefault(z, {})['zr'] = round(v)
        src['zori'] = dict(end=months[-1], name='Zillow Research – ZORI (aluguel típico observado por ZIP)', url='https://www.zillow.com/research/data/')
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
def load_events(today):
    ev = jload(os.path.join(SW, 'events.json'), [])
    seen, out = set(), []
    for h, d, k, n, t in ev:
        c = h.split('.')[0].replace('-', '').replace('myorangeclerk', 'orange')
        di = iso(d); kk = 'TD' if k == 'Tax Deed' else 'FC'
        if di < today or (c, di, kk) in seen: continue
        seen.add((c, di, kk)); out.append([di, county_name(c), kk, n, t])
    return sorted(out)

def render(items, stats, dropped, args):
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    mk = load_market()
    zips = {}
    for it in items:
        z = it.get('zip')
        if z and z in mk and z not in zips and mk[z].get('rf'):
            zips[z] = dict(rf=mk[z]['rf'], zh=mk[z].get('zh'), zr=mk[z].get('zr')); zips[z]['rt'] = resale_temp(mk[z].get('rf'))
    ares, recent, rmeta = load_results()
    meta = dict(dataDate=args.data_date, built=time.strftime('%Y-%m-%d %H:%M'), params=P, zips=zips, mktSrc=mk.get('_src', {}),
                rehabTiers=REHAB_TIERS, rehabUnknown=REHAB_UNKNOWN, rehabPool=REHAB_POOL, stats=stats, dropped=dropped, orlando=ORLANDO,
                events=load_events(args.data_date), ares=ares, recent=recent, rmeta=rmeta, types=TYPES, version='v4')
    data = json.dumps(dict(meta=meta, items=items), ensure_ascii=False, separators=(',', ':'))
    if args.no_compress:
        blob = 'J:' + data.replace('</', '<\\/')
    else:
        blob = 'G:' + base64.b64encode(gzip.compress(data.encode('utf-8'), 9)).decode()
    return tpl.replace('/*__DATA__*/null', blob), len(data)

# ----------------------------------------------------------------------------- site / PWA assets (GitHub Pages)
THEME = '#0d1b2a'          # header navy (template.html --navy); keep in sync with <meta name="theme-color">
NAVY2, GOLD = '#1b2d45', '#c9a227'
BG = '#343b47'             # cinza2 page background (template.html --bg): PWA splash / background_color + password screen
MANIFEST = {
    'name': 'LEILÃO – Leilões Flórida', 'short_name': 'LEILÃO',
    'description': 'Leilões de tax deed e foreclosure na Flórida – CHALLENGE CAPITAL',
    'lang': 'pt-BR', 'start_url': './', 'scope': './', 'display': 'standalone',
    'background_color': BG, 'theme_color': THEME,
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
            '--template-color-primary', '#0d1b2a', '--template-color-secondary', BG]
    env = dict(os.environ, STATICRYPT_PASSWORD=pw)
    r = subprocess.run(cmd, env=env, cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0: sys.exit('staticrypt failed: ' + (r.stderr or r.stdout)[-2000:])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true', help='fetch missing PropertyOnion pages + FLWMI utilities into ./cache (polite)')
    ap.add_argument('--fetch-bids', action='store_true', help='also query RealAuction for missing PO-only opening bids (skipped when --offline or LEILOES_OFFLINE=1)')
    ap.add_argument('--offline', action='store_true', help='never contact RealAuction/PropertyOnion/FLWMI; local files + cache only (or set LEILOES_OFFLINE=1)')
    ap.add_argument('--threads', type=int, default=4, help='PropertyOnion fetch threads (each pauses between requests)')
    ap.add_argument('--no-images', action='store_true', help='(v3 compat; v4 never embeds images – photos are remote, lazy-loaded)')
    ap.add_argument('--fetch-market', action='store_true', help='download Redfin + Zillow ZIP files into ./cache/market')
    ap.add_argument('--data-date', default=dt.date.today().isoformat())
    ap.add_argument('--budget', type=float, default=None, help='(v3 compat, ignored: no budget cap in v4)')
    ap.add_argument('--out', default=None, help='output HTML (default leiloes-florida.html, or index.html with --site)')
    ap.add_argument('--site', action='store_true', help='GitHub Pages build: encrypted index.html + manifest/icons/robots.txt next to build.py')
    ap.add_argument('--password-file', default=PASSWORD_FILE, help='StaticCrypt password file (keep outside the repo)')
    ap.add_argument('--no-encrypt', action='store_true', help='with --site: write plaintext index.html (NOT for publishing)')
    ap.add_argument('--no-compress', action='store_true', help='embed plain JSON instead of gzip+base64 (debug)')
    args = ap.parse_args()
    encrypt = args.site and not args.no_encrypt
    if encrypt and not os.path.exists(args.password_file):
        sys.exit(f'password file not found: {args.password_file} (refusing to build an unprotected site; use --no-encrypt for local tests)')
    if args.out is None:
        args.out = os.path.join(HERE, '.plain', 'index.html') if encrypt else os.path.join(HERE, 'index.html' if args.site else 'leiloes-florida.html')
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    for d in ('po_full', 'search', 'market', 'nal', 'flwmi'): os.makedirs(os.path.join(CACHE, d), exist_ok=True)
    if args.fetch_market: fetch_market()
    items, stats, dropped = build_items(args)
    items.sort(key=lambda r: (r['date'], r['id']))
    html_s, raw_len = render(items, stats, dropped, args)
    open(args.out, 'w', encoding='utf-8').write(html_s)
    if args.site:
        write_site_assets(HERE)
        if encrypt:
            encrypt_page(args.out, HERE, args.password_file)
            print(f"encrypted -> {os.path.join(HERE, 'index.html')}  {os.path.getsize(os.path.join(HERE, 'index.html'))/1e6:.2f} MB (StaticCrypt)")
    from collections import Counter
    print(f"wrote {args.out}  {os.path.getsize(args.out)/1e6:.2f} MB (JSON {raw_len/1e6:.1f} MB before gzip)  items={len(items)}")
    print('por tipo:', dict(Counter(r['ty'] for r in items).most_common()))
    print('por leilão:', dict(Counter(r['t'] for r in items)), ' condados:', len({r['cs'] for r in items}))
    print('com foto:', sum(1 for r in items if r.get('imgs')), ' NAL:', stats['nal'], ' PO:', stats['po'], ' água/esgoto:', sum(1 for r in items if r.get('util')),
          ' comps:', sum(1 for r in items if (r.get('comps') or {}).get('est')), ' coords:', sum(1 for r in items if r.get('lat')))
    if stats.get('poExport'):
        pe = stats['poExport']
        print('PO export: matched', pe.get('matched'), 'added', pe.get('added'), pe.get('by_how'),
              '| POV', stats.get('pov'), 'como ARV', stats.get('povArv'), 'só-PO', stats.get('poOnly'))
        if pe.get('bids'):
            print('PO bids fill:', pe['bids'])
    print('removidos:', json.dumps(dropped, ensure_ascii=False))

if __name__ == '__main__':
    main()
