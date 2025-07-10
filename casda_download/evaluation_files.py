#!/usr/bin/env python3

"""
Download evaluation files from CASDA for a given SBID for ASKAP observations.
Extract content of evaluation files to a specified path.
"""

import os
import sys
import logging
import requests
import argparse
import configparser
import keyring
import concurrent.futures
from keyrings.alt.file import PlaintextKeyring
from astroquery.casda import Casda
from astropy.table import Table
from utils import download_files


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
)

keyring.set_keyring(PlaintextKeyring())
KEYRING_SERVICE = 'astroquery:casda.csiro.au'
DID_URL = "https://casda.csiro.au/casda_data_access/metadata/evaluationEncapsulation"
EVAL_URL = "https://data.csiro.au/casda_vo_proxy/vo/datalink/links?ID="


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--sbid", type=str, required=True, help="SBID for observation")
    parser.add_argument(
        "-p", "--project_code", type=str, required=True, help="Project code")
    parser.add_argument(
        "-o", "--output",
        type=str, required=True,
        help="Output directory for metadata files."
    )
    parser.add_argument(
        "-c", "--credentials",
        type=str, required=False,
        help="CASDA credentials config file.",
        default="./casda.ini"
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Download evaluation files from CASDA for a given observation (sbid) and
    for a specific project (project_code).

    """
    args = parse_args(argv)
    sbid = args.sbid
    parser = configparser.ConfigParser()
    parser.read(args.credentials)
    keyring.set_password(KEYRING_SERVICE, parser['CASDA']['username'], parser['CASDA']['password'])
    casda = Casda()
    casda.login(username=parser["CASDA"]["username"])

    # Get DID (data identifier)
    sbid = sbid.replace('ASKAP-', '')
    did_url = f"{DID_URL}?projectCode={args.project_code}&sbid={sbid}"
    logging.info(f"Request to {did_url}")
    res = requests.get(did_url)
    if res.status_code != 200:
        raise Exception(f"Response: {res.reason} {res.status_code}")
    logging.info(f"Response: {res.json()}")

    # NOTE: What does it mean to have multiple evaluation files?
    evaluation_files = [f for f in res.json() if "evaluation" in f]
    evaluation_files.sort()
    if not evaluation_files:
        logging.warn(f"No evaluation files found with query parameters projectCode={args.project_code} and sbid={sbid}")
        return
    logging.info(f"Downloading evaluation files: {evaluation_files}")

    # Stage data
    t = Table()
    t["access_url"] = [f"{EVAL_URL}{f}" for f in evaluation_files]
    url_list = casda.stage_data(t)
    logging.info(f"Staging files {url_list}")

    # Output directory ensure exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # multithreaded download
    file_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for url in url_list:
            if url.endswith('checksum'):
                continue
            futures.append(executor.submit(download_files, url=url, output=args.output))
        for future in concurrent.futures.as_completed(futures):
            file_list.append(future.result())
    logging.info(file_list)
    logging.info('Complete')
    return


if __name__ == "__main__":
    main(sys.argv[1:])
