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

def _accept(street, matched):
    """mesmo nº da casa, nome da rua e sufixo (o geocoder às vezes troca NW 3 ST -> NW 3RD AVE)."""
    want = _tok(street); got = _tok(str(matched or '').split(',')[0])
    core = [w for w in want if not re.fullmatch(r'(APT|UNIT|STE|#)?\d*[A-Z]?', w) or w == want[0]] if want else []
    return bool(got and want and got[0] == want[0] and all(w in got for w in want[1:4] if not w.isdigit() or w in got) and
                all(w in got for w in core[1:] if w in SUF.values() or len(w) > 2))

def no_unit(street):
    """'3 GROVE ISLE DR C308' -> '3 GROVE ISLE DR'; '10303 BURNTS STORE # 146' -> '10303 BURNTS STORE' (prédio, não a unidade)."""
    t = str(street or '').strip()
    t = re.sub(r'\s*(#|\bUNIT\b|\bAPT\b|\bSTE\b|\bBLDG\b|\bPH(?=\d))\s*[-\w]*\s*$', '', t, flags=re.I).strip()
    w = t.split()
    keys = set(SUF) | set(SUF.values()) | {'ISLE', 'CT', 'CIR', 'LOOP', 'RUN', 'PT', 'XING', 'ROW', 'SQ', 'PATH'}
    if len(w) >= 4 and w[-2].upper() in keys and re.search(r'\d', w[-1]): w = w[:-1]
    out = ' '.join(w)
    return out if out != str(street or '').strip() and re.match(r'\s*[1-9]', out) else None

def variants(street, city):
    """tentativas em ordem: endereço como veio; sem a unidade (prédio); cidade grudada na rua sem cidade
    ('1330 JEFF DRIVE APOPKA' + '' -> '1330 JEFF DRIVE' + 'APOPKA')."""
    out = [(street, city)]
    nu = no_unit(street)
    if nu: out.append((nu, city))
    if not (city or '').strip():
        w = str(street or '').split()
        keys = set(SUF) | set(SUF.values())
        idx = [i for i, x in enumerate(w) if x.upper() in keys and i >= 1]
        if idx and idx[-1] < len(w) - 1 and re.match(r'\s*[1-9]', w[0]):
            out.append((' '.join(w[:idx[-1] + 1]), ' '.join(w[idx[-1] + 1:])))
    return out

def _one(street, city, zip5): return f'{street}, {city or ""}, FL {zip5 or ""}'.replace(' ,', ',')
def _path(one):
    # sem cidade ('RUA CIDADE,, FL') colidia com ('RUA', 'CIDADE') no nome do arquivo -> marca '_nc'
    return os.path.join(C, re.sub(r'[^0-9A-Za-z]+', '_', one)[:120] + ('_nc' if ',,' in one else '') + '.json')
RETRY_DAYS = 14
def _fresh(p):
    """cache válido: acerto sempre; não-achado só por RETRY_DAYS (depois tenta de novo)."""
    try: d = json.load(open(p))
    except Exception: return False
    if d.get('lat'): return True
    try: return (time.time() - time.mktime(time.strptime(d.get('_date', '2000-01-01'), '%Y-%m-%d'))) / 86400 < RETRY_DAYS
    except Exception: return False

def cached(street, city, zip5): return _fresh(_path(_one(street, city, zip5)))

def batch(rows, budget=240, chunk=500, log=print):
    """Geocoder em LOTE do Censo (addressbatch, gratuito, sem chave) para [(street, city, zip5)] ainda sem cache.
    Mesma validação do get(); grava o mesmo cache. Para no fim do budget (segundos). -> dict(asked, found, err, stopped)."""
    import requests, csv, io
    t0 = time.time(); st = dict(asked=0, found=0, err=0, stopped=None)
    todo, seen = [], set()
    for street, city, zip5 in rows:
        if not street or not re.match(r'\s*[1-9]', street): continue
        one = _one(street, city, zip5)
        if one in seen or _fresh(_path(one)): continue
        seen.add(one); todo.append((street, city or '', zip5 or '', one))
    for i in range(0, len(todo), chunk):
        left = budget - (time.time() - t0)
        if left < 20: st['stopped'] = 'budget'; break
        part = todo[i:i + chunk]
        buf = io.StringIO(); w = csv.writer(buf)
        for n, (street, city, zip5, one) in enumerate(part): w.writerow([n, street, city, 'FL', zip5])
        try:
            r = requests.post('https://geocoding.geo.census.gov/geocoder/locations/addressbatch',
                              data=dict(benchmark='Public_AR_Current'), files=dict(addressFile=('a.csv', buf.getvalue(), 'text/csv')),
                              timeout=min(180, max(20, left)))
            r.raise_for_status()
        except Exception as ex:
            st['err'] += 1; log(f'  censo lote: erro {type(ex).__name__}'); continue
        res = {}
        for row in csv.reader(io.StringIO(r.text)):
            if len(row) >= 6 and row[0].isdigit(): res[int(row[0])] = row
        for n, (street, city, zip5, one) in enumerate(part):
            row = res.get(n); d = {'_date': time.strftime('%Y-%m-%d'), '_batch': 1}
            if row is None: continue          # sem resposta para esta linha: tenta de novo no próximo build
            if row[2] == 'Match' and _accept(street, row[4]):
                try:
                    lon, lat = (float(v) for v in row[5].split(','))
                    if 24 < lat < 31.2: d.update(lat=round(lat, 6), lon=round(lon, 6), matched=row[4]); st['found'] += 1
                except Exception: pass
            json.dump(d, open(_path(one), 'w')); st['asked'] += 1
    return st

def get(street, city, zip5, fetch=False, sess=None):
    global _n
    if not street or not re.match(r'\s*[1-9]', street): return None
    one = _one(street, city, zip5)
    p = _path(one)
    if os.path.exists(p) and (_fresh(p) or not fetch):
        try: return json.load(open(p))
        except Exception: pass
    if not fetch or _n >= LIMIT: return None
    _n += 1
    import requests
    s = sess or requests
    try:
        j = s.get(URL, params=dict(address=one, benchmark='Public_AR_Current', format='json'), timeout=30).json()
        d = {'_date': time.strftime('%Y-%m-%d')}
        for m in j['result']['addressMatches']:
            if _accept(street, m['matchedAddress']):
                d.update(lat=round(m['coordinates']['y'], 6), lon=round(m['coordinates']['x'], 6), matched=m['matchedAddress']); break
        json.dump(d, open(p, 'w'))
        return d
    except Exception:
        return None
    finally:
        time.sleep(0.4)
