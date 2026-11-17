#!/usr/bin/env python3
"""Testes de unidade (16/11): autor normalizado, nº do processo, leitura de resultado (PROPOSTA 6 substituta), faixas do backtest (PROPOSTA 10)."""
import unittest, json, os, tempfile
import plaintiff_hist as ph, backtest as bt

class T(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(ph.norm_plaintiff("['NEWREZ LLC', 'DAVID ROBERT BYARS']"), 'NEWREZ / SHELLPOINT')
        self.assertEqual(ph.norm_plaintiff('NATIONSTAR MORTGAGE LLC D/B/A MR. COOPER'), 'NATIONSTAR (MR. COOPER)')
        self.assertEqual(ph.norm_plaintiff("['U.S. BANK TRUST COMPANY, National Association, As Trustee For Velocity Commerc"), 'U.S. BANK')
        self.assertIsNone(ph.norm_plaintiff(''))
    def test_case(self):
        self.assertEqual(ph.case_key('2024 CA 001507 MF'), ('2024', 1507))
        self.assertEqual(ph.case_key('2024-CA-001507-O'), ('2024', 1507))
        self.assertEqual(ph.case_key('2022CA000814'), ('2022', 814))
    def test_outcomes(self):
        d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'results'))
        rows = [dict(AID='1', **{'Auction Type': 'FORECLOSURE', 'Case #': '2024CA000010', 'Final Judgment Amount': '$200,000.00', 'Assessed Value': '$250,000.00'}, res=dict(A='Auction Sold', D='$150,000.00', ST='3rd Party Bidder')),
                dict(AID='2', **{'Auction Type': 'FORECLOSURE', 'Case #': '2024CA000011', 'Final Judgment Amount': '$100,000.00', 'Assessed Value': '$150,000.00'}, res=dict(A='Auction Sold', D='$100.00', ST='Plaintiff')),
                dict(AID='3', **{'Auction Type': 'FORECLOSURE', 'Case #': '2024CA000012', 'Final Judgment Amount': '$100,000.00', 'Assessed Value': '$150,000.00'}, res=dict(A='Auction Sold', D='$80,000.00', ST='Plaintiff'))]
        json.dump(rows, open(os.path.join(d, 'results', 'polk.realforeclose.com_11-01-2026.json'), 'w'))
        idx = {('2024', 10): [('PENNYMAC', 'PENNYMAC', 200000.0)], ('2024', 11): [('PENNYMAC', 'PENNYMAC', 100000.0)], ('2024', 12): [('PENNYMAC', 'PENNYMAC', 100000.0)]}
        o = ph.outcomes(d, idx); k = {r['case']: r['kind'] for r in o}
        self.assertEqual(k, {'2024CA000010': 'released', '2024CA000011': 'nocontest', '2024CA000012': 'kept'})
        s = ph.summarize(o)['PENNYMAC']
        self.assertEqual((s['kept'], s['released'], s['nocontest']), (1, 1, 1)); self.assertEqual(s['relJ'], 0.75); self.assertEqual(s['keptJ'], 0.8)
    def test_band(self):
        self.assertEqual(bt.band(120000), '< 150 mil'); self.assertEqual(bt.band(320000), '300–500 mil'); self.assertEqual(bt.band(900000), '≥ 500 mil')

    def test_cases_git_whitelist(self):   # PROPOSTA 13: no git só campos sem nome de pessoa
        import build
        d = tempfile.mkdtemp(); f = os.path.join(d, 'c.json')
        json.dump({'items': [{'county': 'orange', 'case': '2025-CA-010620-O', 'opened': '2026-11-16', 'rejected': True, 'plaintiff': 'BANCO X', 'defendants': ['FULANO']}]}, open(f, 'w'))
        old = build.CASES_GIT; build.CASES_GIT = f
        try: o = build.load_cases_git()
        finally: build.CASES_GIT = old
        self.assertEqual(o, {'orange|2025-10620': {'opened': '2026-11-16', 'rejected': True}})
        real = json.load(open(old))
        for e in real['items']:
            self.assertFalse(set(e) - set(build.CASES_GIT_KEYS) - {'county', 'case'}, e)

    def test_case_norm_two_digit_year(self):   # Lee '25-CA-005628' casa com cases_open.json
        import build
        self.assertEqual(build.case_norm('lee', '25-CA-005628'), 'lee|2025-5628')
        self.assertEqual(build.case_norm('orange', '2025-CA-011892-O'), 'orange|2025-11892')
        self.assertIsNone(build.case_norm('lee', '12345'))
        self.assertIn('lee|2025-5628', build.load_cases_git())

    def test_manual_parcel_alt(self):   # Wolfs Trl: parcela da RealAuction (S-T-R) e do PO (R-T-S)
        import build, nal
        m = build.load_manual()
        self.assertIs(m[('lake', nal.npid('23-19-27-016000006000'))], m[('lake', nal.npid('271923016000006000'))])

    def test_geo_helpers(self):   # 17/11: Censo em lote (mesma validação) e cache do centro da parcela FDOR
        import census_geo, parcel_geo
        self.assertTrue(census_geo._accept('1481 Providence Blvd', '1481 PROVIDENCE BLVD, DELTONA, FL, 32725'))
        self.assertFalse(census_geo._accept('23 NW 3 ST', '23 NW 3RD AVE, MIAMI, FL, 33128'))
        self.assertEqual(census_geo.no_unit('3 GROVE ISLE DR C308'), '3 GROVE ISLE DR')
        self.assertEqual(census_geo.no_unit('3011 LINTON BLVD # D-107'), '3011 LINTON BLVD')
        self.assertIsNone(census_geo.no_unit('1481 PROVIDENCE BLVD'))
        self.assertIn(('1330 JEFF DRIVE', 'APOPKA'), census_geo.variants('1330 JEFF DRIVE APOPKA', ''))
        self.assertEqual(parcel_geo.k(64, ' 35-09-24-4076-0530-0120 '), '64|35-09-24-4076-0530-0120')
        old = parcel_geo._db
        try:
            parcel_geo._db = {'64|AB-1234': {'lat': 29.6, 'lon': -81.8, 'd': '2026-11-17'}, '64|ZZ-9999': {'d': '2026-11-16'}}
            self.assertEqual(parcel_geo.get(64, ['x', 'ab-1234']), (29.6, -81.8))
            self.assertEqual(parcel_geo.pending(64, ['ZZ-9999', 'QQ-5555'], '2026-11-17'), ['QQ-5555'])
            self.assertEqual(parcel_geo.pending(64, ['ZZ-9999'], '2026-12-17'), ['ZZ-9999'])
            self.assertEqual(parcel_geo.pending(64, ['AB-1234', 'QQ-5555'], '2026-11-17'), [])
        finally: parcel_geo._db = old

if __name__ == '__main__':
    unittest.main()
