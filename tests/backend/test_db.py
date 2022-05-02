import pytest
import connexion

from backend.src.impl.db import get_db, get_api_key, get_special_list


class Config:
    def __init__(self):
        self.DEBUG = False
        self.SPECIAL_LIST = ["1,2,3"]
        self.DATABASE_URI = "test_databse_uri"
        self.API_KEY = "test_api_key"


@pytest.fixture()
def app():
    app = connexion.App(__name__)
    app.app.config.from_object(Config())
    yield app.app


# Disabled for now as the database uri must be real.
# def test_get_db(app):
#     with app.app_context():
#         assert type(get_db()) is PyMongo


def test_get_api_key(app):
    with app.app_context():
        assert get_api_key() == Config().API_KEY


def test_get_special_list():
    with pytest.raises(RuntimeError):
        assert get_special_list() == Config().SPECIAL_LIST
