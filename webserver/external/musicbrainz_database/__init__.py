from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager

def init_db(connect_str):
    global engine
    # Use NullPool so that the only connections we see in Postgres
    # are the connections that are actually being used.
    engine = create_engine(connect_str, poolclass=NullPool)
    Session = scoped_session(sessionmaker(bind=engine))


@contextmanager
def musicbrainz_session():
	session = Session()
	try:
		yield session
	finally:
		session.close()
