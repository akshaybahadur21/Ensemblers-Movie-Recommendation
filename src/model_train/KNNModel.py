import os
import time

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
import requests
from dotenv import load_dotenv
import logging
import gc
import sys
from sklearn.model_selection import train_test_split
import neptune.new as neptune


logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

class KNNModel:
    def __init__(self, properties):
        dotenv_path = properties.get("dotenv.path").data
        load_dotenv(dotenv_path)
        self.properties = properties
        self.run = neptune.init(
            project="akshaybahadur21/Ensemblers",
            api_token="eyJhcGlfYWRkcmVzcyI6Imh0dHBzOi8vYXBwLm5lcHR1bmUuYWkiLCJhcGlfdXJsIjoiaHR0cHM6Ly9hcHAubmVwdHVuZS5haSIsImFwaV9rZXkiOiIxYWFhY2NmZS0yZTY2LTQzMjctOGM4NC04NDgyMjA4M2E0MWYifQ==",
        )
        self.API_KEY = "BreakFree@123"

    @staticmethod
    def create_matrix(df):
        N = len(df['userId'].unique())
        M = len(df['movieId'].unique())

        # Map Ids to indices
        user_mapper = dict(zip(np.unique(df["userId"]), list(range(N))))
        movie_mapper = dict(zip(np.unique(df["movieId"]), list(range(M))))

        # Map indices to IDs
        user_inv_mapper = dict(zip(list(range(N)), np.unique(df["userId"])))
        movie_inv_mapper = dict(zip(list(range(M)), np.unique(df["movieId"])))

        user_index = [user_mapper[i] for i in df['userId']]
        movie_index = [movie_mapper[i] for i in df['movieId']]

        X = csr_matrix((df["rating"], (movie_index, user_index)), shape=(M, N))

        return X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper

    @staticmethod
    def find_similar_movies(movie_id, X, k, movie_mapper, movie_inv_mapper, metric='cosine', show_distance=False):
        neighbour_ids = []

        movie_ind = movie_mapper[movie_id]
        movie_vec = X[movie_ind]
        k += 1
        kNN = NearestNeighbors(n_neighbors=k, algorithm="brute", metric=metric)
        kNN.fit(X)
        movie_vec = movie_vec.reshape(1, -1)
        neighbour = kNN.kneighbors(movie_vec, return_distance=show_distance)
        for i in range(0, k):
            n = neighbour.item(i)
            neighbour_ids.append(movie_inv_mapper[n])
        neighbour_ids.pop(0)
        return neighbour_ids

    @staticmethod
    def separate_train_test(movie_db):
        train, test = train_test_split(movie_db, train_size=0.8, test_size=0.2)
        return train, test

    @staticmethod
    def get_rating_data(path):
        rating = pd.read_csv(path,
                             names=["userId", "movieId", "rating"], header=None)
        return rating

    @staticmethod
    def get_obj_size(obj):
        marked = {id(obj)}
        obj_q = [obj]
        sz = 0

        while obj_q:
            sz += sum(map(sys.getsizeof, obj_q))
            all_refr = ((id(o), o) for o in gc.get_referents(*obj_q))
            new_refr = {o_id: o for o_id, o in all_refr if o_id not in marked and not isinstance(o, type)}
            obj_q = new_refr.values()
            marked.update(new_refr.keys())

        return sz

    @staticmethod
    def simple_cache(X, movie_mapper, movie_inv_mapper, user_id, rating):
        movie_id = rating[rating['userId'] == user_id].iloc[-1]['movieId']
        similar_ids = KNNModel.find_similar_movies(movie_id, X, 50, movie_mapper, movie_inv_mapper)
        rec = ",".join(similar_ids)
        return rec

    def test(self, db_train, db_test, X, movie_mapper, movie_inv_mapper, train_cost):
        test_start_time = time.time()
        rating = self.get_rating_data(self.properties.get("rating.path").data)
        test_df = db_test.filter(['userId', 'movieId', 'rating']).query("rating >= 5")
        test_df = test_df.groupby('userId').agg({'movieId': lambda x: set(x)}).reset_index()

        def f(x):
            movieIds = x['movieId']
            if len(movieIds) >= 4:
                return 'no'
            else:
                return 'yes'
        test_df['drop'] = test_df.apply(lambda x: f(x), axis=1)
        test_df = test_df.filter(['userId', 'movieId', 'drop']).query("drop == 'no'")

        def f(x):
            try:
                user_id = x['userId']
                movieIds = list(x['movieId'])
                rec = self.simple_cache(X, movie_mapper, movie_inv_mapper, user_id, rating)
                for m in movieIds:
                    if m in rec:
                        return "yes"
                    else:
                        return "no"
            except Exception:
                return "no"

        test_df['yes_no'] = test_df.apply(lambda x: f(x), axis=1)

        misses = len(test_df.filter(['userId', 'movieId', 'rating', 'yes_no']).query("yes_no == 'yes'"))
        hits = len(test_df.filter(['userId', 'movieId', 'rating', 'yes_no']).query("yes_no == 'no'"))
        test_end_time = time.time()

        logging.info("Offline evaluation completed.")
        logging.info("Number of filtered testing sample : {}".format(len(test_df)))
        logging.info(
            "Ratio of train : test = {}% : {}%".format(round(len(db_train) * 100 / (len(db_train) + len(db_test)), 2),
                                                       round((len(db_test) * 100 / (len(db_train) + len(db_test))), 2)))
        logging.info("Size of the Model : " + str(self.get_obj_size(X)) + " bytes")
        logging.info("Training Latency : {} seconds".format(train_cost))
        self.run["Training Latency"].log(train_cost)
        logging.info("Testing Latency : {} seconds".format(test_end_time - test_start_time))
        self.run["Testing Latency"].log(test_end_time - test_start_time)
        logging.info("Number of hits : {}".format(hits))
        self.run["Test Hits"].log(hits)
        logging.info("Number of misses : {}".format(misses))
        self.run["Test Misses"].log(misses)
        hr = round(hits * 100 / (misses + hits), 2)
        logging.info("Hit Rate = {}%".format(hr))
        self.run["Test Hit Rate"].log(hr)
        mr = round(misses * 100 / (misses + hits), 2)
        logging.info("Miss Rate = {}%".format(mr))
        self.run["Test Miss Rate"].log(mr)

    def train(self):
        start_time = time.time()
        rating = self.get_rating_data(self.properties.get("rating.path").data)
        db_train, db_test = self.separate_train_test(rating)
        self.run["Algorithm"] = "KNN"

        params = {
            "algorithm": "brute",
            "metric": "brute",
            "N_neighbors": 50,
            "P": 2,
            "weight": "uniform"
        }
        self.run["parameters"] = params
        self.run["movie_dataset"].track_files(self.properties.get("movie.path").data)
        self.run["rating_dataset"].track_files(self.properties.get("rating.path").data)
        self.run["user_dataset"].track_files(self.properties.get("user.path").data)

        X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper = self.create_matrix(db_train)
        end_time = time.time()
        return X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper, db_test, db_train, end_time - start_time

    def cache(self, X, movie_mapper, movie_inv_mapper):
        logging.info("Starting the cache")
        rating = self.get_rating_data(self.properties.get("rating.path").data)
        # For all users in rating

        api_dict = {
            "api_key": self.API_KEY,
            "user_recommendations": []
        }
        count = 0
        # recommend criteria to existing customers -> based on previously watched movie
        recent_watched_movie_rating_filter = 4
        recommend_list_size = 20

        for user_id in rating['userId'].unique():
            try:
                # Most recently watched movie with 4 or above rating
                movie_id = \
                    rating[
                        (rating['userId'] == user_id)].iloc[
                        -1]['movieId']
                similar_ids = self.find_similar_movies(movie_id, X, recommend_list_size, movie_mapper, movie_inv_mapper)
                rec = ",".join(similar_ids)
                api_dict["user_recommendations"].append({"user_id": str(user_id), "recommend": rec, "model_id": 0})
                count += 1
                if count % 10000 == 0:
                    logging.info("Cached the recommendations : {}".format(count))
                    r = requests.post(self.properties.get("recommend.api").data, json=api_dict)
                    if r.status_code != 200:
                        logging.error("Couldn't post recommendation")
                    else:
                        api_dict["user_recommendations"].clear()
            except Exception as e:
                logging.error(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
