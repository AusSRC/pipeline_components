#!/usr/bin/env python3

import sys
import argparse
import configparser


def parse_args(argv):
    """Command line arguments for SoFiAX configuration file and run name.

    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to SoFiAX configuration file"
    )
    parser.add_argument("--db_hostname ", type=str, required=False)
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
    """Update the SoFiAX configuration file with arguments

    """
    # get args
    args = parse_args(argv)

    # update config
    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read(args.config)
    for arg in vars(args):
        val = getattr(args, arg)
        if (arg != "config") and val is not None:
            config.set('SoFiAX', arg, val)

    # write
    with open(args.config, 'w') as f:
        config.write(f)


if __name__ == "__main__":
    main(sys.argv[1:])
