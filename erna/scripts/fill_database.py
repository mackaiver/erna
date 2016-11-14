import pandas as pd
from fact.credentials import create_factdb_engine
from dateutil import parser as date_parser
import click
import yaml

from erna.database import database, init_database, fill_data_runs, fill_drs_runs


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
@click.option('--config', '-c', help='yaml config file with datebase credentials')
def main(start, end, config):
    with open(config or 'config.yaml') as f:
        db_config = yaml.safe_load(f)

    database.init(**db_config)
    database.connect()
    init_database(drop=False)

    runs = pd.read_sql_query(
        query.format(
            columns=', '.join(['fNight', 'fRunID', 'fDrsStep', 'fRunTypeKey']),
            start=start,
            end=end,
        ),
        create_factdb_engine(),
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
