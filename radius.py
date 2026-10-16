"""≈0.5 mi around a lot (true radius, not the PLSS section): parcels by use, single-parcel vacant-lot sales in 12 months,
builder buys, and new homes (built ≥ 2022). Source: FDOR Florida Statewide Cadastral (same public ArcGIS layer as geo_risk).

Why: PLSS sections are useless as a radius in giant plats (Highlands puts 12 k Sun 'n Lake parcels in ONE section).
Polite: 3 small requests per lot (parcel shape, counts by use code, recent vacant sales), 0.5 s pause, 3 workers,
cache 30 days in AUC/statewide/radius/cache.json; any HTTP error from the service stops the run (no retry storm).
"""
import datetime as dt, json, math, os, threading, time
from concurrent.futures import ThreadPoolExecutor

FDOR = 'https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0/query'
DIR = '/workspace/auc/statewide/radius'; PATH = os.path.join(DIR, 'cache.json')
R_M = 804.672   # 0.5 statute mile in metres (layer SR 102967 = Florida GDL Albers, metres)
UA = {'User-Agent': 'Mozilla/5.0 (ChallengeCapital; leiloes-florida)'}
TTL = 30
_lock = threading.Lock()

def load():
    try: return json.load(open(PATH))
    except Exception: return {}

def analyze(pid, s, today):
    import local_comps as lc
    r = s.get(FDOR, params=dict(where=f"PARCEL_ID='{pid}'", outFields='PARCEL_ID', returnGeometry='true', f='json'), timeout=90).json()
    F = r.get('features') or []
    if not F or not F[0].get('geometry'): return dict(at=today, found=False)
    ring = F[0]['geometry']['rings'][0]; sr = r.get('spatialReference') or {'wkid': 102967}
    cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
    circ = [[cx + R_M * math.cos(2 * math.pi * i / 32), cy + R_M * math.sin(2 * math.pi * i / 32)] for i in range(33)]
    base = dict(geometry=json.dumps(dict(rings=[circ], spatialReference=sr)), geometryType='esriGeometryPolygon', spatialRel='esriSpatialRelIntersects', f='json')
    time.sleep(0.5)
    d = s.post(FDOR, data=dict(base, where='1=1', groupByFieldsForStatistics='DOR_UC',
               outStatistics=json.dumps([dict(statisticType='count', onStatisticField='OBJECTID', outStatisticFieldName='n')])), timeout=120).json()
    if d.get('error'): raise RuntimeError(str(d['error'])[:120])
    uc = {f['attributes']['DOR_UC']: f['attributes']['n'] for f in d.get('features', [])}
    res = {k: v for k, v in uc.items() if k in ('000', '001', '002', '004', '005', '008')}
    ntot = sum(res.values()); nvac = res.get('000', 0)
    ty, tm = int(today[:4]), int(today[5:7]); lim = ty * 12 + tm - 12
    time.sleep(0.5)
    d = s.post(FDOR, data=dict(base, where=f"DOR_UC='000' AND VI_CD1='V' AND SALE_YR1>='{ty - 1}' AND SALE_PRC1>=1000",
               outFields='OWN_NAME,SALE_YR1,SALE_MO1,SALE_PRC1,M_PAR_SAL1', returnGeometry='false', resultRecordCount=2000), timeout=120).json()
    if d.get('error'): raise RuntimeError(str(d['error'])[:120])
    iv = lambda v, dflt: int(float(v)) if str(v or '').strip() not in ('', 'None') else dflt
    sales = [f['attributes'] for f in d.get('features', []) if iv(f['attributes'].get('SALE_YR1'), 0) * 12 + iv(f['attributes'].get('SALE_MO1'), 6) >= lim]
    single = [a for a in sales if not (a.get('M_PAR_SAL1') or '').strip()]
    cnt = {}
    for a in sales: cnt[(a.get('OWN_NAME') or '').strip()] = cnt.get((a.get('OWN_NAME') or '').strip(), 0) + 1
    bld, who = 0, {}
    for a in sales:
        own = (a.get('OWN_NAME') or '').strip(); n, o = lc.builder_name(own)
        if not n and cnt.get(own, 0) >= 3 and lc.CORP.search(o) and not lc.NOT_BLD.search(o) and not lc.LANDBANK.search(o): n = o.title()
        if n: bld += 1; who[n] = who.get(n, 0) + 1
    time.sleep(0.5)
    d = s.post(FDOR, data=dict(base, where=f"ACT_YR_BLT>={ty - 4} AND DOR_UC IN ('001','002','004','007')", returnCountOnly='true'), timeout=120).json()
    newh = d.get('count')
    return dict(at=today, found=True, nTot=ntot, nVac=nvac, nBuilt=ntot - nvac, pctBuilt=round(100 * (ntot - nvac) / ntot) if ntot else None,
                s12=len(single), bld=bld, who=sorted(who.items(), key=lambda t: -t[1])[:4], newH=newh, newSince=ty - 4)

def refresh(keys, offline=False, limit=700, today=None):
    """keys: iterable of (county, PARCEL_ID). Fetch missing / older than TTL days (at most `limit`)."""
    import requests
    today = today or dt.date.today().isoformat()
    c = load(); keys = list(dict.fromkeys(keys))
    stale = [k for k in keys if f'{k[0]}|{k[1]}' not in c or
             (dt.date.fromisoformat(today) - dt.date.fromisoformat(c[f'{k[0]}|{k[1]}'].get('at', '2000-01-01'))).days > TTL]
    st = dict(keys=len(keys), stale=len(stale), done=0, err=0, stopped=None)
    if offline or not stale: return st
    os.makedirs(DIR, exist_ok=True); tl = threading.local(); stop = threading.Event()
    def job(k):
        if stop.is_set(): return
        if not hasattr(tl, 's'): tl.s = requests.Session(); tl.s.headers.update(UA)
        try: e = analyze(k[1], tl.s, today)
        except requests.HTTPError as ex: stop.set(); st['stopped'] = str(ex)[:120]; return
        except Exception as ex:
            with _lock: st['err'] += 1
            if 'Too many' in str(ex) or '429' in str(ex): stop.set(); st['stopped'] = str(ex)[:120]
            return
        with _lock:
            c[f'{k[0]}|{k[1]}'] = e; st['done'] += 1
            if st['done'] % 25 == 0: json.dump(c, open(PATH, 'w'))
    with ThreadPoolExecutor(3) as ex: list(ex.map(job, stale[:limit]))
    json.dump(c, open(PATH, 'w'))
    return st
