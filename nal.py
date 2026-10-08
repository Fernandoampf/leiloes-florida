#!/usr/bin/env python3
"""Florida Dept. of Revenue public tax-roll files (NAL, 2026 preliminary; free download from the PTO Data Portal):
- per-parcel facts for auction items (DOR use code, just value, land/buildings, year built, living area, last 2 sales,
  homestead, owner) matched by parcel id (normalized) or by situs address + ZIP;
- qualified sales (qualification code 01 = arm's-length) since START for comparable-sales estimates.
Raw zips: /workspace/auc/nal/*.zip (downloaded by /workspace/auc/nal/dl.py). Compact cache: cache/nal/<county>.json"""
import csv, glob, io, json, os, re, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = '/workspace/auc/nal'
C = os.path.join(HERE, 'cache', 'nal')
START = 2025          # sales from this year on (roll 2026P carries sales through ~mid-2026)
QUAL = {'01'}

def npid(s): return re.sub(r'[^0-9A-Z]', '', str(s or '').upper()).lstrip('0')
def nstreet(s):
    s = re.sub(r'[^A-Z0-9 ]', ' ', str(s or '').upper()); s = re.sub(r'\s+', ' ', s).strip()
    return s
def county_of_zip(name):
    base = re.split(r'_(Preliminary|Final)', os.path.basename(name))[0]
    toks = [t for t in base.split('_') if t and not t.isdigit()]
    c = ''.join(toks).lower().replace('.', '').replace('-', '')
    return {'dade': 'miamidade', 'miamidade': 'miamidade', 'saintlicie': 'stlucie', 'saintlucie': 'stlucie', 'saintjohns': 'stjohns'}.get(c, c)

def zips():
    out = {}
    for f in sorted(glob.glob(os.path.join(RAW, '*.zip')), key=lambda f: ('2026' in f, f)):   # 2026 roll wins over 2025F
        out[county_of_zip(f)] = f
    return out

def _i(v):
    try: return int(float(v))
    except Exception: return None

def process(county, zpath, targets_pid, targets_addr):
    """returns dict(parcels={key: rec}, sales=[...])"""
    z = zipfile.ZipFile(zpath); n = [x for x in z.namelist() if x.lower().endswith('.csv')][0]
    rd = csv.DictReader(io.TextIOWrapper(z.open(n), encoding='latin-1', newline=''))
    parcels, sales = {}, []
    start = START - 1 if ('2025' in os.path.basename(zpath) or 'Final' in os.path.basename(zpath)) else START
    for row in rd:
        pid = npid(row.get('PARCEL_ID')); ak = npid(row.get('ALT_KEY')); sp = npid(row.get('STATE_PAR_ID'))
        addr = nstreet(row.get('PHY_ADDR1')); zp = str(row.get('PHY_ZIPCD') or '')[:5]
        hit = None
        if pid in targets_pid: hit = 'p:' + pid
        elif ak and ak in targets_pid: hit = 'p:' + ak
        elif addr and (addr + '|' + zp) in targets_addr: hit = 'a:' + addr + '|' + zp
        lvg = _i(row.get('TOT_LVG_AREA')); ayb = _i(row.get('ACT_YR_BLT')); uc = (row.get('DOR_UC') or '').zfill(3)
        lsq = _i(row.get('LND_SQFOOT'))
        if hit:
            hm = (_i(row.get('JV_HMSTD')) or 0) > 0 or (_i(row.get('EXMPT_01')) or 0) > 0
            parcels[hit] = dict(pid=row.get('PARCEL_ID'), uc=uc, jv=_i(row.get('JV')), lv=_i(row.get('LND_VAL')), lsq=lsq,
                ayb=ayb, eyb=_i(row.get('EFF_YR_BLT')), lvg=lvg, nb=_i(row.get('NO_BULDNG')), nu=_i(row.get('NO_RES_UNTS')),
                s1=[_i(row.get('SALE_PRC1')), _i(row.get('SALE_YR1')), _i(row.get('SALE_MO1')), row.get('QUAL_CD1'), row.get('VI_CD1')],
                s2=[_i(row.get('SALE_PRC2')), _i(row.get('SALE_YR2')), _i(row.get('SALE_MO2')), row.get('QUAL_CD2'), row.get('VI_CD2')],
                hm=hm, own=(row.get('OWN_NAME') or '').strip(), oa=(row.get('OWN_ADDR1') or '').strip(), oc=(row.get('OWN_CITY') or '').strip(),
                os_=(row.get('OWN_STATE') or '').strip(), addr=row.get('PHY_ADDR1'), city=row.get('PHY_CITY'), zip=zp,
                leg=(row.get('S_LEGAL') or '')[:120], pub=row.get('PUBLIC_LND'))
        for k in ('1', '2'):
            prc = _i(row.get('SALE_PRC' + k)); yr = _i(row.get('SALE_YR' + k))
            if not prc or not yr or yr < start or prc < 5000: continue
            if row.get('QUAL_CD' + k) not in QUAL or row.get('MULTI_PAR_SAL' + k): continue
            sales.append([zp, uc, prc, yr, _i(row.get('SALE_MO' + k)), lvg, ayb, lsq, (row.get('PHY_ADDR1') or '').strip(), (row.get('PHY_CITY') or '').strip(), row.get('VI_CD' + k)])
            break
    return dict(parcels=parcels, sales=sales, src=os.path.basename(zpath))

def load(county, targets_pid, targets_addr, rebuild=False):
    """cached per county; re-processed when the raw zip is newer or targets are missing from the cache."""
    zp = zips().get(county)
    p = os.path.join(C, county + '.json')
    d = None
    if os.path.exists(p) and not rebuild:
        try: d = json.load(open(p))
        except Exception: d = None
    if zp and (d is None or os.path.getmtime(zp) > os.path.getmtime(p) or not set(targets_pid) <= set(d.get('tp', [])) ):
        d = process(county, zp, set(targets_pid), set(targets_addr))
        d['tp'] = sorted(set(targets_pid) | set(d.get('tp', [])))
        json.dump(d, open(p, 'w'))
    return d
