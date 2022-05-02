import logging
from src.model_train.CollabFilteringModel import CollabFilteringModel

from src.model_train.ContNetModel import ContNetModel
from src.model_train.KNNModel import KNNModel
from src.utils.utils import eval_bool

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


class ModelTrainer:
    def __init__(self, properties):
        self.properties = properties

    def train(self):
        logging.info("Selected the Model : {}".format(str(self.properties.get("model.type").data).lower()))
        model_list = str(self.properties.get("model.type").data).lower().strip('][').split(',')
        for m in model_list:
            if m.strip().lower() == "collaborative filtering":
                collab_filter = CollabFilteringModel(self.properties)
                logging.info("Starting to train the model")
                collab_filter.train()
                logging.info("Starting to cache the model")
                collab_filter.predict()

            elif m.strip().lower() == "ContNet".lower():
                contnet = ContNetModel(self.properties)
                logging.info("Starting to train the model")
                for i in range(10):
                    db_train, db_test, train_cost = contnet.train()
                    logging.info("Starting to test the model")
                    contnet.test(db_train, db_test, train_cost)
                if eval_bool(self.properties.get("model.cache").data):
                    logging.info("Starting to cache the model")
                    contnet.cache()
                contnet.run.stop()

            elif m.strip().lower() == "knn":
                knn_model = KNNModel(self.properties)
                logging.info("Starting to train the model")
                for i in range(10):
                    X, user_mapper, movie_mapper, user_inv_mapper, movie_inv_mapper, db_test, db_train, train_cost = knn_model.train()
                    logging.info("Starting to test the model")
                    knn_model.test(db_train, db_test, X, movie_mapper, movie_inv_mapper, train_cost)
                if eval_bool(self.properties.get("model.cache").data):
                    logging.info("Starting to cache the model")
                    knn_model.cache(X, movie_mapper, movie_inv_mapper)
                knn_model.run

            else:
                logging.error("Selected Model does not have an implementation")
