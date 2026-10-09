import { useState } from 'react'
import Room from './pages/Room'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000/api'

function App() {
  const [mode, setMode] = useState('create')
  const [username, setUsername] = useState('')
  const [roomCode, setRoomCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const [roomSession, setRoomSession] = useState(null)

  const handleCreateRoom = async (e) => {
    e.preventDefault()

    if (!username.trim()) {
      setMessage('Please enter your username.')
      return
    }

    try {
      setLoading(true)
      setMessage('')

      const response = await fetch(`${API_BASE}/rooms`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username.trim(),
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to create room.')
      }

      console.log('CREATE ROOM RESPONSE:', data)

      setRoomSession({
        roomCode: data.room_code,
        participantId: data.participant_id,
        username: username.trim(),
        role: data.role,
      })
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleJoinRoom = async (e) => {
    e.preventDefault()

    if (!username.trim()) {
      setMessage('Please enter your username.')
      return
    }

    if (!roomCode.trim()) {
      setMessage('Please enter a room code.')
      return
    }

    try {
      setLoading(true)
      setMessage('')

      const response = await fetch(
        `${API_BASE}/rooms/${roomCode.trim().toUpperCase()}/join`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: username.trim(),
          }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to join room.')
      }

      console.log('JOIN ROOM RESPONSE:', data)

      setRoomSession({
        roomCode: data.room_code,
        participantId: data.participant_id,
        username: username.trim(),
        role: data.role,
      })
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  // Once a room session exists, show the Watch Room.
  if (roomSession) {
    return (
      <Room
        roomCode={roomSession.roomCode}
        participantId={roomSession.participantId}
        username={roomSession.username}
        role={roomSession.role}
      />
    )
  }

  return (
    <main className="app">
      <div className="background-glow glow-one"></div>
      <div className="background-glow glow-two"></div>

      <section className="hero-section">
        <div className="brand">
          <div className="brand-icon">▶</div>
          <span>Watch Party</span>
        </div>

        <div className="hero-content">
          <p className="eyebrow">WATCH TOGETHER</p>

          <h1>
            Press play.
            <br />
            <span>Bring your people.</span>
            <br />
            Make it a moment.
          </h1>

          <p className="subtitle">
            Create a room, invite your friends, and watch videos
            together in real time.
          </p>

          <div className="room-card">
            <div className="tabs">
              <button
                className={mode === 'create' ? 'tab active' : 'tab'}
                onClick={() => {
                  setMode('create')
                  setMessage('')
                }}
              >
                Create Room
              </button>

              <button
                className={mode === 'join' ? 'tab active' : 'tab'}
                onClick={() => {
                  setMode('join')
                  setMessage('')
                }}
              >
                Join Room
              </button>
            </div>

            <form
              onSubmit={
                mode === 'create'
                  ? handleCreateRoom
                  : handleJoinRoom
              }
            >
              <label>Username</label>

              <input
                type="text"
                placeholder="Enter your name"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                maxLength={30}
              />

              {mode === 'join' && (
                <>
                  <label>Room Code</label>

                  <input
                    type="text"
                    placeholder="e.g. 6GUATW"
                    value={roomCode}
                    onChange={(e) =>
                      setRoomCode(e.target.value.toUpperCase())
                    }
                    maxLength={10}
                  />
                </>
              )}

              <button
                type="submit"
                className="primary-button"
                disabled={loading}
              >
                {loading
                  ? 'Please wait...'
                  : mode === 'create'
                    ? 'Create Watch Party'
                    : 'Join Watch Party'}
              </button>

              {message && (
                <div className="message">
                  {message}
                </div>
              )}
            </form>
          </div>
        </div>
      </section>

      <section className="features">
        <div className="feature">
          <div className="feature-icon">▶</div>
          <div>
            <h3>Synced Playback</h3>
            <p>Everyone watches the same moment together.</p>
          </div>
        </div>

        <div className="feature">
          <div className="feature-icon">●</div>
          <div>
            <h3>Live Rooms</h3>
            <p>See who's watching with you in real time.</p>
          </div>
        </div>

        <div className="feature">
          <div className="feature-icon">⚡</div>
          <div>
            <h3>Instant Updates</h3>
            <p>Play, pause and seek without missing a beat.</p>
          </div>
        </div>
      </section>
    </main>
  )
}

export default App