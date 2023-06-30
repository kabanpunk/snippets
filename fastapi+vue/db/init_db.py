import os
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from db import data

import db.models


def init_db():
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', '1234')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5444')
    database = os.getenv('DB_NAME', 'postgres')

    url = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}'
    engine = sqlalchemy.create_engine(url, echo=True)
    data.Base.metadata.create_all(engine)
    data.Session = sessionmaker(bind=engine, query_cls=data.Query)
