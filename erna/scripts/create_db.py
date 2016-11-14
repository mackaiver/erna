import yaml
import click
import logging
from erna.database import FactToolsRun, DrsFile, RawDataFile, init_database
from erna.database import database as db
from IPython import embed

log = logging.getLogger('erna')
log.setLevel(logging.INFO)


@click.command()
@click.argument('configuration_path', type=click.Path(exists=True, dir_okay=False, file_okay=True))
@click.option('--drop', is_flag=True, default=False, help='drop excisitng tables when creating')
def main(configuration_path, drop):
    """
    Intitiate the Tables from the database model
    """
    with open(configuration_path) as f:
        db_config = yaml.load(f)

    db.init(**db_config)
    db.connect()
    init_database(drop)



if __name__ == '__main__':
    main()
