import asyncio
import json
import websockets

ROOM = "6GUATW"
HOST_ID = "1b3cdf0a-21d7-4d1c-971b-b17494f5a556"

async def main():
    url = f"ws://127.0.0.1:8000/ws/rooms/{ROOM}/{HOST_ID}"

    async with websockets.connect(url) as ws:
        print("HOST CONNECTED")

        # Initial sync
        message = await ws.recv()
        print("HOST RECEIVED:", message)

        # Change video
        await ws.send(json.dumps({
            "event": "change_video",
            "payload": {
                "videoId": "dQw4w9WgXcQ"
            },
            "requestId": "test-video-1"
        }))

        print("HOST SENT: change_video")

        message = await ws.recv()
        print("HOST RECEIVED:", message)

        await asyncio.sleep(3)

asyncio.run(main())