#!/usr/bin/env python3
"""Resultados de leilão + acompanhamento dos favoritos (sem rede: só arquivos já coletados).

- results_history.json (fora do git, em /workspace/auc/statewide): resultado por leilão (vendido/preço/comprador,
  resgatado, cancelado, adiado) a partir de results/*.json (RealAuction, script results.py), das listas td/*.json
  (item que sai da área W para C antes da data = retirado antes do leilão) e de results_extra.json (conferências
  manuais em páginas públicas, com fonte).
- archive(): favoritos/candidatos que saíram do site (motivo, data, resultado), para a seção "Já passaram".
- mbhist(): histórico de lance máx. (17%) e ARV por rodada (runs/run_<data>.json) dos favoritos.
- write_changes(today): runs/favoritos_changes_<data>.json — saídas novas e mudanças > 10% em lance máx./ARV.
  Chamado no fim de snapshot_run.py (rotina diária), depois do snapshot do dia.
"""
import glob, json, os, re, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SW = '/workspace/auc/statewide'
HIST = os.path.join(SW, 'results_history.json')
EXTRA = os.path.join(SW, 'results_extra.json')
RUNS = os.path.join(SW, 'runs')
SCHEMA = 1
THR = 0.10

def _money(v):
    try: return float(re.sub(r'[^0-9.]', '', str(v))) if v not in (None, '') and re.search(r'\d', str(v)) else None
    except ValueError: return None

def _iso(mdy):
    try: return dt.datetime.strptime(mdy, '%m/%d/%Y').date().isoformat()
    except Exception: return mdy

def _status(res):
    if not res: return None, None
    a, b, to = res.get('A'), str(res.get('B') or ''), str(res.get('ST') or '')
    if a == 'Auction Sold':
        return ('sold_3p' if '3rd' in to else 'sold_plaintiff' if 'Plaintiff' in to else 'sold_cert' if 'Cert' in to else 'sold'), to or None
    if re.search(r'redeem', b, re.I): return ('redeemed_after_sale' if re.search('after', b, re.I) else 'redeemed'), b
    if re.search(r'reschedul|postpon|reset', b, re.I): return 'postponed', b
    if re.search(r'bankrupt', b, re.I): return 'canceled_bankruptcy', b
    if re.search(r'cancel|vacat|dismiss|did not meet|walked|fees not', b, re.I): return 'canceled', b
    return None, None

def update_history():
    h = {}
    try: h = json.load(open(HIST))
    except Exception: pass
    now = dt.date.today().isoformat()
    for f in glob.glob(os.path.join(SW, 'results', '*.json')):
        host, d = os.path.basename(f)[:-5].rsplit('_', 1)
        try: rows = json.load(open(f))
        except Exception: continue
        for r in rows:
            st, why = _status(r.get('res'))
            if not st and r.get('area') == 'C' and not r.get('res'):
                st, why = 'closed', 'encerrado no leilão; o RealAuction não publicou o resultado do item'
            if not st: continue
            at = (r.get('Auction Type') or '').upper(); t = 'TD' if 'TAX' in at else 'FC'
            k = f"{t}{r['AID']}"
            h[k] = dict(id=k, host=host, co=host.split('.')[0].replace('-', ''), t=t, date=_iso(d.replace('-', '/')), case=r.get('Case #'),
                        parcel=r.get('Parcel ID'), addr=((r.get('Property Address') or '') + ' ' + (r.get('addr2') or '')).strip(),
                        ref=_money(r.get('Opening Bid') if t == 'TD' else r.get('Final Judgment Amount')), av=_money(r.get('Assessed Value')),
                        status=st, why=why, sold=_money((r.get('res') or {}).get('D')) if st.startswith('sold') else None,
                        src='RealAuction (resultados públicos)', at=h.get(k, {}).get('at') or now)
    # listas atuais: leilão futuro que já está na área C (encerrados/cancelados) = retirado antes do leilão
    for f in glob.glob(os.path.join(SW, 'td', '*.json')) + glob.glob(os.path.join(SW, 'fc', '*.json')):
        host_d = os.path.basename(f)[:-5]
        try: co, d = host_d.rsplit('_', 1); rows = json.load(open(f))
        except Exception: continue
        sale = _iso(d.replace('-', '/'))
        fetched = dt.date.fromtimestamp(os.path.getmtime(f)).isoformat()
        if sale <= fetched: continue                      # lista lida depois do leilão: área C = encerrado, não 'retirado'
        for r in rows:
            if r.get('area') != 'C' or 'AID' not in r: continue
            at = (r.get('Auction Type') or '').upper(); t = 'TD' if ('TAX' in at or '/td/' in f) else 'FC'
            k = f"{t}{r['AID']}"
            if k in h: continue
            h[k] = dict(id=k, co=co, t=t, date=sale, case=r.get('Case #'), parcel=r.get('Parcel ID'),
                        addr=((r.get('Property Address') or '') + ' ' + (r.get('addr2') or '')).strip(), ref=_money(r.get('Opening Bid')),
                        status='withdrawn', why='saiu da lista de espera do RealAuction antes do leilão (resgatado ou cancelado)',
                        src='lista RealAuction', at=now)
    try:
        for e in json.load(open(EXTRA)).get('items', []):
            h[e['id']] = dict(h.get(e['id'], {}), **e)          # conferência manual vence (mais específica)
    except Exception: pass
    json.dump(h, open(HIST, 'w'), ensure_ascii=False)
    return h

def run_files():
    return sorted(glob.glob(os.path.join(RUNS, 'run_????-??-??.json')))

def _runs_by_id(ids, limit=40):
    """{id: [(date, item)]} oldest→newest from daily snapshots."""
    out = {i: [] for i in ids}
    for f in run_files()[-limit:]:
        d = os.path.basename(f)[4:14]
        try: items = json.load(open(f))['items']
        except Exception: continue
        for it in items:
            if it.get('id') in out: out[it['id']].append((d, it))
    return out

def fav_ids():
    p = os.path.join(HERE, 'data', 'favoritos.json')
    try: d = json.load(open(p))
    except Exception: return {}
    if isinstance(d.get('cand'), dict): return {k: (v.get('notes') or '') for k, v in d['cand'].items()}
    return {x.get('id'): x.get('note', '') for x in d.get('items', []) if x.get('id')}

LBL = dict(sold_3p='vendido para terceiro', sold_plaintiff='ficou com o autor (banco)', sold_cert='ficou com o detentor do certificado',
           sold='vendido', redeemed='resgatado pelo dono', redeemed_after_sale='resgatado depois da venda', postponed='adiado/remarcado',
           canceled='cancelado', closed='leilão encerrado, resultado não publicado', canceled_bankruptcy='cancelado por falência', withdrawn='retirado antes do leilão (resgatado ou cancelado)')

def archive(current_ids, today, hist=None):
    """Favoritos que não estão mais no site -> lista para 'Já passaram' (embutida no build)."""
    hist = hist if hist is not None else update_history()
    favs = fav_ids(); gone = [i for i in favs if i not in current_ids]
    rb = _runs_by_id(gone)
    out = []
    for i in gone:
        last = rb[i][-1][1] if rb[i] else {}
        r = hist.get(i)
        sale = (r or {}).get('date') or last.get('date')
        if r: reason, st = LBL.get(r['status'], r['status']), r['status']
        elif sale and sale < today: reason, st = 'leilão passou (' + sale + '); resultado ainda não coletado', 'past_unknown'
        else: reason, st = 'saiu das listas; motivo não confirmado', 'unknown'
        out.append(dict(id=i, addr=(r or {}).get('addr') or last.get('addr'), co=last.get('county') or (r or {}).get('co'), t=last.get('t') or (r or {}).get('t'),
                        case=(r or {}).get('case') or last.get('case'), date=sale, status=st, reason=reason, why=(r or {}).get('why'),
                        sold=(r or {}).get('sold'), ref=(r or {}).get('ref') or last.get('ref'), mb=last.get('mb'), val=last.get('val'),
                        lastSeen=rb[i][-1][0] if rb[i] else None, src=(r or {}).get('src'), at=(r or {}).get('at'), note=favs.get(i, '')[:120]))
    return out

def mbhist(ids):
    """{id: [[data, lanceMax17, ARV], ...]} para o selo de mudança no drawer."""
    rb = _runs_by_id(ids)
    return {i: [[d, it.get('maxBid17'), it.get('val')] for d, it in v] for i, v in rb.items() if v}

def _pct(a, b):
    return (b - a) / abs(a) if a not in (None, 0) and b is not None else None

def write_changes(today=None):
    today = today or dt.date.today().isoformat()
    hist = update_history()
    fs = run_files()
    cur_f = os.path.join(RUNS, f'run_{today}.json')
    if not os.path.exists(cur_f): raise SystemExit(f'sem snapshot {cur_f}')
    prev_f = next((f for f in reversed(fs) if os.path.basename(f)[4:14] < today), None)
    cur = {x['id']: x for x in json.load(open(cur_f))['items']}
    prev = {x['id']: x for x in json.load(open(prev_f))['items']} if prev_f else {}
    favs = fav_ids()
    arch = archive(set(cur), today, hist)
    # saídas "novas" = não estavam no arquivo do dia anterior
    reported = set()
    pc = sorted(glob.glob(os.path.join(RUNS, 'favoritos_changes_*.json')))
    pc = [f for f in pc if os.path.basename(f)[18:28] < today]
    if pc:
        try: reported = {(e['id'], e['status']) for e in json.load(open(pc[-1])).get('exited', [])}
        except Exception: pass
    for e in arch: e['new'] = (e['id'], e['status']) not in reported
    mbc = []
    for i in favs:
        a, b = prev.get(i), cur.get(i)
        if not a or not b: continue
        for fld, key in (('maxBid17', 'maxBid17'), ('arv', 'val')):
            p = _pct(a.get(key), b.get(key))
            if p is not None and abs(p) > THR:
                mbc.append(dict(id=i, addr=b.get('addr'), county=b.get('county'), sale_date=b.get('date'), field=fld,
                                before=round(a.get(key)), after=round(b.get(key)), pct=round(p, 3), prev_run=os.path.basename(prev_f)[4:14]))
    out = dict(schema=SCHEMA, date=today, generated=dt.datetime.now().strftime('%Y-%m-%d %H:%M'), favorites=len(favs),
               in_site=sum(1 for i in favs if i in cur), threshold=THR, prev_run=os.path.basename(prev_f)[4:14] if prev_f else None,
               exited=arch, exited_new=sum(1 for e in arch if e['new']), maxbid_changes=mbc)
    p = os.path.join(RUNS, f'favoritos_changes_{today}.json')
    json.dump(out, open(p, 'w'), ensure_ascii=False, indent=1)
    print('favoritos:', p, 'saídas', len(arch), 'novas', out['exited_new'], 'mudanças', len(mbc))
    return p

if __name__ == '__main__':
    import sys
    write_changes(sys.argv[1] if len(sys.argv) > 1 else None)

def calib(hist=None):
    """Calibração: vendas para terceiros vs nosso lance máx. (último snapshot antes do leilão) e vs lance inicial/julgamento."""
    hist = hist if hist is not None else update_history()
    sold = {k: v for k, v in hist.items() if v.get('status') == 'sold_3p' and v.get('sold')}
    last = {}
    for f in run_files():
        d = os.path.basename(f)[4:14]
        try: items = json.load(open(f))['items']
        except Exception: continue
        for it in items:
            h = sold.get(it.get('id'))
            if h and d < h['date']: last[it['id']] = (it.get('maxBid17'), it.get('ty'), it.get('county'))
    q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else None
    g = {}
    for k, v in sold.items():
        mb, ty, co = last.get(k, (None, None, None))
        kind = 'Lote/terreno' if ty in ('Lote', 'Terreno') else ('Casa/condo' if ty else '?')
        for key in ((co or v['co'].title()) + '|' + v['t'], '*|' + v['t']):
            o = g.setdefault(key, dict(n=0, rref=[], rmb=[], over=0, nmb=0, kinds={}))
            o['n'] += 1
            if v.get('ref'): o['rref'].append(v['sold'] / v['ref'])
            if mb:
                o['rmb'].append(v['sold'] / mb); o['nmb'] += 1; o['over'] += v['sold'] > mb
                o['kinds'][kind] = o['kinds'].get(kind, 0) + 1
    out = {}
    for k, o in g.items():
        out[k] = dict(n=o['n'], nmb=o['nmb'], rref=round(q(o['rref'], .5), 2) if o['rref'] else None,
                      rmb=round(q(o['rmb'], .5), 2) if o['rmb'] else None, rmb25=round(q(o['rmb'], .25), 2) if o['rmb'] else None,
                      rmb75=round(q(o['rmb'], .75), 2) if o['rmb'] else None, over=round(o['over'] / o['nmb'], 2) if o['nmb'] else None, kinds=o['kinds'])
    return out
