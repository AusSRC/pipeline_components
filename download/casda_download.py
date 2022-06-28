#!/usr/bin/env python3

import os
import sys
import logging
import argparse
import astropy
import configparser
from astroquery.utils.tap.core import TapPlus
from astroquery.casda import Casda


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
astropy.utils.iers.conf.auto_download = False


# TODO(austin): obs_collection as argument
URL = "https://casda.csiro.au/casda_vo_tools/tap"
DEFAULT_QUERY = "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND (" \
    "filename LIKE 'weights.i.%.cube.fits' OR " \
    "filename LIKE 'image.restored.i.%.cube.contsub.fits')"


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i',
        '--input',
        type=int,
        required=True,
        nargs='+',
        help='List of observing block numbers.'
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
        default='./casda.ini'
    )
    parser.add_argument(
        "-q",
        "--query",
        type=str,
        required=False,
        help="CASDA TAP search query.",
        default=DEFAULT_QUERY,
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Downloads image cubes from CASDA matching the observing block IDs
    provided in the arguments.

    """
    args = parse_args(argv)
    parser = configparser.ConfigParser()
    parser.read(args.credentials)

    # submit TAP query
    SBIDS = ', '.join(f"'{str(i)}'" for i in args.input)
    logging.info(f'CASDA download started for the following scheduling block IDs: {SBIDS}')  # noqa
    query = args.query.replace("$SBIDS", str(SBIDS))
    logging.info(f'CASDA download submitting query: {query}')
    casdatap = TapPlus(url=URL, verbose=False)
    job = casdatap.launch_job_async(query)
    query_result = job.get_results()
    logging.info(f'CASDA download query TAP result: {query_result}')

    # stage and download
    casda = Casda(parser['CASDA']['username'], parser['CASDA']['password'])
    url_list = casda.stage_data(query_result, verbose=True)
    logging.info(f'CASDA download staged data URLs: {url_list}')
    casda.download_files(url_list, savedir=args.output)


if __name__ == "__main__":
    main(sys.argv[1:])
