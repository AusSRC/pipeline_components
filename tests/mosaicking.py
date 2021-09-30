#!/usr/bin/env python3

import os
import sys
import io
import configparser
import unittest
from unittest.mock import patch

import casda_download
import generate_linmos_config
import generate_sofia_params
import database_credentials


class MosaickingTests(unittest.TestCase):
    """Tests of CASDA download components.

    """
    def setUp(self):
        """Set credentials as environment variables for
        local and remote testing.

        """
        creds = "credentials.ini"
        if os.path.isfile(creds):
            config = configparser.ConfigParser()
            config.read(creds)
            login = config["login"]
            os.environ["CASDA_USERNAME"] = login['username']
            os.environ["CASDA_PASSWORD"] = login['password']

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.add_section('SoFiAX')
        config.set('SoFiAX', 'db_hostname', 'db_hostname')
        config.set('SoFiAX', 'db_name', 'db_name')
        config.set('SoFiAX', 'db_username', 'db_username')
        config.set('SoFiAX', 'db_password', 'db_password')
        with open(SOFIAX_CONFIG, 'w') as f:
            config.write(f)

    def tearDown(self):
        if os.path.isfile(LINMOS_CONFIG):
            os.remove(LINMOS_CONFIG)
        if os.path.isfile(SOFIA_PARAMS):
            os.remove(SOFIA_PARAMS)
        if os.path.isfile(SOFIAX_CONFIG):
            os.remove(SOFIAX_CONFIG)

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

        files = "[image.restored.SB100.cube.contsub.fits,image.restored.SB200.cube.contsub.fits]"  # noqa
        generate_linmos_config.main([
            "-i", files, "-f", "mosaicked", "-c", LINMOS_CONFIG
        ])

        # 1. Config generated
        self.assertTrue(os.path.isfile(LINMOS_CONFIG))

        # 2. Config content
        with open(LINMOS_CONFIG, 'r') as f:
            content = f.read().strip()
        self.assertEqual(content, EXPECTED_CONFIG)

        # 3. Stdout
        sys.stdout = sys.__stdout__
        self.assertEqual(
            output.getvalue(), LINMOS_CONFIG, f"Output was {repr(output.getvalue())}"  # noqa
        )

    def test_generate_linmos_config_with_file_path(self):
        """Test that generate_linmos_config.py takes a list of arguments
        (sbids) and returns the correct config file. Ensure that when the file
        path is provided for the image cubes, the correct weight file is
        created.

        Asserts three things:
            1. Config file is generated
            2. Content of the configuration file is as expected
            3. Output (stdout) is the configuration filename.

        """
        output = io.StringIO()
        sys.stdout = output

        files = "[/mnt/shared/image.restored.SB100.cube.contsub.fits,/mnt/shared/image.restored.SB200.cube.contsub.fits]"  # noqa
        generate_linmos_config.main(["-i", files, "-f", "/mnt/shared/mosaicked", "-c", LINMOS_CONFIG])  # noqa

        # 1. Config generated
        self.assertTrue(os.path.isfile(LINMOS_CONFIG))

        # 2. Config content
        with open(LINMOS_CONFIG, 'r') as f:
            content = f.read().strip()
        self.assertEqual(content, EXPECTED_CONFIG_FILE_PATH)

        # 3. Stdout
        sys.stdout = sys.__stdout__
        self.assertEqual(
            output.getvalue(), LINMOS_CONFIG, f"Output was {repr(output.getvalue())}"  # noqa
        )


if __name__ == "__main__":
    unittest.main()
