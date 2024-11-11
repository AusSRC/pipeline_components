#!/usr/bin/env python3

"""
This functionality is specific to the WALLABY full survey operating scheme.
For a given source extraction region (SER), after mosaicking, we will add the SBIDs of the constituent observations
to the header of the mosaic file. This requires a couple of SQL queries to the WALLABY database.
"""

import os
import sys
import asyncpg
import asyncio
import logging
from argparse import ArgumentParser
from astropy.io import fits
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)


async def main(argv):
    parser = ArgumentParser()
    parser.add_argument('-s', dest='ser', help='Source extraction region name')
    parser.add_argument('-f', dest='file', help='Input mosaicked image file path')
    parser.add_argument('-e', dest='env', help='Database credentials environment file')
    args = parser.parse_args(argv)
    logging.info(args)

    assert os.path.exists(args.file), 'File does not exist'
    assert os.path.exists(args.env), 'Database environment file does not exist'

    # Database connection
    load_dotenv(args.env)
    dsn = {
        "host": os.environ["DATABASE_HOST"],
        "database": os.environ["DATABASE_NAME"],
        "user": os.environ["DATABASE_USER"],
        "password": os.environ["DATABASE_PASSWORD"],
	    "port": os.environ["DATABASE_PORT"]
    }
    schema = os.environ["DATABASE_SCHEMA"]
    conn = await asyncpg.connect(dsn=None, **dsn, server_settings={'search_path': schema})
    logging.info('Established database connection')
    res = await conn.fetchrow('SELECT * FROM source_extraction_region WHERE name=$1', args.ser)
    logging.info(res)
    if res is None:
        raise Exception('Source extraction region does not exist')

    # Get SBIDs for SER
    async with conn.transaction():
        footprints_for_ser_query = '''
            SELECT t."footprint_A", t."footprint_B" FROM wallaby.source_extraction_region ser
                LEFT JOIN wallaby.source_extraction_region_tile sert ON ser.id = sert.ser_id
                LEFT JOIN wallaby.tile t ON sert.tile_id = t.id
            WHERE ser.name = $1
        '''
        obs_ids = []
        footprints = await conn.fetch(footprints_for_ser_query, args.ser)
        logging.info(footprints)
        for record in footprints:
            obs_ids.append(int(record['footprint_A']))
            obs_ids.append(int(record['footprint_B']))
        logging.info(obs_ids)

        sbid_list = None
        sbid_query = f'SELECT sbid FROM observation WHERE id in {tuple(obs_ids)}'
        logging.info(sbid_query)
        res = await conn.fetch(sbid_query)
        logging.info(res)
        sbid_list = ' '.join([r['sbid'].strip('ASKAP-') for r in res])
        logging.info(sbid_list)

    await conn.close()

    # Update fits
    with fits.open(args.file, mode='update') as hdu:
        hdr = hdu[0].header
        hdr['SBID'] = sbid_list
    logging.info(f'Added sbids {sbid_list} to fits cube {args.file}')


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
