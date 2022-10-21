#!/usr/bin/env python3

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
WALLABY_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'weights.i.%.cube.fits' OR "
    "filename LIKE 'image.restored.i.%.cube.contsub.fits')"
)
POSSUM_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ($SBIDS) AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'image.restored.i.%.contcube.fits' OR "
    "filename LIKE 'weights.i.%.contcube.fits' OR "
    "filename LIKE 'image.restored.q.%.contcube.fits' OR "
    "filename LIKE 'image.restored.u.%.contcube.fits')"
)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=int,
        required=True,
        nargs="+",
        help="List of scheduling block id numbers.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output directory for downloaded files.",
    )
    parser.add_argument(
        "-p",
        "--project",
        type=str,
        required=True,
        help="ASKAP project name (WALLABY or POSSUM).",
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


def tap_query(project, sbids):
    """Return astropy table with query result (files to download)"""

    if project == "WALLABY":
        SBIDS = ", ".join(f"'{str(i)}'" for i in sbids)
        logging.info(f"Scheduling block IDs: {SBIDS}")
        query = WALLABY_QUERY.replace("$SBIDS", str(SBIDS))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")
    elif project == "POSSUM":
        SBIDS = ", ".join(f"'{str(i)}'" for i in sbids)
        logging.info(f"Scheduling block IDs: {SBIDS}")
        query = POSSUM_QUERY.replace("$SBIDS", str(SBIDS))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")
    else:
        raise Exception(
            'Unexpected project name provided ("WALLABY" or "POSSUM" currently supported).'
        )
    casdatap = TapPlus(url=URL, verbose=False)
    job = casdatap.launch_job_async(query)
    res = job.get_results()
    logging.info(f"Query result: {res}")
    return res


def main(argv):
    """Downloads image cubes from CASDA matching the observing block IDs
    provided in the arguments.

    """
    args = parse_args(argv)
    res = tap_query(args.project, args.input)

    # stage and download
    parser = configparser.ConfigParser()
    parser.read(args.credentials)
    casda = Casda(parser["CASDA"]["username"], parser["CASDA"]["password"])
    url_list = casda.stage_data(res, verbose=True)
    logging.info(f"CASDA download staged data URLs: {url_list}")
    casda.download_files(url_list, savedir=args.output)


if __name__ == "__main__":
    main(sys.argv[1:])
