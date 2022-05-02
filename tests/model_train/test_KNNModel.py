import pytest
import os
import pandas as pd
from src.model_train.KNNModel import KNNModel


def test_get_rating_data_invalid_path():
    with pytest.raises(FileNotFoundError):
        KNNModel.get_rating_data("invalid.path")


def test_get_null_values_userId():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    assert KNNModel.get_rating_data(os.path.join(dir_path, "../../data/rating.csv"))['userId'].isnull().sum() == 0


def test_get_null_values_movieId():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    assert KNNModel.get_rating_data(os.path.join(dir_path, "../../data/rating.csv"))['movieId'].isnull().sum() == 0


def test_get_null_values_rating():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    assert KNNModel.get_rating_data(os.path.join(dir_path, "../../data/rating.csv"))['rating'].isnull().sum() == 0


df = pd.DataFrame({'userId': [16541, 84312, 836903],
                   'movieId': ['apollo+13+1995', 'dead+men+dont+wear+plaid+1982', 'the+shawshank+redemption+1994'],
                   'rating': [4, 3, 4]})
csr_matrix, user_map, movie_map, inv_user_map, inv_movie_map = KNNModel.create_matrix(df)
exp_recommendation_count = 1


def test_create_matrix():
    assert csr_matrix.toarray().tolist() == [[4, 0, 0], [0, 3, 0], [0, 0, 4]]
    assert user_map == {16541: 0, 84312: 1, 836903: 2}
    assert movie_map == {'apollo+13+1995': 0, 'dead+men+dont+wear+plaid+1982': 1, 'the+shawshank+redemption+1994': 2}
    assert inv_user_map == {0: 16541, 1: 84312, 2: 836903}
    assert inv_movie_map == {0: 'apollo+13+1995', 1: 'dead+men+dont+wear+plaid+1982',
                             2: 'the+shawshank+redemption+1994'}


def test_n_neighbors_input():
    # Number of movie recommendation expected = number of samples in dataset - 1    #-1 to exclude the movie for
    # which recommendation is expected
    assert exp_recommendation_count <= len(df) - 1


def test_find_similar_movies():
    assert \
    KNNModel.find_similar_movies('apollo+13+1995', csr_matrix, exp_recommendation_count, movie_map, inv_movie_map,
                                 metric='cosine', show_distance=False)[0] == 'dead+men+dont+wear+plaid+1982'
