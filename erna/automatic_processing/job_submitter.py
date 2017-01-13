from threading import Thread, Event
import logging
import peewee
import os

from .database import ProcessingState, requires_database_connection
from .database_utils import count_jobs, get_pending_jobs
from .qsub import submit_job, get_current_jobs

log = logging.getLogger(__name__)


class JobSubmitter(Thread):

    def __init__(
            self,
            interval,
            max_queued_jobs,
            data_directory,
            host,
            port,
            group,
            mail_address=None,
            mail_settings='a',
            ):
        '''
        Parametrs
        ----------
        interval: int
            number of seconds to wait between submissions
        max_queued_jobs: int
            Maximum number of jobs in the queue of the grid engine
            No new jobs are submitted if the number of jobs in the queue is
            higher than this value
        data_directory: str
            patch to the basic structure for erna. Logfiles, jars, xmls and
            analysis output are stored in subdirectories to this directory.
        host: str
            hostname of the submitter node
        port: int
            port for the zmq communication
        mail_address: str
            mail address to receive the grid engines emails
        mail_setting: str
            mail setting for the grid engine
        '''
        super().__init__()
        self.event = Event()
        self.interval = interval
        self.max_queued_jobs = max_queued_jobs
        self.data_directory = data_directory
        self.host = host
        self.port = port
        self.group = group
        self.mail_settings = mail_settings
        self.mail_address = mail_address

    def run(self):
        while not self.event.is_set():
            try:
                self.process_pending_jobs()
            except peewee.OperationalError:
                log.warning('Lost database connection')
            except:
                log.exception('Error during submission')
            self.event.wait(self.interval)

    def terminate(self):
        self.event.set()

    @requires_database_connection
    def process_pending_jobs(self):
        '''
        Fetches pending runs from the processing database
        and submits them using qsub if not to many jobs are running already.
        '''
        current_jobs = get_current_jobs()
        running_jobs = current_jobs.query('state == "running"')
        queued_jobs = current_jobs.query('state == "pending"')
        log.debug('Currently {} jobs running'.format(len(running_jobs)))
        log.debug('Currently {} jobs queued'.format(len(queued_jobs)))
        log.debug('Currently {} pending jobs in database'.format(
            count_jobs(state='inserted')
        ))

        if len(queued_jobs) < self.max_queued_jobs:
            pending_jobs = get_pending_jobs(limit=self.max_queued_jobs - len(queued_jobs))

            for job in pending_jobs:
                if self.event.is_set():
                    break
                try:
                    submit_job(
                        job,
                        output_base_dir=os.path.join(self.data_directory, 'fact-tools'),
                        data_dir=self.data_directory,
                        mail_address=self.mail_address,
                        mail_settings=self.mail_settings,
                        submitter_host=self.host,
                        submitter_port=self.port,
                        group=self.group,
                    )
                    log.info('New job with id {} queued'.format(job.id))
                except:
                    log.exception('Could not submit job')
                    job.status = ProcessingState.get(description='error')
                    job.save()
