""" Request handlers for WebTransport client requests
"""

from uuid import uuid4

from messages import (
    ClientRequest, ServerResponse,
    CreateRoomRequest,
    CreateUserRequest, CreateUserResponse,
    JoinLobbyRequest, JoinedLobbyResponse,
    JoinRoomRequest, JoinedRoomResponse,
    LeaveRoomRequest, LeftRoomResponse,
    RequestErrorResponse,
    WebRTCOfferRequest, WebRTCAnswerResponse,
)

from rooms import Participant

from media_handler import MediaHandler


class UserError(Exception):
    code = "request-error"

class UserAlreadyCreated(UserError):
    code = "user-already-created"

class UserNotCreated(UserError):
    code = "user-not-created"


async def handle_not_implemented(request: ClientRequest) -> ServerResponse:
    return RequestErrorResponse(
        request_id=request.request_id,
        message=f"{request.type}-not-implemented",
    )

async def handle_webrtc_offer(session, request: ClientRequest) -> ServerResponse:
    assert isinstance(request, WebRTCOfferRequest)
    
    answer_sdp = await session.media.handle_webrtc_offer(request.sdp)

    return WebRTCAnswerResponse(
        request_id=request.request_id,
        sdp=answer_sdp,
    )


async def handle_create_user(session, request: ClientRequest) -> ServerResponse:
    assert isinstance(request, CreateUserRequest)

    if session.participant is not None:
        raise UserAlreadyCreated()

    user_name = request.user_name
    user_id = str(uuid4())

    participant = Participant(id=user_id, name=user_name)

    media = MediaHandler(
        participant=participant,
        room_manager=session.room_manager,
        send_message=session.send_message,
    )

    participant.on_track_published = media._subscribe_to_track
    participant.on_track_unpublished = media._unsubscribe_from_track

    session.participant = participant
    session.media = media

    return CreateUserResponse(
        request_id=request.request_id,
        id=user_id,
    )


async def handle_join_lobby(session, request: ClientRequest) -> ServerResponse:
    assert isinstance(request, JoinLobbyRequest)

    if session.participant is None:
        raise UserNotCreated()

    room = session.room_manager.join_room(
        session.participant,
        request.room_id,
    )

    return JoinedLobbyResponse(
        request_id=request.request_id,
        room=room,
    )


async def handle_join_room(session, request: ClientRequest) -> ServerResponse:
    assert isinstance(request, JoinRoomRequest)

    if session.participant is None:
        raise UserNotCreated()

    room = await session.room_manager.admit_participant(
        session.participant.id,
        session.participant.room_id,
    )

    return JoinedRoomResponse(
        request_id=request.request_id,
        room=room,
    )


async def handle_create_room(session, request: ClientRequest) -> ServerResponse:
    assert isinstance(request, CreateRoomRequest)

    if session.participant is None:
        raise UserNotCreated()

    room = session.room_manager.create_room(
        session.participant
    )

    return JoinedRoomResponse(
        request_id=request.request_id,
        room=room,
    )


async def handle_leave_room(session, request: ClientRequest) -> ServerResponse:
    assert isinstance(request, LeaveRoomRequest)

    if session.participant is None:
        raise UserNotCreated()

    room_id = session.participant.room_id

    await session.room_manager.leave_room(
        session.participant.id,
        room_id,
    )

    return LeftRoomResponse(
        request_id=request.request_id,
        room_id=room_id,
    )
