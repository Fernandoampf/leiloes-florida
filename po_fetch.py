#!/usr/bin/env python3
"""PropertyOnion public-data helper (v4). Polite: few threads, pause after every request, everything cached.

Only public endpoints, no login:
  search:  https://propertyonion.com/api/search/api/search-by-keywords?keyword=<street>
  detail:  https://propertyonion.com/property_search/properties/<seo>/<id>  (embedded ng-state JSON)
Cache: cache/search/s_<street>.json (also reads /workspace/auc/statewide/po/), cache/po_full/p_<id>.json
"""
import json, os, re, time, threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
SW_PO = '/workspace/auc/statewide/po'
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
SCHEMA = 4
PAUSE = 0.6          # seconds after each request, per thread
EXTRA = ['id','seo_url','images','manual_img','prop_cntypicurl','prop_thumbnail','googlestreet_pic','googlemap_pic','prop_hudpicurl',
 'wholesaler_pic1','wholesaler_pic2','wholesaler_pic3','prop_appraiserlink',
 'usps_vacancy','usps_vacancy_date','vacantFlag','homesteadInd','ownerOccupied','landUseCode','mobileHomeInd','lbcs_structure_desc',
 'lbcs_function_desc','lbcs_activity_desc','lbcs_site_desc','propertyClassID','countyLandUseCode','prop_usecode','master_prop_use','master_prop_usecode',
 'master_prop_zoning','master_prop_view','bedrooms','bathTotalCalc','sumLivingAreaSqFt','sumBuildingSqFt','sumCommercialUnits','sumResidentialUnits',
 'yearBuilt','effectiveYearBuilt','lotSizeAcres','lotSizeSqFt','lotSizeFrontageFeet','lotSizeDepthFeet','zoning','municipality',
 'marketTotalValue','marketValueLand','marketValueImprovement','currentAVMValue','vlowValue','vhighValue',
 'vconfidenceScore','estimatedRentalValue','mtg1LoanAmt','mtg1Lender','mtg1RecordingDate','mtg1LienPosition','mtg2LoanAmt','mtg2Lender','mtg2RecordingDate',
 'totalOpenLienNbr','totalOpenLienAmt','currentSalesPrice','currentSaleRecordingDate','currentSaleDocumentType','prevSalesPrice','prevSaleRecordingDate',
 'ownerNAME1FULL','ownerNAME2FULL','owner1CorpInd',
 'mailingFullStreetAddress','mailingCity','mailingState','situsFullStreetAddress','situsCity','situsZIP5','situsLatitude','situsLongitude',
 'fema_flood_zone','fema_flood_zone_raw','legalDescription','subdivisionName','buildingConditionCode','poolCode','apn','taxDeliquentYear',
 'taxAmt','taxYear','taxassess_exemption','prop_hoaconfees','sewerCode','siteInfluenceCode','drivewayCode','padus_public_access',
 'auction_docketurl','storiesNbrCode','garage']
AUC_KEYS = ['auction_date','auction_status','listing_type','auction_openingbid','auction_fj','auction_caseno','auction_url',
 'auction_plaintiffs','auction_defend','ownerOccupied']
_local = threading.local()

def _sess():
    s = getattr(_local, 's', None)
    if s is None:
        import requests
        s = requests.Session(); s.headers['User-Agent'] = UA; _local.s = s
    return s

def jload(p, default=None):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return default

def street_query(street):
    q = re.sub(r'\s+3\d{4}$', '', (street or '').strip())
    q = re.sub(r'\s+(UNIT|APT|#|LT|LOT)\b.*$', '', q, flags=re.I).strip()
    return q if q and re.match(r'^\d', q) else None

def search_cached(q):
    name = 's_' + re.sub(r'\W', '_', q) + '.json'
    res = jload(os.path.join(CACHE, 'search', name))
    if res is None: res = jload(os.path.join(SW_PO, name))
    return res, name

def search(q, fetch=False):
    res, name = search_cached(q)
    if res is None and fetch:
        try:
            r = _sess().get('https://propertyonion.com/api/search/api/search-by-keywords', params={'keyword': q}, timeout=30)
            res = r.json() if r.status_code == 200 else None
            if res is not None: json.dump(res, open(os.path.join(CACHE, 'search', name), 'w'))
        except Exception: res = None
        time.sleep(PAUSE)
    return res

def match(res, zips, city=None):
    cands = [r['value'] for r in (res or []) if r.get('type') == 'Address']
    for c in cands:
        if zips and c.get('situsZIP5') == zips[-1]:
            return c.get('propertyId') or c.get('id'), c.get('seoUrl') or c.get('seo_url')
    if city:
        cc = [c for c in cands if str(c.get('situsCity') or '').upper() == city.upper()]
        if len(cc) == 1: return cc[0].get('propertyId') or cc[0].get('id'), cc[0].get('seoUrl') or cc[0].get('seo_url')
    if len(cands) == 1:
        c = cands[0]; return c.get('propertyId') or c.get('id'), c.get('seoUrl') or c.get('seo_url')
    return None, None

def full(pid, slug, fetch=False, refresh_old=False):
    p = os.path.join(CACHE, 'po_full', f'p_{pid}.json')
    d = jload(p)
    if d is not None and (d.get('v') == SCHEMA or not (fetch and refresh_old)): return d
    if not fetch or not slug: return d
    try:
        h = _sess().get(f'https://propertyonion.com/property_search/properties/{slug}/{pid}', timeout=45).text
        m = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>', h, re.S)
        if not m: return d
        pl = (json.loads(m.group(1)).get(f'property-detail-{pid}') or {}).get('payload') or {}
        if not pl: return d
        nd = {k: pl.get(k) for k in EXTRA}
        nd['auctions'] = [{k: a.get(k) for k in AUC_KEYS} for a in (pl.get('auctionDetails') or [])]
        nd['fetched'] = time.strftime('%Y-%m-%d'); nd['v'] = SCHEMA
        json.dump(nd, open(p, 'w'))
        return nd
    except Exception:
        return d
    finally:
        time.sleep(PAUSE)

def resolve(street, zips, city=None, known=None, fetch=False, refresh_old=False):
    """-> (pid, slug, fulldict|None)"""
    pid = slug = None
    if known and known.get('id'):
        pid, slug = known.get('id'), known.get('seo_url')
    else:
        q = street_query(street)
        if q:
            pid, slug = match(search(q, fetch), zips, city)
    if not pid: return None, None, None
    return pid, slug, full(pid, slug, fetch, refresh_old)

def prefetch(jobs, threads=3, log_every=200):
    """jobs: list of dict(street, zips, city, known). Fetches searches + detail pages for all, politely."""
    n = [0]
    def one(j):
        try: resolve(j.get('street'), j.get('zips'), j.get('city'), j.get('known'), fetch=True, refresh_old=True)
        except Exception: pass
        n[0] += 1
        if n[0] % log_every == 0: print(f'  prefetch {n[0]}/{len(jobs)}', flush=True)
    with ThreadPoolExecutor(threads) as ex: list(ex.map(one, jobs))
