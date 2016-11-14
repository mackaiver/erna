import numpy as np
import os
import pandas as pd
import subprocess
import logging
logger = logging.getLogger(__name__)


def get_qstat_as_df():
    """Get the current users output of qstat as a DataFrame.
    """
    user = os.environ.get("USER")
    try:
        ret = subprocess.Popen(["qstat", "-u", str(user)],
                               stdout=subprocess.PIPE)
        df = pd.read_csv(ret.stdout, delimiter="\s+")
        # drop the first line since it is just one long line
        df = df.drop(df.index[0]).copy()
        # convert objects to numeric otherwise numbers are strings
        df["JOBID"] = pd.to_numeric(df["job-ID"], errors='coerce')
        # df.set_index("JOBID")
        df = df.drop('job-ID', 1)

    except ValueError:
        logger.exception("No jobs in queues for user {}".format(user))
        df = pd.DataFrame()
    return df


def get_finished_jobs(job_ids):
    """Get a list of finished job ids for the given list of jobs

    Keyword arguments:

    job_ids     -- list of lobs that shall be checked
    """
    data = get_qstat_as_df()
    finished_jobs = []

    if len(data) == 0:
        return job_ids

    ids_in_data = data[data["JOBID"].isin(job_ids)]
    finished_jobs = np.setdiff1d(job_ids, ids_in_data["JOBID"])

    return np.array(finished_jobs)


def get_running_jobs(job_ids=None, queue=None):
    """Get a DataFrame with the qstat output of running jobs of the current user.
    optionally a certain list of job ids and/or a certain queue can be given

    Keyword arguments:

    job_ids     -- list of lobs that shall be checked
    queue       -- name of the queue
    """
    data = get_qstat_as_df()
    if len(data) == 0:
        return data
    if queue is not None:
        data = data[data["queue"].str.contains(str(queue))]
    if job_ids is not None:
        data = data[data["JOBID"].isin(job_ids)]
    return data[data["state"] == "r"]


def get_pending_jobs(job_ids=None):
    """Get a DataFrame with the qstat output of pending jobs of the current user.
    optionally a certain list of job ids and/or a certain queue can be given

    Keyword arguments:

    job_ids     -- list of lobs that shall be checked
    queue       -- name of the queue
    """
    data = get_qstat_as_df()
    if len(data) == 0:
        return data
    #     data = data[data["queue"].str.contains(str(queue))].copy()
    if job_ids is not None:
        data = data[data["JOBID"].isin(job_ids)]
    return data[data["state"] == "qw"]


def generate_qsub_command(name, queue, jar, xml, inputfile, outputfile, dbpath,
                          mail_address, mail_setting, stdout, stderr, engine,
                          script):
    command_template = []
    command_template.append("qsub")
    command_template.append("-N {name}")
    command_template.append("-q {queue}")
    command_template.append("-M {mail_address}")
    command_template.append("-m {mail_setting}")
    command_template.append("-v {env}")
    if engine == "SGE":
        command_template.append("-b yes")
    command_template.append("-o {stdout}")
    command_template.append("-e {stderr}")
    command_template.append("{script}")

    command_template = " ".join(command_template)

    env = []
    env.append("INPUTFILE={0}".format(inputfile))
    env.append("JARFILE={0}".format(jar))
    env.append("XMLFILE={0}".format(xml))
    env.append("OUTPUTFILE={0}".format(outputfile))
    env.append("DBPATH={0}".format(dbpath))
    env.append("JOBNAME={0}".format(name))
    env.append("PATH={0}".format(os.environ.get("PATH")))
    env = ",".join(env)

    settings = {
        "name": name,
        "queue": queue,
        "mail_address": mail_address,
        "mail_setting": mail_setting,
        "env": env,
        "stdout": stdout,
        "stderr": stderr,
        "script": script,
    }

    return command_template.format(**settings)


def submit_qsub_jobs(jobname, jar, xml, db_path, df_mapping,  engine, queue,
                     vmem, num_jobs_per_bunch, walltime, dbpath, mail_setting):
    jobs = []
    # create job objects
    # split_indices = np.array_split(np.arange(len(df_mapping)), num_jobs)
    df_mapping["bunch_index"] = np.arange(len(df_mapping)) // num_jobs_per_bunch

    tempfolder = os.environ.get('DEFAULT_TEMP_DIR')
    mail_address = os.environ.get('ERROR_MAIL_RECIPIENT')

    jobname = "_".join(jobname.split())

    for num, group in df_mapping.groupby("bunch_index"):
        df_jobs = group.copy()
        job_name = "{}_{}".format(jobname, num)

        stdout_file = os.path.join(tempfolder, job_name + ".o")
        stderr_file = os.path.join(tempfolder, job_name + ".e")
        input_path = os.path.join(tempfolder, job_name + ".json")
        output_path = os.path.join(tempfolder, job_name + "_out")

        group.to_json(input_path, orient='records', date_format='epoch')

        command = generate_qsub_command(name=job_name, queue=queue, jar=jar,
                                        xml=xml, inputfile=input_path,
                                        outputfile=output_path, dbpath=dbpath,
                                        mail_address=mail_address,
                                        mail_setting=mail_setting,
                                        stdout=stdout_file, stderr=stderr_file,
                                        engine=engine,
                                        script="facttools_executer")

        return_code = subprocess.check_output(command, shell=True)
        logger.info(return_code.decode())

        if engine == "SGE":
            df_jobs["JOBID"] = int(str(return_code.decode()).split(" ")[2])
        if engine == "PBS":
            df_jobs["JOBID"] = int(str(return_code.decode()).split(".")[0])

        df_jobs["output_path"] = output_path
        df_jobs["bunch_index"] = num
        df_jobs["command"] = command
        df_jobs["fact_tools"] = os.path.basename(jar)
        df_jobs["xml"] = os.path.basename(xml)
        jobs.append(df_jobs)
        # if num>=1:
        #     break
    if len(jobs) == 0:
        return pd.DataFrame()

    return pd.concat(jobs)
