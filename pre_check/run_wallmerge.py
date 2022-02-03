#!/usr/bin/env python3

import sys
import os
import glob


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("\n Usage: run_wallmerge.py <OUTPUT_DIRECTORY>\n\n")
        sys.exit(1)

    output_directory = sys.argv[1]
    cube_files = glob.glob(f"{output_directory}/*_mom0.fits")
    cube_files_str = ','.join(cube_files)

    # /app for execution in docker image
    cmd = f'/app/wallmerge.py {cube_files_str}'
    os.system(cmd)


if __name__ == '__main__':
    main()
