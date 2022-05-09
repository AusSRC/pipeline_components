#!/usr/bin/env python3

import os
import sys
import argparse
import configparser
from jinja2 import Template


LINMOS_CONFIG_TEMPLATE = f"{os.path.dirname(__file__)}/templates/linmos_config.j2"


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Input template file for linmos configuration.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Filename and path for output linmos configuration.",
    )
    parser.add_argument("--linmos.names", type=str, required=False)
    parser.add_argument("--linmos.weights", type=str, required=False)
    parser.add_argument("--linmos.imagetype", type=str, required=False)
    parser.add_argument("--linmos.outname", type=str, required=False)
    parser.add_argument("--linmos.outweight", type=str, required=False)
    parser.add_argument("--linmos.weighttype", type=str, required=False)
    parser.add_argument("--linmos.weightstate", type=str, required=False)
    parser.add_argument("--linmos.psfref", type=str, required=False)
    parser.add_argument("--linmos.imageaccess", type=str, required=False)
    parser.add_argument("--linmos.imageaccess.axis", type=str, required=False)
    parser.add_argument("--linmos.imageaccess.order", type=str, required=False)
    parser.add_argument("--linmos.imageaccess.write", type=str, required=False)
    args = parser.parse_args(argv)
    return args


def parse_default_config(filename):
    """Read and parse default values from existing linmos configuration file.

    """
    config = {}
    with open(filename, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.replace(' ', '').replace('\n', '')
            kv_list = line.split('=')
            if len(kv_list) != 2:
                raise Exception("Default linmos config formatting error.")
            config[kv_list[0]] = kv_list[1]
    return config


def main(argv):
    """Parse input linmos configuration for default values.
    Update configuration with argument parameters.

    """
    args = parse_args(argv)
    default_config = parse_default_config(args.config)

    # Get args
    passed_config = {}
    for arg in vars(args):
        val = getattr(args, arg)
        if (arg != "config") and val is not None:
            passed_config[arg] = val
    
    # Final configuration
    config_dict = {}
    tmp_dict = {**default_config, **passed_config}
    keys = tmp_dict.keys()
    for k in keys:
        k_new = k.upper().replace('.', '_')
        config_dict[k_new] = tmp_dict[k]

    # Read template and override linmos config
    with open(LINMOS_CONFIG_TEMPLATE, 'r') as f:
        template = Template(f.read())
    config = template.render(config_dict)
    with open(args.output, 'w') as f:
        f.writelines(config)

    return


if __name__ == "__main__":
    main(sys.argv[1:])
