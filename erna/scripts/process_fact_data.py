import logging
import click

import numpy as np
import sqlalchemy
import os

import gridmap
from gridmap import Job

import erna
from erna import stream_runner
from erna import stream_runner_local_output

import erna.datacheck_conditions as dcc

logger = logging.getLogger(__name__)


def make_jobs(jar, xml, db_path, output_directory, df_mapping,  engine, queue, vmem, num_runs_per_bunch, walltime, local=False):
    jobs = []
    # create job objects
    df_mapping["bunch_index"]= np.arange(len(df_mapping)) // num_runs_per_bunch
    for num, df in df_mapping.groupby("bunch_index"):
        df=df.copy()
        df["bunch_index"] = num
        file = output_directory+"/output"+str(num)+".bin"
        if local:
            job = Job(stream_runner_local_output.run, [jar, xml, df, file, db_path], queue=queue, walltime=walltime, engine=engine, mem_free='{}mb'.format(vmem))
        else:
            job = Job(stream_runner.run, [jar, xml, df, db_path], queue=queue, walltime=walltime, engine=engine, mem_free='{}mb'.format(vmem))
        jobs.append(job)

    return jobs


@click.command()
@click.argument('earliest_night')
@click.argument('latest_night' )
@click.argument('data_dir', type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True) )
@click.argument('jar', type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True) )
@click.argument('xml', type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True) )
@click.argument('db', type=click.Path(exists=True, dir_okay=False, file_okay=True, readable=True) )
@click.argument('out', type=click.Path(exists=False, dir_okay=False, file_okay=True, readable=True) )
@click.option('--queue', help='Name of the queue you want to send jobs to.', default='short')
@click.option('--walltime', help='Estimated maximum walltime of your job in format hh:mm:ss.', default='02:00:00')
@click.option('--engine', help='Name of the grid engine used by the cluster.', type=click.Choice(['PBS', 'SGE',]), default='SGE')
@click.option('--num_runs', help='Number of num runs per bunch to start on the cluster.', default='4', type=click.INT)
@click.option('--vmem', help='Amount of memory to use per node in MB.', default='10000', type=click.INT)
@click.option('--log_level', type=click.Choice(['INFO', 'DEBUG', 'WARN']), help='increase output verbosity', default='INFO')
@click.option('--port', help='The port through which to communicate with the JobMonitor', default=12856, type=int)
@click.option('--source',  help='Name of the source to analyze. e.g Crab', default='Crab')
@click.option('--conditions',  help='Name of the data conditions as given in datacheck_conditions.py e.g std', default='standard')
@click.option('--max_delta_t', default=30,  help='Maximum time difference (minutes) allowed between drs and data files.', type=click.INT)
@click.option('--local', default=False,is_flag=True,   help='Flag indicating whether jobs should be executed localy .')
@click.option('--local_output', default=False,is_flag=True,
              help='Flag indicating whether jobs write their output localy'
              + 'to disk without gathering everything in the mother'
              + 'process. In this case the output file only contains a'
              + 'summary oth the processed jobs. The data ouput will be'
              + 'inseparate files',
              show_default=True)
@click.password_option(help='password to read from the always awesome RunDB', confirmation_prompt=False)
def main(earliest_night, latest_night, data_dir, jar, xml, db, out, queue, walltime, engine, num_runs, vmem, log_level, port, source, conditions, max_delta_t, local, local_output, password):

    level=logging.INFO
    if log_level is 'DEBUG':
        level = logging.DEBUG
    elif log_level is 'WARN':
        level = logging.WARN
    elif log_level is 'INFO':
        level = logging.INFO

    logging.captureWarnings(True)
    logging.basicConfig(format=('%(asctime)s - %(name)s - %(levelname)s - ' +  '%(message)s'), level=level)

    jarpath = os.path.abspath(jar)
    xmlpath =os. path.abspath(xml)
    outpath = os.path.abspath(out)
    erna.ensure_output(out)
    db_path = os.path.abspath(db)
    output_directory = os.path.dirname(outpath)
    #create dir if it doesnt exist #TODO check: should already been done by enra.ensure_output
    os.makedirs(output_directory, exist_ok=True)
    logger.info("Writing output data  to {}".format(out))
    factdb = sqlalchemy.create_engine("mysql+pymysql://factread:{}@129.194.168.95/factdata".format(password))
    data_conditions=dcc.conditions[conditions]
    df_runs = erna.load(earliest_night, latest_night, data_dir, source_name=source, timedelta_in_minutes=max_delta_t, factdb=factdb, data_conditions=data_conditions)

    logger.info("Would process {} jobs with {} runs per job".format(len(df_runs)//num_runs, num_runs))
    click.confirm('Do you want to continue processing and start jobs?', abort=True)

    job_list = make_jobs(jarpath, xmlpath, db_path, output_directory, df_runs,  engine, queue, vmem, num_runs, walltime, local_output)
    job_outputs = gridmap.process_jobs(job_list, max_processes=len(job_list), local=local)
    if not local_output:
        erna.collect_output(job_outputs, out, df_runs)

if __name__ == "__main__":
    main()
