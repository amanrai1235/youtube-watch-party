import asyncio
import json
import websockets

ROOM = "6GUATW"
PARTICIPANT = "94e379ba-93f0-464c-949a-27b2558cb838"


async def main():
    url = f"ws://127.0.0.1:8000/ws/rooms/{ROOM}/{PARTICIPANT}"

    async with websockets.connect(url) as ws:
        print("PARTICIPANT CONNECTED")

        # Initial sync
        message = await ws.recv()
        print("PARTICIPANT RECEIVED:", message)

        # Try to play
        await ws.send(json.dumps({
            "event": "play",
            "payload": {},
            "requestId": "participant-play-test"
        }))

        print("PARTICIPANT SENT: play")

        # Receive server response
        message = await ws.recv()
        print("PARTICIPANT RECEIVED:", message)

        await asyncio.sleep(2)


asyncio.run(main())