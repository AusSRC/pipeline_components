# HPX tiles

Code required for performing HEALPIX tiling of spectral line cubes, and generating the correct observation to HPX tile mapping scheme. Used primarily for the POSSUM pipeline.

## Scripts

| File | Description | Used in |
| --- | --- | --- |
| [fits_split.py](fits_split.py) | Split image cube into N subcubes along frequency axis | `tiling.nf` |
| [casa_tiling.py](casa_tiling.py) | Perform CASA tiling of image cube. Produces either a tiled (CASA) subcube, or a NaN cube (astropy) | `tiling.nf` |
| [join_subcubes.py](join_subcubes.py) | Join split subcubes along frequency axis | `tiling.nf`, `convolution.nf` |
| [repair_incomplete_tiles.py](repair_incomplete_tiles.py) | Fill joined subcubes with NaN values where the last channels of a joined cube do not exist for some reason. Fills with NaN values to the specified number of frequency channels. | `tiling.nf` |
| [generate_tile_pixel_map.py](generate_tile_pixel_map.py) |  Generate CSV file with mapping from observations to HPX tiles | `hpx_tile_map.nf` |
| [split_cube.py](split_cube.py) | Split image cube into N subcubes along frequency axis | `convolution.nf` |

### Archive

| File | Description | Order |
| --- | --- | --- |
| [fits_md5.py](fits_md5.py) |  TBA |  |
| [rename_tiles.py](rename_tiles.py) |  TBA |  |

## Config

Default `NAXIS=2048`

HPX mapping config defaults are provided in config subfolder for ASKAP [band 1](config/hpx_tile_config_band1.json) and [band 2](config/hpx_tile_config_band2.json) observations.

## CASA

We fix the version of Python CASA in the `hpx_tiles` container to ensure the tiling works with the code that we have written. There are some minor modifications (`-1` to `CRPIX1` and `CRPIX2` in header) that are required for the current version of CASA that we are using. These may break if a different version of python casa is used.

```
casatools==6.5.2.26
casatasks==6.5.2.26
```
