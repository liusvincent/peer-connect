import { useState } from "react";

type JoinRoomFormProps = {
    onJoin: (roomCode: string) => Promise<void>;
    onCreate: () => Promise<void>;
};

function JoinRoomForm({
    onJoin,
    onCreate
}: JoinRoomFormProps) {
    const [roomCode, setRoomCode] = useState("");

    return (
        <section>
            <div className="join-row">
                <div className="join-box">
                    <input 
                        placeholder="Enter a code or link" 
                        onChange={(event) => setRoomCode(event.target.value)}
                    />
                    <button 
                        onClick={() => onJoin(roomCode.trim())}
                        disabled={roomCode.trim() === ""}
                    >Join</button>
                    <button onClick={onCreate}>New Room</button>
                </div>
            </div>
        </section>
    );
}

export default JoinRoomForm;