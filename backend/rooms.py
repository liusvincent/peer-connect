from typing import Callable

from dataclasses import dataclass

class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
    
    async def join_room(self, participant: Participant, room_id: str) -> None:
        room = self.rooms.get(room_id)
        
        if room is None:
            room = Room(room_id)
            self.rooms[room_id] = room
        
        participant.room_id = room_id
        room.add_participant(participant)

    async def leave(self, participant_id: str, room_id: str) -> None:
        room = self.rooms.get(room_id)

        if room is None:
            return

        room.remove_participant(participant_id)

        if not room.participants:
            self.rooms.pop(room_id, None)

    async def forward_signal(self, from_id, to_id, payload) -> None:
        pass

class Room:
    def __init__(self, room_id: str) -> None:
        self.id = room_id
        self.participants: dict[str, Participant] = {}

    def add_participant(self, participant: Participant) -> None:
        self.participants[participant.id] = participant
        participant.send(self.stream_id, {
            "type": "joined_room",
            "participant_id": participant.id,
            "roomId": self.room_id
        })

    def remove_participant(self, participant_id) -> None:
        self.participants.pop(participant_id, None)
        self.participants[participant_id].send(self.stream_id, {
            "type": "joined_room",
            "participant_id": participant_id,
            "roomId": self.room_id
        })

    def broadcast(self, message, exclude=None) -> None:
        pass

class Participant:
    def __init__(self, id: str, name: str, stream_id: str, send: Callable[[dict], None]) -> None:
        self.id = id
        self.name = name
        self.room_id: str = None
        self.send = send
        self.stream_id = stream_id

