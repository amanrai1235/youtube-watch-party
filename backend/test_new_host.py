import asyncio
import json
import websockets

ROOM = "6GUATW"
NEW_HOST = "94e379ba-93f0-464c-949a-27b2558cb838"


async def main():
    url = f"ws://127.0.0.1:8000/ws/rooms/{ROOM}/{NEW_HOST}"

    async with websockets.connect(url) as ws:
        print("NEW HOST CONNECTED")

        message = await ws.recv()
        print("NEW HOST RECEIVED:", message)

        await ws.send(json.dumps({
            "event": "play",
            "payload": {},
            "requestId": "new-host-play-test"
        }))

        print("NEW HOST SENT: play")

        message = await ws.recv()
        print("NEW HOST RECEIVED:", message)

        await asyncio.sleep(3)


asyncio.run(main())