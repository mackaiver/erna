from .utils import load_config
import pandas as pd


default_columns = (
    'fNight AS night',
    'fRunID AS run_id',
    'fSourceName AS source',
    'fOnTime AS ontime',
    'fZenithDistanceMean AS zenith',
)


query_template_data = '''
SELECT {columns}
FROM RunInfo
JOIN Source
ON RunInfo.fSourceKey = Source.fSourceKey
JOIN RunType
ON RunInfo.fRunTypeKey = RunType.fRunTypeKey
WHERE {conditions}
;
'''

query_template_drs = '''
SELECT {columns}
FROM RunInfo
WHERE
    fDrsStep = 2
    AND fRoi = 300
    AND fRunTypeKey = 2
    AND {conditions}
;
'''


def get_runs(engine, conditions=None, columns=default_columns):

    if conditions is None:
        conditions = '1'
    else:
        conditions = ' AND '.join(conditions)

    query = query_template_data.format(
        columns=','.join(columns),
        conditions=conditions
    )

    return pd.read_sql_query(query, engine)


def get_drs_runs(engine, conditions, columns=('fNight', 'fRunID')):
    if conditions is None:
        conditions = '1'
    else:
        conditions = ' AND '.join(conditions)

    query = query_template_drs.format(
        columns=','.join(columns),
        conditions=conditions
    )

    return pd.read_sql_query(query, engine)
