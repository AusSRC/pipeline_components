#!/usr/bin/env python3

import os
import sys
import time
import logging
import json
import urllib
import asyncio
import argparse
import astropy
import configparser
import requests
import keyring
from keyrings.alt.file import PlaintextKeyring
from astroquery.utils.tap.core import TapPlus
from astroquery.casda import Casda
import concurrent.futures


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
        "-s",
        "--sbid",
        type=str,
        required=True,
        action='append',
        nargs='+',
        help="Scheduling block id number.",)

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output directory for downloaded files.",)

    parser.add_argument(
        "-p",
        "--project",
        type=str,
        required=True,
        help="ASKAP project name (WALLABY or POSSUM).",)

    parser.add_argument(
        "-c",
        "--credentials",
        type=str,
        required=False,
        help="CASDA credentials config file.",
        default="./casda.ini",)

    parser.add_argument(
        "-m",
        "--manifest",
        type=str,
        required=False,
        help="Manifest Output",)

    parser.add_argument("-t", "--timeout", type=int, required=False, default=3000, help="CASDA download file timeout [seconds]")

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


def download_file(url, check_exists, output, timeout, buffer=4*2**20, retry=3, sleep=5*60):
    """Robust file download from CASDA.
    Large timeout is necessary as the file may need to be stage from tape.
    Introducing retry to resume download from bytes already downloaded.
    Sleep between retries to allow for potential staging from tape issues).
    """
    logging.info(f"Requesting: URL: {url} Timeout: {timeout}")
    if url is None:
        raise ValueError('URL is empty')

    if not os.path.exists(output):
        os.makedirs(output)

    downloaded_bytes = 0
    tries = 0
    while tries <= retry:
        try:
            req =  urllib.request.urlopen(url, timeout=timeout)
            filename = req.info().get_filename()
            filepath = f"{output}/{filename}"
            http_size = int(req.info()['Content-Length'])

            # File exists and is same size; do nothing and return
            if check_exists and os.path.exists(filepath) and os.path.getsize(filepath) == http_size:
                logging.info(f"File exists and is same size as download content, ignoring: {os.path.basename(filepath)}")
                return filepath

            # Resume download from bytes already downloaded
            if os.path.exists(filepath) and os.path.getsize(filepath) != http_size:
                downloaded_bytes = os.path.getsize(filepath)
                logging.info(f"Resuming download: {os.path.basename(filepath)} {downloaded_bytes} bytes")
                headers = {'Range': f'bytes={downloaded_bytes}-'}
                mode = 'ab'

            # Starting download when there is no file
            elif not os.path.exists(filepath):
                logging.info(f"Starting download: {os.path.basename(filepath)}")
                headers = {}
                mode = 'wb'

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                with open(filepath, mode) as o:
                    while True:
                        buff = r.read(buffer)
                        if not buff:
                            break
                        o.write(buff)
                        downloaded_bytes += len(buff)

                download_size = os.path.getsize(filepath)
                if http_size != download_size:
                    raise ValueError(f"File size does not match file {download_size} and http {http_size}")

                logging.info(f"Download complete: {os.path.basename(filepath)}")
                return filepath
        except (OSError, ValueError) as e:
            tries += 1
            logging.info(f'Download error. Retry number {tries}. Error: {e}')
            logging.info(f'Sleeping for 5 minutes before retrying.')
            time.sleep(sleep)  # 5 minutes
    raise Exception(f'Download retried {retry} times with each failing.')
    return None


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

    # download
    file_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for url in url_list:
            if url.endswith('checksum'):
                continue
            futures.append(executor.submit(download_file, url=url, check_exists=True, output=args.output, timeout=args.timeout))

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
