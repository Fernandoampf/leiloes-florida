#!/usr/bin/env python3
"""Last-resort coordinates from the free US Census geocoder (public, no key) for items with a street address but no
parcel polygon (mostly Miami-Dade condos). Accepted only when the matched address keeps the same house number, street
name and suffix (the geocoder sometimes swaps NW 3 ST -> NW 3RD AVE). Interpolated point on the street: approximate.
Cached in cache/census/. Polite: 1 request at a time, pause; at most LIMIT new lookups per build."""
import json, os, re, time
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, 'cache', 'census'); os.makedirs(C, exist_ok=True)
URL = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
LIMIT = 150
_n = 0
SUF = {'STREET': 'ST', 'AVENUE': 'AVE', 'AV': 'AVE', 'ROAD': 'RD', 'DRIVE': 'DR', 'COURT': 'CT', 'LANE': 'LN', 'PLACE': 'PL',
       'TERRACE': 'TER', 'TERR': 'TER', 'BOULEVARD': 'BLVD', 'CIRCLE': 'CIR', 'WAY': 'WAY', 'TRAIL': 'TRL', 'PARKWAY': 'PKWY', 'HIGHWAY': 'HWY'}
def _tok(s):
    t = re.sub(r'[^A-Z0-9 ]', ' ', str(s or '').upper()).split()
    t = [SUF.get(w, w) for w in t]
    return [re.sub(r'^(\d+)(ST|ND|RD|TH)$', r'\1', w) for w in t]

def get(street, city, zip5, fetch=False, sess=None):
    global _n
    if not street or not re.match(r'\s*[1-9]', street): return None
    one = f'{street}, {city or ""}, FL {zip5 or ""}'.replace(' ,', ',')
    p = os.path.join(C, re.sub(r'[^0-9A-Za-z]+', '_', one)[:120] + '.json')
    if os.path.exists(p):
        try: return json.load(open(p))
        except Exception: pass
    if not fetch or _n >= LIMIT: return None
    _n += 1
    import requests
    s = sess or requests
    try:
        j = s.get(URL, params=dict(address=one, benchmark='Public_AR_Current', format='json'), timeout=30).json()
        d = {'_date': time.strftime('%Y-%m-%d')}
        want = _tok(street)
        for m in j['result']['addressMatches']:
            got = _tok(m['matchedAddress'].split(',')[0])
            core = [w for w in want if not re.fullmatch(r'(APT|UNIT|STE|#)?\d*[A-Z]?', w) or w == want[0]]
            if got and want and got[0] == want[0] and all(w in got for w in want[1:4] if not w.isdigit() or w in got) and \
               all(w in got for w in core[1:] if w in SUF.values() or len(w) > 2):
                d.update(lat=round(m['coordinates']['y'], 6), lon=round(m['coordinates']['x'], 6), matched=m['matchedAddress']); break
        json.dump(d, open(p, 'w'))
        return d
    except Exception:
        return None
    finally:
        time.sleep(0.4)
