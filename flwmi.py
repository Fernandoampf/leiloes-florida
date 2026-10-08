#!/usr/bin/env python3
"""Florida Dept. of Health – Florida Water Management Inventory (FLWMI), public ArcGIS service (no key):
drinking water (public / well) and wastewater (sewer / septic) per parcel, with Known/Likely/SomewhatLikely qualifier.
Point-in-parcel query by the property's coordinates. Cached in cache/flwmi/<lat>_<lon>.json. Polite: 1 thread, pause."""
import json, os, re, time
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, 'cache', 'flwmi')
URL = 'https://maps.floridahealth.gov/server/rest/services/FLWMI/FLWMI_Wastewater/FeatureServer/0/query'
FIELDS = 'CO_NO,LANDUSE,BLT_STATUS,PARCELNO,PHY_ADD1,PHY_CITY,GIS_ACRE,WW,WW_UPD,WW_SRC_TYP,DW,DW_UPD,DW_SRC_TYP,ASMNT_YR'

def key(lat, lon): return f'{lat:.6f}_{lon:.6f}'

def get(lat, lon, fetch=False, sess=None):
    p = os.path.join(C, key(lat, lon) + '.json')
    if os.path.exists(p):
        try: return json.load(open(p))
        except Exception: pass
    if not fetch: return None
    import requests
    s = sess or requests
    try:
        r = s.get(URL, params=dict(geometry=f'{lon},{lat}', geometryType='esriGeometryPoint', inSR=4326,
                  spatialRel='esriSpatialRelIntersects', outFields=FIELDS, returnGeometry='false', f='json'), timeout=30)
        j = r.json()
        if 'features' not in j: return None
        feats = [f['attributes'] for f in j['features']]
        d = feats[0] if feats else {}
        d['_n'] = len(feats); d['_date'] = time.strftime('%Y-%m-%d')
        json.dump(d, open(p, 'w'))
        return d
    except Exception:
        return None
    finally:
        time.sleep(0.5)

def prefetch(points):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) leiloes-florida dashboard (personal research)'
    n = 0
    for lat, lon in points:
        if get(lat, lon) is None:
            get(lat, lon, fetch=True, sess=s); n += 1
            if n % 200 == 0: print('  flwmi', n, flush=True)
    print('  flwmi fetched', n, flush=True)

def get_by_parcel(co_no, parcel, fetch=False, sess=None):
    """Fallback when the property has no coordinates: query by DOR county number + DOR parcel id; returns attributes
    plus _lat/_lon (bbox centre of the parcel polygon)."""
    safe = re.sub(r"[^0-9A-Za-z\-\. ]", '', str(parcel or ''))
    if not co_no or not safe: return None
    p = os.path.join(C, f'p_{co_no}_{re.sub(r"[^0-9A-Za-z]", "_", safe)}.json')
    if os.path.exists(p):
        try: return json.load(open(p))
        except Exception: pass
    if not fetch: return None
    import requests
    s = sess or requests
    try:
        r = s.get(URL, params=dict(where=f"CO_NO='{co_no}' AND PARCELNO='{safe}'", outFields=FIELDS, returnGeometry='true',
                  outSR=4326, geometryPrecision=6, f='json'), timeout=30)
        j = r.json()
        if 'features' not in j: return None
        d = {}
        if j['features']:
            f = j['features'][0]; d = f['attributes']
            pts = [pt for ring in (f.get('geometry') or {}).get('rings', []) for pt in ring]
            if pts:
                xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                d['_lon'], d['_lat'] = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        d['_n'] = len(j['features']); d['_date'] = time.strftime('%Y-%m-%d')
        json.dump(d, open(p, 'w'))
        return d
    except Exception:
        return None
    finally:
        time.sleep(0.5)
