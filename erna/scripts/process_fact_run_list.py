import logging
import click
import numpy as np
import pandas as pd
from os import path
import os
import erna
from erna import stream_runner
import gridmap
from gridmap import Job


logger = logging.getLogger(__name__)


def make_jobs(jar, xml, aux_source_path, output_directory, df_mapping,  engine, queue,
              vmem, num_jobs, walltime):
    jobs = []
    # create job objects
    split_indices = np.array_split(np.arange(len(df_mapping)), num_jobs)
    for num, indices in enumerate(split_indices):
        df = df_mapping[indices.min(): indices.max()]

        job = Job(stream_runner.run, [jar, xml, df, aux_source_path, '{}mb'.format(0.9*vmem)],
                  queue=queue, walltime=walltime, engine=engine,
                  mem_free='{}mb'.format(vmem))
        jobs.append(job)

    return jobs




@click.command()
@click.argument('file_list', type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True) )
@click.argument('jar', type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True) )
@click.argument('xml', type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True) )
@click.argument('aux_source', type=click.Path(exists=True, dir_okay=True, file_okay=True, readable=True) )
@click.argument('out', type=click.Path(exists=False, dir_okay=False, file_okay=True, readable=True) )
@click.option('--queue', help='Name of the queue you want to send jobs to.', default='short')
@click.option('--walltime', help='Estimated maximum walltime of your job in format hh:mm:ss.', default='02:00:00')
@click.option('--engine', help='Name of the grid engine used by the cluster.', type=click.Choice(['PBS', 'SGE',]), default='SGE')
@click.option('--num_jobs', help='Number of jobs to start on the cluster.', default='4', type=click.INT)
@click.option('--vmem', help='Amount of memory to use per node in MB.', default='400', type=click.INT)
@click.option("--log_level", type=click.Choice(['INFO', 'DEBUG', 'WARN']), help='increase output verbosity', default='INFO')
@click.option('--port', help='The port through which to communicate with the JobMonitor', default=12856, type=int)
@click.option('--local', default=False,is_flag=True,   help='Flag indicating whether jobs should be executed localy .')
def main(file_list, jar, xml, aux_source, out, queue, walltime, engine, num_jobs, vmem, log_level, port, local):
    '''
    Specify the path to a .json file as created by the fetch_runs.py script via the FILE_LIST argument.
    num_jobs will be created and executed on the cluster.
    '''
    level=logging.INFO
    if log_level is 'DEBUG':
        level = logging.DEBUG
    elif log_level is 'WARN':
        level = logging.WARN
    elif log_level is 'INFO':
        level = logging.INFO

    logging.captureWarnings(True)
    logging.basicConfig(format=('%(asctime)s - %(name)s - %(levelname)s - ' +  '%(message)s'), level=level)

    df = pd.read_json(file_list)
    logger.info("Read {} runs from .json file".format(len(df)))

    #get data files
    jarpath = path.abspath(jar)
    xmlpath = path.abspath(xml)
    aux_source_path = path.abspath(aux_source)
    outpath = path.abspath(out)
    output_directory = path.dirname(outpath)
    #create dir if it doesnt exist
    os.makedirs(output_directory, exist_ok=True)
    logger.info("Writing output and temporary data  to {}".format(output_directory))


    job_list = make_jobs(jarpath, xmlpath, aux_source_path, output_directory, df,  engine, queue, vmem, num_jobs, walltime)
    job_outputs = gridmap.process_jobs(job_list, max_processes=num_jobs, local=local)
    erna.collect_output(job_outputs, out, df)

if __name__ == "__main__":
    main()
