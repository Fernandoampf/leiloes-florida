#!/usr/bin/env python3
"""Official IN-PERSON foreclosure sale lists (Lake, Osceola: sales at the courthouse, not on RealAuction).

Lake:    https://foreclosurecalendar.lakecountyclerkfl.gov/default.aspx  (HTML calendar: case, parties, time, Canceled)
Osceola: https://courts.osceolaclerk.com/reports/CivilMortgageForeclosuresWeb.pdf (PDF, weekdays before 8 AM)

fetch once a day (polite, single request per county) into AUC/statewide/inperson/<county>_<YYYY-MM-DD>.<ext>;
offline / network error -> newest cached copy.  merge() matches to items by case number, updates dates, drops
canceled sales, adds the cases we do not have, and tags every Lake/Osceola foreclosure with the in-person sale info.
"""
import datetime as dt, glob, html, os, re, subprocess, urllib.request

DIR = os.path.join(os.environ.get('AUC', '/workspace/auc'), 'statewide', 'inperson')
UA = 'Mozilla/5.0 (ChallengeCapital daily refresh; 1 request/day)'
SRC = {
    'gulf_td': ('https://www.gulfclerk.com/courts/tax-deeds/', 'html'),
    'sumter_td': ('https://www.sumterclerk.com/public-records/tax-deeds/tax-deed-sales/', 'html'),
    'lake': ('https://foreclosurecalendar.lakecountyclerkfl.gov/default.aspx', 'html'),
    'osceola': ('https://courts.osceolaclerk.com/reports/CivilMortgageForeclosuresWeb.pdf', 'pdf'),
}
INFO = {
    'gulf': dict(where='Fórum de Port St. Joe — lobby do Gulf County Courthouse, 1000 Cecil G. Costin Sr. Blvd., Port St. Joe', time='11:00', city='Port St. Joe',
                 pay='Tax deed PRESENCIAL, 11h (inscrição na hora, 15 min antes; sem lance por internet/correio). Depósito não reembolsável de 5% do lance (mín. US$ 200) na hora, só dinheiro ou cheque administrativo/certified funds (sem cheque comum ou cartão; não pode sair para buscar). Saldo + doc stamps e registro em 24 horas.',
                 docket='https://www.gulfclerk.com/courts/tax-deeds/', dname='Gulf Clerk — Tax Deed Sales (lista e PDF do processo)',
                 list='https://www.gulfclerk.com/courts/tax-deeds/'),
    'sumter': dict(where='Fórum de Bushnell — 316 E. Anderson Ave., Bushnell (Sumter)', time='11:00', city='Bushnell',
                   pay='Tax deed PRESENCIAL (não é RealAuction). Depósito de 5% do lance (mín. US$ 200) na hora, em dinheiro/cheque administrativo; saldo conforme o clerk (em geral até o dia útil seguinte).',
                   docket='https://www.sumterclerk.com/public-records/tax-deeds/tax-deed-sales/', dname='Sumter Clerk — Tax Deed Sales',
                   list='https://www.sumterclerk.com/public-records/tax-deeds/tax-deed-sales/'),
    'collier': dict(where='Fórum de Naples — Collier County Courthouse, 1º andar, Multi-Purpose Room, 3315 Tamiami Trail E., Naples', time='13:00', city='Naples',
                    pay='Tax deed PRESENCIAL às segundas, 13h (chegar 15 min antes; sem lance por internet). Depósito de 5% do lance (mín. US$ 200) na hora, só dinheiro ou cheque administrativo; saldo + doc stamps e registro em 24 horas. O edital não mostra o opening bid nem resgates: conferir com o clerk (Tax Deeds, 239-252-2646) antes do leilão.',
                    docket='https://www.collierclerk.com/tax-deed-sales/', dname='Collier Clerk — Tax Deed Sales (lista e edital)',
                    list='https://notices.collierclerk.com/genre/tax-deeds/'),
    'lake': dict(city='Tavares', where='Fórum de Tavares — Lake County Courthouse (lobby), 550 W. Main St., Tavares', time='11:00',
                 pay='Leilão presencial seg–sex 11h. Depósito de 5% na hora do lance; saldo até 16h do mesmo dia.',
                 docket='https://courtrecords.lakecountyclerk.org/showcaseweb/', dname='Lake ShowCase',
                 list='https://foreclosurecalendar.lakecountyclerkfl.gov/default.aspx'),
    'osceola': dict(city='Kissimmee', where='Fórum de Kissimmee — 3 Courthouse Square, sala 204 (2º andar), Kissimmee', time='11:00',
                    pay='Leilão presencial 11h. Taxa do clerk US$ 70, depósito de 5% na hora; saldo até 16h. Cancelamentos até 10h30 do dia.',
                    docket='https://courts.osceolaclerk.com/BenchmarkWeb/Home.aspx/Search', dname='Osceola Benchmark',
                    list='https://courts.osceolaclerk.com/reports/CivilMortgageForeclosuresWeb.pdf'),
}
HOA_RE = re.compile(r'\b(H\.?O\.?A|HOMEOWNER\S*|HOMOWNERS?|ASSOCIAT\w*|OWNERS|CONDOMINIUM|CONDO|ASSOCIATION|ASSN|ASSOC|COMMUNITY|PROPERTY OWNERS|MASTER|CLUB|VILLAS?|ESTATES|TOWNHOMES)\b')
BANK_RE = re.compile(r'\b(BANK|MORTGAGE|LOANS?|LOANDEPOT\S*|ANNUITY|FINANCE OF AMERICA|LENDING|FUNDING|FINANCIAL|TRUST(EE)?|SERVICING|CREDIT UNION|FEDERAL|FANNIE|FREDDIE|HUD|SECRETARY|NATIONAL ASSOCIATION|N\.A\.|CAPITAL|SAVINGS|INVESTMENT|ACQUISITION|REVERSE|NEWREZ|LAKEVIEW|ROCKET|NATIONSTAR|FREEDOM|PENNYMAC|CARRINGTON|SPECIALIZED|SELENE|SHELLPOINT|MIDFIRST|WELLS FARGO|CITIMORTGAGE|U\.?S\.? BANK|DEUTSCHE|JPMORGAN|CHASE)\b')


def ptype(plaintiff):
    """'hoa' (association/condo: first mortgage SURVIVES), 'banco' (lender), or 'outro' (private/individual)."""
    p = (plaintiff or '').upper()
    if re.search(r'\bASSOCIATION\b', p) and re.search(r'\bNATIONAL ASSOCIATION\b|\bBANK\b|TRUST', p): return 'banco'
    if HOA_RE.search(p) and not BANK_RE.search(p): return 'hoa'
    if BANK_RE.search(p): return 'banco'
    return 'outro'


def ckey(s):
    """year + court type + sequence (no zeros/suffix): '2025 CA 002176 MF' / '2025CA002176' / '2025-CA-2176' -> '2025CA2176'."""
    s = re.sub(r'[^A-Z0-9]', '', (s or '').upper())
    m = re.match(r'^(?:\d{2})?(\d{2}|\d{4})?(CA|CC|DR|CP)0*(\d+)', s) or re.match(r'^(\d{4})(CA|CC)0*(\d+)', s)
    if m:
        y = m.group(1) or ''
        if len(y) == 2: y = '20' + y
        return f'{y}{m.group(2)}{int(m.group(3))}'
    m = re.match(r'^0*(\d+)(\d{4})$', s)       # PropertyOnion Lake style '00979-2024' -> seq + year
    if m: return f'{m.group(2)}?{int(m.group(1))}'
    return s


def fetch(county, offline=False, today=None):
    today = today or dt.date.today().isoformat()
    url, ext = SRC[county]
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, f'{county}_{today}.{ext}')
    if not offline and not os.path.exists(path):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            data = urllib.request.urlopen(req, timeout=40).read()
            if len(data) > 5000:
                open(path, 'wb').write(data)
        except Exception as e:
            print(f'inperson: {county} fetch failed ({type(e).__name__}); using cache')
    files = sorted(glob.glob(os.path.join(DIR, f'{county}_*.{ext}')))
    return files[-1] if files else None


def _year_for(mm, dd, ref):
    y = ref.year
    d = dt.date(y, mm, dd)
    if (ref - d).days > 120: d = dt.date(y + 1, mm, dd)
    return d


def parse_lake(path, ref):
    s = open(path, encoding='utf-8', errors='ignore').read()
    out = []
    for blk in re.split(r'<div class="event_item">', s)[1:]:
        if 'Foreclosure' not in blk: continue
        m = re.search(r'event_time[^>]*>\s*\w+,\s*(\d{1,2})/(\d{1,2})<br\s*/?>\s*([\d:]+\s*[AP]M)', blk)
        c = re.search(r"sale_details\.aspx\?id=(\d+)\">\s*<span class='pscalendar-(\w+)'>\s*([^:<]+):\s*(.*?)</span>", blk, re.S)
        if not (m and c): continue
        d = _year_for(int(m.group(1)), int(m.group(2)), ref)
        txt = html.unescape(re.sub(r'\s+', ' ', c.group(4))).strip()
        pl, _, df = txt.partition(' vs ')
        cx = re.search(r"pscalendar-red'>\s*([^<]+)<", blk)
        loc = re.search(r'<br\s*/?>\s*([^<]+?)\s*</div>', blk[c.end():])
        out.append(dict(county='lake', case=c.group(3).strip(), date=d.isoformat(), time=m.group(3).strip(),
                        plaintiff=pl.strip(), defendant=df.strip(), canceled=bool(cx) or c.group(2) == 'cancelled',
                        cxwhy=html.unescape(cx.group(1)).strip() if cx else None,
                        room=(loc.group(1).strip() if loc else None),
                        detail=f'https://foreclosurecalendar.lakecountyclerkfl.gov/sale_details.aspx?id={c.group(1)}'))
    return out


def parse_osceola(path, ref):
    txt = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True).stdout
    lines = [l.rstrip() for l in txt.split('\n')]
    upd = re.search(r'Last Updated:\s*\w+,\s*(\w+ \d+, \d{4})', txt)
    out, buf = [], []
    i = 0
    while i < len(lines):
        l = lines[i]
        m = re.match(r'^\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{4}\s+[A-Z]{2}\s+\d+(?:\s+[A-Z]{1,3})?)\s*(.*)$', l)
        if m:
            pl = ' '.join(x.strip() for x in buf if x.strip())
            rest = [m.group(5)]
            j = i + 1
            while j < len(lines) and lines[j].strip() and not re.match(r'^\s*\d{2}/\d{2}/\d{4}', lines[j]) and 'Page ' not in lines[j]:
                rest.append(lines[j].strip()); j += 1
            df = re.sub(r'^\s*vs\.?\s*', '', ' '.join(x for x in rest if x).strip())
            out.append(dict(county='osceola', case=re.sub(r'\s+', ' ', m.group(4)).strip(),
                            date=f'{m.group(3)}-{m.group(1)}-{m.group(2)}', time='11:00 AM',
                            plaintiff=pl, defendant=df, canceled=False, cxwhy=None, room='Room 204', detail=None))
            buf = []; i = j; continue
        if not l.strip() or 'Page ' in l or 'Last Updated' in l or re.search(r'Sale Date\s+Case Number', l) or l.strip() == 'vs.':
            if not l.strip() or 'Page ' in l: buf = [] if 'Page ' in l else buf
            i += 1; continue
        buf.append(l.strip()); buf = buf[-3:]
        i += 1
    return out, (upd.group(1) if upd else None)


def parse_sumter_td(path):
    """Sumter clerk page embeds the sale list as JSON in <tax-deed-sales :taxdeeds="[...]">."""
    import json
    s = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r':taxdeeds="(\[.*?\])"', s, re.S)
    if not m: return []
    rows = json.loads(html.unescape(m.group(1)))
    out = []
    for r in rows:
        try: d = dt.datetime.strptime(r.get('sale_date') or '', '%b %d, %Y').date()
        except Exception: continue
        ob = None
        try: ob = float(str(r.get('opening_bid') or '').replace(',', '').replace('$', ''))
        except Exception: pass
        out.append(dict(file=str(r.get('file') or ''), cert=str(r.get('cert') or ''), parcel=(r.get('parcel') or '').strip(), date=d.isoformat(),
                        ob=ob, holder=r.get('cert_holder'), owner=r.get('owner'), status=(r.get('status') or '').lower(),
                        notes=re.sub(r'\s+', ' ', r.get('notes') or '').strip(), link=r.get('link')))
    return out


def parse_gulf_td(path):
    """gulfclerk.com tax-deed page: one '<div class="shadow mb-2">' card per sale."""
    s = open(path, encoding='utf-8', errors='ignore').read(); out = []
    txt = lambda h: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h))).strip()
    for blk in s.split('<div class="shadow mb-2">')[1:]:
        t = txt(blk)
        d = re.search(r'Sale Date (\d\d)/(\d\d)/(\d\d)', t)
        if not d: continue
        g = lambda rx: (re.search(rx, t) or [None, None])[1]
        pdf = re.search(r'href="([^"]+\.pdf)"', blk)
        loc = re.search(r'<strong>Location</strong></p>(.*?)</div>', blk, re.S)
        lines = [txt(x) for x in re.findall(r'<p>(.*?)</p>', loc.group(1), re.S)] if loc else []
        street = re.sub(r'^VACANT,?\s*', '', lines[0]) if lines else ''
        out.append(dict(date=f'20{d.group(3)}-{d.group(1)}-{d.group(2)}', cert=g(r'Certificate No\. (\S+)'), case=g(r'Case No\. (\S+)'),
                        parcel=g(r'Parcel ID (\S+)'), status=(g(r'Parcel ID \S+ (\w+)') or '').lower(),
                        holder=g(r'Applicant (.+?) Owner'), owner=g(r'Owner (.+?) Location'), vacant=bool(lines and lines[0].upper().startswith('VACANT')),
                        street=street, city=(lines[1].title() if len(lines) > 1 else ''), ob=_m(g(r'\$([\d,]+\.\d\d)')), link=pdf.group(1) if pdf else None))
    return out


def _m(v):
    try: return float(v.replace(',', '')) if v else None
    except Exception: return None


def fetch_collier(offline=False, today=None, max_pages=12):
    """Collier legal notices RSS (genre tax-deeds), paged; 1 request/second, cached once a day as one JSON file."""
    import json, time
    today = today or dt.date.today().isoformat()
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, f'collier_td_{today}.json')
    if not offline and not os.path.exists(path):
        pages = []
        try:
            for pg in range(1, max_pages + 1):
                url = 'https://notices.collierclerk.com/genre/tax-deeds/feed/' + (f'?paged={pg}' if pg > 1 else '')
                req = urllib.request.Request(url, headers={'User-Agent': UA})
                try: data = urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'ignore')
                except Exception: break
                if '<item>' not in data: break
                pages.append(data)
                # stop once a whole page was published > 120 days ago (sales happen ~4-8 weeks after publication)
                dts = re.findall(r'<pubDate>[A-Za-z]{3}, (\d{1,2} [A-Za-z]{3} \d{4})', data)
                if dts and all((dt.date.fromisoformat(today) - dt.datetime.strptime(d, '%d %b %Y').date()).days > 120 for d in dts): break
                time.sleep(1)
            if pages: json.dump(pages, open(path, 'w'))
        except Exception as e:
            print(f'inperson: collier fetch failed ({type(e).__name__}); using cache')
    files = sorted(glob.glob(os.path.join(DIR, 'collier_td_*.json')))
    return files[-1] if files else None


def parse_collier(path):
    import json
    out, seen = [], set()
    for page in json.load(open(path)):
        for it in re.findall(r'<item>(.*?)</item>', page, re.S):
            t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', html.unescape(it))))
            if 'APPLICATION FOR TAX DEED' not in t.upper(): continue
            app = re.search(r'Tax Deed Application #\s*(\d+)', t); pid = re.search(r'Parcel ID#?\s*([0-9A-Z-]+)', t)
            sd = re.search(r'on (?:Monday|Tuesday|Wednesday|Thursday|Friday),\s*([A-Za-z]+ \d{1,2}, \d{4})', t)
            if not (app and sd): continue
            if app.group(1) in seen: continue
            seen.add(app.group(1))
            try: d = dt.datetime.strptime(sd.group(1), '%B %d, %Y').date()
            except Exception: continue
            ad = re.search(r'Property Address:\s*(.*?)\s*Name in Which Assessed', t)
            cert = re.search(r'Certificate Number:\s*([0-9/]+)', t); desc = re.search(r'Description of Property:\s*(.*?)\s*Parcel ID', t)
            holder = re.search(r'given that:\s*(.*?)\s*the holder of', t); own = re.search(r'Name in Which Assessed:\s*(.*?)\s*(?:Name on Last|All of said)', t)
            link = re.search(r'(https://notices\.collierclerk\.com/notice/[^ ]+/)', t)
            a = (ad.group(1).strip() if ad else '')
            if a.upper() in ('N/A', 'NONE', 'UNASSIGNED', 'NO SITUS', ''): a = ''
            out.append(dict(app=app.group(1), cert=cert.group(1) if cert else None, parcel=pid.group(1) if pid else None, addr=a,
                            desc=(desc.group(1).strip() if desc else None), date=d.isoformat(), holder=holder.group(1).strip() if holder else None,
                            owner=own.group(1).strip() if own else None, link=link.group(1) if link else None))
    return out


def td_items(offline=False, today=None):
    """Clerk-run (in-person) TAX DEED sales -> list of ('TD', raw item) in the RealAuction item shape, plus stats."""
    today = today or dt.date.today().isoformat()
    items, st = [], {}
    p = fetch('sumter_td', offline, today)
    if p:
        rows = parse_sumter_td(p); i = INFO['sumter']; kept = 0
        for r in rows:
            if r['date'] < today or r['status'] not in ('scheduled', 'rescheduled', ''): continue
            ds = f"{r['date'][5:7]}/{r['date'][8:]}/{r['date'][:4]}"
            x = dict(county='sumter', host=None, date=ds, aid='sumtd' + r['file'], case='TD ' + r['file'], parcel=r['parcel'] or None,
                     plink=None, street='', addr='', multi=None, av=None, url=i['list'], detail=r.get('link') or i['list'],
                     ob=r['ob'], cert=r['cert'], owner=r.get('owner'), time='11:00 AM')
            x['inperson'] = dict(co='sumter', city=i['city'], where=i['where'], time='11:00 AM', pay=i['pay'], docket=i['docket'], dname=i['dname'],
                                 list=i['list'], detail=x['detail'], plaintiff=r.get('holder'), defendant=r.get('owner'), ptype=None,
                                 room=None, case=x['case'], kind='TD')
            x['plaintiff'] = r.get('holder')
            items.append(('TD', x)); kept += 1
        st['sumter'] = dict(file=os.path.basename(p), listed=len(rows), upcoming=kept,
                            status={k: sum(1 for r in rows if r['status'] == k) for k in {r['status'] for r in rows}},
                            dates=sorted({r['date'] for r in rows if r['date'] >= today}))
    p = fetch('gulf_td', offline, today)
    if p:
        rows = parse_gulf_td(p); i = INFO['gulf']; kept = 0
        for r in rows:
            if r['date'] < today or r['status'] not in ('active', 'scheduled', ''): continue
            ds = f"{r['date'][5:7]}/{r['date'][8:]}/{r['date'][:4]}"
            addr = (f"{r['street']}, {r['city']}, FL" if r['street'] else '')
            x = dict(county='gulf', host=None, date=ds, aid='gultd' + re.sub(r'\W', '', r['case'] or r['cert'] or ''), case=r['case'], parcel=r['parcel'],
                     plink=None, street=r['street'], addr=addr, multi=None, av=None, url=i['list'], detail=r.get('link') or i['list'],
                     ob=r['ob'], cert=r['cert'], owner=r.get('owner'), time='11:00 AM')
            if not addr: x['addr'] = f"Processo {r['case']} — endereço pela parcela {r['parcel']}"
            x['inperson'] = dict(co='gulf', city=i['city'], where=i['where'], time='11:00 AM', pay=i['pay'], docket=i['docket'], dname=i['dname'],
                                 list=i['list'], detail=x['detail'], plaintiff=r.get('holder'), defendant=r.get('owner'), ptype=None,
                                 room=None, case=x['case'], kind='TD')
            x['plaintiff'] = r.get('holder')
            items.append(('TD', x)); kept += 1
        st['gulf'] = dict(file=os.path.basename(p), listed=len(rows), upcoming=kept,
                          status={k: sum(1 for r in rows if r['status'] == k) for k in {r['status'] for r in rows}},
                          dates=sorted({r['date'] for r in rows if r['date'] >= today}))
    p = fetch_collier(offline, today)
    if p:
        rows = parse_collier(p); i = INFO['collier']; kept = 0
        for r in rows:
            if r['date'] < today: continue
            ds = f"{r['date'][5:7]}/{r['date'][8:]}/{r['date'][:4]}"
            a = r['addr']; street = re.sub(r',.*$', '', a) if a else ''
            x = dict(county='collier', host=None, date=ds, aid='coltd' + r['app'], case='TD ' + r['app'], parcel=r['parcel'],
                     plink=None, street=street, addr=(a.replace(', FL ', ', FL- ') if a else ''), multi=None, av=None, url=i['list'],
                     detail=r.get('link') or i['list'], ob=None, cert=r['cert'], owner=r.get('owner'), time='1:00 PM', desc=r.get('desc'))
            x['inperson'] = dict(co='collier', city=i['city'], where=i['where'], time='1:00 PM', pay=i['pay'], docket=i['docket'], dname=i['dname'],
                                 list=i['list'], detail=x['detail'], plaintiff=r.get('holder'), defendant=r.get('owner'), ptype=None, room=None,
                                 case=x['case'], kind='TD')
            x['plaintiff'] = r.get('holder')
            items.append(('TD', x)); kept += 1
        st['collier'] = dict(file=os.path.basename(p), notices=len(rows), upcoming=kept, dates=sorted({r['date'] for r in rows if r['date'] >= today}))
    return items, st


def load(offline=False, today=None):
    ref = dt.date.fromisoformat(today) if today else dt.date.today()
    res = {}
    for co in ('lake', 'osceola'):
        p = fetch(co, offline, ref.isoformat())
        if not p: res[co] = dict(rows=[], file=None); continue
        if co == 'lake': rows, upd = parse_lake(p, ref), None
        else: rows, upd = parse_osceola(p, ref)
        rows = [r for r in rows if 'TIMESHARE' not in r['plaintiff'].upper()]   # timeshares are excluded site-wide
        for r in rows: r['ptype'] = ptype(r['plaintiff'])
        res[co] = dict(rows=rows, file=os.path.basename(p), updated=upd)
    return res


def tag(x, row, co):
    i = INFO[co]
    x['host'] = None                          # in-person sale: never a RealAuction host
    x['url'] = i['list']; x['detail'] = row.get('detail') or i['list']
    if row.get('plaintiff') and not x.get('plaintiff'): x['plaintiff'] = row['plaintiff']
    x['inperson'] = dict(co=co, city=i.get('city'), kind='FC', where=i['where'], time=row.get('time') or i['time'], pay=i['pay'], docket=i['docket'],
                         dname=i['dname'], list=i['list'], detail=row.get('detail'), plaintiff=row.get('plaintiff'),
                         defendant=row.get('defendant'), ptype=row.get('ptype'), room=row.get('room'), case=row.get('case'))


def merge(items, offline=False, today=None):
    """Apply official lists to Lake/Osceola foreclosure items. Returns stats per county."""
    today = today or dt.date.today().isoformat()
    data = load(offline, today)
    st = {}
    for co, d in data.items():
        rows = [r for r in d['rows'] if r['date'] >= today]
        if not d['file']: st[co] = dict(file=None); continue
        cur = [it for it in items if it['src'] == 'FC' and (it['raw'].get('county') or '').lower() == co]
        idx = {}
        for it in cur: idx.setdefault(ckey(it['raw'].get('case')), []).append(it)
        # PropertyOnion Lake-style 'seq-year' keys carry no court type: also index them loosely
        loose = {re.sub(r'(CA|CC|\?)', '?', k): v for k, v in idx.items()}
        seen, matched, added, canceled, moved, cx_ours = set(), 0, 0, 0, 0, 0
        drop = set()
        by_case = {}
        for r in rows:        # same case listed twice (reset / canceled + new date): keep the live one, latest list order
            k = ckey(r['case'])
            if k not in by_case or (by_case[k]['canceled'] and not r['canceled']): by_case[k] = r
        for k, r in by_case.items():
            hits = idx.get(k) or loose.get(re.sub(r'(CA|CC)', '?', k))
            if hits:
                matched += 1; seen.add(k)
                for it in hits:
                    if r['canceled']:
                        drop.add(id(it)); cx_ours += 1; continue
                    x = it['raw']
                    ds = f"{r['date'][5:7]}/{r['date'][8:]}/{r['date'][:4]}"
                    if x.get('date') != ds: moved += 1; x['date'] = ds
                    tag(x, r, co)
                if r['canceled']: canceled += 1
                continue
            if r['canceled']: canceled += 1; continue
            ds = f"{r['date'][5:7]}/{r['date'][8:]}/{r['date'][:4]}"
            x = dict(county=co.capitalize(), host=None, date=ds, aid='ip' + co[:3] + re.sub(r'[^0-9A-Z]', '', r['case'].upper()),
                     case=r['case'], parcel=None, plink=None, street=None, addr='', av=None,
                     url=INFO[co]['list'], detail=r.get('detail') or INFO[co]['list'], owner=None, fj=None, pmax=None,
                     plaintiff=r['plaintiff'])
            tag(x, r, co)
            items.append(dict(src='FC', raw=x, known=None, avoid=None, po_only=True, inperson_only=True))
            added += 1; seen.add(k)
        # our items in these counties absent from the official list: not scheduled any more
        gone = 0
        for k, its in idx.items():
            if k in seen or re.sub(r'(CA|CC|\?)', '?', k) in {re.sub(r'(CA|CC)', '?', s) for s in seen}: continue
            for it in its:
                if (it['raw'].get('date') and _iso(it['raw']['date']) >= today and _iso(it['raw']['date']) <= max((r['date'] for r in rows), default=today)):
                    drop.add(id(it)); gone += 1
        items[:] = [it for it in items if id(it) not in drop]
        pt = {}
        for r in by_case.values():
            if not r['canceled']: pt[r['ptype']] = pt.get(r['ptype'], 0) + 1
        st[co] = dict(file=d['file'], updated=d.get('updated'), listed=len(by_case), ours=len(cur), matched=matched,
                      added=added, canceled=canceled, canceled_ours=cx_ours, moved=moved, not_listed_dropped=gone, ptype=pt)
    return st


def _iso(d):
    return f'{d[6:10]}-{d[0:2]}-{d[3:5]}' if re.match(r'\d{2}/\d{2}/\d{4}', d or '') else (d or '')


if __name__ == '__main__':
    import json, sys
    d = load(offline='--offline' in sys.argv)
    for co, v in d.items():
        rs = v['rows']
        print(co, v['file'], v.get('updated'), len(rs), 'canceled', sum(r['canceled'] for r in rs),
              {t: sum(1 for r in rs if r['ptype'] == t) for t in ('hoa', 'banco', 'outro')})
        for r in rs[:3]: print('  ', json.dumps(r, ensure_ascii=False)[:260])
