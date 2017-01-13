from datetime import date


def test_aux_dirs():
    from erna.automatic_processing.utils import get_aux_dir

    night = date(2015, 1, 1)

    auxdir_isdc = get_aux_dir(night)
    assert auxdir_isdc == '/fact/aux/2015/01/01'

    auxdir_dortmund = get_aux_dir(night, location='dortmund')
    assert auxdir_dortmund == '/fhgfs/groups/app/fact/aux/2015/01/01'
