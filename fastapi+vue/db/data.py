from sqlalchemy.orm import relationship, exc, column_property
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.query import Query as _Query

Base = declarative_base()
Session = None


class Query(_Query):
    def values(self):
        try:
            return [i for (i,) in self]
        except ValueError as e:
            raise MultipleValuesFound(str(e))


class MultipleValuesFound(ValueError, exc.MultipleResultsFound):
    """
    raised when multiple values are found in a single result row
    """
