from IPython import embed
import click
from datetime import date
from tqdm import tqdm
from threading import Thread
from time import sleep

from ..automatic_processing.database import *
from ..automatic_processing.database_utils import *
from ..utils import load_config

def reconnect():
    while True:
        database.connect()
        sleep(10)


@click.command()
@click.option('--config', '-c', help='Path to the yaml config file')
def main(config):
    ''' Starts an IPython shell with helpful imports to work with erna '''
    config = load_config(config)

    database.init(**config['processing_database'])
    database.connect()

    t = Thread(target=reconnect, daemon=True)
    t.start()

    embed()


if __name__ == '__main__':
    main()
