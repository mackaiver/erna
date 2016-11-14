from setuptools import setup

setup(
    name='erna',
    version='0.0.2',
    description='Easy RuN Access. Tools that help to do batch processing of FACT data',
    url='https://github.com/fact-project/erna',
    author='Kai Brügge',
    author_email='kai.bruegge@tu-dortmund.de',
    license='BEER',
    packages=[
        'erna',
        'erna.scripts',
    ],
    # dependency_links = ['git+https://github.com/mackaiver/gridmap.git#egg=gridmap'],
    package_data={
        'erna': ['resources/*'],
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
        # 'hdf5',
        'click',
        'drmaa',
        'pyzmq',
        'peewee',
        'numexpr',
        'pyyaml',
        'pytest', # also in  conda
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
    ],
  }
)
