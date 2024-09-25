#!/usr/bin/env python3

"""
Upload plots as bytes to database table.
"""

import os
import sys
import logging
import argparse
import asyncio
import asyncpg
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)


DEFAULT_QUERY = 'INSERT INTO $TABLE (run_id, $COLUMN) VALUES ($1, $2) ON CONFLICT (run_id) DO UPDATE SET $COLUMN = $2;'


def get_file_bytes(path: str, mode: str = 'rb'):
    buffer = []
    if not os.path.isfile(path):
        return b''
    with open(path, mode) as f:
        while True:
            buff = f.read()
            if not buff:
                break
            buffer.append(buff)
        if 'b' in mode:
            return b''.join(buffer)
        else:
            return ''.join(buffer)

async def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--run', required=True)
    parser.add_argument('-t', '--table', default='quality_check', required=False)
    parser.add_argument('-c', '--column', required=True)
    parser.add_argument('-f', '--file', help='Output filename', required=True)
    parser.add_argument('-e', '--env', help='Database credentials', required=True)
    parser.add_argument('-q', '--query', default=DEFAULT_QUERY, required=False)
    args = parser.parse_args(argv)

    # Get file
    assert os.path.exists(args.file), f'File does not exist {args.file}'
    filebytes = get_file_bytes(args.file)

    # Establish database connection
    load_dotenv(args.env)
    d_dsn = {
        "host": os.environ["DATABASE_HOST"],
        "database": os.environ["DATABASE_NAME"],
        "user": os.environ["DATABASE_USER"],
        "password": os.environ["DATABASE_PASSWORD"]
    }
    schema = os.environ["DATABASE_SCHEMA"]

    # Get detections
    query = args.query.replace('$TABLE', args.table)
    query = query.replace('$COLUMN', args.column)
    logging.info(query)
    conn = await asyncpg.connect(dsn=None, **d_dsn, server_settings={'search_path': schema})
    async with conn.transaction():
        run = await conn.fetchrow('SELECT * FROM run WHERE name=$1', args.run)
        run_id = int(run['id'])
        logging.info(f'Inserting into run {args.run} [{run_id}]')
        res = await conn.fetchrow(query, run_id, filebytes)
        logging.info(res)
    await conn.close()
    return 0

if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
