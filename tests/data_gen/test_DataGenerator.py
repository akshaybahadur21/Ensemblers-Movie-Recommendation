import pytest

from src.data_gen.DataGenerator import DataGenerator


def test_get_movie_id():
    movie_id = DataGenerator.get_movie_id("2022-03-13T00:30:14,544914,GET /data/m/the+cure+1995/74.mpg")
    assert movie_id == "the+cure+1995"


def test_get_user_id():
    user_id = DataGenerator.get_user_id("2022-03-14T13:30:10,504248,GET /data/m/ace+ventura+pet+detective+1994/13.mpg")
    assert user_id == "504248"


def test_write_to_file():
    with pytest.raises(TypeError):
        DataGenerator.write_to_file(None, "invalid path")


def test_get_umr_from_rating_data():
    u, m, r = DataGenerator.get_umr_from_rating_data(
        "2022-02-02T21:34:12,139345,GET /rate/bo+burnham+words_+words_+words+2010=3")
    assert u == "139345" and m == "bo+burnham+words_+words_+words+2010" and r == "3"
