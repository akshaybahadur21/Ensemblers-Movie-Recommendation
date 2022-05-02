import json

from kafka import KafkaConsumer
import requests
import csv
import pandas as pd
from src.utils.utils import eval_bool
import logging
from src.data_gen.data_validator import validate_movie_message, validate_rating_message, validate_user_message

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class DataGenerator:
    def __init__(self, properties):
        self.properties = properties
        self.consumer = KafkaConsumer(
            properties.get('kafka.consumer').data,
            bootstrap_servers=properties.get('kafka.bootstrap_servers').data,
            auto_offset_reset=properties.get('kafka.auto_offset_reset').data,
            enable_auto_commit=eval_bool(properties.get('kafka.enable_auto_commit').data),
            group_id=properties.get('kafka.group_id').data)

    @staticmethod
    def get_movie_id(message):
        return str(message).split(" ")[1].split("/")[3]

    @staticmethod
    def get_user_id(message):
        return str(message).split(",")[1]

    @staticmethod
    def get_requests(request):
        return requests.get(request)

    @staticmethod
    def write_to_file(movie, path):
        file = open(path, 'a+', newline='')
        with file:
            write = csv.writer(file)
            write.writerows(movie)
        file.close()

    @staticmethod
    def get_umr_from_rating_data(message):
        user_id = str(message).split(" ")[0].split(",")[1]
        movie_id = str(message).split(" ")[1].split("/")[2].split("=")[0]
        rating = str(message).split(" ")[1].split("/")[2].split("=")[1].split("'")[0]
        return user_id, movie_id, rating

    def generate_movie_metadata(self):
        data = []
        movie = []
        count = 0
        movie_set = set()

        for message in self.consumer:
            message = message.value
            if count == 10000:
                break
            try:
                if validate_movie_message(message):
                    movie_id = self.get_movie_id(message)
                    if movie_id in movie_set:
                        continue
                    movie_set.add(movie_id)
                    count += 1
                    r = self.get_requests("http://128.2.204.215:8080/movie/" + movie_id)
                    data.append(movie_id)
                    data.append(r.text)
                    movie.append(data)
                    data = []
                    if count % 100 == 0:
                        logging.info("Number of movies consumed : {}".format(count))
                        self.write_to_file(movie, self.properties.get('movie.path').data)
                        movie = []
            except Exception:
                logging.error("Data Quality Check: Message schema invalid for movie meta data")
                logging.error("Message from Kafka Stream: {}".format(message))

    def generate_user_metadata(self):
        count = 0
        user_set = set()
        for message in self.consumer:
            message = message.value
            if count == 10000:
                break
            try:
                if validate_user_message(message):
                    user_id = self.get_user_id(message)
                    if user_id in user_set:
                        continue
                    user_set.add(user_id)
                    count += 1
                    url = ("http://128.2.204.215:8080/user/" + user_id)
                    response = requests.request("GET", url)
                    if response.status_code != 200:
                        pass
                    elif count == 1:
                        data = pd.DataFrame.from_records([json.loads(response.text)])
                        data.to_csv(self.properties.get('user.path').data, index=False)
                        data = data[0:0]
                    else:
                        data = data.append(pd.DataFrame.from_records([json.loads(response.text)]))

                    #print(data)
                    if count % 100 == 0:
                        data.to_csv(self.properties.get('user.path').data, index=False, header=False, mode='a')
                        data[0:0]
            except Exception:
                logging.error("Data Quality Check: Message schema invalid for user meta data")
                logging.error("Message from Kafka Stream: {}".format(message))

    def generate_rating_data(self):
        data = []
        movie = []
        count = 0
        user_set = set()
        for message in self.consumer:
            message = message.value
            if count == 10000:
                break
            try:
                if validate_rating_message(message):
                    user_id, movie_id, rating = self.get_umr_from_rating_data(message)
                    if user_id + movie_id + rating in user_set:
                        continue
                    user_set.add(user_id + movie_id + rating)
                    count += 1
                    data.append(user_id)
                    data.append(movie_id)
                    data.append(rating)
                    movie.append(data)
                    data = []
                    if count % 100 == 0:
                        logging.info("Number of ratings consumed : {}".format(count))
                        self.write_to_file(movie, self.properties.get('rating.path').data)
                        movie = []
            except Exception:
                logging.error("Data Quality Check: Message schema invalid for rating meta data")
                logging.error("Message from Kafka Stream: {}".format(message))

    def generate(self):
        if eval_bool(self.properties.get("generate.data.movie").data):
            logging.info("Started Data Generation for movies")
            self.generate_movie_metadata()
        if eval_bool(self.properties.get("generate.data.user").data):
            logging.info("Started Data Generation for users")
            self.generate_user_metadata()
        if eval_bool(self.properties.get("generate.data.rating").data):
            logging.info("Started Data Generation for ratings")
            self.generate_rating_data()
