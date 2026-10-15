#!/usr/bin/env python3

"""
Create a run entry in the survey database. Does nothing if a run with the
same name already exists.
"""

import argparse
import asyncio
import logging
import os
import sys

import asyncpg
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


QUERY = (
    "INSERT INTO run (name, sanity_thresholds) VALUES ($1, $2) "
    "ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name "
    "RETURNING id"
)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", help="Run name", required=True)
    parser.add_argument("-e", "--env", help="Database credentials", required=True)
    parser.add_argument(
        "-s",
        "--sanity_thresholds",
        help="Sanity thresholds for the run (JSON string)",
        default="{}",
        required=False,
    )
    args = parser.parse_args(argv)
    return args


async def main(argv):
    args = parse_args(argv)

    # Establish database connection
    load_dotenv(args.env)
    d_dsn = {
        "host": os.environ["DATABASE_HOST"],
        "database": os.environ["DATABASE_NAME"],
        "user": os.environ["DATABASE_USER"],
        "password": os.environ["DATABASE_PASSWORD"],
        "port": os.getenv("DATABASE_PORT", "5432"),
    }
    schema = os.environ["DATABASE_SCHEMA"]

    # Create run
    conn = await asyncpg.connect(
        dsn=None, **d_dsn, server_settings={"search_path": schema}
    )
    async with conn.transaction():
        run = await conn.fetchrow(QUERY, args.run, args.sanity_thresholds)
        run_id = int(run["id"])
        logger.info(f"Run {args.run} [{run_id}]")
    await conn.close()
    return run_id


if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
