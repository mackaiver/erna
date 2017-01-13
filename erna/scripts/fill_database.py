import pandas as pd
from dateutil import parser as date_parser
import click

from ..automatic_processing import fill_data_runs, fill_drs_runs
from ..automatic_processing.database import database, setup_database
from ..utils import load_config
from ..utils import create_mysql_engine


def parse_date(date):
    d = date_parser.parse(date)
    return 10000 * d.year + 100 * d.month + d.day


query = '''
SELECT {columns}
FROM RunInfo
WHERE
    fNight >= {start}
    AND fNight < {end}
    AND (
        fRunTypeKey = 1 OR (fDrsStep = 2 AND fRunTypeKey = 2)
    )
;
'''


@click.command()
@click.argument('start', type=parse_date)
@click.argument('end', type=parse_date)
@click.option('--config', '-c', help='yaml config file with database credentials')
def main(start, end, config):
    '''
    Fill RawDataFile and DrsFile tables from the FACT RunInfo database
    from START to END.
    '''

    config = load_config(config)

    database.init(**config['processing_database'])
    database.connect()
    setup_database(database, drop=False)

    runs = pd.read_sql_query(
        query.format(
            columns=', '.join(['fNight', 'fRunID', 'fDrsStep', 'fRunTypeKey']),
            start=start,
            end=end,
        ),
        create_mysql_engine(**config['fact_database']),
    )
    runs['fNight'] = pd.to_datetime(runs.fNight.astype(str), format='%Y%m%d')

    for runtype, df in runs.groupby('fRunTypeKey'):
        if runtype == 1:
            fill_data_runs(df, database=database)
        elif runtype == 2:
            fill_drs_runs(df, database=database)

    database.close()


if __name__ == '__main__':
    main()
