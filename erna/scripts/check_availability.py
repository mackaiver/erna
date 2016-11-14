import os
from os.path import isfile
import socket
import click
import yaml
import logging
import pandas as pd
from dateutil.parser import parse as parse_date
import datetime
from sqlalchemy import create_engine
from tqdm import tqdm

from ..database import rawdirs, RawDataFile, DrsFile, database, night_int_to_date

log = logging.getLogger()
log.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(fmt='%(asctime)s|%(levelname)s|%(name)s|%(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

db_specification = 'mysql+pymysql://{user}:{password}@{host}/{database}'


run_query = '''
SELECT fNight AS night, fRunID AS run_id, fRunTypeKey AS run_type, fDrsStep AS drs_step
FROM RunInfo
WHERE (fNight >= {start:%Y%m%d} and fNight <= {end:%Y%m%d});
'''


def check_availability(run, basedir='/fact/raw', location='isdc'):
    log.debug('Checking run {:%Y%m%d}_{:03d}'.format(run.night, run.run_id))

    basename = os.path.join(
        basedir, str(run.night.year), '{:02d}'.format(run.night.month),
        '{:02d}'.format(run.night.day), '{:%Y%m%d}_{:03d}'.format(run.night, run.run_id)
    )
    log.debug('Basename: {}'.format(basename))

    if run.run_type == 1:
        f = RawDataFile.select_night_runid(run.night, run.run_id)
        available = isfile(basename + '.fits.fz') or isfile(basename + '.fits.gz')
        log.debug('Available: {}'.format(available))

        if location == 'isdc':
            f.available_isdc = available
            f.save(only=[
                RawDataFile.night, RawDataFile.run_id, RawDataFile.available_isdc
            ])
        elif location == 'dortmund':
            f.available_dortmund = available
            f.save(only=[
                RawDataFile.night, RawDataFile.run_id, RawDataFile.available_dortmund
            ])

    elif run.run_type == 2 and run.drs_step == 2:
        log.debug('is a drs file')
        f = DrsFile.select_night_runid(run.night, run.run_id)
        available = isfile(basename + '.drs.fits.gz')
        log.debug('Available: {}'.format(available))
        if location == 'isdc':
            f.available_isdc = available
            f.save(only=[
                DrsFile.night, DrsFile.run_id, DrsFile.available_isdc
            ])
        if location == 'dortmund':
            f.available_dortmund = available
            f.save(only=[
                DrsFile.night, DrsFile.run_id, DrsFile.available_dortmund
            ])
    else:
        log.debug('Neither drs nor data file')


@click.command()
@click.option('--year', help='The year to update (default all)')
@click.option('--month', help='The month to update (default all)')
@click.option('--day', help='The day to update (default all)')
@click.option('--config', '-c', help='Yaml file containing database credentials')
@click.option('--verbose', '-v', help='Set logging level to DEBUG', is_flag=True)
@click.option('--start', type=parse_date, default=str(datetime.date(2011, 10, 1)))
@click.option('--end', type=parse_date, default=str(datetime.date.today()))
def main(year, month, day, config, verbose, start, end):

    if verbose:
        log.setLevel(logging.DEBUG)
        logging.captureWarnings(True)

    with open(config or 'config.yaml') as f:
        log.debug('Reading config file {}'.format(f.name))
        config = yaml.safe_load(f)

    log.debug('Connecting to database')
    database.init(**config['processing_database'])
    database.connect()
    log.info('Database connection established')

    if 'isdc' in socket.gethostname():
        log.info('Assuming ISDC')
        basedir = rawdirs['isdc']
        location = 'isdc'
        config['fact_database']['host'] = 'lp-fact'
    else:
        log.info('Assuming PHIDO')
        basedir = rawdirs['phido']
        location = 'dortmund'

    fact_db = create_engine(db_specification.format(**config['fact_database']))
    runs = pd.read_sql_query(run_query.format(start=start, end=end), fact_db)
    runs['night'] = runs['night'].apply(night_int_to_date)

    log.info('basedir is: {}'.format(basedir))

    runs = runs.query('run_type == 1 or (run_type == 2 and drs_step == 2)')

    log.info('Checking data files')

    for run in tqdm(runs.itertuples(), total=len(runs)):
        check_availability(run, basedir=basedir, location=location)

    database.close()


if __name__ == '__main__':
    main()
