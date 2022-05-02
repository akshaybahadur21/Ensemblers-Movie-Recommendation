from flask import abort, jsonify


def abort_with_error_message(status_code: int, message: str):
    response = jsonify({"message": message})
    response.status_code = status_code
    abort(response)
