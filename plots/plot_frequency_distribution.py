#!/usr/bin/env python3

"""
Plot detection x frequency distribution to help with quality checking

"""

import os
import sys
import math
import argparse
import asyncio
import asyncpg
from dotenv import load_dotenv
import matplotlib.pyplot as plt

plt.rcParams["figure.figsize"] = (40,24)
plt.rcParams.update({"font.size": 24})

async def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--run', required=True)
    parser.add_argument('-e', '--env', help='Database credentials', required=True)
    parser.add_argument('-o', '--output', help='Output filename', required=True)
    args = parser.parse_args(argv)

    load_dotenv(args.env)
    d_dsn = {
        "host": os.environ["DATABASE_HOST"],
        "database": os.environ["DATABASE_NAME"],
        "user": os.environ["DATABASE_USER"],
        "password": os.environ["DATABASE_PASSWORD"],
        "port": os.getenv("DATABASE_PORT", 5432)
    }
    schema = os.environ["DATABASE_SCHEMA"]

    # Get detections
    conn = await asyncpg.connect(dsn=None, **d_dsn, server_settings={'search_path': schema})
    run = await conn.fetchrow('SELECT * FROM run WHERE name=$1', args.run)
    data = await conn.fetch('SELECT (name, f_sum, freq) FROM detection WHERE run_id=$1', int(run['id']))
    data = [d['row'] for d in data]
    detections = [d[0] for d in list(data)]
    f_sum = [math.log10(float(d[1])) for d in list(data)]
    freq = [float(d[2]) / 1e+9 for d in list(data)]

    # Create plot
    plt.scatter(freq, f_sum, s=25, c="red")
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("log(Flux / Jy Hz)")
    plt.xlim(1.31, 1.42)
    plt.grid()
    plt.title(run['name'])
    plt.savefig(args.output)

if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
