# Changelog

All changes to the Docker image `docker://aussrc/hpx_tiles` will be documented in this file.

## [v1.0.1]

- CASA tiling fix by subtracting `1.0` from CRPIX1 and CRPIX2 to conform to NaN cube
- CRPIX1 and CRPIX2 in reference header add `0.5`
- Mapping fix affecting all tiles, correctly computing CRPIX for edge tiles
- `BMAJ` and `BMIN` added to template header where appropriate (with try-catch)
- Assume default axis ordering (ra, dec, pol, freq) in cubes prior to mosaicking. Reverting all changes to flip pol and freq. Preferred axis order will be applied at the mosaicking stage of the workflow.
- Move `repair_incomplete_tiles.py` from AusSRC metadata image into this repository and `hpx_tiles` image
- Cleanup archived scripts in subdirectory (codes no longer used in main pipeline)

## [v1.0.0]

- Wasn't tracking changes at this stage, everything was just pushed to `latest` tag
- Basic tiling functionality with bugs. Used to generate all tiles up until 2025 (before rerunning all POSSUM observations)
- Outdated...