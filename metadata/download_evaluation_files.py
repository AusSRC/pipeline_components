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
from astroquery.casda import Casda
from astropy.table import Table


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


DID_URL = 'https://casda.csiro.au/casda_data_access/metadata/evaluationEncapsulation'
EVAL_URL = 'https://data.csiro.au/casda_vo_proxy/vo/datalink/links?ID='


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s',
        '--sbid',
        type=int,
        required=True,
        help='SBID for observation'
    )
    parser.add_argument(
        '-p',
        '--project_code',
        type=str,
        required=True,
        help='Project code'
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
        default='./casda.ini'
    )
    args = parser.parse_args(argv)
    return args


def download_evaluation_files(sbid, project_code, username, password, output):
    """Download evaluation files from CASDA for a given observation (sbid) and
    for a specific project (project_code).

    """
    # ensure output exists or create
    if not os.path.exists(output):
        logging.info(f'Making output directory {output}')
        os.mkdir(output)

    # get did
    url = f"{DID_URL}?projectCode={project_code}&sbid={sbid}"
    logging.info(f'Request to {url}')
    res = requests.get(url)
    if res.status_code != 200:
        raise Exception(f'Response: {res.reason} {res.status_code}')
    logging.info(f'Response: {res.json()}')

    # TODO(austin): what does it mean to have multiple evaluation files?
    evaluation_files = [f for f in res.json() if 'evaluation' in f]
    evaluation_files.sort()
    if not evaluation_files:
        raise Exception(f"No evaluation files found with query parameters projectCode={project_code} and sbid={sbid}")

    # Download evaluation files
    casda = Casda(username, password)

    # TODO(austin): may not be necessary to download all evaluation files at once
    logging.info(f'Downloading evaluation files: {evaluation_files}')
    t = Table()
    t['access_url'] = [f'{EVAL_URL}{f}' for f in evaluation_files]
    logging.info(f'Downloading from: {t}')
    url_list = casda.stage_data(t)
    logging.info(f'Staging files {url_list}')
    filelist = casda.download_files(url_list, savedir=output)
    logging.info(f'Downloaded files {filelist}')

    compressed = [f for f in filelist if (('checksum' not in f) & ('.tar' in f))]
    out_dirs = []
    for f in compressed:
        out_dir = f.rsplit('.', 1)[0]
        logging.info(f'Extracting {f} to {out_dir}')
        out_dirs.append(out_dir)
        os.system(f'tar -xvf {f} -C {out_dir}')

    return out_dirs


def main(argv):
    args = parse_args(argv)
    casda_parser = configparser.ConfigParser()
    casda_parser.read(args.credentials)

    output = download_evaluation_files(
        args.sbid,
        args.project_code,
        casda_parser['CASDA']['username'],
        casda_parser['CASDA']['password'],
        args.output
    )
    print(output)


if __name__ == '__main__':
    main(sys.argv[1:])
