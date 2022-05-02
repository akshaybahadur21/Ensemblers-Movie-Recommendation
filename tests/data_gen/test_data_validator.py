from src.data_gen.data_validator import validate_movie_message, validate_rating_message, validate_user_message


def test_validate_movie_message1():
    assert validate_movie_message("2022-03-13T00:30:14,544914,GET /data/m/the+cure+1995/74.mpg") == True


def test_validate_movie_message2():
    assert validate_movie_message("invalidMessage") == False


def test_validate_rating_message1():
    assert validate_rating_message("2022-02-02T21:34:12,139345,GET /rate/bo+burnham+words_+words_+words+2010=3") == True


def test_validate_rating_message2():
    assert validate_rating_message("invalidMessage") == False


def test_validate_user_message1():
    assert validate_user_message("2022-03-13T00:30:14,544914,GET /data/m/the+cure+1995/74.mpg") == True


def test_validate_user_message2():
    assert validate_user_message("invalidMessage") == False