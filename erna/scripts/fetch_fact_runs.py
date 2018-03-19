__author__ = 'kai, lena'

import numpy as np
from sqlalchemy import create_engine
import logging
import click
import erna
import erna.datacheck_conditions as dcc


logger = logging.getLogger(__name__)


@click.command()
@click.argument('earliest_night')
@click.argument('latest_night' )
@click.argument('data_dir', type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True) )
@click.option('--source',  help='Name of the source to analyze. e.g Crab', default='Crab')
@click.option('--max_delta_t', default=30,  help='Maximum time difference (minutes) allowed between drs and data files.', type=click.INT)
@click.option('--parts', default=1, help='Number of parts to split the .json file into. This is useful for submitting this to a cluster later on', type=click.INT)
@click.option('--conditions', '-c', help='Name of the data conditions as given in datacheck_conditions.py e.g @standard or "fParameter < 42 "', default=['@standard'], multiple=True)
@click.password_option(help='password to read from the always awesome RunDB')
def main(earliest_night, latest_night, data_dir, source,  max_delta_t, parts, password, conditions):
    '''  This script connects to the rundb and fetches all runs belonging to the specified source.
        Provide time range by specifying ealriest and lates night to fetch. As in 20131001,  20141001.
        This script will produce a json file containing paths to the data files and their drs files. The
        path prefix is specified by the DATA_DIR argument. The files in this folder will not actually be read
        by this script. It simply needs the path to construct the json file containing the full paths to the raw data files
    '''

    logging.basicConfig(level=logging.INFO)

    factdb = create_engine("mysql+pymysql://factread:{}@129.194.168.95/factdata".format(password))

    # create the set of conditions we want to use
    data_conditions = dcc.create_condition_set(conditions)
    
    mapping = erna.load(earliest_night, latest_night, data_dir,  source_name=source, timedelta_in_minutes=max_delta_t, factdb=factdb, data_conditions=data_conditions)
    if mapping.empty:
        logger.error('No entries matching the conditions could be found in the RunDB')
        return


    if parts > 1:
        split_indices = np.array_split(np.arange(len(mapping)), parts)
        for num, indices in enumerate(split_indices):
            df = mapping[indices.min(): indices.max()]
            filename = "{}_{}_{}_part_{}.json".format(earliest_night, latest_night, source.replace(' ', '_'), num)
            logger.info("Writing {} entries to json file  {}".format(len(df), filename))
            df.to_json(filename, orient='records', date_format='epoch' )
    else:
        filename = earliest_night + "_" + latest_night + "_" + source + ".json"
        logger.info("Writing list to json file  {}".format(filename))
        mapping.to_json(filename, orient='records', date_format='epoch' )


if __name__ == '__main__':
    main()
