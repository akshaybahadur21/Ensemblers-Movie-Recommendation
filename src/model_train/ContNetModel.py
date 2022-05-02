import gc
import json
import logging
import os
import sys
import time
import requests
from pandas.core.common import SettingWithCopyWarning
import numpy as np
import pandas as pd
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv
import neptune.new as neptune
import warnings

warnings.filterwarnings("ignore", category=SettingWithCopyWarning)

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
total_recom = 20


def extract_from_dict(x, key):
    if key not in x.keys():
        return None
    return x.get(key)


def imdb_rule_rating(x, C, M):
    v = x['vote_count']
    r = x['vote_average']
    return ((v / (v + M)) * r + (M / (v + M)) * C)


class ContNetModel:
    def __init__(self, properties):
        if properties is None:
            return
        self.properties = properties
        dotenv_path = properties.get("dotenv.path").data
        load_dotenv(dotenv_path)
        self.run = neptune.init(
            project="akshaybahadur21/Ensemblers",
            api_token="eyJhcGlfYWRkcmVzcyI6Imh0dHBzOi8vYXBwLm5lcHR1bmUuYWkiLCJhcGlfdXJsIjoiaHR0cHM6Ly9hcHAubmVwdHVuZS5haSIsImFwaV9rZXkiOiIxYWFhY2NmZS0yZTY2LTQzMjctOGM4NC04NDgyMjA4M2E0MWYifQ==",
        )
        self.API_KEY = os.environ.get("API_KEY_PROD")

    def preprocess_user(self, user_rating_df):
        urd = user_rating_df.groupby(by=['user_id', 'title']).mean().reset_index()
        urd.set_index('user_id', inplace=True)
        return urd

    def preprocess_movie(self, movie_data_df):

        movie_data_df['genres'] = movie_data_df['info'].apply(lambda x: extract_from_dict(x, 'genres'))
        movie_data_df['overview'] = movie_data_df['info'].apply(lambda x: extract_from_dict(x, 'overview'))
        movie_data_df['production_companies'] = movie_data_df['info'].apply(
            lambda x: extract_from_dict(x, 'production_companies'))
        movie_data_df['vote_average'] = movie_data_df['info'].apply(
            lambda x: extract_from_dict(x, 'vote_average')).astype('float')
        movie_data_df['vote_count'] = movie_data_df['info'].apply(
            lambda x: extract_from_dict(x, 'vote_count')).astype('float')
        movie_data_df['genres'] = movie_data_df['genres'].apply(
            lambda x: [i['name'] for i in x] if isinstance(x, list) else [])
        movie_data_df['production_companies'] = movie_data_df['production_companies'].apply(
            lambda x: [i['name'] for i in x] if isinstance(x, list) else [])
        mdd = movie_data_df.drop('info', axis=1)

        return mdd

    @staticmethod
    def separate_train_test(movie_db):
        train, test = train_test_split(movie_db, train_size=0.8, test_size=0.2)
        return train, test

    def create_ranking(self, temp_df):
        C = temp_df['vote_average'].mean()
        M = temp_df['vote_count'].quantile(0.75)
        ranked_df = temp_df[
            (temp_df['vote_count'] >= M) & (temp_df['vote_count'].notnull()) & (temp_df['vote_average'].notnull())]
        ranked_df.loc[:, 'rating'] = ranked_df.apply(lambda x: imdb_rule_rating(x, C, M), axis=1)

        return ranked_df

    def create_content(self, temp_df):
        temp_df['genres'] = temp_df['genres'].apply(lambda x: ' '.join(x))
        temp_df['production_companies'] = temp_df['production_companies'].apply(lambda x: ' '.join(x))
        temp_df['description'] = temp_df['overview'] + ' ' + temp_df['genres'] + ' ' + temp_df['genres'] + ' ' + \
                                 temp_df['production_companies'] + ' ' + temp_df['production_companies']

        return temp_df

    def train(self):
        start_time = time.time()
        user_rating_df = pd.read_csv(self.properties.get("rating.path").data, names=["user_id", "title", "rating"])
        movie_data_df = pd.read_csv(self.properties.get("movie.path").data, names=["title", "info"])
        movie_data_df['info'] = movie_data_df['info'].apply(lambda x: json.loads(x))

        db_train, db_test = self.separate_train_test(user_rating_df)
        self.run["Algorithm"] = "ContNet"

        params = {
            "algorithm": "ContNet",
            "Similarity": "cosine",
            "Vectorizer": "TfIdf",
            "Stemmer": "Porter",
            "Analyzer": "Word",
            "Stop Words": "English",
            "ngram_range": "(1, 2)"
        }
        self.run["parameters"] = params
        self.run["movie_dataset"].track_files(self.properties.get("movie.path").data)
        self.run["rating_dataset"].track_files(self.properties.get("rating.path").data)
        self.run["user_dataset"].track_files(self.properties.get("user.path").data)
        urd = self.preprocess_user(db_train)
        mdd = self.preprocess_movie(movie_data_df)
        ranked = self.create_ranking(mdd)
        best_movie_df = self.create_content(ranked)

        porter_stemmer = PorterStemmer()
        best_movie_df.loc[:, 'description'] = best_movie_df['description'].apply(
            lambda x: porter_stemmer.stem(x.lower()))
        tf = TfidfVectorizer(analyzer='word', ngram_range=(1, 2), min_df=0, stop_words='english')
        tfidf_matrix = tf.fit_transform(best_movie_df['description'])
        cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

        # Dumping the files
        urd.to_pickle(self.properties.get("model_aux_user.dump.path").data)
        best_movie_df.to_pickle(self.properties.get("model_aux_movie.dump.path").data)
        cosine_sim.dump(self.properties.get("model.dump.path").data)
        end_time = time.time()
        return db_train, db_test, end_time - start_time

    def get_top_user_movies(self, user_id, urd, titles, best_movie_df):
        try:
            top_movie_list = urd.loc[user_id].sort_values(by='rating', ascending=False)['title'].tolist()
        except Exception:
            return []
        movie_list = titles.to_list()
        indices = [x for x in top_movie_list if x in movie_list]

        top_movies = best_movie_df.loc[best_movie_df['title'].isin(indices)]['title'].to_list()
        if (len(top_movies) > total_recom):
            return top_movies[:total_recom]
        return top_movies

    def get_recommendations(self, title, recom_number, indices, titles, cosine_sim):
        idx = indices[title]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:61]
        movie_indices = [i[0] for i in sim_scores]
        return titles.iloc[movie_indices].to_list()[0:recom_number]

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

    def test(self, db_train, db_test, train_cost):
        best_movie_df = pd.read_pickle(self.properties.get("model_aux_movie.dump.path").data)
        titles = best_movie_df['title']
        urd = pd.read_pickle(self.properties.get("model_aux_user.dump.path").data)
        test_start_time = time.time()
        test_df = db_test.filter(['user_id', 'title', 'rating']).query("rating >= 5")
        test_df = test_df.groupby('user_id').agg({'title': lambda x: set(x)}).reset_index()

        def f(x):
            movieIds = x['title']
            if len(movieIds) >= 4:
                return 'no'
            else:
                return 'yes'

        test_df['drop'] = test_df.apply(lambda x: f(x), axis=1)
        test_df = test_df.filter(['user_id', 'title', 'drop']).query("drop == 'no'")

        def f(x):
            try:
                user_id = x['user_id']
                movieIds = list(x['title'])
                rec = self.get_top_user_movies(user_id, urd, titles, best_movie_df)
                for m in movieIds:
                    if m in rec:
                        return "yes"
                    else:
                        return "no"
            except Exception:
                return "no"

        test_df['yes_no'] = test_df.apply(lambda x: f(x), axis=1)

        misses = len(test_df.filter(['user_id', 'title', 'rating', 'yes_no']).query("yes_no == 'yes'"))
        hits = len(test_df.filter(['user_id', 'title', 'rating', 'yes_no']).query("yes_no == 'no'"))
        test_end_time = time.time()

        logging.info("Offline evaluation completed.")
        logging.info("Number of filtered testing sample : {}".format(len(test_df)))
        logging.info(
            "Ratio of train : test = {}% : {}%".format(round(len(db_train) * 100 / (len(db_train) + len(db_test)), 2),
                                                       round((len(db_test) * 100 / (len(db_train) + len(db_test))), 2)))
        logging.info("Size of the Model : " + str(self.get_obj_size(urd)) + " bytes")
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

    def cache(self):
        logging.info("Starting the cache")
        best_movie_df = pd.read_pickle(self.properties.get("model_aux_movie.dump.path").data)
        urd = pd.read_pickle(self.properties.get("model_aux_user.dump.path").data)
        cosine_sim = np.load(self.properties.get("model.dump.path").data, allow_pickle=True)
        best_movie_df = best_movie_df.reset_index()
        titles = best_movie_df['title']
        indices = pd.Series(best_movie_df.index, index=best_movie_df['title'])
        count = 0
        api_dict = {
            "api_key": self.API_KEY,
            "user_recommendations": []
        }
        for user_id in urd.index.unique():
            try:
                recommended_movies = []
                top_movies = self.get_top_user_movies(user_id, urd, titles, best_movie_df)
                # if the user has no record in the system, or all the rated movies are removed, return chef's special
                if len(top_movies) == 0:
                    # logging.info('chefs special for {}'.format(user_id))
                    continue
                    # return give_chefs_sepcial(genre_list)
                temp = []
                for idx, movie in enumerate(top_movies):
                    temp.append(self.get_recommendations(movie, total_recom, indices, titles, cosine_sim))
                for i in range(total_recom):
                    for j in range(len(temp)):
                        if temp[j][i] not in recommended_movies:
                            recommended_movies.append(temp[j][i])
                    if len(recommended_movies) == total_recom:
                        break
                rec = ",".join(recommended_movies)
                api_dict["user_recommendations"].append({"user_id": str(user_id), "recommend": rec, "model_id": 1})
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
