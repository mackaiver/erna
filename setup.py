from setuptools import setup

setup(
    name='erna',
    version='0.0.2',
    description='Easy RuN Access. Tools that help to do batch processing of FACT data',
    url='https://github.com/fact-project/erna',
    author='Kai Brügge, Jens Buss, Maximilian Nöthe',
    author_email='kai.bruegge@tu-dortmund.de',
    license='BEER',
    packages=[
        'erna',
        'erna.scripts',
        'erna.automatic_processing',
    ],
    package_data={
        'erna': ['resources/*'],
        'erna.automatic_processing': ['xml/*']
    },
    install_requires=[
        'pandas',           # in anaconda
        'numpy',            # in anaconda
        'matplotlib>=1.4',  # in anaconda
        'python-dateutil',  # in anaconda
        'sqlalchemy',       # in anaconda
        'PyMySQL',          # in anaconda
        'pytz',             # in anaconda
        'tables',           # needs to be installed by pip for some reason
        'astropy',
        'h5py',
        # 'hdf5',
        'tqdm',
        'click',
        'drmaa',
        'pyzmq',
        'peewee',
        'numexpr',
        'pyyaml',
        'pytest',           # also in  conda
        'xmltodict',
        'wrapt',
        # 'gridmap>=0.13.1', install from https://github.com/mackaiver/gridmap'
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'process_fact_data = erna.scripts.process_fact_data:main',
            'process_fact_data_qsub = erna.scripts.process_fact_data_qsub:main',
            'process_fact_mc = erna.scripts.process_fact_mc:main',
            'fetch_fact_runs = erna.scripts.fetch_fact_runs:main',
            'process_fact_run_list = erna.scripts.process_fact_run_list:main',
            'read_aux_files_to_sqlite = erna.scripts.read_aux_files_to_sqlite:main',
            'facttools_executer = erna.scripts.facttools_executer:main',
            'erna_fill_database = erna.scripts.fill_database:main',
            'erna_check_availability = erna.scripts.check_availability:main',
            'erna_create_tables = erna.scripts.create_db:main',
            'erna_upload = erna.scripts.upload:main',
            'erna_console = erna.scripts.console:main',
            'erna_automatic_processing_executor = erna.automatic_processing.executor:main',
            'erna_automatic_processing = erna.automatic_processing.__main__:main',
            'erna_gather_fits = erna.scripts.gather_fits:main',
        ],
    },
    setup_requires=['pytest-runner'],
    tests_require=['pytest>=3.0.0'],
)
