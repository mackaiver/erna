import logging
import pandas as pd
import os
import numpy as np
import datetime
import json
import pkg_resources
from datetime import timedelta

from . import datacheck_conditions as dcc
from .datacheck import get_runs, get_drs_runs

logger = logging.getLogger(__name__)


def build_path(row, path_to_data, extension):
    night = str(row.NIGHT)
    year = night[0:4]
    month = night[4:6]
    day = night[6:8]
    return os.path.join(path_to_data, year, month, day, row.filename + extension)


def build_filename(night, run_id):
    return night.astype(str) + '_' + run_id.map('{:03d}'.format)


def mc_drs_file():
    '''
    return path to the drs file used for monte carlo files
    '''
    drs_path = pkg_resources.resource_filename(
        __name__, 'resources/mc_drs_constants.drs.fits.gz'
    )
    return drs_path


def ensure_output(output_path):
    '''
    Make sure the output file does not exist yet.
    Create directorie to new output file if necessary
    '''
    if os.path.exists(output_path):
        raise FileExistsError('The output file already exists.')
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def collect_output(job_outputs, output_path, df_started_runs=None, **kwargs):
    '''
    Collects the output from the list of job_outputs and merges them into a dataframe.
    The Dataframe will then be written to a file as specified by the output_path.
    The datatframe df_started_runs is joined with the job outputs to get the real ontime.
    '''
    logger.info("Concatenating results from each job and writing result to {}".format(output_path))
    frames = [f for f in job_outputs if isinstance(f, type(pd.DataFrame()))]

    if len(frames) != len(job_outputs):
        logger.warn("Only {} jobs returned a proper DataFrame.".format(len(frames)))

    if len(frames) == 0:
        return

    df_returned_data = pd.concat(frames, ignore_index=True)
    logger.info("There are a total of {} events in the result".format(len(df_returned_data)))

    if df_started_runs is not None:
        df_merged = pd.merge(df_started_runs, df_returned_data, on=['NIGHT','RUNID'], how='inner')
        total_on_time_in_seconds = df_merged.on_time.sum()
        logger.info("Effective on time: {}. Thats {} hours.".format(datetime.timedelta(seconds=total_on_time_in_seconds), total_on_time_in_seconds/3600))

        difference = pd.Index(df_started_runs).difference(pd.Index(df_returned_data))

        df_returned_data.total_on_time_in_seconds = total_on_time_in_seconds
        df_returned_data.failed_jobs=difference

    name, extension = os.path.splitext(output_path)
    if extension not in ['.json', '.h5', '.hdf5', '.hdf' , '.csv']:
        logger.warn("Did not recognize file extension {}. Writing to JSON".format(extension))
        df_returned_data.to_json(output_path, orient='records', date_format='epoch', **kwargs )
    elif extension == '.json':
        logger.info("Writing JSON to {}".format(output_path))
        df_returned_data.to_json(output_path, orient='records', date_format='epoch', **kwargs )
    elif extension in ['.h5', '.hdf','.hdf5']:
        logger.info("Writing HDF5 to {}".format(output_path))
        df_returned_data.to_hdf(output_path, 'data', mode='w', **kwargs)
    elif extension == '.csv':
        logger.info("Writing CSV to {}".format(output_path))
        df_returned_data.to_csv(output_path, **kwargs)


def load(
        earliest_night,
        latest_night,
        path_to_data,
        factdb,
        source_name="Crab",
        timedelta_in_minutes=30,
        data_conditions=dcc.conditions["standard"]
        ):
    '''
    Given the earliest and latest night to fetch as a factnight string (as in 20141024)
    this method returns a DataFrame containing the paths to data files
    and their correpsonding .drs files.
    The maximum time difference between the data and drs files is
    specified by the timedelta_in_minutes parameter.

    Returns None if no files can be found.
    '''

    logger.debug("Table names in DB: ")
    logger.debug(factdb.table_names())

    if len(factdb.table_names()) > 0:
        logger.info("Connected to Database.")

    logger.info("Reading Data from DataBase from {} to {} for source: {}".format(
        earliest_night, latest_night, source_name
    ))

    conditions = [
        'fNight >= {}'.format(earliest_night),
        'fNight <= {}'.format(latest_night),
        'fSourceName = "{}"'.format(source_name),
    ]
    conditions.extend(data_conditions)
    logger.info('Querying data with conditions: {}'.format(' AND '.join(conditions)))
    data = get_runs(
        factdb,
        conditions=conditions,
        columns=(
            'fNight AS NIGHT', 'fRunID AS RUNID',
            'fRunStart', 'fRunStop',
            'fOnTime', 'fEffectiveOn',
        ),
    )

    # now lets get all drs runs
    drs_conditions = [
        'fNight >= {}'.format(earliest_night),
        'fNight <= {}'.format(latest_night),
    ]

    drs_data = get_drs_runs(
        factdb, conditions=drs_conditions,
        columns=('fNight AS NIGHT', 'fRunID AS RUNID', 'fRunStart', 'fRunStop'),
    )

    if len(data) == 0 or len(drs_data) == 0:
        logger.error('No data or drs files found that adhere to the specified query.')
        return None

    logger.info("Got {} data runs and {} runs".format(len(data), len(drs_data)))

    # the timestamp should be unique for each observation.
    # No two observations start at the same time
    data.set_index("fRunStart", inplace=True)
    drs_data.set_index("fRunStart", inplace=True)
    # sorting data by their timestamp.
    data = data.sort_index()
    drs_data = drs_data.sort_index()

    # write filenames
    data["filename"] = build_filename(data.NIGHT, data.RUNID)
    drs_data["filename"] = build_filename(drs_data.NIGHT, drs_data.RUNID)

    # write path TODO: file ending? is everything in fz?
    data["path"] = data.apply(build_path, axis=1, path_to_data=path_to_data, extension='.fits.fz')
    drs_data["path"] = drs_data.apply(build_path, axis=1, path_to_data=path_to_data, extension='.drs.fits.gz')

    # reindex the drs table using the index of the data table.
    # There are always more data runs than drs run in the db.
    # hence missing rows have to be filled either forward or backwards
    earlier_drs_entries = drs_data.reindex(data.index, method="ffill")
    later_drs_entries = drs_data.reindex(data.index, method="backfill")

    # when backfilling the drs obeservations the last rows might be invalid and contain nans.
    # We cannot drop them becasue the tables have to have the same length.
    # in that case simply fill them up.
    earlier_drs_entries["deltaT"] = np.abs(earlier_drs_entries.fRunStop - data.fRunStop)
    later_drs_entries["deltaT"] = np.abs(later_drs_entries.fRunStop - data.fRunStop).fillna(axis='index', method='ffill')
    d_later = later_drs_entries[later_drs_entries.deltaT < earlier_drs_entries.deltaT]
    d_early = earlier_drs_entries[later_drs_entries.deltaT >= earlier_drs_entries.deltaT]

    closest_drs_entries = pd.concat([d_early, d_later])
    closest_drs_entries = closest_drs_entries[closest_drs_entries.deltaT < timedelta(minutes = timedelta_in_minutes)]

    mapping = pd.concat([
        closest_drs_entries.filename,
        closest_drs_entries.path,
        data.path,
        closest_drs_entries.deltaT,
        data.fOnTime, data.fEffectiveOn,
        data.NIGHT,
        data.RUNID
    ], axis=1, keys=[
        "filename",
        "drs_path",
        "data_path",
        "delta_t",
        "on_time",
        "effective_on",
        "NIGHT",
        "RUNID",
    ])

    mapping = mapping.dropna(how='any')

    logger.info("Fetched {} data runs and approx {} drs entries from database where time delta is less than {} minutes".format(len(mapping), mapping['drs_path'].nunique(), timedelta_in_minutes))
    # effective_on_time = (mapping['on_time'] * mapping['effective_on']).sum()
    # logger.info("Effective on time: {}. Thats {} hours.".format(datetime.timedelta(seconds=effective_on_time), effective_on_time/3600))

    return mapping


def ft_json_to_df(json_path):
    with open(json_path,'r') as text:
        try:
            logger.info("Reading fact-tools output.")
            y=json.loads(text.read())
            df_out=pd.DataFrame(y)
            logger.info("Returning data frame with {} entries".format(len(df_out)))
            return df_out
        except ValueError:
            logger.exception("Fact-tools output could not be read.")
            return "error reading json"
        except Exception:
            logger.exception("Fact-tools output could not be gathered.")
            return "error gathering output"
