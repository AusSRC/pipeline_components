#!/usr/bin/env python3

import unittest

from aussrc_pipeline_components.casda.urls import encode_query_plus

STAGED_URL = (
    "https://ingest.pawsey.org.au/casda-prd-as203-03/sb87072/primary_images/"
    "image.restored.i.EMU_0251+04A.SB87072.contcube.conv.fits"
    '?response-content-disposition=attachment; filename ="image.restored.i.EMU_0251+04A.SB87072.contcube.conv.fits"'
    "&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=259179"
)


class TestEncodeQueryPlus(unittest.TestCase):
    def test_plus_encoded_in_query_only(self):
        """The "+" is encoded in the query string and left in the path"""
        path, query = encode_query_plus(STAGED_URL).split("?", 1)
        self.assertIn("EMU_0251+04A", path)
        self.assertNotIn("+", query)
        self.assertIn("EMU_0251%2B04A", query)

    def test_unchanged(self):
        """URLs without a "+" in the query string, or already encoded, are unchanged"""
        url = STAGED_URL.replace("+", "-")
        self.assertEqual(encode_query_plus(url), url)
        encoded = encode_query_plus(STAGED_URL)
        self.assertEqual(encode_query_plus(encoded), encoded)
        self.assertEqual(encode_query_plus("https://example.org/a+b"), "https://example.org/a+b")


if __name__ == "__main__":
    unittest.main()
