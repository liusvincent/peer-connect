from uuid import uuid4

# custom exceptions
class RoomError(Exception):
    code = "room-error"

class RoomNotFound(RoomError):
    code = "room-not-found"

class ParticipantAlreadyJoined(RoomError):
    code = "participant-already-joined"

class ParticipantNotFound(RoomError):
    code = "participant-not-found"
# end of custom exceptions

class Participant:
    def __init__(self, id: str, name: str, stream_id: int) -> None:
        self.id = id
        self.name = name
        self.room_id: str = None
        self.stream_id = stream_id # currently not being used

class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def create_room(self, participant: Participant) -> str:
        room_id = str(uuid4())
        room = Room(room_id)

        room.add_participant(participant)
        self.rooms[room_id] = room
        participant.room_id = room_id

        return room_id

    def get_room(self, room_id: str) -> Room:
        room = self.rooms.get(room_id)
        if room is None:
            raise RoomNotFound()
        return room
    
    def join_lobby(self, participant: Participant, room_id: str) -> None:
        room = self.get_room(room_id)

        if participant.room_id == room_id:
            return  # repeated join
            
        room.join_lobby(participant)
        participant.room_id = room_id

    def admit_participant(self, participant_id: str, room_id: str) -> None:
        room = self.get_room(room_id)
        room.admit_participant(participant_id)

    def leave_room(self, participant_id: str, room_id: str) -> None:
        room = self.get_room(room_id)
        room.remove_participant(participant_id)
        # if room empty, delete room. ignore lobby
        if not room.participants:
            room.close_room()
            self.rooms.pop(room_id, None)
        

class Room:
    def __init__(self, room_id: str) -> None:
        self.id = room_id
        self.lobby = Lobby(room_id)
        self.participants: dict[str, Participant] = {}

    def join_lobby(self, participant: Participant) -> None:
        self.lobby.add_participant(participant)

    def add_participant(self, participant: Participant) -> None:
        if participant.id in self.participants:
            raise ParticipantAlreadyJoined(participant.id)
        self.participants[participant.id] = participant
        participant.room_id = self.id

    def remove_participant(self, participant_id: str) -> None:
        participant = self.participants.pop(participant_id, None)

        if participant is None:
            participant = self.lobby.remove_participant(participant_id)

        participant.room_id = None
        return participant

    def admit_participant(self, participant_id: str) -> None:
        participant = self.lobby.remove_participant(participant_id)
        self.add_participant(participant)

    def close_room(self) -> None:
        self.lobby.close_lobby()
        for participant in self.participants.values():
            participant.room_id = None
        self.participants.clear()

class Lobby:
    def __init__(self, room_id: str) -> None:
        self.room_id = room_id
        self.participants: dict[str, Participant] = {}

    def add_participant(self, participant: Participant) -> None:
        if participant.id in self.participants:
            raise ParticipantAlreadyJoined(participant.id)
        self.participants[participant.id] = participant

    def remove_participant(self, participant_id: str) -> Participant:
        participant = self.participants.pop(participant_id, None)

        if participant is None:
            raise ParticipantNotFound()

        return participant

    def close_lobby(self) -> None:
        for participant in self.participants.values():
            participant.room_id = None
        self.participants.clear()

    
        



