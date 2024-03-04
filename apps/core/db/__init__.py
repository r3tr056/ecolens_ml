import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy

Base = declarative_base()

def create_database_engine():
    try:
        engine = create_engine(os.getenv('POSTGRES_DB_CONN_STR'))
        Base.metadata.create_all(engine)
        return engine
    except Exception as ex:
        logging.error(f"Error creating database engine : {ex}")

def create_session(engine):
    try:
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as ex:
        logging.error(f"Error creating database session : {ex}")
        

# postgres setup
engine = create_database_engine()
db_session = create_session(engine)
