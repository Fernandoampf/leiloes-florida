#!/usr/bin/env python3
"""Histórico por autor (banco/servicer) nos leilões de foreclosure passados — PROPOSTAS 6 (substituta) e 9, 16/11.

Liga cada resultado do RealAuction (statewide/results/*.json, que traz Case #, Final Judgment, Assessed Value e
quem levou) ao autor da ação pelo nº do processo publicado no PropertyOnion (cache/po_full + statewide/po,
campo auctions[].auction_plaintiffs / auction_caseno). Confirmação: mesmo ano+sequência do processo E julgamento igual (±1%).

Leitura de cada resultado (Fernando t319u):
  (a) autor ficou com o imóvel por X (X > lance inicial)  -> o máximo oculto dele era >= X  ('kept')
  (b) terceiro comprou por X                              -> o máximo oculto do autor era < X ('released')
  (c) autor ficou pelo lance inicial (~US$100)            -> sem disputa                    ('nocontest')
Nada aqui é número oficial do processo; só histórico para mostrar ao lado do julgamento."""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SW = '/workspace/auc/statewide'
NOCONTEST = 1000          # autor ficou por até US$ 1.000 = lance de abertura (~US$100), sem disputa

_SUFFIX = {'LLC', 'INC', 'CORP', 'CORPORATION', 'COMPANY', 'CO', 'NA', 'FSB', 'LP', 'LTD', 'THE', 'LLP', 'PLLC', 'PA', 'ASSOCIATION', 'NATIONAL', 'ASSN'}
_ALIAS = [(r'^NATIONSTAR|MR COOPER', 'NATIONSTAR (MR. COOPER)'), (r'^PENNYMAC', 'PENNYMAC'), (r'^LAKEVIEW', 'LAKEVIEW LOAN SERVICING'),
          (r'^FREEDOM MORTGAGE', 'FREEDOM MORTGAGE'), (r'^NEWREZ|SHELLPOINT', 'NEWREZ / SHELLPOINT'), (r'^ROCKET|QUICKEN', 'ROCKET MORTGAGE'),
          (r'^WELLS FARGO', 'WELLS FARGO'), (r'^U ?S BANK', 'U.S. BANK'), (r'^BANK OF AMERICA', 'BANK OF AMERICA'), (r'^JPMORGAN|^JP MORGAN', 'JPMORGAN CHASE'),
          (r'^DEUTSCHE BANK', 'DEUTSCHE BANK'), (r'^THE BANK OF NEW YORK|^BANK OF NEW YORK', 'BANK OF NEW YORK MELLON'), (r'^WILMINGTON', 'WILMINGTON'),
          (r'^MIDFIRST', 'MIDFIRST BANK'), (r'^CARRINGTON', 'CARRINGTON'), (r'^SPECIALIZED LOAN', 'SPECIALIZED LOAN SERVICING'),
          (r'^SECRETARY OF HOUSING|^HUD\b|^UNITED STATES OF AMERICA', 'EUA / HUD'), (r'^ROUNDPOINT', 'ROUNDPOINT'), (r'^PHH|^OCWEN', 'PHH / OCWEN'),
          (r'^CROSSCOUNTRY', 'CROSSCOUNTRY MORTGAGE'), (r'^SELENE', 'SELENE FINANCE'), (r'^LOANDEPOT|^LOAN DEPOT', 'LOANDEPOT'), (r'^CITIZENS', 'CITIZENS BANK'),
          (r'^TRUIST|^BRANCH BANKING|^SUNTRUST', 'TRUIST'), (r'^REGIONS', 'REGIONS'), (r'^AMERIHOME', 'AMERIHOME'), (r'^GUILD', 'GUILD MORTGAGE'),
          (r'^MORTGAGE ASSETS MANAGEMENT|^MAM\b', 'MORTGAGE ASSETS MANAGEMENT'), (r'^FIFTH THIRD', 'FIFTH THIRD'), (r'^CITIBANK|^CITIMORTGAGE', 'CITI')]

def norm_plaintiff(s):
    """'NATIONSTAR MORTGAGE LLC D/B/A MR. COOPER' -> 'NATIONSTAR (MR. COOPER)'; '' -> None. Só o 1º autor."""
    s = str(s or '').strip()
    if s.startswith('['):                 # PO: "['AUTOR', 'ADVOGADO']" (às vezes cortado)
        s = re.sub(r"^\[\s*['\"]", '', s); s = re.split(r"['\"]\s*,|['\"]\s*\]", s)[0]
    s = s.upper().strip()
    if not s or s in ('NONE', 'NULL'): return None
    s = re.split(r'\s*[;|]\s*', s)[0]
    s = re.sub(r'[.\'’]', '', s)
    for pat, name in _ALIAS:
        if re.search(pat, s): return name
    s = re.split(r',|\s+AS\s+|\s+D/?B/?A\b|\s+F/?K/?A\b|\s+A/?K/?A\b|\s+SUCCESSOR\b|\s+ON BEHALF\b|\s+NOT IN ITS\b|\s+SOLELY\b', s)[0]
    w = [t for t in re.sub(r'[^A-Z0-9 ]', ' ', s).split() if t not in _SUFFIX]
    return ' '.join(w[:5]) or None

def case_key(s):
    """'2024 CA 001507 MF' / '2024-CA-001507-O' / '2024CA001507' -> ('2024', 1507); sem ano -> None."""
    m = re.search(r'((?:19|20)\d{2})\D{0,3}([A-Z]{2})?\D{0,3}0*(\d{2,7})', str(s or '').upper())
    return (m.group(1), int(m.group(3))) if m else None

def _money(v):
    try: return float(str(v).replace('$', '').replace(',', '').strip())
    except Exception: return None

def po_case_index(dirs=None):
    """case_key -> list of (plaintiff_norm, plaintiff_raw, fj)"""
    dirs = dirs or [os.path.join(HERE, 'cache', 'po_full'), os.path.join(SW, 'po')]
    idx = {}
    for d in dirs:
        for f in glob.glob(os.path.join(d, '*.json')):
            try: P = json.load(open(f))
            except Exception: continue
            if not isinstance(P, dict): continue
            for a in P.get('auctions') or []:
                if 'fore' not in str(a.get('listing_type') or '').lower(): continue
                k = case_key(a.get('auction_caseno')); pn = norm_plaintiff(a.get('auction_plaintiffs'))
                if not k or not pn: continue
                e = (pn, str(a.get('auction_plaintiffs'))[:80], _money(a.get('auction_fj')))
                if e not in idx.setdefault(k, []): idx[k].append(e)
    return idx

def outcomes(sw=SW, idx=None):
    """-> list of dict(co, d, case, pl, ref, av, sold, kind) for FC results sold (to plaintiff or 3rd party) with a known plaintiff."""
    idx = po_case_index() if idx is None else idx
    out = []
    for f in glob.glob(os.path.join(sw, 'results', '*.json')):
        host, date = os.path.basename(f)[:-5].rsplit('_', 1)
        co = host.split('.')[0].replace('-', '').replace('myorangeclerk', 'orange')
        try: data = json.load(open(f))
        except Exception: continue
        for r in data:
            if 'FORECL' not in str(r.get('Auction Type') or '').upper(): continue
            res = r.get('res') or {}
            if res.get('A') != 'Auction Sold': continue
            to = str(res.get('ST') or '')
            who = 'PL' if 'Plaintiff' in to else '3P' if '3rd' in to else None
            sold = _money(res.get('D'))
            if not who or not sold: continue
            ref = _money(r.get('Final Judgment Amount')); av = _money(r.get('Assessed Value'))
            k = case_key(r.get('Case #'))
            cands = idx.get(k) or []
            pl = None
            for pn, raw, fj in cands:     # confirmação pelo julgamento
                if ref and fj and abs(fj - ref) <= max(2.0, 0.01 * ref): pl = pn; break
            if pl is None and len({c[0] for c in cands}) == 1 and not any(c[2] for c in cands): pl = cands[0][0]
            if not pl: continue
            kind = 'released' if who == '3P' else ('nocontest' if sold <= NOCONTEST else 'kept')
            out.append(dict(co=co, d=date, case=r.get('Case #'), pl=pl, ref=ref, av=av, sold=sold, kind=kind))
    return out

def _med(v):
    v = sorted(x for x in v if x is not None)
    return round(v[len(v) // 2], 3) if v else None

def summarize(rows):
    """plaintiff -> {n, kept, released, nocontest, keptJ, relJ, keptA, relA, cos} (J = ÷ julgamento, A = ÷ valor do condado; medianas)"""
    S = {}
    for r in rows:
        s = S.setdefault(r['pl'], dict(n=0, kept=0, released=0, nocontest=0, _kj=[], _rj=[], _ka=[], _ra=[], cos={}))
        s['n'] += 1; s[r['kind']] += 1; s['cos'][r['co']] = s['cos'].get(r['co'], 0) + 1
        j = r['sold'] / r['ref'] if r['ref'] else None; a = r['sold'] / r['av'] if r['av'] else None
        if r['kind'] == 'kept': s['_kj'].append(j); s['_ka'].append(a)
        if r['kind'] == 'released': s['_rj'].append(j); s['_ra'].append(a)
    for s in S.values():
        s['keptJ'], s['relJ'], s['keptA'], s['relA'] = _med(s.pop('_kj')), _med(s.pop('_rj')), _med(s.pop('_ka')), _med(s.pop('_ra'))
    return S

if __name__ == '__main__':
    rows = outcomes(); S = summarize(rows)
    print(len(rows), 'resultados com autor;', len(S), 'autores')
    for k, s in sorted(S.items(), key=lambda kv: -kv[1]['n'])[:15]: print(k, s)
