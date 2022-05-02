import logging

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


def validate_movie_message(message):
    try:
        movie_id = str(message).split(" ")[1].split("/")[3]
        # Checks missing values
        return len(movie_id) != 0
    except Exception:
        logging.error("Data Quality Check: Message schema invalid for movie meta data")
        logging.error("Message from Kafka Stream: {}".format(message))
        return False


def validate_rating_message(message):
    try:
        user_id = str(message).split(" ")[0].split(",")[1]
        movie_id = str(message).split(" ")[1].split("/")[2].split("=")[0]
        rating = str(message).split(" ")[1].split("/")[2].split("=")[1].split("'")[0]

        # Checks missing values and numeric values
        return len(movie_id) != 0 and len(user_id) != 0 and len(rating) != 0 and 0 <= int(
            rating) <= 5 and rating.isnumeric() and user_id.isnumeric()
    except Exception:
        logging.error("Data Quality Check: Message schema invalid for rating meta data")
        logging.error("Message from Kafka Stream: {}".format(message))
        return False


def validate_user_message(message):
    try:
        user_id = str(message).split(",")[1]

        # Checks missing values and numeric values
        return len(user_id) != 0 and user_id.isnumeric()
    except Exception:
        logging.error("Data Quality Check: Message schema invalid for user meta data")
        logging.error("Message from Kafka Stream: {}".format(message))
        return False
