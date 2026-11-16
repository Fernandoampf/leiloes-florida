#!/usr/bin/env python3
"""PROPOSTA 10 (aprovada pelo Fernando 16/11) – backtest dos leilões passados.

Cada resultado do RealAuction (statewide/results/*.json) vendido a terceiro (3P) ou que ficou com o banco/autor (PL)
é ligado ao snapshot diário do painel (statewide/runs/run_<data>.json) mais recente ATÉ a data do leilão, que guarda
o ARV (val) e o preço esperado (xbid) que o painel mostrava. Mede preço final ÷ ARV, ÷ Zillow (só quando havia Zillow
manual), ÷ valor do condado (Assessed Value da lista), por condado e faixa de ARV. Construído (B) e lote (L) separados.
Usado para recalibrar o preço esperado: xbid = mediana(preço 3P ÷ ARV) × ARV atual (condado com ≥10 vendas; senão faixa estadual)."""
import glob, json, os, re, statistics as stt
import rawdata

SW = '/workspace/auc/statewide'
BANDS = [(0, 150000, '< 150 mil'), (150000, 300000, '150–300 mil'), (300000, 500000, '300–500 mil'), (500000, 1e12, '≥ 500 mil')]
MINN = 10

def band(v):
    for lo, hi, lb in BANDS:
        if lo <= v < hi: return lb
    return None

def _snapshots(sw=SW):
    snap = {}
    for f in sorted(glob.glob(os.path.join(sw, 'runs', 'run_2026-*.json'))):
        m = re.search(r'run_(\d{4}-\d{2}-\d{2})\.json$', f)
        if not m: continue
        try: its = json.load(open(f))['items']
        except Exception: continue
        for i in its:
            if i.get('val') and i.get('id'): snap.setdefault(i['id'], []).append((m.group(1), i['val'], i.get('ty'), i.get('xbid'), i.get('zw')))
    return snap

def outcomes(sw=SW):
    snap = _snapshots(sw); rows = []
    for f in glob.glob(os.path.join(sw, 'results', '*.json')):
        host, date = os.path.basename(f)[:-5].rsplit('_', 1)
        co = host.split('.')[0].replace('-', '').replace('myorangeclerk', 'orange')
        co = {'saintjohns': 'stjohns'}.get(co, co)
        mm, dd, yy = date.split('-'); di = f'{yy}-{mm}-{dd}'
        try: data = json.load(open(f))
        except Exception: continue
        for r in data:
            at = (r.get('Auction Type') or '').upper()
            if not at: continue
            t = 'TD' if 'TAX' in at else 'FC'
            res = r.get('res') or {}
            if res.get('A') != 'Auction Sold': continue
            to = res.get('ST') or ''; who = '3P' if '3rd' in to else 'PL' if 'Plaintiff' in to else None
            sold = rawdata.money(res.get('D'))
            if not who or not sold: continue
            s = [e for e in snap.get(t + str(r.get('AID')), []) if e[0] <= di]
            if not s: continue
            d0, val, ty, xb, zw = s[-1]
            zv = (zw or {}).get('v') if isinstance(zw, dict) else None
            rows.append(dict(co=co, t=t, who=who, sold=sold, val=val, z=zv, av=rawdata.money(r.get('Assessed Value')), xb=xb,
                             kk='L' if ty in ('Lote', 'Terreno') else 'B', d=di))
    return rows

def _m(v):
    v = [x for x in v if x is not None]
    return (round(stt.median(v), 3), len(v)) if v else (None, 0)

def summarize(rows):
    """-> dict(tab=[[co, band, t, kk, who, n, arv, z, av, nz]], ratio={key: (med, n)}, n, first, last)"""
    G = {}
    for r in rows:
        for co in (r['co'], '*'):
            for bd in (band(r['val']), '*'):
                G.setdefault((co, bd, r['t'], r['kk'], r['who']), []).append(r)
    tab, ratio = [], {}
    for (co, bd, t, kk, who), L in G.items():
        a = _m([x['sold'] / x['val'] for x in L]); z = _m([x['sold'] / x['z'] for x in L if x['z']]); c = _m([x['sold'] / x['av'] for x in L if x['av']])
        tab.append([co, bd, t, kk, who, len(L), a[0], z[0], c[0], z[1]])
        if who == '3P': ratio['|'.join((co, bd, t, kk))] = a
    tab.sort(key=lambda t: (t[0] != '*', -t[5]))
    ds = sorted(r['d'] for r in rows)
    return dict(tab=tab, ratio=ratio, n=len(rows), first=ds[0] if ds else None, last=ds[-1] if ds else None)

def calib(rows, cname=lambda s: s):
    """Mesmo formato do favtrack.calib (rxp = vendido ÷ preço esperado, rval = vendido ÷ ARV, só vendas a terceiros), chave 'Condado|TD/FC|L/B'
    e '*|TD/FC|L/B'. Usado para recalibrar o preço esperado (compAdjust no painel) com TODOS os resultados, não só os favoritos."""
    g = {}
    for r in rows:
        if r['who'] != '3P': continue
        for key in (cname(r['co']) + '|' + r['t'] + '|' + r['kk'], '*|' + r['t'] + '|' + r['kk']):
            o = g.setdefault(key, dict(rxp=[], rval=[]))
            if r['xb']: o['rxp'].append(r['sold'] / r['xb'])
            o['rval'].append(r['sold'] / r['val'])
    return {k: dict(n=max(len(o['rxp']), len(o['rval'])), nxp=len(o['rxp']), rxp=round(stt.median(o['rxp']), 2) if o['rxp'] else None,
                    nval=len(o['rval']), rval=round(stt.median(o['rval']), 2) if o['rval'] else None, src='backtest') for k, o in g.items()}

def ratio_for(S, co, val, t, kk):
    """mediana preço 3P ÷ ARV: condado (≥10 vendas, todas as faixas) > faixa estadual (≥10) > estado (≥10); -> (r, n, nível) ou None"""
    R = S.get('ratio') or {}
    for key, lvl in (((co, '*', t, kk), 'condado'), (('*', band(val), t, kk), 'faixa ' + str(band(val)) + ' (estado)'), (('*', '*', t, kk), 'estado')):
        v = R.get('|'.join(key))
        if v and v[0] and v[1] >= MINN: return v[0], v[1], lvl
    return None

if __name__ == '__main__':
    S = summarize(outcomes())
    print(S['n'], S['first'], S['last'])
    for t in S['tab'][:30]: print(t)
