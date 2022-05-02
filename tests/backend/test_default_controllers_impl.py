from os.path import dirname, abspath, join
import sys
import pytest


# IMPORTANT: Make sure to run ./openapi/gen_api_layer.sh before running this test!
# Add module directory
ensemblers_web_module_dir = join(dirname(dirname(dirname(abspath(__file__)))), "backend/src/gen")
sys.path.append(ensemblers_web_module_dir)


def mock_get_api_key():
    return "123"


class MockFluentLogger:
    def emit(self, name, result):
        pass


def mock_get_fluent_logger(name):
    return MockFluentLogger()


class MockBulkWriteResult:
    def __init__(self, inserted_count=None, upserted_count=None, modified_count=None):
        self.inserted_count = inserted_count
        self.upserted_count = upserted_count
        self.modified_count = modified_count


class MockRecommendDBModel:
    @classmethod
    def find_one_by_id(cls, _id):
        return {"_id": "0", "recommend": "1,2,3,4,5"}

    @classmethod
    def upsert_many(cls, documents):
        return MockBulkWriteResult(upserted_count=len(documents), modified_count=0)

class MockTelemetryRecommendDBModel:
    @classmethod
    def find(cls, filter, limit):
        if filter["user_id"] != "1":
            return []
        return [{"user_id": "1", "recommend": "1,2,3,4,5"}][:limit]

class MockEvaluationOnlineDBModel:
    @classmethod
    def insert_many(cls, documents):
        return MockBulkWriteResult(inserted_count=len(documents))


def test_recommend_user_id_get(monkeypatch):
    # Init all monkeypatches here:
    monkeypatch.setattr("ensemblers_web.impl.db.get_fluent_logger", mock_get_fluent_logger)
    monkeypatch.setattr("ensemblers_web.impl.db.get_api_key", mock_get_api_key)
    monkeypatch.setattr("ensemblers_web.impl.db_models.db_model.RecommendDBModel", MockRecommendDBModel)
    monkeypatch.setattr("ensemblers_web.impl.db_models.db_model.TelemetryRecommendDBModel", MockTelemetryRecommendDBModel)
    monkeypatch.setattr("ensemblers_web.impl.db_models.db_model.EvaluationOnlineDBModel", MockEvaluationOnlineDBModel)
    from ensemblers_web.impl.default_controllers_impl import recommend_user_id_get
    user_id = "1"
    assert recommend_user_id_get(user_id) == MockRecommendDBModel.find_one_by_id(user_id)["recommend"]


def test_recommend_post(monkeypatch):
    from ensemblers_web.impl.default_controllers_impl import recommend_post
    from ensemblers_web.models.user_recommendation_upload import UserRecommendationUpload
    body = {
        "api_key": mock_get_api_key(),
        "user_recommendations": [
            {
            "model_id": 0,
            "recommend": "1,2,3,4,5",
            "user_id": "1"
            }
        ]
    }
    body = UserRecommendationUpload(**body)
    upserted_count = len(body.user_recommendations)
    modified_count = 0
    assert recommend_post(body) == \
        f"Total count: {upserted_count + modified_count}, Upserted count: {upserted_count}, Modified count: {modified_count}"


def test_telemetry_recommend_post(monkeypatch):
    from ensemblers_web.impl.default_controllers_impl import telemetry_recommend_post
    from ensemblers_web.models.telemetry_recommend_request import TelemetryRecommendRequest
    filter = { "user_id": "1" }
    limit = 1
    body = {
        "api_key": mock_get_api_key(),
        "filter": filter,
        "limit": limit
    }
    body = TelemetryRecommendRequest(**body)
    response = {
        "telemetry_data": MockTelemetryRecommendDBModel.find(filter, limit)
    }
    assert telemetry_recommend_post(body) == response


def test_online_evaluation_post():
    from ensemblers_web.impl.default_controllers_impl import online_evaluation_post
    from ensemblers_web.models.online_evaluation_upload import OnlineEvaluationUpload
    body = {
        "api_key": mock_get_api_key(),
        "online_evaluations": [{"metric1": 0}]
    }
    inserted_count = len(body["online_evaluations"])
    body = OnlineEvaluationUpload(**body)
    assert online_evaluation_post(body) == f"Inserted count: {inserted_count}"
    