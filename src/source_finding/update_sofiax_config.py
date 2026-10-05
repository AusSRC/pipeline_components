#!/usr/bin/env python3

import argparse
import configparser
import os
import sys

from dotenv import load_dotenv


def parse_args(argv):
    """Command line arguments for SoFiAX configuration file and run name."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=str,
        required=False,
        help="Path to database configuration file",
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to template SoFiAX configuration file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output SoFiAX configuration file for the specific run.",
    )
    parser.add_argument("--db_hostname", type=str, required=False)
    parser.add_argument("--db_name", type=str, required=False)
    parser.add_argument("--db_username", type=str, required=False)
    parser.add_argument("--db_password", type=str, required=False)
    parser.add_argument("--db_schema", type=str, required=False)
    parser.add_argument("--db_port", type=str, required=False)
    parser.add_argument("--sofia_execute", type=str, required=False)
    parser.add_argument("--sofia_path", type=str, required=False)
    parser.add_argument("--sofia_processes", type=str, required=False)
    parser.add_argument("--run_name", type=str, required=False)
    parser.add_argument("--spatial_extent", type=str, required=False)
    parser.add_argument("--spectral_extent", type=str, required=False)
    parser.add_argument("--flux", type=str, required=False)
    parser.add_argument("--uncertainty_sigma", type=str, required=False)
    args = parser.parse_args(argv)
    return args


# Owner only
def opener(path, flags):
    return os.open(path, flags, 0o600)


def main(argv):
    """Update the SoFiAX configuration file with arguments"""
    # get args
    file_args = ["database", "config", "output"]
    args = parse_args(argv)
    args_dict = vars(args)

    # get database credentials from file
    if args.database is not None:
        load_dotenv(args.database)
        if args.db_hostname is None:
            args_dict["db_hostname"] = os.environ["DATABASE_HOST"]
        if args.db_name is None:
            args_dict["db_name"] = os.environ["DATABASE_NAME"]
        if args.db_username is None:
            args_dict["db_username"] = os.environ["DATABASE_USER"]
        if args.db_password is None:
            args_dict["db_password"] = os.environ["DATABASE_PASSWORD"]
        if args.db_schema is None:
            args_dict["db_schema"] = os.environ.get("DATABASE_SCHEMA")
        if args.db_port is None:
            args_dict["db_port"] = os.environ.get("DATABASE_PORT")

    # update config
    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(args.config)
    for arg, val in args_dict.items():
        if (arg not in file_args) and val is not None:
            config.set("SoFiAX", arg, val)

    # remove template placeholders that have not been set
    for option, val in config.items("SoFiAX"):
        if val.startswith("{{") and val.endswith("}}"):
            config.remove_option("SoFiAX", option)

    os.umask(0)

    # write
    with open(args.output, "w", opener=opener) as f:
        config.write(f)


if __name__ == "__main__":
    main(sys.argv[1:])
