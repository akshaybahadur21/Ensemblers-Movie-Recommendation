import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self) -> None:
        self.DEBUG = False
        self.SPECIAL_LIST = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(f"{dir_path}/special_list.txt", "r") as f:
            for line in f:
                self.SPECIAL_LIST.append(line.strip())

class DevelopmentConfig(Config):
    def __init__(self) -> None:
        super().__init__()
        self.DEBUG = True
        self.DATABASE_URI = os.environ['DATABASE_URI_DEV']
        self.API_KEY = os.environ['API_KEY_DEV']

class ProductionConfig(Config):
    def __init__(self) -> None:
        super().__init__()
        self.DATABASE_URI = os.environ['DATABASE_URI_PROD']
        self.API_KEY = os.environ['API_KEY_PROD']
