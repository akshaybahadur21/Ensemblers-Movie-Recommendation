import sys
import logging
from src.data_gen.DataGenerator import DataGenerator
from src.model_train.ModelTrainer import ModelTrainer
from src.utils.utils import get_properties, eval_bool, print_banner

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class MovieRecommendation:
    def __init__(self, config_file):
        print_banner()
        self.properties = get_properties(config_file)

    def recommend(self):
        logging.info("Starting the application")
        if eval_bool(self.properties.get("generate.data").data):
            logging.info("Started Data Generation")
            data_gen = DataGenerator(self.properties)
            data_gen.generate()
        if eval_bool(self.properties.get("model.train").data):
            logging.info("Started Model Training")
            model_trainer = ModelTrainer(self.properties)
            model_trainer.train()


if __name__ == '__main__':
    num = len(sys.argv)
    if len(sys.argv) != 2:
        logging.error("Missing property file")
        raise ValueError("Missing property file")
    config_file = sys.argv[1]
    logging.info("Movie Recommendation Started")
    movie_recommendation = MovieRecommendation(config_file)
    movie_recommendation.recommend()
    logging.info("Movie Recommendation finished")
