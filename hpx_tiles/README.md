# HPX tiles

Code required for performing HEALPIX tiling of spectral line cubes.

## Scripts

| File | Description |
| --- | --- |
| [casa_tiling.py](casa_tiling.py) |  TBA |
| [generate_tile_pixel_map.py](generate_tile_pixel_map.py) |  TBA |
| [repair_incomplete_tiles.py](repair_incomplete_tiles.py) |  TBA |
| ... | ... |

## Config

Default `NAXIS=2048`

HPX mapping config defaults are provided in config subfolder for ASKAP [band 1](config/hpx_tile_config_band1.json) and [band 2](config/hpx_tile_config_band2.json) observations.

## CASA

We fix the version of Python CASA in the `hpx_tiles` container to ensure the tiling works with the code that we have written. There are some minor modifications (`-1` to `CRPIX1` and `CRPIX2` in header) that are required for the current version of CASA that we are using. These may break if a different version of python casa is used.

```
casatools==6.5.2.26
casatasks==6.5.2.26
```
