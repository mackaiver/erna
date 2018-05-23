import subprocess
import pandas as pd
import os
import json
import logging
import tempfile
from shutil import copyfile
from erna import ft_json_to_df
from erna.utils import (
    assemble_facttools_call,
    check_environment_on_node
    )


def run(jar, xml, input_files_df, output_path, aux_source_path=None 
        max_heap_size='2014m'
        ):
    '''
    This is a version of ernas stream runner that will be executed on the cluster,
    but writes its results directly to disk without sending them
    via zeroMq
    '''
    logger = logging.getLogger(__name__)
    logger.info("stream runner has been started.")

    with tempfile.TemporaryDirectory() as output_directory:
        input_path = os.path.join(output_directory, "input.json")
        tmp_output_path = os.path.join(output_directory, "output.json")

        input_files_df.to_json(input_path, orient='records', date_format='epoch')
        call = assemble_facttools_call(
                    jar,
                    xml,
                    input_path,
                    tmp_output_path,
                    aux_source_path,
                    max_heap_size,
                    )

        check_environment_on_node()

        logger.info("Calling fact-tools with call: {}".format(call))
        try:
            subprocess.check_call(call)
        except subprocess.CalledProcessError as e:
            logger.error("Fact tools returned an error:")
            logger.error(e)
            return "fact-tools error"

        if not os.path.exists(tmp_output_path):
            logger.error("Not output generated, returning no results")
            return "fact-tools generated no output"

        copyfile(tmp_output_path, output_path)
        input_files_df['output_path'] = output_path

        return input_files_df
