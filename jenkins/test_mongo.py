from pymongo import MongoClient

try:
    client = MongoClient('localhost', 27017)
    print("MongoDB Status : ONLINE")
except Exception:
    print("Error in connecting to Mongo")
    exit(1)
