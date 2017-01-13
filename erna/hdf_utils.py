import logging
import h5py
from astropy.io import fits
from tqdm import tqdm
import sys

log = logging.getLogger(__name__)

native_byteorder = {'little': '<', 'big': '>'}[sys.byteorder]


def initialize_hdf5(f, dtypes, groupname='events', **kwargs):
    '''
    Create a group with name `groupname` and empty datasets for each
    entry in dtypes.

    Parameters
    ----------
    f: h5py.File
        the hdf5 file, opened either in write or append mode
    dtypes: numpy.dtype
        the numpy dtype object of a record or structured array describing
        the columns
    groupname: str
        the name for the hdf5 group to hold all datasets, default: data
    '''
    group = f.create_group(groupname)

    for name in dtypes.names:
        dtype = dtypes[name]
        maxshape = [None] + list(dtype.shape)
        shape = [0] + list(dtype.shape)

        group.create_dataset(
            name,
            shape=tuple(shape),
            maxshape=tuple(maxshape),
            dtype=dtype.base,
            **kwargs
        )

    return group


def append_to_hdf5(f, array, groupname='events'):
    '''
    Append a numpy record or structured array to the given hdf5 file
    The file should have been previously initialized with initialize_hdf5

    Parameters
    ----------
    f: h5py.File
        the hdf5 file, opened either in write or append mode
    array: numpy.array or numpy.recarray
        the numpy array to append
    groupname: str
        the name for the hdf5 group with the corresponding data sets
    '''

    group = f.get(groupname)

    for key in array.dtype.names:
        dataset = group.get(key)

        n_existing_rows = dataset.shape[0]
        n_new_rows = array[key].shape[0]

        dataset.resize(n_existing_rows + n_new_rows, axis=0)

        # swap byteorder if not native
        if array[key].dtype.byteorder not in ('=', native_byteorder):
            data = array[key].newbyteorder().byteswap()
        else:
            data = array[key]

        if data.ndim == 1:
            dataset[n_existing_rows:] = data

        elif data.ndim == 2:
            dataset[n_existing_rows:, :] = data

        else:
            raise NotImplementedError('Only 1d and 2d arrays are supported at this point')


def write_fits_to_hdf5(
        outputfile,
        inputfiles,
        mode='a',
        compression='gzip',
        progress=True,
        groupname='events',
        ):

    initialized = False

    with h5py.File(outputfile, mode) as hdf_file:

        for inputfile in tqdm(inputfiles, disable=not progress):
            with fits.open(inputfile) as f:
                if len(f) < 2:
                    continue

                if not initialized:
                    initialize_hdf5(
                        hdf_file,
                        f[1].data.dtype,
                        groupname=groupname,
                        compression=compression,
                    )
                    initialized = True


                append_to_hdf5(hdf_file, f[1].data, groupname=groupname)
