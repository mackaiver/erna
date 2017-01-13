import click
import logging
from ..automatic_processing.database import database as db, setup_database
from ..utils import load_config

log = logging.getLogger('erna')
log.setLevel(logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())


@click.command()
@click.option(
    '--config', '-c', type=click.Path(exists=True, dir_okay=False, file_okay=True),
    help=(
        'Path to the yaml config file.'
        ' If not given, first the ERNA_CONFIG variable, then "erna.yaml" is tried'
    ),
)
@click.option('--verbose', '-v', help='Set logging level to DEBUG', is_flag=True)
@click.option(
    '--drop', is_flag=True, default=False,
    help='Drop exisiting tables when creating',
)
def main(config, verbose, drop):
    """
    Intitiate the Tables from the database model
    """

    if verbose:
        logging.getLogger('erna').setLevel(logging.DEBUG)

    config = load_config(config)

    db.init(**config['processing_database'])
    db.connect()
    log.info('Database connection established')
    log.info('Initialising database with drop={}'.format(drop))
    setup_database(db, drop=drop)
    db.close()
    log.info('Done')


if __name__ == '__main__':
    main()
