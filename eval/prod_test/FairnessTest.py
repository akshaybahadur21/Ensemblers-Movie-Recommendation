import json
import logging
import os
import sys

import requests
from dotenv import load_dotenv
from kafka import KafkaConsumer

from eval.prod_test.LoadBalancer import LoadBalancer
from src.data_gen.DataGenerator import DataGenerator
from src.data_gen.data_validator import validate_rating_message
from src.utils.utils import get_properties, eval_bool

import pandas as pd

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

user_thresh = 50  # 50 users


class FairnessTest:
    def __init__(self, config_file):
        self.load_balancer = LoadBalancer()
        properties = get_properties(config_file)
        self.consumer = KafkaConsumer(
            properties.get('kafka.consumer').data,
            bootstrap_servers=properties.get('kafka.bootstrap_servers').data,
            auto_offset_reset=properties.get('kafka.auto_offset_reset').data,
            enable_auto_commit=eval_bool(properties.get('kafka.enable_auto_commit').data),
            group_id="movielog22-online-abs1")
        dotenv_path = properties.get("dotenv.path").data
        load_dotenv(dotenv_path)
        self.API_KEY = os.environ.get("API_KEY_PROD")
        self.user_info = pd.read_csv('../../data/user.csv')

    def isFemaleOrMale(self, user_id):
        '''
            return F if female and M if male
            -1 if the record is not available
        '''
        try:
            url = ("http://128.2.204.215:8080/user/" + user_id)
            response = requests.request("GET", url)
            data = json.loads(response.text)
            return data['gender']
        except Exception:
            return -1

    def evaluate_win_loss(self):
        user_movie_dict_male = {}
        user_movie_dict_female = {}

        tele_knn_F, tele_knn_M, tele_contnet_F, tele_contnet_M = 0, 0, 0, 0
        total_knn_F, total_knn_M, total_contnet_F, total_contnet_M = 0, 0, 0, 0
        for message in self.consumer:
            message = message.value
            try:
                if validate_rating_message(message):
                    user_id, movie_id, rating = DataGenerator.get_umr_from_rating_data(message)
                    rating = float(rating)
                    if rating >= 4:
                        gender = self.isFemaleOrMale(user_id)
                        if gender == -1:
                            continue
                        if gender == 'F':
                            if len(user_movie_dict_female) == user_thresh:
                                continue
                            user_movie_dict_female[user_id] = []
                            user_movie_dict_female[user_id].append(movie_id)
                        else:
                            if len(user_movie_dict_male) == user_thresh:
                                continue
                            user_movie_dict_male[user_id] = []
                            user_movie_dict_male[user_id].append(movie_id)

                        if len(user_movie_dict_male) >= user_thresh and len(user_movie_dict_female) >= user_thresh:

                            for user, movie in user_movie_dict_female.items():
                                url = self.load_balancer.balance()
                                if url == "http://172.17.0.4:9001/recommend/":
                                    total_knn_F += 1
                                if url == "http://172.17.0.5:9002/recommend/":
                                    total_contnet_F += 1
                                r = DataGenerator.get_requests(url + user)
                                movie = movie[0]
                                movie_list = r.text.split(",")
                                if movie in movie_list and url == "http://172.17.0.4:9001/recommend/":
                                    tele_knn_F += 1
                                if movie in movie_list and url == "http://172.17.0.5:9002/recommend/":
                                    tele_contnet_F += 1

                            for user, movie in user_movie_dict_male.items():
                                url = self.load_balancer.balance()
                                if url == "http://172.17.0.4:9001/recommend/":
                                    total_knn_M += 1
                                if url == "http://172.17.0.5:9002/recommend/":
                                    total_contnet_M += 1
                                r = DataGenerator.get_requests(url + user)
                                movie = movie[0]
                                movie_list = r.text.split(",")
                                if movie in movie_list and url == "http://172.17.0.4:9001/recommend/":
                                    tele_knn_M += 1
                                if movie in movie_list and url == "http://172.17.0.5:9002/recommend/":
                                    tele_contnet_M += 1

                            logging.info("Total Number of Users for this Fairness Test Run : {}".format(
                                len(user_movie_dict_female) + len(user_movie_dict_male)))
                            logging.info("Total Number of Male Users for this Fairness Test Run : {}".format(
                                len(user_movie_dict_male)))
                            logging.info("Total Number of Female Users for this Fairness Test Run : {}".format(
                                len(user_movie_dict_female)))

                            logging.info(
                                "Number of Female users that received KNN recommendation : {}".format(total_knn_F))
                            logging.info(
                                "Number of Male users that received KNN recommendation : {}".format(total_knn_M))

                            logging.info("Number of Female users that liked KNN recommendation : {}".format(tele_knn_F))
                            logging.info("Number of Male users that liked KNN recommendation : {}".format(tele_knn_M))
                            logging.info(
                                "Female Customer Conversion Rate for KNN recommendations : {}%".format(
                                    round(tele_knn_F * 100 / total_knn_F), 2))
                            logging.info(
                                "Male Customer Conversion Rate for KNN recommendations : {}%".format(
                                    round(tele_knn_M * 100 / total_knn_M), 2))

                            logging.info(
                                "Number of Female users that received ContNet recommendation : {}".format(
                                    total_contnet_F))
                            logging.info(
                                "Number of Male users that received ContNet recommendation : {}".format(
                                    total_contnet_M))

                            logging.info(
                                "Number of Female users that liked ContNet recommendation : {}".format(tele_contnet_F))
                            logging.info(
                                "Number of Male users that liked ContNet recommendation : {}".format(tele_contnet_M))
                            logging.info(
                                "Female Customer Conversion Rate for ContNet recommendations : {}%".format(
                                    round(tele_contnet_F * 100 / total_contnet_F), 2))
                            logging.info(
                                "Male Customer Conversion Rate for ContNet recommendations : {}%".format(
                                    round(tele_contnet_M * 100 / total_contnet_M), 2))
                            break
            except Exception as e:
                logging.error(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
                logging.error("Data Quality Check: Message schema invalid for movie meta data")
                logging.error("Message from Kafka Stream: {}".format(message))
                break

    def run_ab_test(self):
        self.evaluate_win_loss()


if __name__ == '__main__':
    num = len(sys.argv)
    if len(sys.argv) != 2:
        logging.error("Missing property file")
        raise ValueError("Missing property file")
    config_file = sys.argv[1]
    logging.info("Movie Recommendation Started")
    ab = FairnessTest(config_file)
    ab.run_ab_test()
