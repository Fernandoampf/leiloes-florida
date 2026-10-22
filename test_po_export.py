#!/usr/bin/env python3
"""Unit tests for PropertyOnion Premium CSV join + POV rule (no browser)."""
import csv, os, tempfile, unittest, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import po_export

HDR = ['Street Address','City','State','Zip','Listing Type','Auction Status','Case Number',
       'Auction Date','Parcel Number','Appraiser Link','County','Property Type','Bedrooms',
       'Total Baths','Area SQFT','Lot Size','Owner 1 Name','POV','Confidence Rating',
       'County Market Value','County Land Value','Last Sale','Last Sale Date','Previous Sale Type',
       'Vacant Flag','Owner Occupied','Total Liens','Total Lien Amount','Auction Winners Name',
       'Auction Winning Bid','Winning Bidder','Auction Win Type','Property Details Link']

def row(**kw):
    d = {h: '' for h in HDR}
    d.update({
        'Street Address': '100 Main St', 'City': 'Orlando', 'State': 'FL', 'Zip': '32801',
        'Listing Type': 'Foreclosure', 'Auction Status': 'Upcoming',
        'Case Number': '2024-CA-000001-O', 'Auction Date': '2026-11-15',
        'Parcel Number': '28-22-29-0000-00-001',
        'Appraiser Link': 'https://ocpaweb.ocpafl.org/parcelsearch/parcel%20id/292228000000001',
        'County': 'Orange', 'Property Type': 'Single Family', 'POV': '300000', 'Confidence Rating': '80',
        'County Market Value': '280000', 'Owner Occupied': 'Yes', 'Total Liens': '1',
        'Total Lien Amount': '50000', 'Property Details Link': 'https://propertyonion.com/p/1',
    })
    d.update(kw)
    return d

class TestPoExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, rows):
        path = os.path.join(self.dir, name)
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=HDR); w.writeheader()
            for r in rows: w.writerow(r)
        return path

    def test_newest_file_per_county(self):
        self._write('po_orange_2026-10-01.csv', [row(POV='100000')])
        self._write('po_orange_2026-10-08.csv', [row(POV='200000')])
        files = po_export.list_export_files(self.dir)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0][0], 'orange')
        self.assertEqual(files[0][1], '2026-10-08')
        rows = po_export.load_exports(self.dir)
        self.assertEqual(rows[0]['pov'], 200000)

    def test_merge_partial_newer_export_keeps_older_rows(self):
        # full export 10-08 (2 auctions) + 21-day export 10-22 (only the near one, new POV)
        self._write('po_orange_2026-10-08.csv', [
            row(**{'Case Number': '2024-CA-000001-O', 'Auction Date': '2026-10-27', 'POV': '100000'}),
            row(**{'Case Number': '2024-CA-000009-O', 'Street Address': '900 Far Ave',
                   'Parcel Number': '10-24-28-2495-00-690', 'Appraiser Link': '',
                   'Auction Date': '2026-12-03', 'POV': '150000'}),
        ])
        self._write('po_orange_2026-10-22.csv', [
            row(**{'Case Number': '2024-CA-000001-O', 'Auction Date': '2026-10-29', 'POV': '120000'}),
        ])
        rows = po_export.load_exports(self.dir)
        by = {r['case_n']: r for r in rows}
        self.assertEqual(len(rows), 2)
        self.assertEqual(by['2024CA000001O']['pov'], 120000)            # newer row wins
        self.assertEqual(by['2024CA000001O']['date_iso'], '2026-10-29')
        self.assertEqual(by['2024CA000009O']['pov'], 150000)            # only in older file: kept
        self.assertEqual(len(po_export.list_all_export_files(self.dir)), 2)

    def test_match_case_parcel_address_no_dup(self):
        self._write('po_orange_2026-10-08.csv', [
            row(**{'Case Number': '2024-CA-000001-O', 'Street Address': '100 Main St'}),
            row(**{'Case Number': '2024-CA-000002-O', 'Street Address': '200 Oak Ave',
                   'Parcel Number': '10-24-28-2495-00-690',
                   'Appraiser Link': 'https://ocpaweb.ocpafl.org/parcelsearch/parcel%20id/282410249500690'}),
            row(**{'Case Number': 'NOMATCH-1', 'Street Address': '999 Nowhere Rd', 'Zip': '32899',
                   'Auction Date': '2026-12-01'}),
        ])
        items = [
            dict(src='FC', raw=dict(county='myorangeclerk', case='2024-CA-000001-O',
                                    parcel='292228000000001', street='100 MAIN ST', addr='100 MAIN ST ORLANDO, 32801',
                                    date='11/15/2026', aid='1', fj=100000, av=200000)),
            dict(src='FC', raw=dict(county='myorangeclerk', case='OTHER',
                                    parcel='282410249500690', street='200 OAK AVE', addr='200 OAK AVE ORLANDO, 32801',
                                    date='11/15/2026', aid='2', fj=50000, av=150000)),
        ]
        items, st = po_export.enrich(items, directory=self.dir, today='2026-10-08')
        self.assertEqual(st['matched'], 2)
        self.assertEqual(st['added'], 1)
        self.assertEqual(sum(1 for it in items if it.get('poe') and not it.get('po_only')), 2)
        self.assertEqual(sum(1 for it in items if it.get('po_only')), 1)
        aids = [it['raw']['aid'] for it in items if not it.get('po_only')]
        self.assertEqual(len(aids), len(set(aids)))

    def test_multi_lot_case_shares_judgment(self):
        # Orange 2024-CA-010169-O: one judgment, 2 lots (PO .mlti1/.mlti2); RealAuction lists one item
        self._write('po_orange_2026-10-22.csv', [
            row(**{'Case Number': '2024-ca-010169-o.mlti1', 'Street Address': '2710 Butler Bay Dr N # 3', 'City': 'Windermere',
                   'Zip': '34786', 'Auction Date': '2026-10-29', 'Parcel Number': '01-23-27-1108-00-001',
                   'Appraiser Link': 'https://ocpaweb.ocpafl.org/parcelsearch/parcel%20id/272301110800001'}),
            row(**{'Case Number': '2024-ca-010169-o.mlti2', 'Street Address': '2730 Butler Bay Dr N', 'City': 'Windermere',
                   'Zip': '34786', 'Auction Date': '2026-10-29', 'Parcel Number': '01-23-27-1117-00-001',
                   'Appraiser Link': 'https://ocpaweb.ocpafl.org/parcelsearch/parcel%20id/272301111700001'}),
            row(**{'Case Number': '2024-CA-000001-O', 'Auction Date': '2026-10-29'}),
        ])
        items = [dict(src='FC', raw=dict(county='orange', case='2024-CA-010169-O', parcel='', street='2730 BUTLER BAY DR N',
                                         addr='2730 Butler Bay Dr N Windermere, FL 34786', date='10/29/2026', aid='1515954', fj=2060966.11)),
                 dict(src='FC', raw=dict(county='orange', case='2024-CA-000001-O', parcel='292228000000001', street='100 MAIN ST',
                                         addr='100 MAIN ST ORLANDO, 32801', date='10/29/2026', aid='9', fj=1000))]
        items, st = po_export.enrich(items, directory=self.dir, today='2026-10-22')
        lots = [it for it in items if po_export.ncase(it['raw']['case']) == '2024CA010169O']
        self.assertEqual(len(lots), 2)
        for it in lots:
            self.assertEqual(it['mlot']['n'], 2)
            self.assertEqual(it['raw']['fj'], 2060966.11)       # whole-case judgment, never split
            self.assertEqual(it['mlot']['fj'], 2060966.11)
        self.assertEqual(st['by_how']['multi_cases'], 1)
        single = next(it for it in items if it['raw'].get('aid') == '9')
        self.assertNotIn('mlot', single)

    def test_pov_rule(self):
        self.assertTrue(po_export.pov_ok_for_arv(300000, 80, 280000))
        self.assertFalse(po_export.pov_ok_for_arv(300000, 60, 280000))
        self.assertFalse(po_export.pov_ok_for_arv(500000, 90, 280000))
        self.assertFalse(po_export.pov_ok_for_arv(300000, 80, None))
        self.assertFalse(po_export.pov_ok_for_arv(None, 80, 280000))

    def test_ncase_mlti(self):
        self.assertEqual(po_export.ncase('2025-ca-000399-o.mlti2'), po_export.ncase('2025-CA-000399-O'))
        self.assertEqual(po_export.ncase('2026-CC-005415-O (CT I)'), '2026CC005415O')

    def test_county_from_csv_column(self):
        self._write('po_misc_2026-10-08.csv', [row(**{'County': 'Seminole', 'Case Number': '2024-CA-9'})])
        rows = po_export.load_exports(self.dir)
        self.assertEqual(rows[0]['county'], 'seminole')

if __name__ == '__main__':
    unittest.main()
