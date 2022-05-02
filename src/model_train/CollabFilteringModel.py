import logging

import pandas as pd
import surprise.dump
from surprise import Dataset
from surprise import KNNWithMeans
from surprise import Reader

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

class CollabFilteringModel:
    def __init__(self, properties):
        self.properties = properties

    def train(self):
        df = pd.read_csv(self.properties.get("model.data.path").data)
        df.drop_duplicates(subset=["user_id", "movie", "rating"],
                           keep='last', inplace=True)
        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(df[["user_id", "movie", "rating"]], reader)
        sim_options = {
            "name": "cosine",
            "user_based": True,
        }
        algo = KNNWithMeans(sim_options=sim_options)
        trainingSet = data.build_full_trainset()
        logging.info("Fitting")
        algo.fit(trainingSet)
        surprise.dump.dump(self.properties.get("model.dump.path").data, algo)
        logging.info("Done")

    def predict(self):
        logging.info("Predicting")
        algo = surprise.dump.load(self.properties.get("model.load.path").data)[0]
        prediction = algo.predict(16541, "apollo+13+1995")
        logging.info(prediction.est)
        prediction = algo.predict(84312, "dead+men+dont+wear+plaid+1982")
        logging.info(prediction.est)
