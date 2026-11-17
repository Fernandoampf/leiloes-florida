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

if __name__ == '__main__':
    unittest.main()
