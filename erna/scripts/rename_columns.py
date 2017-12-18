import click
import numpy as np
import h5py
from fact.instrument import camera_distance_mm_to_deg
import logging
import pandas as pd

from ..hdf_utils import rename_columns, theta_columns, theta_deg_columns


@click.command()
@click.argument('inputfile', type=click.Path(exists=True, dir_okay=False))
@click.option('-k', '--key', help='HDF5 key in inputfile', default='events')
@click.option('-f', '--fmt', type=click.Choice(['h5py', 'pandas']), help='Type of hdf file', default='h5py')
def main(inputfile, key, fmt):
    '''
    Rename columns in hdf5 file to the new format, add theta columns in degrees
    e.g.
    COGx -> cog_x,
    Theta_Off_1 -> theta_off_1,
    MCORSIKA_EVT_HEADER.fTotalEnergy -> corsika_evt_header_total_energy

    INPUTFILE: A pandas-style hdf5 file
    '''

    log = logging.getLogger()

    if fmt == 'h5py':
        with h5py.File(inputfile, 'r+') as f:

            log.info('Renaming columns')

            group = f[key]

            old_names = list(group.keys())
            new_names = rename_columns(old_names)

            for old_name, new_name in zip(old_names, new_names):
                group.move(old_name, new_name)

            log.info('Adding theta deg columns')
            for theta_key, theta_deg_key in zip(theta_columns, theta_deg_columns):
                if theta_key in group:
                    group.create_dataset(
                        theta_deg_key,
                        data=camera_distance_mm_to_deg(group[theta_key]),
                        maxshape=(None, )
                    )

            log.info('Done')

    if fmt == 'pandas':
        df = pd.read_hdf(inputfile, key=key)
        df.columns = rename_columns(df.columns)

        for theta_key, theta_deg_key in zip(theta_columns, theta_deg_columns):
            if theta_key in df:
                df[theta_deg_key] = camera_distance_mm_to_deg(group[theta_key])

        df.to_hdf(inputfile, key=key)


if __name__ == '__main__':
    main()
