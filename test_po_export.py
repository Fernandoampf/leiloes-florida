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
