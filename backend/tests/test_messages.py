import pytest
from pydantic import ValidationError

from messages import (
    CreateUserRequest,
    parse_client_message,
    serialize_server_message,
)


@pytest.fixture
def client_message():
    return {
        "type": "create-user",
        "request_id": "request-1",
        "user_name": "Alice",
    }


def test_parse_client_message(client_message):
    result = parse_client_message(client_message)

    assert isinstance(result, CreateUserRequest)
    assert result.request_id == "request-1"
    assert result.user_name == "Alice"


def test_parse_client_message_rejects_invalid():
    with pytest.raises(ValidationError):
        parse_client_message(
            {
                "type": "invalid-type",
                "request_id": "request-1",
            }
        )


@pytest.fixture
def server_message():
    return {
        "type": "message-error",
        "message": "Invalid message",
    }


def test_serialize_server_message(server_message):
    result = serialize_server_message(server_message)

    assert result == server_message


def test_serialize_server_message_rejects_invalid():
    with pytest.raises(ValidationError):
        serialize_server_message({"type": "message-error"})
