import pytest
import db as db_module
from app import app as flask_app

@pytest.fixture
def tmp_db(tmp_path):
    db_file = str(tmp_path / 'test.db')
    original = db_module.DATABASE
    db_module.DATABASE = db_file
    db_module.init_db()
    yield db_file
    db_module.DATABASE = original

@pytest.fixture
def client(tmp_db):
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c
