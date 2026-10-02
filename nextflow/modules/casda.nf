#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// ----------------------------------------------------------------------------------------
// CASDA download
//
// Generic processes for downloading ASKAP data products and evaluation files from CASDA.
// These wrap aussrc_tools.casda.download and aussrc_tools.casda.download_evaluation_files.
//
// Required params:
//      AUSSRC_TOOLS_IMAGE      Container image with aussrc_tools installed
//      CASDA_CREDENTIALS       CASDA credentials config file (section [CASDA] with username
//                              and password)
//      SCRATCH_ROOT            Scratch filesystem to bind into the container
//
// The pipelines are responsible for
//      1. Constructing the TAP query for the files they need (see download)
//      2. Parsing the manifest to find those files once downloaded
// ----------------------------------------------------------------------------------------

// Download all files returned by a TAP query to CASDA (https://casda.csiro.au/casda_vo_tools/tap).
//
// The query is constructed in the pipeline as a groovy string, for example
//
//      def ids = sbids.collect { "'${it}'" }.join(',')
//      def query = "SELECT * FROM ivoa.obscore WHERE obs_id IN (${ids}) AND " +
//                  "dataproduct_type='cube' AND (" +
//                  "filename LIKE 'weights.i.%.cube.fits' OR " +
//                  "filename LIKE 'image.restored.i.%.cube.contsub.fits')"
//      download(query, output_dir, "${output_dir}/manifest.json")
//
// The query is passed to the script in double quotes so it must not contain the
// characters " $ ` or \
//
// The manifest is a JSON list of the paths of the downloaded files. It is only written once
// all files have been downloaded, so the download is skipped if the manifest already exists.
// The download fails if the query does not return any files.

process download {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT} --bind \$HOME:\$HOME"

    errorStrategy { sleep(Math.pow(2, task.attempt) * 200 as long); return 'retry' }
    maxErrors 10

    input:
        val query
        val output_dir
        val manifest

    output:
        val manifest, emit: manifest

    script:
        """
        #!/bin/bash

        if [ ! -f "$manifest" ]; then
            python3 -u -m aussrc_tools.casda.download \
                -q "$query" \
                -o $output_dir \
                -m $manifest \
                -c ${params.CASDA_CREDENTIALS}
        fi
        """
}

// Download and extract the evaluation files for an observation (sbid).
//
// Evaluation files are found by project code and not with a TAP query. The project_codes
// can be a single code or a list of codes, for example
//
//      download_evaluation_files(sbid, ['AS203', 'AS202', 'AS201'], output_dir)
//
// Project codes that have no evaluation files for the observation are ignored. No manifest
// is written, the evaluation files are found in the output directory.

process download_evaluation_files {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT} --bind \$HOME:\$HOME"

    errorStrategy { sleep(Math.pow(2, task.attempt) * 200 as long); return 'retry' }
    maxErrors 3

    input:
        val sbid
        val project_codes
        val output_dir

    output:
        val output_dir, emit: evaluation_files

    script:
        def codes = project_codes instanceof List ? project_codes.join(' ') : project_codes
        """
        #!/bin/bash

        python3 -u -m aussrc_tools.casda.download_evaluation_files \
            -s $sbid \
            -p $codes \
            -o $output_dir \
            -c ${params.CASDA_CREDENTIALS}
        """
}
