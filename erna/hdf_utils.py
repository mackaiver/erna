import logging
import h5py
from astropy.io import fits
from tqdm import tqdm
import sys
from fact.io import append_to_h5py, initialize_h5py
from fact.instrument import camera_distance_mm_to_deg
import re
from numpy.lib import recfunctions
import numpy as np

log = logging.getLogger(__name__)

native_byteorder = {'little': '<', 'big': '>'}[sys.byteorder]


theta_columns = tuple(
    ['theta'] + ['theta_off_{}'.format(i) for i in range(1, 6)]
)

theta_deg_columns = tuple(
    ['theta_deg'] + ['theta_deg_off_{}'.format(i) for i in range(1, 6)]
)

snake_re_1 = re.compile('(.)([A-Z][a-z]+)')
snake_re_2 = re.compile('([a-z0-9])([A-Z])')


renames = {'RUNID': 'run_id', 'COGx': 'cog_x', 'COGy': 'cog_y'}


def camel2snake(key):
    ''' see http://stackoverflow.com/a/1176023/3838691 '''
    s1 = snake_re_1.sub(r'\1_\2', key)
    s2 = snake_re_2.sub(r'\1_\2', s1).lower().replace('__', '_')
    s3 = re.sub('^m_', '', s2)
    return s3.replace('.f_', '_')


def rename_columns(columns):
    return [camel2snake(renames.get(col, col)) for col in columns]


def add_theta_deg_columns(array):
    ''' add columns with theta in degrees '''
    arrays = []
    names = []
    for in_col, out_col in zip(theta_columns, theta_deg_columns):
        if in_col in array.dtype.names:
            arrays.append(camera_distance_mm_to_deg(array[in_col]))
            names.append(out_col)

    if len(names) > 0:
        array = recfunctions.append_fields(
            array,
            names=names,
            data=arrays,
            usemask=False,
        )
    return array


def write_fits_to_hdf5(
        outputfile,
        inputfiles,
        mode='a',
        compression='gzip',
        progress=True,
        key='events',
        ):

    initialized = False

    with h5py.File(outputfile, mode) as hdf_file:

        for inputfile in tqdm(inputfiles, disable=not progress):
            with fits.open(inputfile) as f:
                if len(f) < 2:
                    continue

                array = np.array(f[1].data[:])

                # convert all names to snake case
                array.dtype.names = rename_columns(array.dtype.names)

                # add columns with theta in degrees
                array = add_theta_deg_columns(array)

                if not initialized:
                    initialize_h5py(
                        hdf_file,
                        array,
                        key=key,
                        compression=compression,
                    )
                    initialized = True

                append_to_h5py(hdf_file, array, key=key)
