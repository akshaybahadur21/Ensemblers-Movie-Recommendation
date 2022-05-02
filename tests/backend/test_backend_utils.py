import pytest
import connexion
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response

from backend.src.impl.utils import abort_with_error_message

@pytest.fixture()
def app():
    app = connexion.App(__name__)
    yield app.app


def test_abort_with_error_message_type_error():
    with pytest.raises(TypeError):
        abort_with_error_message()


def test_abort_with_error_message(app):
    with app.app_context():
        try:
            abort_with_error_message("401", "Unauthorized")
        except Exception as e:
            assert type(e) is HTTPException
            response = e.get_response()
            assert isinstance(response, Response) 
            assert response.status == "401 UNAUTHORIZED"
