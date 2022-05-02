import logging
import os
import sys

from dotenv import load_dotenv
from kafka import KafkaConsumer

from eval.prod_test.LoadBalancer import LoadBalancer
from src.data_gen.DataGenerator import DataGenerator
from src.data_gen.data_validator import validate_rating_message
from src.utils.utils import get_properties, eval_bool

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class ABTest:
    def __init__(self, config_file):
        self.load_balancer = LoadBalancer()
        properties = get_properties(config_file)
        self.consumer = KafkaConsumer(
            properties.get('kafka.consumer').data,
            bootstrap_servers=properties.get('kafka.bootstrap_servers').data,
            auto_offset_reset=properties.get('kafka.auto_offset_reset').data,
            enable_auto_commit=eval_bool(properties.get('kafka.enable_auto_commit').data),
            group_id="movielog22-online-ab")
        dotenv_path = properties.get("dotenv.path").data
        load_dotenv(dotenv_path)
        self.API_KEY = os.environ.get("API_KEY_PROD")

    def evaluate_win_loss(self):
        user_movie_dict = {}
        tele_knn, tele_contnet = 0, 0
        total_knn, total_contnet = 0, 0
        for message in self.consumer:
            message = message.value
            try:
                if validate_rating_message(message):
                    user_id, movie_id, rating = DataGenerator.get_umr_from_rating_data(message)
                    rating = float(rating)
                    if rating == 5:
                        user_movie_dict[user_id] = []
                        user_movie_dict[user_id].append(movie_id)
                        if len(user_movie_dict) == 100:
                            for user, movie in user_movie_dict.items():
                                url = self.load_balancer.balance()
                                if url == "http://172.17.0.4:9001/recommend/":
                                    total_knn += 1
                                if url == "http://172.17.0.5:9002/recommend/":
                                    total_contnet += 1
                                r = DataGenerator.get_requests(url + user)
                                movie = movie[0]
                                movie_list = r.text.split(",")
                                if movie in movie_list and url == "http://172.17.0.4:9001/recommend/":
                                    tele_knn += 1
                                if movie in movie_list and url == "http://172.17.0.5:9002/recommend/":
                                    tele_contnet += 1
                            logging.info("Total Number of Users for this A/B Test Run : {}".format(len(user_movie_dict)))
                            logging.info("Number of users that received KNN recommendation : {}".format(total_knn))
                            logging.info("Number of users that liked KNN recommendation : {}".format(tele_knn))
                            logging.info(
                                "Customer Conversion Rate for KNN recommendations : {}%".format(
                                    round(tele_knn * 100 / total_knn), 2))

                            logging.info(
                                "Number of users that received ContNet recommendation : {}".format(total_contnet))
                            logging.info(
                                "Number of users that liked ContNet recommendation : {}".format(tele_contnet))
                            logging.info(
                                "Customer Conversion Rate for ContNet recommendations : {}%".format(
                                    round(tele_contnet * 100 / total_contnet), 2))
                            break
            except Exception:
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
    ab = ABTest(config_file)
    ab.run_ab_test()
