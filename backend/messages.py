"""File for standardized messaging over the WebTransport"""

from typing import Annotated, Literal
from pydantic import BaseModel, Field, TypeAdapter, ConfigDict

# Shared Model


class ParticipantInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    role: Literal["host", "co", "member"]


class RoomInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    participants: dict[str, ParticipantInfo]
    lobby: dict[str, ParticipantInfo]


class MediaSubscriptionHint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    participant_id: str
    track_id: str
    kind: Literal["audio", "video"]


class MediaSubscriptionInfo(MediaSubscriptionHint):
    model_config = ConfigDict(from_attributes=True)

    mid: str


# Client Request


class ClientRequestBase(BaseModel):
    request_id: str


class WebRTCOfferRequest(ClientRequestBase):
    type: Literal["webrtc-offer"]
    sdp: str


class CreateUserRequest(ClientRequestBase):
    type: Literal["create-user"]
    user_name: str


class CreateRoomRequest(ClientRequestBase):
    type: Literal["create-room"]


class JoinLobbyRequest(ClientRequestBase):
    type: Literal["join-lobby"]
    room_id: str


class JoinRoomRequest(ClientRequestBase):
    type: Literal["join-room"]


class LeaveRoomRequest(ClientRequestBase):
    type: Literal["leave-room"]


ClientRequest = Annotated[
    WebRTCOfferRequest
    | CreateUserRequest
    | CreateRoomRequest
    | JoinLobbyRequest
    | JoinRoomRequest
    | LeaveRoomRequest,
    Field(discriminator="type"),
]

# Client Event


class ClientEventBase(BaseModel):
    event_id: str


class WebRTCReady(ClientEventBase):
    type: Literal["webrtc-ready"] = "webrtc-ready"


ClientEvent = Annotated[
    WebRTCReady,
    Field(discriminator="type"),
]

# Client Message

ClientMessage = Annotated[ClientRequest | ClientEvent, Field(discriminator="type")]

# Server Resopnse


class ServerResponseBase(BaseModel):
    request_id: str


class RequestErrorResponse(ServerResponseBase):
    type: Literal["request-error"] = "request-error"
    message: str


class WebRTCAnswerResponse(ServerResponseBase):
    type: Literal["webrtc-answer"] = "webrtc-answer"
    sdp: str
    media_info: list[MediaSubscriptionInfo]


class CreateUserResponse(ServerResponseBase):
    type: Literal["user-answer"] = "user-answer"
    id: str


class JoinedRoomResponse(ServerResponseBase):
    type: Literal["joined-room"] = "joined-room"
    room: RoomInfo


class JoinedLobbyResponse(ServerResponseBase):
    type: Literal["joined-lobby"] = "joined-lobby"
    room: RoomInfo


class LeftRoomResponse(ServerResponseBase):
    type: Literal["left-room"] = "left-room"
    room_id: str


ServerResponse = Annotated[
    WebRTCAnswerResponse
    | CreateUserResponse
    | RequestErrorResponse
    | JoinedRoomResponse
    | JoinedLobbyResponse
    | LeftRoomResponse,
    Field(discriminator="type"),
]

# Server Event


class ServerEventBase(BaseModel):
    event_id: str


class WebRTCOfferNeeded(ServerEventBase):
    type: Literal["webrtc-offer-needed"] = "webrtc-offer-needed"
    media_hint: list[MediaSubscriptionHint]


class RoomUpdated(ServerEventBase):
    type: Literal["room-updated"] = "room-updated"
    room: RoomInfo


class EventErrorResponse(ServerEventBase):
    type: Literal["event-error"] = "event-error"
    message: str


ServerEvent = Annotated[
    WebRTCOfferNeeded | RoomUpdated | EventErrorResponse, Field(discriminator="type")
]

# Server Message


class MessageErrorResponse(BaseModel):
    type: Literal["message-error"] = "message-error"
    message: str


ServerMessage = Annotated[
    ServerResponse | ServerEvent | MessageErrorResponse, Field(discriminator="type")
]

# Helper Functions

client_message_adapter = TypeAdapter(ClientMessage)


def parse_client_message(data: object) -> ClientMessage:
    return client_message_adapter.validate_python(data)


server_message_adapter = TypeAdapter(ServerMessage)


def serialize_server_message(message: ServerMessage) -> dict:
    """Validate a response and convert it into a JSON-compatible dictionary."""
    validated = server_message_adapter.validate_python(message)
    return validated.model_dump(mode="json")
