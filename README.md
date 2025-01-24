# AusSRC pipeline components

Docker images and component scripts for AusSRC ASKAP science data post-processing workflows. These components provide code snippets for generic functionality used across these workflows. They are used across the following pipelines

- [POSSUM pipeline](https://github.com/AusSRC/POSSUM_workflow)
- [WALLABY pipeline](https://github.com/AusSRC/WALLABY_pipelines)
- [DINGO pipeline](https://github.com/AusSRC/DINGO_workflows)

## Container images

| Repo | Description | Image |
| --- | --- | --- |
| [casda_download](casda_download/README.md) |  Code for downloading image cubes from CASDA | [docker://aussrc/casda_download](https://hub.docker.com/r/aussrc/casda_download) |
| [hpx_tiles](hpx_tiles/README.md) |  Codes for performing HPX tiling of POSSUM data cubes using CASA | [docker://aussrc/hpx_tiles](https://hub.docker.com/r/aussrc/hpx_tiles) |
| ... | ... | ... |

## Contributing

### Structure

Each folder in this repository contains:

- README.md
- Dockerfile
- RELEASES.md

### Building images

```
docker build --platform linux/amd64 <project> docker://aussrc/<image_name>:<tag>
docker push docker://aussrc/<image_name>:<tag>
```