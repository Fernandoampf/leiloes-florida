#!/usr/bin/env python3
"""Unit tests for po_bids matching + fill without network."""
import json, os, tempfile, unittest
from unittest import mock
import po_bids

class TestPoBids(unittest.TestCase):
    def test_ncase_parcel(self):
        self.assertEqual(po_bids.ncase('2024-CA-001234-O'), '2024CA001234O')
        self.assertEqual(po_bids.digits('06-22-28-0000-00-001'), '062228000000001')

    def test_match_row_by_case(self):
        rows = [
            {'Case #': '2024-CA-001234', 'Final Judgment Amount': '$50,000.00', 'AID': '1', 'area': 'W'},
            {'Case #': 'other', 'Final Judgment Amount': '$1', 'AID': '2'},
        ]
        want = dict(case_n=po_bids.ncase('2024-CA-001234'), parcel='', street_n='')
        row, how = po_bids.match_row(want, rows)
        self.assertEqual(row['AID'], '1')
        self.assertEqual(how, 'case')

    def test_bid_from_row_fc_td(self):
        r, k = po_bids.bid_from_row({'Final Judgment Amount': '$12,345.67'}, 'FC')
        self.assertEqual(r, 12345.67)
        self.assertEqual(k, 'fj')
        r, k = po_bids.bid_from_row({'Opening Bid': '$900'}, 'TD')
        self.assertEqual(r, 900.0)

    def test_fill_from_cache_no_network(self):
        items = [dict(src='FC', po_only=True, raw=dict(
            aid='X1', case='2024-CA-9', county='Orange', date='10/15/2026',
            host='orange.realforeclose.com', street='100 MAIN ST', addr='100 MAIN ST, ORLANDO, FL',
            parcel='123'))]
        with tempfile.TemporaryDirectory() as td:
            cache_path = os.path.join(td, 'po_bids.json')
            cache = {'bids': {'FC:X1': dict(ref=55000, how='case', kind='fj')}, 'fetched': {}, 'meta': {}}
            json.dump(cache, open(cache_path, 'w'))
            with mock.patch.object(po_bids, 'CACHE', cache_path):
                with mock.patch.object(po_bids, 'load_day_rows', return_value=([], 'skip')):
                    st = po_bids.fill_po_bids(items, fetch=False)
            self.assertEqual(st['filled'], 1)
            self.assertEqual(items[0]['raw']['fj'], 55000)
            self.assertTrue(items[0].get('bid_fill'))

if __name__ == '__main__':
    unittest.main()
