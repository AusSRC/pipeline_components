#!/usr/bin/env python3

import os
import sys
import json
import tarfile
import requests
import argparse
import configparser
import logging
import psycopg2
import psycopg2.extras
from astroquery.casda import Casda
from astropy.table import Table


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


# NOTE: this URL is specific for WALLABY observations
DID_URL = 'https://casda.csiro.au/casda_data_access/metadata/evaluationEncapsulation?projectCode=AS102&sbid='
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
    # NOTE: currently this will be the SoFiAX configuration file
    parser.add_argument(
        "-d",
        "--database",
        type=str,
        required=True,
        help="Database credentials config file."
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Get most recent slurmOutput metadata from SDP run and attach to observation in database

    """
    args = parse_args(argv)
    casda_parser = configparser.ConfigParser()
    casda_parser.read(args.credentials)
    db_parser = configparser.ConfigParser()
    db_parser.read(args.database)

    # get did
    res = requests.get(f"{DID_URL}{args.sbid}")
    logging.info(f'Response: {res.json()}')
    # TODO(austin): what does it mean to have multiple evaluation files?
    evaluation_files = [f for f in res.json() if 'evaluation' in f]
    evaluation_files.sort()
    if not evaluation_files:
        raise Exception(f"No evaluation files found for SBID={args.sbid}")

    casda = Casda(
        casda_parser['CASDA']['username'],
        casda_parser['CASDA']['password']
    )

    # Download evaluation files
    # TODO(austin): may not be necessary to download all evaluation files at once
    logging.info(f'Downloading evaluation files: {evaluation_files}')
    t = Table()
    t['access_url'] = [f'{EVAL_URL}{f}' for f in evaluation_files]
    logging.info(f'Downloading from: {t}')
    url_list = casda.stage_data(t)
    logging.info(f'Staging files {url_list}')
    filelist = casda.download_files(url_list, savedir=args.output)
    logging.info(f'Downloaded files {filelist}')

    # check content for slurm logs
    slurm_logs_map = {}
    tarfiles = [f for f in filelist if 'checksum' not in f]
    for tf in tarfiles:
        with tarfile.open(tf) as tar:
            files = [ti.name for ti in tar.getmembers() if 'slurmOutput/pipelineConfig' in ti.name]
            for f in files:
                slurm_logs_map[f] = tf

    slurm_logs = list(slurm_logs_map.keys())
    slurm_logs.sort(reverse=True)

    # extract config
    config = {}
    if len(slurm_logs) == 0:
        logging.error(f'No slurmOutput log files found for SBID={args.sbid}')
    else:
        logging.info(f'Slurm log files: {slurm_logs}')
        for log in slurm_logs:
            if not bool(config):
                # extract if does not exist
                if not os.path.exists(f'{args.output}/{log}'):
                    with tarfile.open(slurm_logs_map[log]) as tar:
                        tar.extractall(args.output)

                # parse and construct parameter dictionary
                logging.info(f'Reading slurm log file {args.output}/{log}')
                config_string = '[SLURM]\n'
                with open(f'{args.output}/{log}', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if ('=' in line) and (line[0] != '#'):
                            config_string += line

                log_parser = configparser.ConfigParser(
                    strict=False,
                    allow_no_value=True
                )
                logging.info(f'File content:\n{config_string}')
                log_parser.read_string(config_string)
                keys = list(log_parser['SLURM'].keys())
                for key in keys:
                    try:
                        value = log_parser['SLURM'].get(key)
                        config[key] = value
                    except Exception as e:
                        logging.warning(f"Unable to parse config item {key} with error: {e}")
                logging.info(f'Constructed slurmOutput: {config}')
            else:
                logging.info('Logs extracted, writing to database')
                break

    # add to database
    conn = psycopg2.connect(
        host=db_parser['SoFiAX']['db_hostname'],
        database=db_parser['SoFiAX']['db_name'],
        user=db_parser['SoFiAX']['db_username'],
        password=db_parser['SoFiAX']['db_password']
    )
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(f"SELECT * FROM wallaby.observation WHERE sbid={args.sbid}")
    obs_row = dict(cursor.fetchone())
    cursor.close()
    obs_id = int(obs_row['id'])

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO wallaby.observation_metadata (observation_id, slurm_output) \
        VALUES (%s, %s) \
        ON CONFLICT (observation_id) \
        DO UPDATE SET slurm_output = %s",
        (obs_id, json.dumps(config), json.dumps(config))
    )
    conn.commit()
    logging.info("Updated wallaby.observation_metadata table with slurmOutput")
    cursor.close()
    conn.close()


if __name__ == '__main__':
    main(sys.argv[1:])
