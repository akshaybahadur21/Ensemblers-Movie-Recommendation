import sys
import os
import logging
import pandas as pd
import requests
from kafka import KafkaConsumer
from dotenv import load_dotenv
from datetime import datetime
import json

from src.data_gen.DataGenerator import DataGenerator
from src.data_gen.data_validator import validate_rating_message
from src.utils.utils import get_properties, eval_bool

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class OnlineModelEval:
    def __init__(self):
        properties = get_properties(config_file)
        self.consumer = KafkaConsumer(
            properties.get('kafka.consumer').data,
            bootstrap_servers=properties.get('kafka.bootstrap_servers').data,
            auto_offset_reset=properties.get('kafka.auto_offset_reset').data,
            enable_auto_commit=eval_bool(properties.get('kafka.enable_auto_commit').data),
            group_id="movielog22-online-eval")
        dotenv_path = properties.get("dotenv.path").data
        load_dotenv(dotenv_path)
        self.properties = properties
        self.API_KEY = os.environ.get("API_KEY_PROD")

    def evaluate_win_loss(self):
        user_movie_dict = {}

        in_recommended_and_above_rating = 0  # Movie watched by user was in recommended list and rating provided is >= median of movie rating
        not_in_recommended_and_above_rating = 0  # Movie watched by user was not in recommended list and rating provided is >= median of movie rating
        in_recommended_and_below_rating = 0  # Movie watched by user in recommended list and rating provided is < median of movie rating
        not_in_recommended_and_below_rating = 0  # Movie watched by user was not in recommended list and rating provided is < median of movie rating
        tele = 0
        api_dict = {
            "api_key": self.API_KEY,
            "online_evaluations": []
        }
        api_dict_telemetry = {
            "api_key": self.API_KEY,
            "filter": {
                "user_id": "16541"
            },
            "limit": 1
        }

        dir_path = os.path.dirname(os.path.realpath(__file__))
        rating_data = pd.read_csv(os.path.join(dir_path, "../../data/rating.csv"),
                                  names=["userId", "movieId", "rating"], header=None)
        for message in self.consumer:
            message = message.value
            try:
                if validate_rating_message(message):
                    user_id, movie_id, rating = DataGenerator.get_umr_from_rating_data(message)
                    api_dict_telemetry["filter"]["user_id"] = user_id
                    r = requests.post("http://128.2.205.123:8082/telemetry_recommend", json=api_dict_telemetry)
                    json_object = json.loads(r.text)
                    prev_rec = str(json_object['telemetry_data'][0]['recommend']).split(",")
                    if json_object['telemetry_data'][0]['user_id_exists']:
                        rating = float(rating)
                        # if int(rating) == 5:
                        user_movie_dict[user_id] = []
                        user_movie_dict[user_id].append(movie_id)
                        user_movie_dict[user_id].append(prev_rec)
                        if len(user_movie_dict) == 100:
                            for user, movie in user_movie_dict.items():
                                r = DataGenerator.get_requests("http://128.2.205.123:8082/recommend/" + user)
                                movie_list = r.text.split(",")
                                prev_rec = movie[1]
                                movie = movie[0]
                                if movie in prev_rec:
                                    tele += 1
                                median_rating_for_movie = rating_data[(rating_data['movieId'] == movie)]['rating'].median()
                                if movie in movie_list and rating >= float(median_rating_for_movie):
                                    in_recommended_and_above_rating += 1
                                elif movie in movie_list and rating < float(median_rating_for_movie):
                                    in_recommended_and_below_rating += 1
                                elif movie not in movie_list and rating >= float(median_rating_for_movie):
                                    not_in_recommended_and_above_rating += 1
                                else:
                                    not_in_recommended_and_below_rating += 1
                            logging.info("Number of users that have liked our recommendation : {}".format(tele))
                            api_dict["online_evaluations"].append({
                                "evaluation": {
                                    "user_likes": tele,
                                    "timestamp": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                                },
                                "model_id": 0
                            })
                            logging.info("Win Loss of movie recommendation (Online Evaluation) : {}%".format(
                                in_recommended_and_above_rating + in_recommended_and_below_rating))
                            api_dict["online_evaluations"].append({
                                "evaluation": {
                                    "win_loss": in_recommended_and_above_rating + in_recommended_and_below_rating,
                                    "timestamp": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                                },
                                "model_id": 0
                            })
                            logging.info("Win loss based on both movie and rating (Online evaluation): {}%".format(
                                in_recommended_and_above_rating + not_in_recommended_and_below_rating))
                            api_dict["online_evaluations"].append({
                                "evaluation": {
                                    "win_loss_mr": in_recommended_and_above_rating + not_in_recommended_and_below_rating,
                                    "timestamp": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                                },
                                "model_id": 0
                            })
                            r = requests.post(self.properties.get("eval_online.api").data, json=api_dict)
                            if r.status_code != 200:
                                logging.error("Couldn't post online evaluation")
                            break
            except Exception:
                logging.error("Data Quality Check: Message schema invalid for movie meta data")
                logging.error("Message from Kafka Stream: {}".format(message))


if __name__ == '__main__':
    num = len(sys.argv)
    if len(sys.argv) != 2:
        logging.error("Missing property file")
        raise ValueError("Missing property file")
    config_file = sys.argv[1]
    logging.info("Movie Recommendation Started")
    online_eval = OnlineModelEval()
    online_eval.evaluate_win_loss()
