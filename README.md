# AusSRC pipeline components

Docker images and component scripts for AusSRC ASKAP science data post-processing workflows. These components provide code snippets for generic functionality used across these workflows. They are used across the following pipelines

- [POSSUM pipeline](https://github.com/AusSRC/POSSUM_workflow)
- [WALLABY pipeline](https://github.com/AusSRC/WALLABY_pipelines)
- [DINGO pipeline](https://github.com/AusSRC/DINGO_workflows)

## Container images

The Python code is installed as the `aussrc_tools` package in two images, built from this repository.

| Image | Dockerfile | Contents |
| --- | --- | --- |
| `aussrc/aussrc_tools` | [Dockerfile](Dockerfile) | All components except CASA tiling |
| `aussrc/aussrc_tools_casa` | [Dockerfile.casa](Dockerfile.casa) | All components, plus CASA and the HPX tiling requirements |

Scripts are run as modules from inside the container

```
python3 -m aussrc_tools.casda_download.casda_download -s <sbid> -o <output_dir> -c <credentials> -p <project>
```

## Components

| Component | Description |
| --- | --- |
| [casda_download](src/aussrc_tools/casda_download/README.md) | Download image cubes and evaluation files from CASDA |
| [hpx_tiles](src/aussrc_tools/hpx_tiles/README.md) | HPX tiling of POSSUM data cubes using CASA |
| [metadata](src/aussrc_tools/metadata/README.md) | FITS header and observation metadata tools |
| mom0 | Merge moment 0 maps |
| mosaicking | Update linmos configuration |
| plots | Diagnostic and summary plots |
| source_finding | Update SoFiAX configuration |

## Contributing

### Structure

- `src/aussrc_tools`: Python package, with one subpackage per component
- `nextflow`: Nextflow modules, templates and config shared across the pipelines
- `tests`: unit tests

Requirements are listed in `pyproject.toml`. Those only needed for HPX tiling are in the `casa` optional dependencies.

### Install

```
pip install -e ".[dev]"
```

### Building images

```
docker build --platform linux/amd64 -t aussrc/aussrc_tools:<tag> .
docker build --platform linux/amd64 -f Dockerfile.casa -t aussrc/aussrc_tools_casa:<tag> .
docker push aussrc/aussrc_tools:<tag>
docker push aussrc/aussrc_tools_casa:<tag>
```
