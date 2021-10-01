#!/usr/bin/env python3

import sys
import argparse
from jinja2 import Template


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Input file names for CASDA image cubes.",
    )
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        required=True,
        help="Output filename and directory for mosiacked image cubes.",
    )
    parser.add_argument(
        "-t",
        "--template",
        type=str,
        required=False,
        help="Jinja template file for the linmos configuration.",
        default="/app/templates/linmos_config.j2"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Filename and path for linmos configuration.",
    )
    args = parser.parse_args(argv)
    return args


def main(argv):
    """Create a linmos configuration file from the image cubes and
    weights downloaded from CASDA.

    """
    args = parse_args(argv)
    config_values = {
        "LINMOS_IMAGE_TYPE": "fits",
        "LINMOS_WEIGHT_TYPE": "FromWeightImages",
        "LINMOS_WEIGHT_STATE": "Corrected",
        "LINMOS_PSFREF": "0",
        "LINMOS_IMAGE_ACCESS": "collective",
        "LINMOS_IMAGE_ACCESS_AXIS": "3",
        "LINMOS_IMAGE_ACCESS_ORDER": "distributed",
        "LINMOS_IMAGE_ACCESS_WRITE": "parallel"
    }

    # Overwrite template
    with open(args.template, 'r') as f:
        template = Template(f.read())

    # Provide arguments to template
    cubes = args.input.replace('.fits', '')
    config_values["LINMOS_NAMES"] = cubes
    config_values["LINMOS_WEIGHTS"] = cubes\
        .replace('image.restored', 'weights')\
        .replace('.contsub', '')
    config_values["LINMOS_OUTNAME"] = args.filename
    config_values["LINMOS_OUTWEIGHT"] = f"{args.filename}.weights"

    config = template.render(config_values)
    with open(args.config, 'w') as f:
        f.writelines(config)
    print(args.config, end="")


if __name__ == "__main__":
    main(sys.argv[1:])
