import subprocess
import pandas as pd
import os
import json
import logging
import tempfile
from erna import ft_json_to_df
from erna.utils import (
    assemble_facttools_call,
    check_environment_on_node
    )


def run(jar, xml, input_files_df, aux_source_path=None, 
        max_heap_size='2014m'
        ):
    '''
    This is what will be executed on the cluster
    '''
    logger = logging.getLogger(__name__)
    logger.info("stream runner has been started.")

    with tempfile.TemporaryDirectory() as output_directory:
        input_path = os.path.join(output_directory, "input.json")
        output_path = os.path.join(output_directory, "output.json")

        input_files_df.to_json(input_path, orient='records', date_format='epoch')
        call = assemble_facttools_call(
                    jar,
                    xml,
                    input_path,
                    output_path,
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
            if os.path.exists(output_path):
                logger.error("Trying to collect output files")
            else:
                return "fact-tools error"

        # try to read nans else return empty frame
        return ft_json_to_df(output_path)
