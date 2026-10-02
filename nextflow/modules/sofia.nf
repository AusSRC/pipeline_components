#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// ----------------------------------------------------------------------------------------
// Source finding
//
// Generic workflows for running SoFiA-2 on an image cube and writing the detections to a
// survey database with SoFiAX. There are two workflows
//
//      run_sofia       Split the image cube into sub-cubes and run SoFiA-2 on each
//      run_sofiax      Write the output of run_sofia to the database with SoFiAX
//
// A quality check runs run_sofia only. A full source finding run is run_sofia followed by
// run_sofiax. The image and weights cubes are paths, so they can come from a download or
// mosaicking step or be provided explicitly by the user.
//
// Required params:
//      AUSSRC_TOOLS_IMAGE      Container image with aussrc_tools installed
//      S2P_SETUP_IMAGE         Container image for s2p_setup
//      SOFIA_IMAGE             Container image for SoFiA-2
//      SOFIAX_IMAGE            Container image for SoFiAX (run_sofiax only)
//      SOFIA_CATALOG           Continuum source catalogue used for flagging (flag.catalog)
//      DATABASE_ENV            Database credentials file (run_sofiax only)
//      SCRATCH_ROOT            Scratch filesystem to bind into the container
//
// The SoFiA-2 parameter file, s2p_setup config and SoFiAX config are created from the
// templates (sofia.j2, s2p_setup.ini, sofiax.j2) in this repository.
// ----------------------------------------------------------------------------------------

templates = "${moduleDir}/../templates"

// ----------------------------------------------------------------------------------------
// Processes
// ----------------------------------------------------------------------------------------

// Create the SoFiA-2 parameter file for the run from the template
process sofia_parameter_file {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val output_dir

    output:
        val parameter_file, emit: parameter_file

    script:
        parameter_file = "${output_dir}/sofia.par"
        """
        #!python3

        import os
        from jinja2 import Environment, FileSystemLoader

        j2_env = Environment(loader=FileSystemLoader('${templates}'), trim_blocks=True)
        result = j2_env.get_template('sofia.j2').render(catalog='${params.SOFIA_CATALOG}')

        os.makedirs('${output_dir}', exist_ok=True)
        with open('${parameter_file}', 'w') as f:
            print(result, file=f)
        """
}

// Create a parameter file for each sub-cube of the image cube (sofia_*.par in output_dir).
// Additional arguments for s2p_setup are provided with options, for example to restrict
// source finding to part of the cube
//
//      '--pixel_extent "1170, 1170" --centre_coord "292.5 -38.0"'
process s2p_setup {
    container = params.S2P_SETUP_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val image_cube
        val weights_cube
        val run_name
        val parameter_file
        val output_dir
        val products_dir
        val options

    output:
        val output_dir, emit: output_dir

    script:
        """
        #!/bin/bash

        python3 -u /app/s2p_setup.py \
            --config ${templates}/s2p_setup.ini \
            --image_cube $image_cube \
            --weights_cube $weights_cube \
            --run_name $run_name \
            --sofia_template $parameter_file \
            --output_dir $output_dir \
            --products_dir $products_dir \
            $options
        """
}

// Fetch parameter files from the filesystem (dynamically)
process get_parameter_files {
    executor = 'local'

    input:
        val output_dir

    output:
        val parameter_files, emit: parameter_files

    exec:
        parameter_files = file("${output_dir}/sofia_*.par")
}

// Run source finding application (sofia)
// Currently works for SoFiA-2 version 2.6 onwards
process sofia {
    container = params.SOFIA_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val parameter_file

    output:
        val parameter_file, emit: parameter_file

    script:
        """
        #!/bin/bash

        OMP_NUM_THREADS=8 sofia $parameter_file
        """
}

// Create the SoFiAX configuration file for the run from the template. Database details
// are read from the credentials file.
process update_sofiax_config {
    container = params.AUSSRC_TOOLS_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val run_name
        val sofiax_config
        val parameter_files

    output:
        val sofiax_config, emit: sofiax_config

    script:
        """
        #!/bin/bash

        python3 -u -m aussrc_tools.source_finding.update_sofiax_config \
            --config ${templates}/sofiax.j2 \
            --database ${params.DATABASE_ENV} \
            --output $sofiax_config \
            --run_name $run_name
        """
}

// Write sofia output to database (sofiax)
process sofiax {
    container = params.SOFIAX_IMAGE
    containerOptions = "--bind ${params.SCRATCH_ROOT}:${params.SCRATCH_ROOT}"

    input:
        val parameter_files
        val sofiax_config

    output:
        val true, emit: ready

    script:
        """
        #!/bin/bash

        python -m sofiax -c $sofiax_config -p ${parameter_files.join(' ')}
        """
}

// ----------------------------------------------------------------------------------------
// Workflows
// ----------------------------------------------------------------------------------------

// Run SoFiA-2 on an image cube.
//
//      run_sofia(image_cube, weights_cube, run_name, output_dir, "${output_dir}/outputs", "")
//
// Parameter files are written to output_dir and SoFiA-2 products to products_dir. The
// s2p_options are additional arguments for s2p_setup (see s2p_setup), or "" for none.
workflow run_sofia {
    take:
        image_cube
        weights_cube
        run_name
        output_dir
        products_dir
        s2p_options

    main:
        sofia_parameter_file(output_dir)
        s2p_setup(
            image_cube,
            weights_cube,
            run_name,
            sofia_parameter_file.out.parameter_file,
            output_dir,
            products_dir,
            s2p_options
        )
        get_parameter_files(s2p_setup.out.output_dir)
        sofia(get_parameter_files.out.parameter_files.flatten())

    emit:
        parameter_files = sofia.out.parameter_file.collect()
}

// Write the output of run_sofia to the database. The SoFiAX configuration file for the run
// is written to sofiax_config.
//
//      run_sofiax(run_name, run_sofia.out.parameter_files, "${output_dir}/sofiax.ini")
workflow run_sofiax {
    take:
        run_name
        parameter_files
        sofiax_config

    main:
        update_sofiax_config(run_name, sofiax_config, parameter_files)
        sofiax(parameter_files, update_sofiax_config.out.sofiax_config)

    emit:
        ready = sofiax.out.ready
}
