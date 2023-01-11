#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv
import argparse
import configparser


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


def main(argv):
    """Update the SoFiAX configuration file with arguments"""
    # get args
    file_args = ["database", "config", "output"]
    args = parse_args(argv)
    args_dict = vars(args)

    # get database credentials from file
    if getattr(args, "database") is not None:
        load_dotenv(args.database)
        if getattr(args, "db_hostname") is None:
            args_dict["db_hostname"] = os.environ["DATABASE_HOST"]
        if getattr(args, "db_name") is None:
            args_dict["db_name"] = os.environ["DATABASE_NAME"]
        if getattr(args, "db_username") is None:
            args_dict["db_username"] = os.environ["DATABASE_USER"]
        if getattr(args, "db_password") is None:
            args_dict["db_password"] = os.environ["DATABASE_PASSWORD"]

    # update config
    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(args.config)
    for arg, val in args_dict.items():
        if (arg not in file_args) and val is not None:
            config.set("SoFiAX", arg, val)

    # write
    with open(args.output, "w") as f:
        config.write(f)


if __name__ == "__main__":
    main(sys.argv[1:])
