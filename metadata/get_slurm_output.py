#!/usr/bin/env python3

"""
Get the relevant metadata from the evaluation files (slurmOutput) and write to database.
This is required for WALLABY to track beam information.
"""

import os
import sys
import glob
import json
import tarfile
import argparse
import configparser
import logging
import asyncio
import asyncpg


logging.basicConfig(level=logging.INFO)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--sbid",
        type=int,
        required=True,
        help="SBID corresponding to downloaded evaluation files.",
    )
    parser.add_argument(
        "-f",
        "--files",
        type=str,
        required=True,
        help="Path to parent directory containing evaluation files.",
    )
    parser.add_argument(
        "-d",
        "--database",
        type=str,
        required=True,
        help="Database credentials config file (sofiax.ini).",
    )
    parser.add_argument(
        "-k",
        "--keyword",
        type=str,
        required=False,
        help="Search key word for identifying slurmOutput files",
        default="slurmOutput/pipelineConfig",
    )
    args = parser.parse_args(argv)
    return args


async def main(argv):
    args = parse_args(argv)
    db_parser = configparser.ConfigParser()
    db_parser.read(args.database)

    if not os.path.exists(args.files):
        raise Exception(
            f"Evaluation files not found. Path {args.files} does not exist."
        )

    # check content for slurm logs
    slurm_logs_map = {}
    filelist = glob.glob(f"{args.files}/*")
    logging.info(f"Found the following files: {args.files}")
    tarfiles = [f for f in filelist if (("checksum" not in f) and (".tar" in f))]
    logging.info(f"Compressed files: {tarfiles}")
    for tf in tarfiles:
        with tarfile.open(tf) as tar:
            logging.info(tf)
            files = [ti.name for ti in tar.getmembers() if args.keyword in ti.name]
            logging.info(f"Contains: {files}")
            for f in files:
                slurm_logs_map[f] = tf

    slurm_logs = list(slurm_logs_map.keys())
    slurm_logs.sort(reverse=True)

    # extract config
    config = {}
    if len(slurm_logs) == 0:
        logging.error("No slurmOutput log files found.")
    else:
        logging.info(f"Slurm log files: {slurm_logs}")
        for log in slurm_logs:
            if not bool(config):
                # extract if does not exist
                if not os.path.exists(f"{args.files}/{log}"):
                    with tarfile.open(slurm_logs_map[log]) as tar:
                        tar.extractall(args.files)

                # parse and construct parameter dictionary
                logging.info(f"Reading slurm log file {args.files}/{log}")
                config_string = "[SLURM]\n"
                with open(f"{args.files}/{log}", "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if ("=" in line) and (line[0] != "#"):
                            config_string += line

                log_parser = configparser.ConfigParser(
                    strict=False, allow_no_value=True
                )
                logging.info(f"File content:\n{config_string}")
                log_parser.read_string(config_string)
                keys = list(log_parser["SLURM"].keys())
                for key in keys:
                    try:
                        value = log_parser["SLURM"].get(key)
                        config[key] = value
                    except Exception as e:
                        logging.warning(
                            f"Unable to parse config item {key} with error: {e}"
                        )
                logging.info(f"Constructed slurmOutput: {config}")
            else:
                logging.info("Logs extracted, preparing to write to database")
                break

    # add to database
    dsn = {
        "host": db_parser["SoFiAX"]["db_hostname"],
        "database": db_parser["SoFiAX"]["db_name"],
        "user": db_parser["SoFiAX"]["db_username"],
        "password": db_parser["SoFiAX"]["db_password"],
    }
    pool = await asyncpg.create_pool(**dsn)
    async with pool.acquire() as conn:
        obs = await conn.fetchrow(
            f"SELECT * FROM wallaby.observation WHERE sbid={args.sbid}"
        )
        if obs is None:
            raise Exception(f"No observation in WALLABY database for SBID={args.sbid}")
        logging.info(f"Found observation: {obs}")
        logging.info(f'Updating metadata for observation {obs["id"]}')
        await conn.execute(
            "INSERT INTO wallaby.observation_metadata (observation_id, slurm_output) \
            VALUES ($1, $2) \
            ON CONFLICT (observation_id) \
            DO UPDATE SET slurm_output = $2",
            obs["id"],
            json.dumps(config),
        )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
