from peewee import (
    Model, CharField, IntegerField, BooleanField,
    ForeignKeyField, FixedCharField, TextField, MySQLDatabase
)
import os
import logging
import wrapt

from .utils import parse_path
from .custom_fields import NightField, LongBlobField


__all__ = [
    'RawDataFile', 'DrsFile',
    'Jar', 'XML', 'Job', 'Queue',
    'ProcessingState',
    'database', 'setup_database',
]


log = logging.getLogger(__name__)

PROCESSING_STATES = [
    'inserted',
    'queued',
    'running',
    'success',
    'failed',
    'walltime_exceeded',
]

WALLTIMES = {
    'fact_short': 60 * 60,
    'fact_medium': 6 * 60 * 60,
    'fact_long': 7 * 24 * 60 * 60,
}

database = MySQLDatabase(None, fields={
    'night': 'INTEGER',
    'longblob': 'LONGBLOB',
})


def setup_database(database, drop=False):
    '''
    Initiliaze all tables in the databse
    If drop is True, drop all tables before recreating them.
    '''
    tables = [
        RawDataFile,
        DrsFile,
        Jar,
        XML,
        Job,
        ProcessingState,
    ]
    if drop is True:
        log.info('dropping tables')
        database.drop_tables(tables, safe=True, cascade=True)

    database.create_tables(tables, safe=True)

    for description in PROCESSING_STATES:
        ProcessingState.get_or_create(description=description)

    for name, walltime in WALLTIMES.items():
        Queue.get_or_create(name=name, walltime=walltime)


class File(Model):
    night = NightField()
    run_id = IntegerField()
    available = BooleanField(null=True)

    class Meta:
        database = database
        indexes = ((('night', 'run_id'), True), )  # unique index

    def get_path(self):
        return os.path.join(
            '/fact/raw',
            str(self.night.year),
            '{:02d}'.format(self.night.month),
            '{:02d}'.format(self.night.day),
            self.basename
        )

    @classmethod
    def get_or_create_from_path(cls, path):
        ''' Selects either an existing database entry or returns a new instance '''
        night, run_id = parse_path(path)
        return cls.get_or_create(night=night, run_id=run_id)

    def __repr__(self):
        return self.basename


class RawDataFile(File):
    @property
    def basename(self):
        return '{:%Y%m%d}_{:03d}.fits.fz'.format(self.night, self.run_id)

    class Meta:
        database = database
        db_table = 'raw_data_files'


class DrsFile(File):
    @property
    def basename(self):
        return '{:%Y%m%d}_{:03d}.drs.fits.gz'.format(self.night, self.run_id)

    class Meta:
        database = database
        db_table = 'drs_files'


class Jar(Model):
    version = CharField(unique=True)
    data = LongBlobField()

    class Meta:
        database = database
        db_table = 'jars'


class XML(Model):
    name = CharField()
    content = TextField()
    comment = TextField()
    jar = ForeignKeyField(Jar)

    class Meta:
        database = database
        db_table = 'xmls'

        indexes = (
            (('name', 'jar'), True),  # unique constraint
        )


class ProcessingState(Model):
    description = CharField(unique=True)

    class Meta:
        database = database
        db_table = 'processing_states'

    def __repr__(self):
        return '{}'.format(self.description)


class Queue(Model):
    name = CharField(unique=True)
    walltime = IntegerField()

    class Meta:
        database = database
        db_table = 'queues'


class Job(Model):
    raw_data_file = ForeignKeyField(RawDataFile, related_name='raw_data_file')
    drs_file = ForeignKeyField(DrsFile, related_name='drs_file')
    jar = ForeignKeyField(Jar, related_name='jar')
    result_file = CharField(null=True)
    status = ForeignKeyField(ProcessingState, related_name='status')
    priority = IntegerField(default=5)
    xml = ForeignKeyField(XML)
    md5hash = FixedCharField(32, null=True)
    queue = ForeignKeyField(Queue, related_name='queue')

    class Meta:
        database = database
        db_table = 'jobs'
        indexes = (
            (('raw_data_file', 'jar', 'xml'), True),  # unique constraint
        )

MODELS = [RawDataFile, DrsFile, Jar, XML, Job, ProcessingState, Queue]


@wrapt.decorator
def requires_database_connection(wrapped, instance, args, kwargs):
    database.connect()
    return wrapped(*args, **kwargs)
