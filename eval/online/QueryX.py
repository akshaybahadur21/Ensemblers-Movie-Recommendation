import json
import logging
import os
import sys

import pandas as pd
import psutil
import requests
from dotenv import load_dotenv
from kafka import KafkaConsumer
from pymongo import MongoClient

from src.data_gen.DataGenerator import DataGenerator
from src.data_gen.data_validator import validate_rating_message
from src.utils.utils import get_properties, eval_bool

app_pass = "dspuakazwilyrauj"
sender = 'ensemblers.queryx@gmail.com'
receiver = ['akshayba@andrew.cmu.edu', "schannag@andrew.cmu.edu", "arpitagr@andrew.cmu.edu", "aizadkha@andrew.cmu.edu",
            "chihhaow@andrew.cmu.edu"]
subject = "QueryX Alert | ML in Production"


def send_email(user, pwd, recipient, subject, body):
    import smtplib

    FROM = user
    TO = recipient if isinstance(recipient, list) else [recipient]
    SUBJECT = subject
    TEXT = body

    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print('successfully sent the mail')
    except:
        print("failed to send mail")


logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class QueryX:
    def __init__(self):
        self.properties = get_properties(config_file)
        dotenv_path = self.properties.get("dotenv.path").data
        load_dotenv(dotenv_path)
        self.API_KEY = os.environ.get("API_KEY_PROD")
        self.endpoint = "http://128.2.205.123:8082/recommend/1"

    def test_kafka(self):
        try:
            properties = self.properties
            consumer = KafkaConsumer(
                properties.get('kafka.consumer').data,
                bootstrap_servers=properties.get('kafka.bootstrap_servers').data,
                auto_offset_reset=properties.get('kafka.auto_offset_reset').data,
                enable_auto_commit=eval_bool(properties.get('kafka.enable_auto_commit').data),
                group_id="movielog22-queryx-eval2")
            logging.info("Kafka Status : ONLINE")
        except Exception:
            logging.error("Error in connecting to Kafka")
            send_email(sender, app_pass, receiver, subject, "Error in connecting to Kafka")

    def test_API(self):
        try:
            r = requests.get(self.endpoint)
            if r.status_code == 200:
                logging.info("API Status : ONLINE")
            else:
                logging.error("Error in connecting to API")
                send_email(sender, app_pass, receiver, subject, "Error in connecting to API")
        except Exception:
            logging.error("Error in connecting to API")

    @staticmethod
    def test_mongo():
        try:
            client = MongoClient('localhost', 27017)
            logging.info("MongoDB Status : ONLINE")
        except Exception:
            logging.error("Error in connecting to Mongo")
            send_email(sender, app_pass, receiver, subject, "Error in connecting to Mongo")

    @staticmethod
    def test_system():
        try:
            ram = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent()
            if ram > 95 or cpu > 95:
                logging.error("RAM or CPU usage high")
                send_email(sender, app_pass, receiver, subject, "Error in connecting to system services")
            else:
                logging.info("System Status : ONLINE")
                logging.info("RAM usage : {}".format(ram))
                logging.info("CPU usage : {}".format(cpu))
        except Exception:
            logging.error("Error in connecting to system services")
            send_email(sender, app_pass, receiver, subject, "Error in connecting to system services")

    def test_model_quality(self):
        user_movie_dict = {}
        in_recommended_and_above_rating = 0  # Movie watched by user was in recommended list and rating provided is >= median of movie rating
        not_in_recommended_and_above_rating = 0  # Movie watched by user was not in recommended list and rating provided is >= median of movie rating
        in_recommended_and_below_rating = 0  # Movie watched by user in recommended list and rating provided is < median of movie rating
        not_in_recommended_and_below_rating = 0  # Movie watched by user was not in recommended list and rating provided is < median of movie rating
        tele = 0
        api_dict_telemetry = {
            "api_key": self.API_KEY,
            "filter": {
                "user_id": ""
            },
            "limit": 1
        }

        dir_path = os.path.dirname(os.path.realpath(__file__))
        rating_data = pd.read_csv(os.path.join(dir_path, "../../data/rating.csv"),
                                  names=["userId", "movieId", "rating"], header=None)
        properties = self.properties
        consumer = KafkaConsumer(
            properties.get('kafka.consumer').data,
            bootstrap_servers=properties.get('kafka.bootstrap_servers').data,
            auto_offset_reset=properties.get('kafka.auto_offset_reset').data,
            enable_auto_commit=eval_bool(properties.get('kafka.enable_auto_commit').data),
            group_id="movielog22-queryx-eval2")

        for message in consumer:
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
                                median_rating_for_movie = rating_data[(rating_data['movieId'] == movie)][
                                    'rating'].median()
                                if movie in movie_list and rating >= float(median_rating_for_movie):
                                    in_recommended_and_above_rating += 1
                                elif movie in movie_list and rating < float(median_rating_for_movie):
                                    in_recommended_and_below_rating += 1
                                elif movie not in movie_list and rating >= float(median_rating_for_movie):
                                    not_in_recommended_and_above_rating += 1
                                else:
                                    not_in_recommended_and_below_rating += 1
                            logging.info("Number of users that have liked our recommendation : {}".format(tele))
                            win_loss = in_recommended_and_above_rating + in_recommended_and_below_rating
                            logging.info("Win Loss of movie recommendations (QueryX) : {}%".format(
                                in_recommended_and_above_rating + in_recommended_and_below_rating))
                            win_loss_n = in_recommended_and_above_rating + not_in_recommended_and_below_rating
                            logging.info("Win loss based on both movie and rating (QueryX): {}%".format(
                                in_recommended_and_above_rating + not_in_recommended_and_below_rating))
                            if win_loss < 20 or win_loss_n < 20:
                                logging.error("Error in the Model Quality")
                                send_email(sender, app_pass, receiver, subject,
                                           "Error in the Model Quality")
                            else:
                                logging.info("Model Quality : OK")
                            break
            except Exception:
                pass

    def run(self):
        self.test_kafka()
        self.test_API()
        self.test_mongo()
        self.test_system()
        self.test_model_quality()


if __name__ == '__main__':
    num = len(sys.argv)
    if len(sys.argv) != 2:
        logging.error("Missing property file")
        raise ValueError("Missing property file")
    config_file = sys.argv[1]
    logging.info("QueryX Started")
    qx = QueryX()
    qx.run()
