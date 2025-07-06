#!/usr/bin/env python3
"""
Unit tests for build_product_set_input
Created: 2025-07-03T23:00:41.119Z
Type: Ad-hoc tool
"""

import unittest, json, sys, os
from unittest.mock import patch, MagicMock
sys.path.insert(0, '/home/pranav/espressobot/frontend/python-tools')
from update_full_product import build_product_set_input

class BuildProductSetInputTest(unittest.TestCase):
    def test_mapping(self):
        gid = 'gid://shopify/Product/1'
        payload = {
            'title': 'New',
            'descriptionHtml': 'desc',
            'tags': ['A','B'],
            'metafields': [{'namespace':'global','key':'test','value':'x','type':'single_line_text_field'}],
            'variants': [{'price':'10.00'}]
        }
        result = build_product_set_input(gid, payload)
        self.assertEqual(result['id'], gid)
        self.assertEqual(result['title'], 'New')
        self.assertEqual(result['tags'], ['A','B'])
        self.assertIn('metafields', result)
        self.assertIn('variants', result)

if __name__ == '__main__':
    unittest.main()
