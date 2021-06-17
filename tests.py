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


LINMOS_CONFIG = "filename.config"
EXPECTED_CONFIG = """
linmos.names        = [image.restored.SB100.cube.contsub,image.restored.SB200.cube.contsub]
linmos.weights      = [weights.SB100.cube,weights.SB200.cube]
linmos.imagetype    = fits
linmos.outname      = mosaicked
linmos.outweight    = mosaicked.weights
linmos.weighttype   = FromWeightImages
linmos.weightstate  = Corrected
linmos.psfref       = 0
""".strip()  # noqa
EXPECTED_CONFIG_FILE_PATH = """
linmos.names        = [/mnt/shared/image.restored.SB100.cube.contsub,/mnt/shared/image.restored.SB200.cube.contsub]
linmos.weights      = [/mnt/shared/weights.SB100.cube,/mnt/shared/weights.SB200.cube]
linmos.imagetype    = fits
linmos.outname      = /mnt/shared/mosaicked
linmos.outweight    = /mnt/shared/mosaicked.weights
linmos.weighttype   = FromWeightImages
linmos.weightstate  = Corrected
linmos.psfref       = 0
""".strip()  # noqa
SOFIA_PARAMS = "sofia.par"
SOFIAX_CONFIG = "config.ini"


class Testing(unittest.TestCase):
    """Testing suite for WALLABY workflow scripts

    """
    def setUp(self):
        """Set credentials as environment variables for
        local and remote testing.

        """
        creds = "../credentials.ini"
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

    @patch("casda_download.download", lambda *_: ["hello", "hello.checksum"])
    def test_download(self):
        """Ensure casda_download.py process returns a single
        output that is the file that has been downloaded.

        """
        output = io.StringIO()
        sys.stdout = output

        casda_download.main(["-i", "10809", "-o", "mosaicked"])
        sys.stdout = sys.__stdout__

        self.assertEqual(
            output.getvalue(), "hello", f"Output was {repr(output.getvalue())}"
        )

    @patch("casda_download.download", lambda *_: ["hello", "hello.checksum"])
    def test_download_from_nextflow(self):
        """Run the download command as called by nextflow to ensure there
        are no errors.

        """
        output = io.StringIO()
        sys.stdout = output

        casda_download.main([
            "-i", "10809",
            "-o", "/mnt/shared/home/ashen/tmp",
            "-u", os.environ["CASDA_USERNAME"],
            "-p", os.environ["CASDA_PASSWORD"],
            "-ct", "cube",
            "-cf", "image.restored.%SB$SBID%.cube.MilkyWay.contsub.fits",
            "-wt", "cube",
            "-wf", "weights%SB$SBID%.cube.MilkyWay.fits"
        ])
        sys.stdout = sys.__stdout__

        self.assertEqual(
            output.getvalue(), "hello", f"Output was {repr(output.getvalue())}"
        )

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

    def test_number_of_print_statements(self):
        """Each script should only produce a single output
        (for stdout to nextflow) so we will test that there
        is at most one print statement per file.

        """
        pass

    def test_generate_sofia_params(self):
        """Test to ensure a sofia parameter file is generated correctly.
        Asserts the following:
            1. Parameter file is generated
            2. Output (stdout) is the configuration filename.

        """
        output = io.StringIO()
        sys.stdout = output

        generate_sofia_params.main([
            "-i", "/mnt/shared/test.fits",
            "-f", SOFIA_PARAMS,
            "-d", "templates/sofia.ini",
            "-t", "templates/sofia.j2",
            "-p", "SOFIA_PIPELINE_VERBOSE=1"
        ])

        # 1. Config generated
        self.assertTrue(os.path.isfile(SOFIA_PARAMS))

        # 2. Stdout
        sys.stdout = sys.__stdout__
        self.assertEqual(
            output.getvalue(), SOFIA_PARAMS, f"Output was {repr(output.getvalue())}"  # noqa
        )

    def test_generate_sofia_params_no_params(self):
        """Test to ensure a sofia parameter file is generated correctly even
        when no custom parameters are passed.

        Asserts the following:
            1. Parameter file is generated
            2. Output (stdout) is the configuration filename.

        """
        output = io.StringIO()
        sys.stdout = output

        generate_sofia_params.main([
            "-i", "/mnt/shared/test.fits",
            "-f", SOFIA_PARAMS,
            "-d", "templates/sofia.ini",
            "-t", "templates/sofia.j2"
        ])

        # 1. Config generated
        self.assertTrue(os.path.isfile(SOFIA_PARAMS))

        # 2. Stdout
        sys.stdout = sys.__stdout__
        self.assertEqual(
            output.getvalue(), SOFIA_PARAMS, f"Output was {repr(output.getvalue())}"  # noqa
        )

    def test_sofiax_config_write(self):
        """Assert that database credentials are updated with the
        database_credentials.py file.

        """
        host = "hostname"
        name = "user"
        user = "admin"
        pwd = "admin"

        database_credentials.main([
            "--config", SOFIAX_CONFIG,
            "--host", host,
            "--name", name,
            "--username", user,
            "--password", pwd
        ])

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(SOFIAX_CONFIG)

        self.assertEqual(host, config.get('SoFiAX', 'db_hostname'))
        self.assertEqual(name, config.get('SoFiAX', 'db_name'))
        self.assertEqual(user, config.get('SoFiAX', 'db_username'))
        self.assertEqual(pwd, config.get('SoFiAX', 'db_password'))


if __name__ == "__main__":
    unittest.main()
