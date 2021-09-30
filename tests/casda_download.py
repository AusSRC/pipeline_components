#!/usr/bin/env python3

import os
import sys
import io
import configparser
import unittest
from unittest.mock import patch
from download import casda_download


DOWNLOAD = "download.casda_download.download"


class CASDADownloadTests(unittest.TestCase):
    """Tests of CASDA download components.

    """
    def setUp(self):
        """Set CASDA credentials.

        """
        creds = "credentials.ini"
        if os.path.isfile(creds):
            config = configparser.ConfigParser()
            config.read(creds)
            login = config["login"]
            os.environ["CASDA_USERNAME"] = login['username']
            os.environ["CASDA_PASSWORD"] = login['password']

    @patch(DOWNLOAD, lambda *_: ["image_cube", "image_cube.checksum"])
    def test_download(self):
        """Ensure casda_download.py process returns a single
        output that is the file that has been downloaded.

        """
        output = io.StringIO()
        sys.stdout = output

        casda_download.main(
            ["-i", "10809", "-o", "mosaicked", "-pr", "WALLABY"]
        )
        sys.stdout = sys.__stdout__

        self.assertEqual(
            output.getvalue(),
            "image_cube",
            f"Output was {repr(output.getvalue())}"
        )

    @patch(DOWNLOAD, lambda *_: ["image_cube", "image_cube.checksum"])
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
            "-wf", "weights%SB$SBID%.cube.MilkyWay.fits",
            "-pr", "WALLABY"
        ])
        sys.stdout = sys.__stdout__

        self.assertEqual(
            output.getvalue(),
            "image_cube",
            f"Output was {repr(output.getvalue())}"
        )


if __name__ == "__main__":
    unittest.main()
