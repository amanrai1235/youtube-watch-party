# YouTube Watch Party

A real-time watch-party web application that lets multiple users watch YouTube videos together in a shared room. Playback events are communicated through WebSockets so participants can follow the room's current video state.

## Project Links

- **GitHub repository:** https://github.com/amanrai1235/youtube-watch-party
- **Backend API (Render):** https://youtube-watch-party-api-zya9.onrender.com
- **Frontend:** https://youtube-watch-party-tan.vercel.app/

> The backend deployment is live, but verify the complete application flow before submitting. A live backend alone does not confirm that every feature works in production.

## Features

- Create and join watch-party rooms.
- Room-based participant management.
- Real-time playback synchronization for play, pause, seek, and video changes.
- WebSocket communication between the client and server.
- Role-based access control:
  - **Host:** Full room control, including playback and participant/role management.
  - **Moderator:** Playback controls; request moderation features depend on the implemented permissions.
  - **Participant:** Watch-only playback access and can request actions for approval, where supported by the application.
- Participant presence and room state updates.
- YouTube video playback in the room.

Some features may still need production verification. Update this list if any item is not implemented or working in the submitted build.

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React, Vite | User interface and room experience |
| Backend | Python, FastAPI | API and room/application logic |
| Real-time communication | WebSockets | Broadcast playback and room events |
| Database | SQLite / SQLAlchemy (as configured) | Local persistence and data models |
| Video | YouTube embedded player / IFrame integration | Video playback |
| Deployment | Render (backend) | Public backend hosting |

## Architecture Overview

1. A user opens the React frontend and creates or joins a room.
2. The frontend connects to the FastAPI backend using a WebSocket connection.
3. The backend identifies the participant and their role in the room.
4. When an authorized user sends a playback event, the backend validates permissions before processing it.
5. The backend updates the room's playback state and broadcasts the relevant event to connected participants.
6. The frontend updates the player and room UI when it receives synchronization or participant events.
7. Participants without playback permission can request an action for Host/Moderator approval if that workflow is enabled.

### Simplified event flow

```text
React Frontend
      |
      | WebSocket events
      v
FastAPI WebSocket Handler
      |
      | Validate role and event
      v
Room / Playback State
      |
      | Broadcast updated state
      v
All connected room participants
```

## Roles and Permissions

| Action | Host | Moderator | Participant |
|---|---:|---:|---:|
| Play / pause | Yes | Yes | No direct control |
| Seek | Yes | Yes | No direct control |
| Change video | Yes | Yes | No direct control |
| Assign roles | Yes | Only if explicitly enabled | No |
| Remove participants | Yes | Only if explicitly enabled | No |
| Request playback action | Not needed | Not needed | Where supported |

The backend must enforce permissions; hiding or disabling a frontend control alone is not sufficient.

## Run Locally

### Requirements

- Python 3.11 or the Python version specified by `backend/.python-version`
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/amanrai1235/youtube-watch-party.git
cd youtube-watch-party
```

### 2. Configure the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If the project uses environment variables, create a local `.env` file based on `backend/.env.example` and fill in the required values. Do not commit `.env` or secrets to GitHub.

Start the backend from the `backend` directory using the project's FastAPI application:

```bash
uvicorn app.main:app --reload
```

The local API will usually be available at `http://127.0.0.1:8000`. If configured, interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Configure the frontend

Open a second terminal at the repository root:

```bash
cd frontend
npm install
```

Set the frontend's backend/API/WebSocket URL using the variable name expected by the frontend code or its environment example. For local development, use the local backend address and the appropriate `ws://` WebSocket URL. For production, use the deployed backend URL and `wss://`.

Start the development server:

```bash
npm run dev
```

Vite prints the local frontend URL in the terminal, commonly `http://localhost:5173`.

> The exact environment-variable names depend on the current source code. Check the frontend configuration and `.env.example` files rather than inventing new variable names.

## Deployment

### Backend

- Hosting provider: Render
- Service: `youtube-watch-party-api`
- Backend URL: https://youtube-watch-party-api-zya9.onrender.com
- Repository: `amanrai1235/youtube-watch-party`

The Render service is configured to deploy from the repository. Check the Render build and runtime logs if a deployment fails.

### Frontend

Live URL : https://youtube-watch-party-tan.vercel.app/

### Production checklist

- [ ] Frontend opens from a public URL.
- [ ] Backend responds from its public URL.
- [ ] A user can create a room.
- [ ] Another user can join the same room.
- [ ] Play/pause, seek, and video changes synchronize across clients.
- [ ] Host and Moderator permissions work as intended.
- [ ] Participants cannot bypass backend playback permissions.
- [ ] Participant action requests can be approved/rejected, if included.
- [ ] Reconnection and room-state recovery are checked.
- [ ] README contains the final frontend and backend URLs.

Render free instances may spin down after inactivity, which can delay the first request.

## Testing

Run tests from the backend directory:

```powershell
python -m pytest -v
```

If pytest does not discover tests or hangs during collection, inspect the test files and collection-time code before treating the test suite as passing. Record actual test results here before final submission.

**Test status:** Not yet confirmed. Update this section with the results of the tests you actually run.

## Important Implementation Notes

- WebSockets provide bidirectional, low-latency communication between the browser and server.
- Playback and room events should be validated by the backend before state changes are broadcast.
- Role updates should be reflected in the participant list and UI.
- Never commit database credentials, API keys, tokens, or `.env` files.
- A successful deployment indicates that the service started; it does not replace end-to-end testing.

## Future Improvements

- Persistent room state and recovery after server restarts.
- Authentication and user profiles.
- More robust reconnection handling.
- Chat and reactions.
- Horizontal scaling and shared pub/sub for multiple backend instances.

## Assignment Deliverables

This README covers setup instructions, deployment links, architecture overview, and core role/synchronization design. Before submission, ensure that the public application is working and that you can explain the technologies, WebSocket event flow, backend permission checks, and deployment choices.
