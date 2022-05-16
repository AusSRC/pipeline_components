#!/usr/bin/env python3

import os
import sys
import io
import unittest
from mosaicking import update_linmos_config


DEFAULT_CONTENT = """
linmos.names                = [image.restored.SB100.cube.contsub,image.restored.SB200.cube.contsub]
linmos.weights              = [weights.SB100.cube,weights.SB200.cube]
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


class TestUpdateLinmosConfig(unittest.TestCase):
    def setUp(self):
        """Reset linmos config. Remove existing and write default config.

        """
        self.linmos_config = f"{os.path.dirname(__file__)}/linmos.config"
        if os.path.isfile(self.linmos_config):
            os.remove(self.linmos_config)

        with open(self.linmos_config, 'w') as f:
            f.writelines(DEFAULT_CONTENT)
    
    def read_config_to_dict(self, filename):
        """Helper function to read linmos configuration into a dict

        """
        config = {}
        with open(filename, 'r') as f:
            lines = f.readlines()
            for line in lines:
                line = line.replace(' ', '').replace('\n', '')
                kv_list = line.split('=')
                if len(kv_list) != 2:
                    raise Exception("Default linmos config formatting error.")
                config[kv_list[0]] = kv_list[1]
        return config

    def test_update_image_cube_files(self):
        """Update image cube files for linmos.
        1. Verify default values initially
        2. Update config linmos.names to new values
        3. Verify linmos.names values have been updated.

        """
        initial_config = self.read_config_to_dict(self.linmos_config)
        self.assertEqual(
            initial_config['linmos.names'],
            '[image.restored.SB100.cube.contsub,image.restored.SB200.cube.contsub]'
        )

        files = "[image.restored.SB400.cube.contsub.fits,image.restored.SB500.cube.contsub.fits]"  # noqa
        update_linmos_config.main([
            "--config", self.linmos_config,
            "--output", self.linmos_config,
            "--linmos.names", files
        ])

        updated_config = self.read_config_to_dict(self.linmos_config)
        self.assertEqual(updated_config['linmos.names'], files.replace('.fits', ''))


if __name__ == "__main__":
    unittest.main()
