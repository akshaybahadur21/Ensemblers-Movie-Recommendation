import random, logging
from typing import List, Dict, Optional
from datetime import datetime
from timeit import default_timer
from pymongo import InsertOne, ReplaceOne
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult, DeleteResult, BulkWriteResult
from pymongo.errors import DuplicateKeyError, BulkWriteError
from ensemblers_web.impl.utils import abort_with_error_message
from ensemblers_web.impl.db import get_db, get_special_list
from bson.objectid import InvalidId

EXCEPTION_COLLECTION_NAME_NOT_DEFINED = "collection_name not defined"
EXCEPTION_COLLECTION_NOT_EXIST = "collection: {} does not exist"
EXCEPTION_DUP_KEY = "duplicated key found in collection {}. consider removing the entire collection!"
ERROR_INVALID_ID = "_id: {} is not a valid MongoDB _id"

class DBModel:
    _database_name: str
    _collection_name: str

    @classmethod
    def get_database(cls):
        return get_db().cx[cls._database_name]

    @classmethod
    def get_collection(cls, collection_name: str, check_collection_exist=True):
        database = cls.get_database()
        if check_collection_exist:
            collection_names = database.list_collection_names()
            if collection_name in collection_names:
                return database.get_collection(collection_name)
            raise DBModelException(EXCEPTION_COLLECTION_NOT_EXIST.format(collection_name))
        return database.get_collection(collection_name)

    @classmethod
    def drop_collection(cls, check_collection_exist=False):
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)
        cls.get_collection(cls._collection_name, check_collection_exist).drop()

    @classmethod
    def insert_one(cls, document: dict, check_collection_exist=True) -> InsertOneResult:
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)
        return cls.get_collection(cls._collection_name, check_collection_exist).insert_one(document)

    @classmethod
    def insert_many(cls, documents: List[dict], check_collection_exist=True) -> InsertManyResult:
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)
        return cls.get_collection(cls._collection_name, check_collection_exist).insert_many(documents)

    @classmethod
    def find_one_by_id(cls, _id: str, projection: Optional[Dict] = None):
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)
        try:
            return cls.get_collection(cls._collection_name).find_one({"_id": _id}, projection)
        except InvalidId as e:
            abort_with_error_message(400, ERROR_INVALID_ID.format(_id))

    @classmethod
    def delete_one_by_id(cls, _id: str):
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)
        try:
            result: DeleteResult = cls.get_collection(
                cls._collection_name).delete_one({"_id": _id})
            if int(result.deleted_count) == 1:
                return True
            return False

        except InvalidId as e:
            abort_with_error_message(400, ERROR_INVALID_ID.format(_id))

    @classmethod
    def find(cls, filter: Optional[dict] = None, sort: Optional[list] = None, limit: int = 10):
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)

        if filter is None:
            filter = {}
        cursor = cls.get_collection(
            cls._collection_name).find(filter)
        if sort is not None:
            cursor = cursor.sort(sort)

        cursor = cursor.limit(limit)
        return cursor


class RecommendDBModel(DBModel):
    _database_name = "ensemblers_web"
    _collection_name = "recommend"

    @classmethod
    def find_one_by_id(cls, user_id: str, projection: Optional[Dict] = None):
        # in projection, 0 excludes the field while 1 includes.
        document = super().find_one_by_id(user_id, {"_id": 0, "recommend": 1, "model_id": 1})
        user_id_exists: bool = document is not None
        inference_time: float = None
        timestamp = datetime.now().strftime("%d/%b/%Y:%H:%M:%S")
        model_id = 0
        if document is not None and "model_id" in document:
            model_id = document["model_id"]
        if user_id_exists:
            start = default_timer()
            recommend = document["recommend"]
            end = default_timer()
            inference_time = 1000 * (end - start) # in milliseconds
        else:
            special_list = random.choices(get_special_list(), k=20)
            recommend = ",".join(special_list)
        return {
            "user_id": user_id,
            "user_id_exists": user_id_exists,
            "model_id": model_id,
            "inference_time": inference_time,
            "recommend": recommend,
            "timestamp": timestamp
        }

    @classmethod
    def insert_many(cls, documents: List[dict], check_collection_exist=True) -> InsertManyResult:
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)
        # Must do id replacement here because swagger overwrites "_id" to "id"
        for document in documents:
            document["_id"] = document["user_id"]
            del document["user_id"]
        try:
            result = cls.get_collection(cls._collection_name, check_collection_exist).insert_many(documents)
        except BulkWriteError as e:
            raise DBModelException(e.details)
        return result

    @classmethod
    def upsert_many(cls, documents: List[dict], check_collection_exist=True) -> BulkWriteResult:
        """
        Mongo has no direct methods of inserting while updating existing documents.
        So we rely on a bulk write of multiple "replace ones + upsert"
        https://stackoverflow.com/questions/49068960/mongoose-nodejs-replace-many-documents-in-one-i-o
        """
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)

        write_ops = []
        for document in documents:
            # Must do id replacement here because swagger overwrites "_id" to "id"
            filter = {"_id": document["user_id"]}
            replacement = {"_id": document["user_id"], "recommend": document["recommend"]}
            write_ops.append(
                ReplaceOne(filter, replacement, upsert=True)
            )
        try:
            result = cls.get_collection(cls._collection_name, check_collection_exist).bulk_write(write_ops)
        except BulkWriteError as e:
            raise DBModelException(e.details)
        return result


class EvaluationOnlineDBModel(DBModel):
    _database_name = "ensemblers_web"
    _collection_name = "evaluation_online"
        
    @classmethod
    def insert_many(cls, documents: List[dict], check_collection_exist=True) -> BulkWriteResult:
        if not cls._collection_name:
            raise DBModelException(EXCEPTION_COLLECTION_NAME_NOT_DEFINED)
        
        server_time = datetime.now()
        server_timestamp = server_time.strftime("%d/%b/%Y:%H:%M:%S")

        write_ops = []
        for document in documents:
            document["server_time"] = server_time
            document["server_timestamp"] = server_timestamp
            write_ops.append(
                InsertOne(document)
            )
        try:
            result = cls.get_collection(cls._collection_name, check_collection_exist).bulk_write(write_ops)
        except BulkWriteError as e:
            raise DBModelException(e.details)
        return result


class TelemetryRecommendDBModel(DBModel):
    _database_name = "ensemblers_web"
    _collection_name = "telemetry_recommend"

    @classmethod
    def find(cls, filter: dict, limit):
        """
        Index in MongoDB has been created.
        { "user_id": 1, "time": -1 }
        """
        sort = None
        cursor = super().find(filter, sort, limit)
        results = list(cursor)
        for result in results:
            result["_id"] = str(result["_id"])
        return results


class DBModelException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
