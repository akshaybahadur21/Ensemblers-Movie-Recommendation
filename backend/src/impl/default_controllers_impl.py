from __future__ import annotations
from ensemblers_web.impl.utils import abort_with_error_message
from ensemblers_web.impl.db import get_api_key, get_fluent_logger
from ensemblers_web.impl.db_models.db_model import DBModelException
from ensemblers_web.impl.db_models.db_model import RecommendDBModel, EvaluationOnlineDBModel, TelemetryRecommendDBModel
from ensemblers_web.models.user_recommendation_upload import UserRecommendationUpload
from ensemblers_web.models.online_evaluation_upload import OnlineEvaluationUpload
from ensemblers_web.models.telemetry_recommend_request import TelemetryRecommendRequest
from ensemblers_web.models.telemetry_recommend_return import TelemetryRecommendReturn


def recommend_user_id_get(user_id: str) -> str:
    result = RecommendDBModel.find_one_by_id(user_id)
    logger = get_fluent_logger('telemetry')
    logger.emit('mongo.recommend', result)
    return result["recommend"]


def recommend_post(body: UserRecommendationUpload):
    body = body.to_dict()
    if body["api_key"] != get_api_key():
        abort_with_error_message(401, "Unauthorized access")
    else:
        try:
            result = RecommendDBModel.upsert_many(body["user_recommendations"])
        except DBModelException as e:
            return e.message
        return f"Total count: {result.upserted_count + result.modified_count}, Upserted count: {result.upserted_count}, Modified count: {result.modified_count}"


def telemetry_recommend_post(body: TelemetryRecommendRequest):
    body = body.to_dict()
    if body["api_key"] != get_api_key():
        abort_with_error_message(401, "Unauthorized access")
    else:
        filter = body["filter"]
        limit = body["limit"]
        telemetry_data = TelemetryRecommendDBModel.find(filter, limit)
        return TelemetryRecommendReturn(telemetry_data).to_dict()   


def online_evaluation_post(body: OnlineEvaluationUpload):
    body = body.to_dict()
    if body["api_key"] != get_api_key():
        abort_with_error_message(401, "Unauthorized access")
    else:
        try:
            result = EvaluationOnlineDBModel.insert_many(body["online_evaluations"])
        except DBModelException as e:
            return e.message
        return f"Inserted count: {result.inserted_count}"

