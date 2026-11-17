#!/usr/bin/env python3
"""Centro da parcela pelo número da parcela – camada pública "FDOR Cadastral Centroids" (Florida Statewide Parcel
Centroid Version, ArcGIS, sem chave). Usado só para o mapa/satélite de itens sem coordenada (lotes "Unassigned Location",
"NO SITUS", condos sem ponto). Consulta em lote por condado (PARCEL_ID/PARCELNO IN (...)), com cache em cache/pgeo.json
(acertos e não-achados com data; não-achado é reconsultado depois de 14 dias). Tempo total limitado (budget)."""
import json, os, re, time
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache', 'pgeo.json')
URL = 'https://services9.arcgis.com/Gh9awoU677aKree0/ArcGIS/rest/services/Florida_Statewide_Parcel_Centroid_Version/FeatureServer/0/query'
RETRY_DAYS = 14
_db = None

def _load():
    global _db
    if _db is None:
        try: _db = json.load(open(CACHE))
        except Exception: _db = {}
    return _db

def save():
    if _db is not None:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        tmp = CACHE + '.tmp'; json.dump(_db, open(tmp, 'w')); os.replace(tmp, CACHE)

def clean(pid): return re.sub(r"[^0-9A-Za-z\-\. ]", '', str(pid or '')).strip()

def k(co_no, pid): return f'{int(co_no)}|{clean(pid).upper()}'

def get(co_no, pids):
    """-> (lat, lon) do primeiro candidato achado no cache, senão None (sem rede)."""
    db = _load()
    for p in pids:
        if not co_no or not clean(p): continue
        e = db.get(k(co_no, p))
        if e and e.get('lat'): return e['lat'], e['lon']
    return None

def pending(co_no, pids, today):
    """candidatos ainda não consultados (ou não-achados com mais de RETRY_DAYS)."""
    db = _load(); out = []
    for p in pids:
        if not co_no or not clean(p) or len(clean(p)) < 4: continue
        e = db.get(k(co_no, p))
        if e and e.get('lat'): return []
        if e and e.get('d') and (time.mktime(time.strptime(today, '%Y-%m-%d')) - time.mktime(time.strptime(e['d'], '%Y-%m-%d'))) / 86400 < RETRY_DAYS: continue
        out.append(clean(p))
    return out

PENDING = os.path.join(HERE, 'cache', 'pgeo_pending.json')

def save_pending(jobs):
    json.dump({str(int(c)): sorted(v) for c, v in jobs.items()}, open(PENDING, 'w'))

def _query(s, part, timeout=45):
    ids = ','.join("'" + p.replace("'", "") + "'" for p in part)
    r = s.get(URL, params=dict(where=f"PARCEL_ID IN ({ids})", outFields='PARCEL_ID,CO_NO', returnGeometry='true', outSR=4326, f='json'), timeout=timeout)
    j = r.json()
    if 'features' not in j: raise ValueError(str(j.get('error'))[:80])
    return j['features']

def fetch(jobs, budget=240, chunk=25, threads=3, log=print):
    """jobs: {co_no: set(pids)}. Consulta em lote por PARCEL_ID (indexado; filtra o CO_NO na resposta), 3 threads daemon;
    para no fim do budget (segundos) e grava o que achou. -> dict(asked, found, err, stopped)."""
    import requests, threading, queue
    db = _load(); t0 = time.time(); st = dict(asked=0, found=0, err=0, stopped=None)
    today = time.strftime('%Y-%m-%d'); lock = threading.Lock(); q = queue.Queue()
    for co_no, pids in sorted(jobs.items()):
        L = sorted(set(pids))
        for i in range(0, len(L), chunk): q.put((int(co_no), L[i:i + chunk]))
    def worker():
        s = requests.Session(); s.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) leiloes-florida dashboard (personal research)'
        while time.time() - t0 < budget:
            try: co_no, part = q.get_nowait()
            except queue.Empty: return
            try: feats = _query(s, part, timeout=max(10, min(45, budget - (time.time() - t0))))
            except Exception:
                with lock: st['err'] += 1
                continue
            hit = {}
            for f in feats:
                g = f.get('geometry') or {}; a = f['attributes']
                if g.get('y') is None or int(a.get('CO_NO') or 0) != co_no: continue
                v = clean(a.get('PARCEL_ID')).upper()
                if v: hit[v] = (round(g['y'], 6), round(g['x'], 6))
            with lock:
                for p in part:
                    ll = hit.get(p.upper())
                    db[k(co_no, p)] = dict(lat=ll[0], lon=ll[1], d=today) if ll and 24 < ll[0] < 31.2 else dict(d=today)
                    st['asked'] += 1; st['found'] += 1 if ll else 0
            time.sleep(0.2)
    ts = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
    for t in ts: t.start()
    for t in ts: t.join(max(0.0, budget + 50 - (time.time() - t0)))
    if not q.empty() or any(t.is_alive() for t in ts): st['stopped'] = 'budget'
    with lock: save()
    return st

if __name__ == '__main__':
    # pendentes gravados pelo build (cache/pgeo_pending.json): python3 parcel_geo.py [budget_s]
    import sys
    try: P = json.load(open(PENDING))
    except Exception: P = {}
    b = float(sys.argv[1]) if len(sys.argv) > 1 else 900
    print('pgeo pendentes:', sum(len(v) for v in P.values()), json.dumps(fetch({int(c): set(v) for c, v in P.items()}, budget=b)), flush=True)
