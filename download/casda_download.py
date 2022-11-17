#!/usr/bin/env python3

import os
import sys
import logging
from dotenv import load_dotenv
import asyncpg
import asyncio
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
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ('$SBIDS') AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'weights.i.%.cube.fits' OR "
    "filename LIKE 'image.restored.i.%.cube.contsub.fits')"
)
POSSUM_QUERY = (
    "SELECT * FROM ivoa.obscore WHERE obs_id IN ('$SBIDS') AND "
    "dataproduct_type='cube' AND ("
    "filename LIKE 'image.restored.i.%.contcube.fits' OR "
    "filename LIKE 'weights.i.%.contcube.fits' OR "
    "filename LIKE 'image.restored.q.%.contcube.fits' OR "
    "filename LIKE 'image.restored.u.%.contcube.fits')"
)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--sbid",
        type=int,
        required=True,
        help="Scheduling block id number.",
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
    parser.add_argument(
        '-d',
        '--database',
        type=str,
        required=False,
        help='Database access credentials'
    )
    parser.add_argument(
        "--dryrun",
        dest="dryrun",
        action="store_true",
        help="Dry run mode (will not download)",
        default=False,
    )
    args = parser.parse_args(argv)
    return args


def tap_query(project, sbid):
    """Return astropy table with query result (files to download)"""

    if project == "WALLABY":
        logging.info(f"Scheduling block ID: {sbid}")
        query = WALLABY_QUERY.replace("$SBIDS", str(sbid))
        query = query.replace("$SURVEY", str(project))
        logging.info(f"TAP Query: {query}")
    elif project == "POSSUM":
        logging.info(f"Scheduling block ID: {sbid}")
        query = POSSUM_QUERY.replace("$SBIDS", str(sbid))
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


async def main(argv):
    """Downloads image cubes from CASDA matching the observing block IDs
    provided in the arguments.

    """
    args = parse_args(argv)
    res = tap_query(args.project, args.sbid)
    logging.info(res)

    if args.project == 'WALLABY' and not args.database:
        raise Exception('WALLABY needs database credentials to write observation to database.')

    # stage
    parser = configparser.ConfigParser()
    parser.read(args.credentials)
    casda = Casda(parser["CASDA"]["username"], parser["CASDA"]["password"])
    url_list = casda.stage_data(res, verbose=True)
    logging.info(f"CASDA download staged data URLs: {url_list}")

    # get files
    files = [str(f) for f in res['filename'].data.data]
    image_cube_file = os.path.join(args.output, [f for f in files if 'image' in f][0])
    weights_cube_file = os.path.join(args.output, [f for f in files if 'weights' in f][0])

    # add to observation table (WALLABY)
    if args.project == 'WALLABY':
        logging.info('Adding observation(s) to database')
        load_dotenv(args.database)
        creds = {
            "host": os.environ["DATABASE_HOST"],
            "database": os.environ["DATABASE_NAME"],
            "user": os.environ["DATABASE_USER"],
            "password": os.environ["DATABASE_PASSWORD"],
        }
        pool = await asyncpg.create_pool(**creds)
        async with pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO wallaby.observation \
                    (sbid, ra, dec, image_cube_file, weights_cube_file) \
                VALUES \
                    ($1, $2, $3, $4, $5) \
                ON CONFLICT (sbid) \
                DO UPDATE SET \
                    image_cube_file = $4, \
                    weights_cube_file = $5;',
                int(args.sbid),
                float(res[0]['s_ra']),
                float(res[0]['s_dec']),
                image_cube_file,
                weights_cube_file
            )
            logging.info("Writing observation to WALLABY database.")

    # download if files do not exist
    if not os.path.exists(image_cube_file) or not os.path.exists(weights_cube_file):
        if not args.dryrun:
            logging.info('Starting download')
            logging.info(f'Writing image cube to {image_cube_file}')
            logging.info(f'Writing weights cube to {weights_cube_file}')
            casda.download_files(url_list, savedir=args.output)
        else:
            logging.info('Dry run mode - not downloading any files')
    else:
        logging.info('Files already exist, skipping download')


if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
