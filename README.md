<h1 align="center">Pipeline components</h1>

[![Tests](https://github.com/AusSRC/WALLABY_components/actions/workflows/tests.yaml/badge.svg)](https://github.com/AusSRC/WALLABY_components/actions/workflows/tests.yaml)
[![Linting](https://github.com/AusSRC/WALLABY_components/actions/workflows/lint.yaml/badge.svg)](https://github.com/AusSRC/WALLABY_components/actions/workflows/lint.yaml)
[![Docker build latest](https://github.com/AusSRC/WALLABY_components/actions/workflows/docker-build-latest.yml/badge.svg)](https://github.com/AusSRC/WALLABY_components/actions/workflows/docker-build-latest.yml)
[![Docker build release](https://github.com/AusSRC/WALLABY_components/actions/workflows/docker-build-release.yml/badge.svg)](https://github.com/AusSRC/WALLABY_components/actions/workflows/docker-build-release.yml)

# Overview

A repository for components used as part of the ASKAP science project post-processing workflows. The workflows can be accessed here

* [WALLABY](https://github.com/AusSRC/WALLABY_workflows)
* [POSSUM](https://github.com/AusSRC/POSSUM_workflows)
* [EMU](https://github.com/ASKAP-EMUCat)* 

*Note EMU workflows have their own separate components repository at the moment.

# Components

## CASDA Download

The CASDA download component scripts are used to retrieve image cubes from CASDA to the AusSRC slurm cluster for processing. Both WALLABY and POSSUM make use of this component. It includes scripts for verifying the checksum of the downloaded file.

## Mosaicking

The mosaicking component is for the execution of `linmos` on image cubes. It includes scripts for generating the `linmos` configuration file.

## Source Finding

This source finding component provides users with the ability to execute `sofia` for source finding on a mosaicked image cube.