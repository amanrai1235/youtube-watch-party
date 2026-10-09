from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.database.connection import Base, SessionLocal, engine
from app.websocket.handlers import WebSocketHandler
from app.websocket.manager import room_manager

# Phase 2 uses automatic table creation for local development.
# Alembic migrations will be introduced before production deployment.
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.websocket("/ws/rooms/{room_code}/{participant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    participant_id: str
) -> None:
    db = SessionLocal()
    try:
        handler = WebSocketHandler(db, room_manager)
        await handler.run(websocket, room_code, participant_id)
    finally:
        db.close()
