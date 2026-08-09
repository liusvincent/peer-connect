from typing import Annotated, Literal
from pydantic import BaseModel, Field, TypeAdapter, ConfigDict


# Shared Models
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


# Client Messages
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

class ClientEventBase(BaseModel):
    event_id: str

class WebRTCRenegotiationAnswer(ClientEventBase):
    type: Literal["webrtc-renegotiation-answer"]
    sdp: str

class WebRTCReady(ClientEventBase):
    type: Literal["webrtc-ready"] = "webrtc-ready"

ClientEvent = Annotated[
    WebRTCRenegotiationAnswer
    | WebRTCReady,
    Field(discriminator="type"),
]

ClientMessage = Annotated[
    ClientRequest | ClientEvent,
    Field(discriminator="type")
]


# Server Messages
class ServerResponseBase(BaseModel):
    request_id: str

class RequestErrorResponse(ServerResponseBase):
    type: Literal["request-error"] = "request-error"
    message: str

class WebRTCAnswerResponse(ServerResponseBase):
    type: Literal["webrtc-answer"] = "webrtc-answer"
    sdp: str

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

class ServerEventBase(BaseModel):
    event_id: str

class MediaSubscriptionInfo(BaseModel):
    mid: str
    participant_id: str
    track_id: str
    kind: Literal["audio", "video"]

class WebRTCRenegotiationOffer(ServerEventBase):
    type: Literal["webrtc-renegotiation-offer"] = "webrtc-renegotiation-offer"
    sdp: str
    media: list[MediaSubscriptionInfo]

ServerEvent = Annotated[
    WebRTCRenegotiationOffer,
    Field(discriminator="type")
]

ServerMessage = Annotated[
    ServerResponse | ServerEvent,
    Field(discriminator="type")
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