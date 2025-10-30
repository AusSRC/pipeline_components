#!/usr/bin/env python3

"""
Plot detection x frequency distribution to help with quality checking
Use XML files
"""


import os
import sys
import glob
import math
import argparse
import logging
import numpy as np
from astropy.table import vstack
from astropy.io import ascii
from astropy.io.votable import parse
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)

plt.rcParams["figure.figsize"] = (40,24)
plt.rcParams.update({"font.size": 24})

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Directory of the sofia output products', required=True)
    parser.add_argument('-o', '--output', help='Output filename of plot', required=True)
    parser.add_argument('-r', '--run_name', help='Title of plot produced', required=True)
    args = parser.parse_args(argv)
    assert os.path.exists(args.input), "Directory of sofia output products does not exist."

    # Read XML
    files = glob.glob(os.path.join(args.input, '*.xml'))
    logging.info(files)
    if not files:
        logging.info('No VOtable files found')
        return
    detection_table = None
    for f in files:
        votable = parse(f)
        resource = votable.resources[0]
        params = resource.params
        input_region = eval([p for p in params if p.name=='input.region'][0].value)
        (xmin, _, ymin, _, zmin, _) = input_region
        table = votable.get_first_table().to_table()
        table['x'] = table['x'] + xmin
        table['y'] = table['y'] + ymin
        table['z'] = table['z'] + zmin
        logging.info(f'Joining {f} with {len(table)} rows')
        if detection_table is None:
            detection_table = table
            continue
        detection_table = vstack([detection_table, table])
    logging.debug(detection_table)

    f_sum = np.log10(np.array(detection_table['f_sum'].data))
    freq = np.array(detection_table['freq'].data) / 1e9

    # Create text file
    write_table_filename = os.path.splitext(args.output)[0] + '.txt'
    write_table = detection_table
    write_table.keep_columns(['name', 'x', 'y', 'z', 'f_sum', 'f_max'])
    write_table.sort('z')
    ascii.write(write_table, write_table_filename, overwrite=True)

    # Create plot
    plt.scatter(freq, f_sum, s=25, c="red")
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("log(Flux / Jy Hz)")
    plt.xlim(1.31, 1.42)
    plt.grid()
    plt.title(str(args.run_name))
    plt.savefig(args.output)
    logging.info(f'Flux vs frequency plot produced at {args.output}')

if __name__ == '__main__':
    argv = sys.argv[1:]
    main(argv)
