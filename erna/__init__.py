import logging
import pandas as pd
import os
import numpy as np
import datetime
import json
from datetime import timedelta
from . import datacheck_conditions as dcc
from . import qsub

logger = logging.getLogger(__name__)


def _build_path(fNight, path_to_data):
        year = fNight[0:4]
        month = fNight[4:6]
        day = fNight[6:8]
        return os.path.join(path_to_data, year, month, day)

def _build_RunID(fRunID):
    if(len(fRunID) == 1):
        return('00' + fRunID)

    if(len(fRunID) == 2):
        return('0' + fRunID)

    return(fRunID)


def mc_drs_file():
    '''
    return path to the drs file used for monte carlo files
    '''
    import pkg_resources
    drs_path = pkg_resources.resource_filename(__name__,'resources/mc_drs_constants.drs.fits.gz')
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
    Collects the output from the list of job_outputs and merges them into a dataframe. The Dataframe will then be written
    to a file as specified by the output_path.
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



def load(earliest_night, latest_night, path_to_data, factdb,source_name="Crab", timedelta_in_minutes="30", data_conditions=dcc.conditions["std"]):
    '''
    Given the earliest and latest night to fetch as a factnight string (as in 20141024) this method returns a DataFrame
    containing the paths to data files and their correpsonding .drs files. The maximum time difference between the
    data and drs files is specified by the timedelta_in_minutes parameter.

    Returns None if no files can be found.
    '''



    logger.debug("Table names in DB: ")
    logger.debug(factdb.table_names())

    if (len(factdb.table_names()) > 0):
        logger.info("Connected to Database.")


    #read source table
    sourceDB = pd.read_sql_table('Source', factdb, columns=["fSourceName", "fSourceKEY"])

    firstNight = earliest_night
    lastNight = latest_night

    logger.info("Reading Data from DataBase from " + str(firstNight) + " to " + str(lastNight) +
                " for source: " + source_name)

    rundb = pd.read_sql("SELECT * from RunInfo WHERE (fNight > " + firstNight + " AND fNight <" + lastNight + ") ", factdb)


    #lets try to get all data runs from a specific source between two dates
    source = sourceDB[sourceDB.fSourceName == source_name]
    if source.size != 2:
        # embed()
        logger.error('Given source name does not return a specific source from the DB')
        logger.error('Allowed names are: {}'.format(sourceDB.fSourceName) )
        return pd.DataFrame()

    #source key to conditions for data quality
    data_conditions += [
         "fSourceKEY == " + str(int(source.fSourceKEY)),
    ]
    querystring = " & ".join(data_conditions)

    logger.info('Querying data with conditions: {}'.format(querystring))
    #get all data runs according to the conditions
    data = rundb.query(querystring)



    # now lets get all drs runs
    conditions = [
        "fRunTypeKey == 2", #  300 roi Drs files
        "fROI == 300",
        "fDrsStep == 2",
        # "fZenithDistanceMean < 30",
        # "fSourceKEY == " + str(int(source.fSourceKEY)),
    ]

    querystring = " & ".join(conditions)
    drs_data = rundb.query(querystring)

    if len(data) == 0 or len(drs_data) == 0:
        logger.error('No data or drs files found that adhere to the specified query.')
        return None

    logger.info("Got " + str(len(data)) + " data entries and " + str(len(drs_data)) + " drs entries")

    #the timestamp should be unique for each observation. No two observations start at the same time
    data = data.set_index("fRunStart")
    drs_data = drs_data.set_index("fRunStart")



    #write filenames
    data["filename"] = data.fNight.astype(str) + "_" + data.fRunID.astype(str).apply(_build_RunID)
    drs_data["filename"] = drs_data.fNight.astype(str) + "_" + drs_data.fRunID.astype(str).apply(_build_RunID)

    #write path TODO: file ending? is everythiong in fz?
    data["path"] = data.fNight.astype(str).apply(_build_path, args=[path_to_data]) + "/" + data.filename.astype(str) + ".fits.fz"
    drs_data["path"] = drs_data.fNight.astype(str).apply(_build_path, args=[path_to_data]) + "/" + drs_data.filename.astype(str) + ".drs.fits.gz"


    #sorting data by their timestamp.
    data = data.sort_index()
    drs_data = drs_data.sort_index()

    #reindex the drs table using the index of the data table. There are always more data runs than drs run in the db.
    #hence missing rows have to be filled either forward or backwards
    earlier_drs_entries = drs_data.reindex(data.index, method="ffill")
    later_drs_entries = drs_data.reindex(data.index, method="backfill")


    #when backfilling the drs obeservations the last rows might be invalid and contain nans. We cannot drop them becasue the tables have to have the same length.
    # in that case simply fill them up.
    earlier_drs_entries["deltaT"] = np.abs(earlier_drs_entries.fRunStop - data.fRunStop)
    later_drs_entries["deltaT"] = np.abs(later_drs_entries.fRunStop - data.fRunStop).fillna(axis='index', method='ffill')
    d_later = later_drs_entries[later_drs_entries.deltaT < earlier_drs_entries.deltaT]
    d_early = earlier_drs_entries[later_drs_entries.deltaT >= earlier_drs_entries.deltaT]

    closest_drs_entries = pd.concat([d_early, d_later])
    closest_drs_entries = closest_drs_entries[closest_drs_entries.deltaT < timedelta(minutes = timedelta_in_minutes)]


    mapping = pd.concat([closest_drs_entries.filename, closest_drs_entries.path, data.path, closest_drs_entries.deltaT, data.fOnTime, data.fEffectiveOn, data.fNight, data.fRunID],
                                        axis=1, keys=["filename", "drs_path", "data_path", "delta_t", "on_time", "effective_on", "fNight", "fRunID"])

    mapping = mapping.dropna( how='any')

    mapping = mapping.rename(columns={'fNight':'NIGHT', 'fRunID':'RUNID'})

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
