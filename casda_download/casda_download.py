#!/usr/bin/env python3

import os
import sys
import logging
import json
import asyncio
import argparse
import astropy
import configparser
import keyring
from keyrings.alt.file import PlaintextKeyring
from astroquery.utils.tap.core import TapPlus
from astroquery.casda import Casda
import concurrent.futures
from utils import download_files


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
)

astropy.utils.iers.conf.auto_download = False
keyring.set_keyring(PlaintextKeyring())
KEYRING_SERVICE = 'astroquery:casda.csiro.au'
URL = "https://casda.csiro.au/casda_vo_tools/tap"


WALLABY_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'weights.i.%.cube.fits' OR "
    "filename LIKE 'image.restored.i.%.cube.contsub.fits')")

WALLABY_MILKYWAY_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) "
    "AND dataproduct_type='cube' AND "
    "(filename LIKE 'weights.i.%.cube.MilkyWay.fits' OR filename LIKE 'image.restored.i.%.cube.MilkyWay.contsub.fits')"
)

POSSUM_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'image.restored.i.%.contcube.conv.fits' OR "
    "filename LIKE 'weights.q.%.contcube.fits' OR "
    "filename LIKE 'image.restored.q.%.contcube.conv.fits' OR "
    "filename LIKE 'image.restored.u.%.contcube.conv.fits')")

EMU_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND ( "
    "filename LIKE 'image.i.%.cont.taylor.%.restored.conv.fits' OR "
    "filename LIKE 'weights.i.%.cont.taylor%.fits')")

DINGO_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "(filename LIKE 'weights.i.%.cube.fits' OR "
    "filename LIKE 'image.restored.i.%.cube.contsub.fits' OR "
    "filename LIKE 'image.i.%.0.restored.conv.fits')")


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--sbid",
        type=str, required=True,
        action='append', nargs='+', help="Scheduling block id number."
    )
    parser.add_argument(
        "-o", "--output",
        type=str, required=True, help="Output directory for downloaded files."
    )
    parser.add_argument(
        "-p", "--project",
        type=str, required=True,
        help="ASKAP project name (WALLABY or POSSUM)."
    )
    parser.add_argument(
        "-c", "--credentials",
        type=str, required=False,
        help="CASDA credentials config file.", default="./casda.ini"
    )
    parser.add_argument(
        "-m", "--manifest",
        type=str, required=False,
        help="Manifest Output"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int, required=False,
        default=3000, help="CASDA download file timeout [seconds]"
    )
    args = parser.parse_args(argv)
    return args


def tap_query(project, sbid):
    """Return astropy table with query result (files to download)"""

    ids = [f"'{str(i)}'" for i in sbid[0]]

    if project == "WALLABY":
        logging.info(f"Scheduling block ID: {sbid}")
        query = WALLABY_QUERY.replace("$SBIDS", ",".join(ids))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")

    elif project == "WALLABY_MILKYWAY":
        logging.info(f"Scheduling block ID: {sbid}")
        query = WALLABY_MILKYWAY_QUERY.replace("$SBIDS", ",".join(ids))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")

    elif project == "POSSUM":
        logging.info(f"Scheduling block ID: {sbid}")
        query = POSSUM_QUERY.replace("$SBIDS", ",".join(ids))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")

    elif project == "DINGO":
        logging.info(f"Scheduling block ID: {sbid}")
        query = DINGO_QUERY.replace("$SBIDS", ",".join(ids))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")

    elif project == "EMU":
        logging.info(f"Scheduling block ID: {sbid}")
        query = EMU_QUERY.replace("$SBIDS", ",".join(ids))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")
    else:
        raise Exception('Unexpected project name provided.')

    casdatap = TapPlus(url=URL, verbose=False)
    job = casdatap.launch_job_async(query)
    res = job.get_results()
    logging.info(f"Query result: {res}")
    return res


async def main(argv):
    """Downloads image cubes from CASDA matching the observing block IDs
    provided in the arguments.

    """
    args = parse_args(argv)
    res = tap_query(args.project, args.sbid)
    logging.info(res)

    # stage
    parser = configparser.ConfigParser()
    parser.read(args.credentials)
    keyring.set_password(KEYRING_SERVICE, parser['CASDA']['username'], parser['CASDA']['password'])
    casda = Casda()
    casda.login(username=parser["CASDA"]["username"])
    url_list = casda.stage_data(res, verbose=True)
    logging.info(f"CASDA download staged data URLs: {url_list}")

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
            futures.append(
                executor.submit(download_files, url=url, output=args.output, timeout=args.timeout)
            )
        for future in concurrent.futures.as_completed(futures):
            file_list.append(future.result())

    # write output manifest
    if args.manifest:
        directory = os.path.dirname(args.manifest)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(args.manifest, "w") as outfile:
            outfile.write(json.dumps(file_list))
            logging.info(f"Writing manifest complete: {args.manifest}")

if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
