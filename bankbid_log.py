#!/usr/bin/env python3
"""PROPOSTA 20 (Fernando 17/11): histórico das leituras do lance do banco + resultado do leilão, por item (FC).
Lê as listas públicas do RealAuction já baixadas (fc/*.json; nada de rede aqui) e grava em
/workspace/auc/statewide/bankbid_history.json (fora do git):
  {AID: {"c": county, "d": "YYYY-MM-DD" (leilão), "r": [[lido "YYYY-MM-DD HH:MM", julgamento, lance do banco (valor | "Hidden" | null), status]],
         "res": {"st": "sold"|"canceled"|..., "amt": valor, "to": "Plaintiff"|"3rd Party Bidder", "txt": texto do RealAuction}}}
Uso: python3 bankbid_log.py   (rodado pelo build e pelo dayof_refresh.py)"""
import json, glob, os, time, re
SW = '/workspace/auc/statewide'; OUT = os.path.join(SW, 'bankbid_history.json')
money = lambda v: (lambda s: float(s) if re.fullmatch(r'[\d.]+', s) else None)(str(v or '').replace('$', '').replace(',', '').strip())

def update():
    try: H = json.load(open(OUT))
    except Exception: H = {}
    for f in glob.glob(os.path.join(SW, 'fc', '*.json')):
        base = os.path.basename(f)[:-5]; county, d = base.rsplit('_', 1); d = d[6:] + '-' + d[:2] + '-' + d[3:5]
        at = time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(f)))
        try: rows = json.load(open(f))
        except Exception: continue
        for r in rows:
            if 'AID' not in r or 'Case #' not in r: continue
            e = H.setdefault(str(r['AID']), {'c': county, 'd': d, 'r': []}); e['d'] = d; e['cs'] = r.get('Case #')
            u = r.get('upd') or {}; pm = r.get('Plaintiff Max Bid'); pmv = money(pm)
            st = u.get('A') or r.get('area')
            row = [at, money(r.get('Final Judgment Amount')), pmv if pmv is not None else pm, st]
            if not e['r'] or e['r'][-1][0] < at: e['r'].append(row); del e['r'][:-20]
            if r.get('area') == 'C':
                txt = ' '.join(str(u.get(k) or '') for k in ('A', 'B', 'C', 'D', 'SL', 'ST')).strip()
                res = {'txt': txt[:120]}
                if u.get('A') == 'Auction Sold': res.update(st='sold', amt=money(u.get('D')), to=u.get('ST'))
                elif re.search(r'cancel', txt, re.I): res['st'] = 'canceled'
                else: res['st'] = (u.get('A') or 'closed')
                e['res'] = res
    json.dump(H, open(OUT + '.tmp', 'w')); os.replace(OUT + '.tmp', OUT)
    return H

def day_read(H, aid, today):
    """Leitura do lance do banco feita HOJE (dia do leilão) -> {at, v, h} ou None."""
    e = H.get(str(aid))
    if not e or e.get('d') != today: return None
    rs = [x for x in e['r'] if x[0][:10] == today]
    if not rs: return None
    x = rs[-1]; return {'at': x[0], 'v': x[2] if isinstance(x[2], (int, float)) else None, 'h': (x[2] == 'Hidden') or None, 'fj': x[1]}

def pk_map(H):
    """AID -> autor (mesma chave do histórico por autor), pelo número do processo no índice do PropertyOnion."""
    import plaintiff_hist as ph
    idx = ph.po_case_index(); out = {}
    for aid, e in H.items():
        if not e.get('res'): continue
        k = ph.case_key(e.get('cs')); c = idx.get(k) or []
        fj = next((x[1] for x in reversed(e['r']) if x[1]), None)
        pl = next((pn for pn, raw, f in c if fj and f and abs(f - fj) <= max(2.0, 0.01 * fj)), None)
        if pl is None and len({x[0] for x in c}) == 1: pl = c[0][0]
        if pl: out[aid] = pl
    return out

def plaintiff_stats(H, pk_of):
    """por autor: leilões com resultado; quantos o banco CAIU o lance (publicado < julgamento, ou vendido ao banco < julgamento),
    quantos foram TIRADOS (cancelados), quantos vendidos a terceiros."""
    S = {}
    for aid, e in H.items():
        pk = pk_of.get(aid); res = e.get('res')
        if not pk or not res: continue
        s = S.setdefault(pk, {'n': 0, 'drop': 0, 'pulled': 0, 'third': 0, 'bank': 0, 'pubLow': 0})
        s['n'] += 1; fj = next((x[1] for x in reversed(e['r']) if x[1]), None)
        pubs = [x[2] for x in e['r'] if isinstance(x[2], (int, float))]
        if pubs and fj and min(pubs) < fj - 0.5: s['pubLow'] += 1
        if res.get('st') == 'canceled': s['pulled'] += 1
        elif res.get('st') == 'sold':
            if (res.get('to') or '').lower().startswith('plaintiff'):
                s['bank'] += 1
                if fj and res.get('amt') and res['amt'] < fj * 0.98: s['drop'] += 1
            else: s['third'] += 1
    return S

if __name__ == '__main__':
    H = update(); print(len(H), 'itens;', sum(1 for e in H.values() if e.get('res')), 'com resultado')
