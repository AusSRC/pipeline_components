#!/usr/bin/env python3

import os
import sys
import io
import unittest
from mosaicking import generate_linmos_config


LINMOS_CONFIG_FILE = "linmos.config"
EXPECTED_CONFIG_CONTENT = """
linmos.names                = [/mnt/shared/image.restored.SB100.cube.contsub,/mnt/shared/image.restored.SB200.cube.contsub]
linmos.weights              = [/mnt/shared/weights.SB100.cube,/mnt/shared/weights.SB200.cube]
linmos.imagetype            = fits
linmos.outname              = mosaicked
linmos.outweight            = mosaicked.weights
linmos.weighttype           = FromWeightImages
linmos.weightstate          = Corrected
linmos.psfref               = 0
linmos.imageaccess          = collective
linmos.imageaccess.axis     = 3
linmos.imageaccess.order    = distributed
linmos.imageaccess.write    = parallel
""".strip()  # noqa


class MosaickingTests(unittest.TestCase):
    """Tests of mosaicking components.

    """
    def tearDown(self):
        if os.path.isfile(LINMOS_CONFIG_FILE):
            os.remove(LINMOS_CONFIG_FILE)

    def test_generate_linmos_config(self):
        """Test that generate_linmos_config.py takes a list of arguments
        (sbids) and returns the correct config file.

        Asserts three things:
            1. Config file is generated
            2. Content of the configuration file is as expected
            3. Output (stdout) is the configuration filename.

        """
        output = io.StringIO()
        sys.stdout = output

        files = "[/mnt/shared/image.restored.SB100.cube.contsub.fits,/mnt/shared/image.restored.SB200.cube.contsub.fits]"  # noqa
        generate_linmos_config.main([
            "-i", files,
            "-f", "mosaicked",
            "-t", "mosaicking/templates/linmos_config.j2",
            "-c", LINMOS_CONFIG_FILE
        ])

        # 1. Config generated
        self.assertTrue(os.path.isfile(LINMOS_CONFIG_FILE))

        # 2. Config content
        with open(LINMOS_CONFIG_FILE, 'r') as f:
            content = f.read().strip()
        self.assertEqual(content, EXPECTED_CONFIG_CONTENT)

        # 3. Stdout
        sys.stdout = sys.__stdout__
        self.assertEqual(
            output.getvalue(), LINMOS_CONFIG_FILE, f"Output was {repr(output.getvalue())}"  # noqa
        )


if __name__ == "__main__":
    unittest.main()
