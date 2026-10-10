"""Tax deed sale notices from floridapublicnotices.com (Florida Press Association statewide archive, Fla. Stat. 50.0211).

Used only for counties whose clerk publishes no parcel list online. Polite by design:
- one search request per newspaper per day (cached), notice PDFs fetched once each (permanent cache);
- >= 3 s between requests; any 403/429/5xx stops the whole run for the day (no retry, no circumvention).
The site's own JSON search (POST / with keywords+paper) is the same call its search page makes.
"""
import datetime as dt, json, os, re, subprocess, time

DIR = '/workspace/auc/statewide/notices'
BASE = 'https://floridapublicnotices.com/'
UA = 'Mozilla/5.0 (ChallengeCapital; leiloes-florida; contato via clerk)'
GAP = 3.0
# county -> newspaper ids (from the site's newspaper list) that carry its legal ads
PAPERS = {'hardee': [179], 'desoto': [285, 265, 92, 339], 'bradford': [173, 227], 'glades': [222],
          'taylor': [161], 'madison': [143], 'union': [228, 173, 168, 227], 'dixie': [246]}
NAMES = {'desoto': r'DE\s?SOTO', 'hardee': 'HARDEE', 'bradford': 'BRADFORD', 'glades': 'GLADES',
         'taylor': 'TAYLOR', 'madison': 'MADISON', 'union': 'UNION', 'dixie': 'DIXIE'}
MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                      'september', 'october', 'november', 'december'], 1)}


class Blocked(Exception):
    pass


_last = [0.0]


def _req(method, url, body=None, accept='application/hal+json'):
    import requests
    w = GAP - (time.time() - _last[0])
    if w > 0: time.sleep(w)
    _last[0] = time.time()
    h = {'User-Agent': UA, 'Accept': accept}
    if body is not None: h['Content-Type'] = 'application/json'
    r = requests.request(method, url, headers=h, data=json.dumps(body) if body is not None else None, timeout=60)
    if r.status_code in (401, 403, 429) or r.status_code >= 500:
        raise Blocked(f'{r.status_code} {url}')
    r.raise_for_status()
    return r


def _search(paper, today, offline):
    p = os.path.join(DIR, f'search_{paper}_{today}.json')
    if os.path.exists(p): return json.load(open(p))
    if offline:
        olds = sorted(f for f in os.listdir(DIR) if f.startswith(f'search_{paper}_')) if os.path.isdir(DIR) else []
        return json.load(open(os.path.join(DIR, olds[-1]))) if olds else None
    d = _req('POST', BASE, dict(keywords='"tax deed"', paper=str(paper), limit=100, offset=0)).json()
    L = d.get('_embedded', {}).get('notices', [])
    cut = (dt.date.fromisoformat(today) - dt.timedelta(days=75)).isoformat()
    while L and len(L) < min(d.get('totalCount') or 0, 300) and (L[-1].get('date') or '') >= cut:   # next page only while still recent
        L += _req('POST', BASE, dict(keywords='"tax deed"', paper=str(paper), limit=100, offset=len(L))).json().get('_embedded', {}).get('notices', []) or [None]
        L = [x for x in L if x]
    d.setdefault('_embedded', {})['notices'] = L
    os.makedirs(DIR, exist_ok=True); json.dump(d, open(p, 'w'))
    return d


def _text(n, offline):
    t = n.get('notice') or ''
    if len(t) > 300: return t
    fp = os.path.join(DIR, 'txt', f"{n['id']}.txt")
    if os.path.exists(fp): return open(fp).read()
    ext = (n.get('image') or 'pdf').lower()
    if offline or ext not in ('pdf', 'png', 'jpg', 'jpeg'): return t
    url = f"https://dgfc4k3gho5kh.cloudfront.net/{str(n['id'])[-2:]}/{n['id']}.{ext}"
    b = _req('GET', url, accept='*/*').content
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    tmp = fp + '.' + ext; open(tmp, 'wb').write(b)
    if ext == 'pdf': out = subprocess.run(['pdftotext', '-layout', tmp, '-'], capture_output=True, text=True).stdout
    else: out = subprocess.run(['tesseract', tmp, '-'], capture_output=True, text=True).stdout   # image-only notice: OCR
    os.remove(tmp)
    if len(out) > 100: open(fp, 'w').write(out)
    return out


def _date(t):
    T = re.sub(r'\s+', ' ', t)
    m = re.search(r'(?:on|the)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+day\s+of\s+([A-Za-z]+),?\s+(\d{4})', T, re.I)
    if m and m.group(2).lower() in MONTHS: return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
    for m in re.finditer(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', T, re.I):
        ctx = T[max(0, m.start() - 160):m.start()].lower()
        if re.search(r'sold|sale|auction|bidder|redeemed', ctx) and not re.search(r'dated|issuance|issued', T[max(0, m.start() - 30):m.start()].lower()):
            return dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
    m = re.search(r'(?:sold|sale|bidder)[^.]{0,120}?\bon\s+(\d{1,2})/(\d{1,2})/(\d{4})', T, re.I)
    if m: return dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    return None


def parse(t):
    T = re.sub(r'[ \t]+', ' ', t)
    g = lambda rx, fl=re.I: (re.search(rx, T, fl).group(1).strip() if re.search(rx, T, fl) else None)
    parcel = g(r'(?:Parcel\s*(?:ID|I\.D\.)?\s*(?:Number|No\.?|#)?|PARCEL)\s*[:#]\s*([0-9A-Z][0-9A-Z\-\. ]{5,40}?)\s*(?:\n|$|,|;)')
    if parcel: parcel = re.sub(r'[\s\-\.]', '', parcel).upper()
    tm = g(r'at\s+(\d{1,2}:\d{2})\s*([AaPp])\.?\s*[Mm]')
    pm = re.search(r'at\s+\d{1,2}:\d{2}\s*[Pp]\.?\s*[Mm]', T)
    if tm and pm and int(tm.split(':')[0]) < 12: tm = f"{int(tm.split(':')[0]) + 12}:{tm.split(':')[1]}"
    ob = g(r'(?:OPENING\s+BID(?:\s+AMOUNT)?|MINIMUM\s+BID|BASE\s+BID)[^$\d]{0,30}[\$S]\s*([\d,]+\.\d{2})')
    return dict(
        date=_date(T), time=tm, parcel=parcel,
        cert=g(r'CERTIFICATE\s*(?:NO\.?|NUMBER|#)\s*:?\s*#?\s*(\d[\w\-/]*)'),
        year=g(r'YEAR\s+OF\s+ISSUANCE\s*:?\s*(\d{4})'),
        file=g(r'(?:TAX\s+DEED\s+(?:FILE|CASE)\s*(?:NO\.?|NUMBER|#)|FILE\s+(?:NO\.?|NUMBER))\s*:?\s*([\w\-]+)'),
        holder=g(r'(?:that|THAT)\s+([A-Z0-9][^\n,]{2,80}?),?\s+(?:the\s+)?holder', 0),
        owner=g(r'(?:NAMES?(?:\(S\))?\s+IN\s+WHICH\s+(?:IT\s+WAS\s+)?ASSESSED|Names?(?:\(s\))?\s+[Ii]n\s+[Ww]hich\s+[Aa]ssessed)\s*(?:IS|ARE|WAS)?\s*:?[ \t]*\n?\s*([A-Za-z][^\n]{2,120})', 0),
        ob=float(ob.replace(',', '')) if ob else None,
        paddr=g(r'PROPERTY\s+ADDRESS\s*:?\s*\n?\s*(\d+[^\n]{3,80})'),
        legal=re.sub(r'\s+', ' ', g(r'Description\s+of\s+Property\s*:?\s*(.{10,400}?)(?:Parcel|NAME|All of|SUBJECT|$)', re.I | re.S) or '')[:220],
        redeemed=bool(re.search(r'\bREDEEMED\b|\bCANCEL+ED\b|\bWITHDRAWN\b', T)) and not re.search(r'shall be redeemed|unless .{0,40}redeemed', T, re.I))


def collect(counties=None, offline=False, today=None):
    """Return ({county: [notice dicts]}, stats). Newest publication per (county, cert/parcel) wins."""
    today = today or dt.date.today().isoformat()
    out, st, blocked = {}, {}, None
    for co in (counties or PAPERS):
        seen, s = {}, dict(papers=PAPERS[co], notices=0, td=0, upcoming=0, nopar=0, err=None)
        for pid in PAPERS[co]:
            if blocked and not offline: s['err'] = 'parado: ' + blocked; break
            try: d = _search(pid, today, offline or bool(blocked))
            except Blocked as e: blocked = str(e); s['err'] = 'bloqueado: ' + blocked; break
            except Exception as e: s['err'] = type(e).__name__; continue
            if not d: continue
            for n in sorted(d.get('_embedded', {}).get('notices', []), key=lambda n: n.get('date') or '', reverse=True):
                if (n.get('date') or '') < (dt.date.fromisoformat(today) - dt.timedelta(days=75)).isoformat(): continue
                s['notices'] += 1
                key0 = re.sub(r'\s+', ' ', (n.get('notice') or '').strip()) if len(n.get('notice') or '') < 300 else None
                if key0 and key0 in seen: continue          # same short title = same notice re-published; read newest only
                try: t = _text(n, offline or bool(blocked))
                except Blocked as e: blocked = str(e); s['err'] = 'bloqueado: ' + blocked; break
                except Exception: continue
                if not re.search(r'TAX\s+DEED', t, re.I) or not re.search(NAMES[co] + r'\s+COUNTY', t, re.I): continue
                p = parse(t); s['td'] += 1
                k = p.get('cert') and f"{p.get('year')}-{p['cert']}" or p.get('parcel') or key0 or n['id']
                if key0: seen[key0] = 1
                if k in seen: continue
                seen[k] = 1
                p.update(nid=n['id'], pub=n.get('date'), paper=n.get('paper'), url=f"{BASE}notices/{n['id']}")
                if not p['date'] or p['date'].isoformat() < today or p['redeemed']: continue
                if not p['parcel']: s['nopar'] += 1
                p['date'] = p['date'].isoformat()
                out.setdefault(co, []).append(p); s['upcoming'] += 1
        st[co] = s
    return out, st


if __name__ == '__main__':
    import sys
    o, s = collect(sys.argv[1].split(',') if len(sys.argv) > 1 else None)
    print(json.dumps(s, indent=1))
    for co, L in o.items():
        for p in L: print(co, p['date'], p['time'], p['parcel'], p['cert'], p['ob'], (p['owner'] or '')[:30], '|', p['legal'][:50])
