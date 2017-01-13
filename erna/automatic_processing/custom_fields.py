from peewee import Field, BlobField
import logging
from ..utils import date_to_night_int, night_int_to_date


log = logging.getLogger(__name__)


class NightField(Field):
    db_field = 'night'

    def db_value(self, value):
        return date_to_night_int(value)

    def python_value(self, value):
        return night_int_to_date(value)


class LongBlobField(BlobField):
    db_field = 'longblob'
