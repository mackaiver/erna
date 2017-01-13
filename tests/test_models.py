from playhouse.test_utils import test_database


def test_init():
    from peewee import SqliteDatabase
    from erna.automatic_processing import database
    import tempfile

    with tempfile.NamedTemporaryFile() as f:
        test_db = SqliteDatabase(
            f.name,
            fields={'night': 'INTEGER', 'longblob': 'BLOB'}
        )
        with test_database(test_db, database.MODELS):
            database.setup_database(test_db)


def test_init_twice():
    from peewee import SqliteDatabase
    from erna.automatic_processing import database
    import tempfile

    with tempfile.NamedTemporaryFile() as f:
        test_db = SqliteDatabase(
            f.name,
            fields={'night': 'INTEGER', 'longblob': 'BLOB'}
        )
        with test_database(test_db, database.MODELS):
            database.setup_database(test_db)
            database.setup_database(test_db)
