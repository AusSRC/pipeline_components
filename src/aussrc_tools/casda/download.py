#!/usr/bin/env python3

"""
Generic CASDA download script for ASKAP data products.
Will download the output of the query provided in arguments.
Example queries for CASDA TAP service

WALLABY
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'weights.i.%.cube.fits' OR "
    "filename LIKE 'image.restored.i.%.cube.contsub.fits')"

WALLABY_MILKYWAY
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) "
    "AND dataproduct_type='cube' AND "
    "(filename LIKE 'weights.i.%.cube.MilkyWay.fits' OR filename LIKE 'image.restored.i.%.cube.MilkyWay.contsub.fits')"

POSSUM
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'image.restored.i.%.contcube.conv.fits' OR "
    "filename LIKE 'weights.q.%.contcube.fits' OR "
    "filename LIKE 'image.restored.q.%.contcube.conv.fits' OR "
    "filename LIKE 'image.restored.u.%.contcube.conv.fits')"

EMU
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND ( "
    "filename LIKE 'image.i.%.cont.taylor.%.restored.conv.fits' OR "
    "filename LIKE 'weights.i.%.cont.taylor%.fits')"

DINGO
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "(filename LIKE 'weights.i.%.cube.fits' OR "
    "filename LIKE 'image.restored.i.%.cube.contsub.fits' OR "
    "filename LIKE 'image.i.%.0.restored.conv.fits')"
"""

import os
import sys
import logging
import json
import argparse
import astropy
import configparser
import keyring
from keyrings.alt.file import PlaintextKeyring
from astroquery.utils.tap.core import TapPlus
from astroquery.casda import Casda


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
)

astropy.utils.iers.conf.auto_download = False
keyring.set_keyring(PlaintextKeyring())
KEYRING_SERVICE = "astroquery:casda.csiro.au"
URL = "https://casda.csiro.au/casda_vo_tools/tap"


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--query",
        type=str,
        required=True,
        help="TAP query string.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output directory for downloaded files.",
    )
    parser.add_argument(
        "-c",
        "--credentials",
        type=str,
        required=False,
        help="CASDA credentials config file.",
        default="./casda.ini",
    )
    parser.add_argument(
        "-m",
        "--manifest",
        type=str,
        required=True,
        help="Output manifest file (JSON list of downloaded files).",
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Downloads files from CASDA matching the TAP query provided in the
    arguments. Writes a manifest of the downloaded files.

    """
    args = parse_args(argv)
    logging.info(f"TAP Query: {args.query}")
    casdatap = TapPlus(url=URL, verbose=False)
    job = casdatap.launch_job_async(args.query)
    res = job.get_results()
    logging.info(f"Query result: {res}")
    if len(res) == 0:
        raise Exception(f"No files found for TAP query: {args.query}")

    # stage
    parser = configparser.ConfigParser()
    parser.read(args.credentials)
    keyring.set_password(
        KEYRING_SERVICE, parser["CASDA"]["username"], parser["CASDA"]["password"]
    )
    casda = Casda()
    casda.login(username=parser["CASDA"]["username"])
    url_list = casda.stage_data(res, verbose=True)
    logging.info(f"CASDA download staged data URLs: {url_list}")

    # Output directory ensure exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # CASDA download
    url_list = [url for url in url_list if not url.endswith("checksum")]
    file_list = casda.download_files(url_list, savedir=args.output)

    # write output manifest
    directory = os.path.dirname(args.manifest)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(args.manifest, "w") as outfile:
        outfile.write(json.dumps(file_list))
        logging.info(f"Writing manifest complete: {args.manifest}")


if __name__ == "__main__":
    main(sys.argv[1:])
