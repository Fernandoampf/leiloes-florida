#!/usr/bin/env python3
"""Wetland + flood risk per LOT, from the parcel POLYGON (not the address point).
- polygon: FDOR statewide cadastral (ArcGIS, by PARCEL_ID = NAL parcel id; covers all 67 counties)
- wetlands: USFWS NWI (ArcGIS MapServer/0) -> % of the parcel area per wetland type
- flood: FEMA NFHL flood hazard zones (MapServer/28) -> % of the parcel area per zone (exact area overlay, which also
  covers 'centroid + interior sample points')
Cache: AUC/statewide/georisk/cache.json keyed 'county|PARCEL_ID' (refresh after 90 days). Polite: ~0.4 s between requests,
at most LIMIT new parcels per run, stops on the first 403/429/503 from a host."""
import json, os, time, datetime as dt, warnings
import requests
warnings.filterwarnings('ignore', category=DeprecationWarning)
DIR = '/workspace/auc/statewide/georisk'; CACHE = os.path.join(DIR, 'cache.json')
FDOR = 'https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0/query'
NWI = 'https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0/query'
NFHL = 'https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query'
SFHA = {'A', 'AE', 'AH', 'AO', 'VE', 'V', 'A99', 'AR'}
UA = {'User-Agent': 'ChallengeCapital lot risk check (polite, cached)'}
MAXAGE = 90


def load():
    try: return json.load(open(CACHE))
    except Exception: return {}


def _q(url, geom, fields, s):
    r = s.post(url, data=dict(geometry=geom, geometryType='esriGeometryPolygon', inSR=4326, spatialRel='esriSpatialRelIntersects',
                              outFields=fields, returnGeometry='true', outSR=4326, f='json'), timeout=120)
    if r.status_code in (403, 429, 503): raise PermissionError(f'{r.status_code} {url}')
    j = r.json()
    if j.get('error'): raise RuntimeError(str(j['error'])[:120])
    return j.get('features', [])


def analyze(pid, s):
    from shapely.geometry import Polygon
    from shapely.ops import transform, unary_union
    import pyproj
    to_m = pyproj.Transformer.from_crs(4326, 3086, always_xy=True).transform   # Florida GDL Albers, meters
    r = s.get(FDOR, params=dict(where=f"PARCEL_ID='{pid}'", outFields='PARCEL_ID', returnGeometry='true', outSR=4326, f='json'), timeout=90)
    if r.status_code in (403, 429, 503): raise PermissionError(f'{r.status_code} FDOR')
    fs = r.json().get('features', [])
    if not fs: return dict(poly=False)
    rings = [x for f in fs for x in f['geometry'].get('rings', [])]
    poly = unary_union([Polygon(x).buffer(0) for x in rings if len(x) >= 4])
    pm = transform(to_m, poly)
    if pm.area <= 1: return dict(poly=False)
    geom = json.dumps(dict(rings=rings, spatialReference=dict(wkid=4326)))
    clip = poly.buffer(0.0005)

    def cover(feats, key):
        out = {}
        for f in feats:
            g = unary_union([Polygon(x).buffer(0) for x in f['geometry'].get('rings', []) if len(x) >= 4])
            g = g.intersection(clip)                      # clip the (often county-sized) zone to the parcel first, then project
            if g.is_empty: continue
            a = transform(to_m, g).intersection(pm).area
            k = f['attributes'].get(key) or '?'; out[k] = out.get(k, 0) + a
        return {k: round(100 * v / pm.area, 1) for k, v in out.items() if v > 0}
    time.sleep(0.4); wet = cover(_q(NWI, geom, 'WETLAND_TYPE', s), 'WETLAND_TYPE')
    # NWI types that are not wetland habitat for buildability purposes: deepwater lake/riverine are still water -> keep all
    time.sleep(0.4); fz = cover(_q(NFHL, geom, 'FLD_ZONE', s), 'FLD_ZONE')
    return dict(poly=True, ac=round(pm.area / 4046.86, 3), wet=wet, wetPct=round(min(100, sum(wet.values())), 1), fz=fz,
                sfhaPct=round(min(100, sum(v for k, v in fz.items() if k in SFHA)), 1))


def refresh(keys, offline=False, limit=600):
    """keys: iterable of (county, PARCEL_ID). Fetches missing/stale ones (at most `limit`). Returns stats."""
    c = load(); st = dict(asked=0, fetched=0, nopoly=0, err=0, blocked=None)
    if offline: return st
    today = dt.date.today()
    todo = []
    for co, pid in keys:
        k = f'{co}|{pid}'; e = c.get(k)
        if e and e.get('at') and (today - dt.date.fromisoformat(e['at'])).days < MAXAGE and 'err' not in e: continue
        todo.append((k, pid))
    st['asked'] = len(todo)
    os.makedirs(DIR, exist_ok=True)
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock(); stop = threading.Event(); tl = threading.local()

    def job(kp):
        k, pid = kp
        if stop.is_set(): return
        if not hasattr(tl, 's'): tl.s = requests.Session(); tl.s.headers.update(UA)
        try:
            res = analyze(pid, tl.s); res['at'] = today.isoformat()
        except PermissionError as e:
            st['blocked'] = str(e); stop.set(); return
        except Exception as e:
            res = dict(err=type(e).__name__, at=today.isoformat())
        with lock:
            c[k] = res
            if 'err' in res: st['err'] += 1
            else: st['fetched'] += 1; st['nopoly'] += 0 if res.get('poly') else 1
            if (st['fetched'] + st['err']) % 25 == 0: json.dump(c, open(CACHE, 'w'))
        time.sleep(0.4)
    with ThreadPoolExecutor(3) as ex: list(ex.map(job, todo[:limit]))
    json.dump(c, open(CACHE, 'w'))
    st['left'] = max(0, len(todo) - limit)
    return st
