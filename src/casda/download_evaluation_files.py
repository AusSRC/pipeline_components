#!/usr/bin/env python3

"""
Download evaluation files from CASDA for a given SBID for ASKAP observations.
Extract content of evaluation files to a specified path.
"""

import argparse
import configparser
import logging
import os
import sys

import keyring
import requests
from astropy.table import Table
from astroquery.casda import Casda
from keyrings.alt.file import PlaintextKeyring

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

keyring.set_keyring(PlaintextKeyring())
KEYRING_SERVICE = "astroquery:casda.csiro.au"
DID_URL = "https://casda.csiro.au/casda_data_access/metadata/evaluationEncapsulation"
EVAL_URL = "https://data.csiro.au/casda_vo_proxy/vo/datalink/links?ID="


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--sbid", type=str, required=True, help="SBID for observation"
    )
    parser.add_argument(
        "-p",
        "--project_code",
        type=str,
        required=True,
        nargs="+",
        help="Project code(s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output directory for metadata files.",
    )
    parser.add_argument(
        "-c",
        "--credentials",
        type=str,
        required=False,
        help="CASDA credentials config file.",
        default="./casda.ini",
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Download evaluation files from CASDA for a given observation (sbid) and
    for one or more projects (project_code).

    """
    args = parse_args(argv)
    sbid = args.sbid
    parser = configparser.ConfigParser()
    parser.read(args.credentials)
    keyring.set_password(
        KEYRING_SERVICE, parser["CASDA"]["username"], parser["CASDA"]["password"]
    )
    casda = Casda()
    casda.login(username=parser["CASDA"]["username"])

    # Get DID (data identifier)
    sbid = sbid.replace("ASKAP-", "")
    evaluation_files = []
    for project_code in args.project_code:
        did_url = f"{DID_URL}?projectCode={project_code}&sbid={sbid}"
        logger.info(f"Request to {did_url}")
        res = requests.get(did_url)
        if res.status_code != 200:
            raise Exception(f"Response: {res.reason} {res.status_code}")
        logger.info(f"Response: {res.json()}")

        # NOTE: What does it mean to have multiple evaluation files?
        evaluation_files += [f for f in res.json() if "evaluation" in f]
    evaluation_files.sort()
    if not evaluation_files:
        logger.warning(
            f"No evaluation files found with query parameters projectCode={args.project_code} and sbid={sbid}"
        )
        return
    logger.info(f"Downloading evaluation files: {evaluation_files}")

    # Stage data
    t = Table()
    t["access_url"] = [f"{EVAL_URL}{f}" for f in evaluation_files]
    url_list = casda.stage_data(t)
    logger.info(f"Staging files {url_list}")

    # Output directory ensure exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # CASDA download
    url_list = [url for url in url_list if not url.endswith("checksum")]
    file_list = casda.download_files(url_list, savedir=args.output)

    logger.info(file_list)
    logger.info("Complete")
    return


if __name__ == "__main__":
    main(sys.argv[1:])
