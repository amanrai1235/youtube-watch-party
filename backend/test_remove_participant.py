import asyncio
import json
import websockets

ROOM = "6GUATW"

HOST_ID = "94e379ba-93f0-464c-949a-27b2558cb838"
TARGET_ID = "82dcbd70-8c3b-48f4-b26f-58628d80f817"


async def main():
    url = f"ws://127.0.0.1:8000/ws/rooms/{ROOM}/{HOST_ID}"

    async with websockets.connect(url) as ws:
        print("HOST CONNECTED")

        message = await ws.recv()
        print("HOST RECEIVED:", message)

        await ws.send(json.dumps({
            "event": "remove_participant",
            "payload": {
                "userId": TARGET_ID
            },
            "requestId": "remove-participant-test"
        }))

        print("HOST SENT: remove_participant")

        message = await ws.recv()
        print("HOST RECEIVED:", message)

        await asyncio.sleep(2)


asyncio.run(main())