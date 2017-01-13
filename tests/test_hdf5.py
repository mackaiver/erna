import tempfile
import h5py
import numpy as np


data = np.array([
    (1.0, 2, (3, 4)),
    (5.0, 6, (7, 8)),
    (5.0, 6, (7, 8)),
], dtype=[('x', float), ('y', float), ('a', int, 2)])


def test_init_h5():
    from erna.hdf_utils import initialize_hdf5

    with tempfile.NamedTemporaryFile() as tmpfile:
        with h5py.File(tmpfile.name, 'w') as f:
            initialize_hdf5(f, data.dtype)


def test_append_h5():
    from erna.hdf_utils import initialize_hdf5, append_to_hdf5

    with tempfile.NamedTemporaryFile() as tmpfile:
        with h5py.File(tmpfile.name, 'w') as f:

            initialize_hdf5(f, data.dtype)

            for i in range(5):
                append_to_hdf5(f, data)

        with h5py.File(tmpfile.name, 'r') as f:

            assert f['data']['a'].shape == (15, 2)
            assert f['data']['x'].shape == (15, )
            assert f['data']['y'].shape == (15, )
