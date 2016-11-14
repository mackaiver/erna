from peewee import (
    Model, MySQLDatabase, CharField, IntegerField, BooleanField,
    ForeignKeyField, SqliteDatabase, DateField, Field, FixedCharField
)
from datetime import date
import os
import re
import logging

log = logging.getLogger(__name__)

__all__ = ['RawDataFile', 'DrsFile', 'FactToolsRun']


datafile_re = re.compile(r'(?:.*/)?([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{3})\.fits(?:\.[fg]z)?$')
drsfile_re = re.compile(r'(?:.*/)?([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{3})\.drs\.fits(?:\.gz)?$')


def night_int_to_date(night):
    return date(night // 10000, (night % 10000) // 100, night % 100)


def parse_path(path):
    match = datafile_re.search(path)
    if match is None:
        match = drsfile_re.search(path)
    if match is None:
        raise IOError('File seems not to be a drs or data file')

    year, month, day, run_id = map(int, match.groups())

    return date(year, month, day), run_id


class NightField(Field):
    db_field = 'night'

    def db_value(self, value):
        log.debug('Converting date to night integer')
        return 10000 * value.year + 100 * value.month + value.day

    def python_value(self, value):
        log.debug('Converting night integer to date ')
        return night_int_to_date(value)


database = MySQLDatabase(None, fields={'night': 'integer'})  # specify database at runtime


rawdirs = {
    'isdc': '/fact/raw',
    'phido': '/fhgfs/groups/app/fact/raw'
}


def init_database(drop=False):
    if drop is True:
        log.info('dropping tables')
        database.drop_tables(
            [RawDataFile, DrsFile, FactToolsRun], safe=True, cascade=True
        )
    database.create_tables([RawDataFile, DrsFile, FactToolsRun], safe=True)


class File(Model):
    night = NightField()
    run_id = IntegerField()
    available_dortmund = BooleanField(null=True)
    available_isdc = BooleanField(null=True)

    class Meta:
        database = database
        indexes = ((('night', 'run_id'), True), )  # unique index

    def get_path(self, location='isdc'):
        return os.path.join(
            rawdirs[location],
            str(self.night.year),
            '{:02d}'.format(self.night.month),
            '{:02d}'.format(self.night.day),
            self.basename
        )

    @classmethod
    def select_from_path(cls, path):
        ''' Selects either an existing database entry or returns a new instance '''
        log.debug('In from_path')
        night, run_id = parse_path(path)
        return cls.select_night_runid(night, run_id)

    @classmethod
    def select_night_runid(cls, night, run_id):
        ''' Selects either an existing database entry or returns a new instance '''
        try:
            run = cls.select().where((cls.night == night) & (cls.run_id == run_id)).get()
            log.debug('returnig existing instance')
            return run
        except cls.DoesNotExist:
            log.debug('returnig new instance')
            return cls(night=night, run_id=run_id)

    def __repr__(self):
        return self.basename


class RawDataFile(File):
    @property
    def basename(self):
        return '{:%Y%m%d}_{:03d}.fits.fz'.format(self.night, self.run_id)


class DrsFile(File):
    @property
    def basename(self):
        return '{:%Y%m%d}_{:03d}.drs.fits.gz'.format(self.night, self.run_id)


class FactToolsRun(Model):
    raw_data_id = ForeignKeyField(RawDataFile, related_name='fact_tools_runs')
    drs_file_id = ForeignKeyField(DrsFile, related_name='fact_tools_runs')
    fact_tools_version = CharField()
    result_file = CharField()
    status = CharField()
    md5hash = FixedCharField(null=True)

    class Meta:
        database = database


def fill_data_runs(df, database):
    df.rename(columns={'fNight': 'night', 'fRunID': 'run_id'}, inplace=True)
    df.drop(['fDrsStep', 'fRunTypeKey'], axis=1, inplace=True)
    with database.atomic():
        RawDataFile.insert_many(df.to_dict(orient='records')).upsert().execute()


def fill_drs_runs(df, database):
    df.rename(columns={'fNight': 'night', 'fRunID': 'run_id'}, inplace=True)
    df.drop(['fDrsStep', 'fRunTypeKey'], axis=1, inplace=True)
    with database.atomic():
        DrsFile.insert_many(df.to_dict(orient='records')).upsert().execute()
