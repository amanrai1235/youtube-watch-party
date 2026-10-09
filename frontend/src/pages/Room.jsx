import { useEffect, useRef, useState } from 'react'

import YouTube from 'react-youtube'

import './Room.css'



const WS_BASE = 'wss://youtube-watch-party-api-zya9.onrender.com'



const REACTIONS = ['❤️', '😂', '🔥', '👏', '😮']



function Room({ roomCode, participantId, username, role }) {

  const socketRef = useRef(null)

  const playerRef = useRef(null)

  const reconnectTimerRef = useRef(null)

  const reconnectAttemptsRef = useRef(0)



  const [connectionStatus, setConnectionStatus] = useState('connecting')



  const [currentRole, setCurrentRole] = useState(role)



  const [roomState, setRoomState] = useState({

    videoId: null,

    isPlaying: false,

    currentTime: 0,

    stateVersion: 0,

  })



  const [participants, setParticipants] = useState([])

  const [videoUrl, setVideoUrl] = useState('')



  const [chatMessages, setChatMessages] = useState([])

  const [chatInput, setChatInput] = useState('')



  const [pendingRequests, setPendingRequests] = useState([])

  const [floatingReactions, setFloatingReactions] = useState([])



  const [notifications, setNotifications] = useState([])



  const isPrivileged =

    currentRole === 'HOST' ||

    currentRole === 'MODERATOR'



  const isHost = currentRole === 'HOST'



  const addNotification = (message, type = 'info') => {

    const id = crypto.randomUUID()



    setNotifications((current) => [

      ...current,

      {

        id,

        message,

        type,

      },

    ])



    setTimeout(() => {

      setNotifications((current) =>

        current.filter(

          (notification) =>

            notification.id !== id

        )

      )

    }, 3500)

  }



  const sendEvent = (event, payload = {}) => {

    if (!socketRef.current) {

      addNotification(

        'WebSocket is not initialized.',

        'error'

      )

      return null

    }



    if (

      socketRef.current.readyState !==

      WebSocket.OPEN

    ) {

      addNotification(

        'You are not connected to the room.',

        'error'

      )

      return null

    }



    const requestId = crypto.randomUUID()



    socketRef.current.send(

      JSON.stringify({

        event,

        payload,

        requestId,

      })

    )



    return requestId

  }



  useEffect(() => {

    let cancelled = false



    const connect = () => {

      if (cancelled) {

        return

      }



      setConnectionStatus(

        reconnectAttemptsRef.current > 0

          ? 'reconnecting'

          : 'connecting'

      )



      const url =

        `${WS_BASE}/ws/rooms/` +

        `${roomCode}/${participantId}`



      console.log('Connecting to:', url)



      const socket = new WebSocket(url)



      socketRef.current = socket



      socket.onopen = () => {

        console.log('WebSocket connected')



        reconnectAttemptsRef.current = 0



        setConnectionStatus('connected')



        addNotification(

          'Connected to watch party.',

          'success'

        )

      }



      socket.onmessage = (event) => {

        const message = JSON.parse(event.data)



        console.log('WS MESSAGE:', message)




/*
 * Initial state
 */
if (message.event === 'sync_state') {
  setRoomState(message.payload)

  if (Array.isArray(message.payload?.participants)) {
    setParticipants(
      message.payload.participants.map((participant) => ({
        ...participant,
        online: Boolean(participant.online),
      }))
    )
  } else {
    // Fallback if the server doesn't send participants yet.
    setParticipants((current) => {
      const exists = current.some(
        (participant) => participant.userId === participantId
      )

      if (exists) {
        return current.map((participant) =>
          participant.userId === participantId
            ? {
                ...participant,
                username,
                role: currentRole,
                online: true,
              }
            : participant
        )
      }

      return [
        ...current,
        {
          userId: participantId,
          username,
          role: currentRole,
          online: true,
        },
      ]
    })
  }
}



        /*

         * User joined

         */

        if (message.event === 'user_joined') {

          const user = message.payload



          setParticipants((current) => {

            const exists = current.some(

              (participant) =>

                participant.userId === user.userId

            )



            if (exists) {

              return current.map((participant) =>

                participant.userId === user.userId

                  ? {

                      ...participant,

                      ...user,

                      online: true,

                    }

                  : participant

              )

            }



            return [

              ...current,

              {

                ...user,

                online: true,

              },

            ]

          })



          addNotification(

            `${user.username} joined the room.`,

            'info'

          )

        }



        /*

         * User left

         */

        if (message.event === 'user_left') {
  const user = message.payload

  setParticipants((current) =>
    current.map((participant) =>
      participant.userId === user.userId
        ? {
            ...participant,
            online: false,
          }
        : participant
    )
  )

  addNotification(
    `${user.username} left the room.`,
    'info'
  )
}


        /*

         * Play

         */

        if (message.event === 'play') {

          setRoomState(message.payload)



          if (playerRef.current) {

            playerRef.current.playVideo()

          }

        }



        /*

         * Pause

         */

        if (message.event === 'pause') {

          setRoomState(message.payload)



          if (playerRef.current) {

            playerRef.current.pauseVideo()

          }

        }



        /*

         * Seek

         */

        if (message.event === 'seek') {

          setRoomState(message.payload)



          if (playerRef.current) {

            playerRef.current.seekTo(

              message.payload.currentTime,

              true

            )

          }

        }



        /*

         * Video changed

         */

        if (message.event === 'video_changed') {

          setRoomState(message.payload)



          if (

            playerRef.current &&

            message.payload.videoId

          ) {

            playerRef.current.loadVideoById(

              message.payload.videoId

            )

          }

        }



        /*

         * Role assigned

         */

        if (message.event === 'role_assigned') {

          const user = message.payload



          setParticipants((current) =>

            current.map((participant) =>

              participant.userId === user.userId

                ? {

                    ...participant,

                    role: user.role,

                  }

                : participant

            )

          )



          if (user.userId === participantId) {

            setCurrentRole(user.role)



            addNotification(

              `Your role is now ${user.role}.`,

              'success'

            )

          } else {

            addNotification(

              `${user.username} is now ${user.role}.`,

              'info'

            )

          }

        }



        /*

         * Host transferred

         */

        if (message.event === 'host_transferred') {
  const { previousHostId, newHostId } = message.payload

  setParticipants((current) =>
    current.map((participant) => {
      if (participant.userId === newHostId) {
        return {
          ...participant,
          role: 'HOST',
        }
      }

      if (participant.userId === previousHostId) {
        return {
          ...participant,
          role: 'PARTICIPANT',
        }
      }

      return participant
    })
  )

  if (previousHostId === participantId) {
    setCurrentRole('PARTICIPANT')
    addNotification(
      'Host role transferred to another participant.',
      'info'
    )
  }

  if (newHostId === participantId) {
    setCurrentRole('HOST')
    addNotification(
      'You are now the host.',
      'success'
    )
  }
}



        /*

         * Participant removed

         */

        if (

          message.event ===

          'participant_removed'

        ) {

          const removedUserId =

            message.payload.userId



          if (removedUserId === participantId) {

            addNotification(

              'You were removed from the room.',

              'error'

            )



            setTimeout(() => {

              window.location.href = '/'

            }, 1200)



            return

          }



          setParticipants((current) =>

            current.filter(

              (participant) =>

                participant.userId !==

                removedUserId

            )

          )



          addNotification(

            `${message.payload.username} was removed.`,

            'info'

          )

        }



        /*

         * Chat

         */

        if (

          message.event ===

          'chat_message'

        ) {

          setChatMessages((current) => [

            ...current,

            {

              userId:

                message.payload.userId,

              username:

                message.payload.username,

              message:

                message.payload.message,

              timestamp: new Date(),

            },

          ])

        }



        /*

         * Reaction

         */

        if (message.event === 'reaction') {

          const reaction = {

            id: crypto.randomUUID(),

            userId:

              message.payload.userId,

            username:

              message.payload.username,

            reaction:

              message.payload.reaction,

          }



          setFloatingReactions((current) => [

            ...current,

            reaction,

          ])



          setTimeout(() => {

            setFloatingReactions((current) =>

              current.filter(

                (item) =>

                  item.id !== reaction.id

              )

            )

          }, 2500)



          setChatMessages((current) => [

            ...current,

            {

              userId:

                message.payload.userId,

              username:

                message.payload.username,

              message:

                `${message.payload.reaction} reacted`,

              isReaction: true,

              timestamp: new Date(),

            },

          ])

        }



        /*

         * Action request received by host/moderator

         */

        if (

          message.event ===

          'action_requested'

        ) {

          const request =

            message.payload



          setPendingRequests((current) => {

            const exists = current.some(

              (item) =>

                item.requestId ===

                request.requestId

            )



            if (exists) {

              return current

            }



            return [

              ...current,

              request,

            ]

          })



          addNotification(

            `${request.username} requested ${request.action}.`,

            'info'

          )

        }



        /*

         * Action request resolved

         */

        if (

          message.event ===

          'action_request_resolved'

        ) {

          const request =

            message.payload



          setPendingRequests((current) =>

            current.filter(

              (item) =>

                item.requestId !==

                request.requestId

            )

          )



          if (

            request.userId ===

            participantId

          ) {

            if (

              request.status ===

              'approved'

            ) {

              addNotification(

                `Your ${request.action} request was approved.`,

                'success'

              )

            } else {

              addNotification(

                `Your ${request.action} request was rejected.`,

                'error'

              )

            }

          }

        }



        /*

         * Error

         */

        if (message.event === 'error') {

          console.error(

            'Backend error:',

            message.payload

          )



          addNotification(

            message.payload?.message ||

              'Something went wrong.',

            'error'

          )

        }

      }



      socket.onerror = (error) => {

        console.error(

          'WebSocket error:',

          error

        )



        setConnectionStatus('error')

      }



      socket.onclose = () => {

        if (cancelled) {

          return

        }



        console.log(

          'WebSocket disconnected'

        )



        setConnectionStatus(

          'reconnecting'

        )



        reconnectAttemptsRef.current += 1



        const delay = Math.min(

          1000 *

            2 **

              Math.min(

                reconnectAttemptsRef.current,

                5

              ),

          10000

        )



        reconnectTimerRef.current =

          setTimeout(connect, delay)

      }

    }



    connect()



    return () => {

      cancelled = true



      if (reconnectTimerRef.current) {

        clearTimeout(

          reconnectTimerRef.current

        )

      }



      if (socketRef.current) {

        socketRef.current.close()

      }

    }

  }, [

    roomCode,

    participantId,

    username,

  ])



  /*

   * Keep participant's own role synchronized

   */

  useEffect(() => {

    setCurrentRole(role)

  }, [role])



  /*

   * Playback

   */

  const handlePlay = () => {

    if (isPrivileged) {

      sendEvent('play')

      return

    }



    sendActionRequest('play')

  }



  const handlePause = () => {

    if (isPrivileged) {

      sendEvent('pause')

      return

    }



    sendActionRequest('pause')

  }



  const handleSeek = () => {

    const value = window.prompt(

      'Enter time in seconds:',

      String(

        Math.floor(

          roomState.currentTime

        )

      )

    )



    if (value === null) {

      return

    }



    const time = Number(value)



    if (

      !Number.isFinite(time) ||

      time < 0

    ) {

      addNotification(

        'Enter a valid time.',

        'error'

      )

      return

    }



    if (isPrivileged) {

      sendEvent('seek', {

        time,

      })

      return

    }



    sendActionRequest(

      'seek',

      {

        time,

      }

    )

  }



  /*

   * YouTube URL parsing

   */

  const extractVideoId = (url) => {

    try {

      const parsedUrl = new URL(url)



      const hostname =

        parsedUrl.hostname.toLowerCase()



      if (

        hostname === 'youtube.com' ||

        hostname === 'www.youtube.com' ||

        hostname === 'm.youtube.com'

      ) {

        const queryId =

          parsedUrl.searchParams.get('v')



        if (queryId) {

          return queryId

        }



        const embedMatch =

          parsedUrl.pathname.match(

            /^\/embed\/([^/?]+)/

          )



        if (embedMatch) {

          return embedMatch[1]

        }



        const shortMatch =

          parsedUrl.pathname.match(

            /^\/shorts\/([^/?]+)/

          )



        if (shortMatch) {

          return shortMatch[1]

        }

      }



      if (

        hostname === 'youtu.be'

      ) {

        const id =

          parsedUrl.pathname

            .split('/')

            .filter(Boolean)[0]



        if (id) {

          return id

        }

      }



      return null

    } catch {

      return null

    }

  }



  const handleLoadVideo = () => {

    const url = videoUrl.trim()



    if (!url) {

      addNotification(

        'Paste a YouTube URL first.',

        'error'

      )

      return

    }



    const videoId =

      extractVideoId(url)



    if (!videoId) {

      addNotification(

        'Invalid YouTube URL.',

        'error'

      )

      return

    }



    if (isPrivileged) {

      sendEvent(

        'change_video',

        {

          videoId,

        }

      )

    } else {

      sendActionRequest(

        'change_video',

        {

          videoId,

        }

      )

    }



    setVideoUrl('')

  }



  /*

   * Action request

   */

  const sendActionRequest = (

    action,

    payload = {}

  ) => {

    const requestId = sendEvent(

      'action_request',

      {

        action,

        payload,

      }

    )



    if (requestId) {

      addNotification(

        `${action} request sent.`,

        'success'

      )

    }

  }



  const handleApproveRequest = (

    requestId

  ) => {

    sendEvent(

      'approve_request',

      {

        requestId,

      }

    )

  }



  const handleRejectRequest = (

    requestId

  ) => {

    sendEvent(

      'reject_request',

      {

        requestId,

      }

    )

  }



  /*

   * Chat

   */

  const handleSendChat = (event) => {

    event.preventDefault()



    const message =

      chatInput.trim()



    if (!message) {

      return

    }



    sendEvent(

      'chat_message',

      {

        message,

      }

    )



    setChatInput('')

  }



  /*

   * Reactions

   */

  const handleReaction = (

    reaction

  ) => {

    sendEvent(

      'reaction',

      {

        reaction,

      }

    )

  }



  /*

   * Role management

   */

  const handleRoleChange = (

    userId,

    newRole

  ) => {

    sendEvent(

      'assign_role',

      {

        userId,

        role: newRole,

      }

    )

  }



  /*

   * Remove participant

   */

  const handleRemoveParticipant = (

    participant

  ) => {

    const confirmed =

      window.confirm(

        `Remove ${participant.username} from the room?`

      )



    if (!confirmed) {

      return

    }



    sendEvent(

      'remove_participant',

      {

        userId:

          participant.userId,

      }

    )

  }



  /*

   * Transfer host

   */

  const handleTransferHost = (

    participant

  ) => {

    const confirmed =

      window.confirm(

        `Transfer host to ${participant.username}?`

      )



    if (!confirmed) {

      return

    }



    sendEvent(

      'transfer_host',

      {

        userId:

          participant.userId,

      }

    )

  }



  /*

   * Leave room

   */

  const handleLeaveRoom = () => {

    const confirmed =

      window.confirm(

        'Leave this watch party?'

      )



    if (!confirmed) {

      return

    }



    sendEvent('leave_room')



    setTimeout(() => {

      window.location.href = '/'

    }, 250)

  }



  /*

   * Copy room link

   */

  const handleCopyRoomLink =

    async () => {

      const link =

        window.location.origin +

        `/?room=${roomCode}`



      try {

        await navigator.clipboard.writeText(

          link

        )



        addNotification(

          'Room link copied.',

          'success'

        )

      } catch {

        addNotification(

          'Could not copy room link.',

          'error'

        )

      }

    }



  const getRoleClass = (value) =>

    value

      ?.toLowerCase()

      .replace('_', '-')



  return (

    <main className="room-page">



      {/* Notifications */}

      <div className="toast-container">

        {notifications.map(

          (notification) => (

            <div

              key={notification.id}

              className={`toast toast-${notification.type}`}

            >

              {notification.message}

            </div>

          )

        )}

      </div>



      {/* Floating reactions */}

      <div className="floating-reactions">

        {floatingReactions.map(

          (item) => (

            <div

              key={item.id}

              className="floating-reaction"

              title={item.username}

            >

              {item.reaction}

            </div>

          )

        )}

      </div>



      {/* Header */}

      <header className="room-header">



        <div className="room-brand">

          <div className="brand-icon">

            ▶

          </div>



          <span>Watch Party</span>

        </div>



        <div className="room-info">

          <span>Room</span>



          <strong>

            {roomCode}

          </strong>



          <button

            className="copy-room-button"

            onClick={() => navigator.clipboard.writeText(roomCode)}

          >

            Copy Code

          </button>

        </div>



        <div className="header-actions">



          <div

            className={`status ${connectionStatus}`}

          >

            <span className="status-dot"></span>

            {connectionStatus}

          </div>



          <button

            className="leave-room-button"

            onClick={handleLeaveRoom}

          >

            Leave Room

          </button>



        </div>



      </header>



      <section className="room-layout">



        {/* =========================

            MAIN PLAYER AREA

           ========================= */}



        <div className="player-section">



          <div className="video-wrapper">



            <div className="video-placeholder">



              {roomState.videoId ? (

                <YouTube

                  videoId={

                    roomState.videoId

                  }

                  onReady={(event) => {

                    playerRef.current =

                      event.target

                  }}

                  opts={{

                    width: '100%',

                    height: '100%',

                    playerVars: {

                      autoplay: 0,

                      controls: 1,

                      rel: 0,

                    },

                  }}

                  style={{

                    width: '100%',

                    height: '100%',

                  }}

                />

              ) : (

                <>

                  <div className="play-placeholder">

                    ▶

                  </div>



                  <p>

                    No video selected

                  </p>

                </>

              )}



            </div>



          </div>



          {/* Video loader */}



          <div className="video-loader">



            <input

              type="text"

              placeholder={

                isPrivileged

                  ? 'Paste YouTube video URL'

                  : 'Request a YouTube video change'

              }

              value={videoUrl}

              onChange={(event) =>

                setVideoUrl(

                  event.target.value

                )

              }

            />



            <button

              onClick={handleLoadVideo}

            >

              {isPrivileged

                ? 'Load Video'

                : 'Request Change'}

            </button>



          </div>



          {/* Playback controls */}



          <div className="controls">



            <button

              onClick={handlePlay}

              className={

                !isPrivileged

                  ? 'request-control'

                  : ''

              }

            >

              ▶ Play

              {!isPrivileged &&

                ' Request'}

            </button>



            <button

              onClick={handlePause}

              className={

                !isPrivileged

                  ? 'request-control'

                  : ''

              }

            >

              ⏸ Pause

              {!isPrivileged &&

                ' Request'}

            </button>



            <button

              onClick={handleSeek}

              className={

                !isPrivileged

                  ? 'request-control'

                  : ''

              }

            >

              ⏩ Seek

              {!isPrivileged &&

                ' Request'}

            </button>



          </div>



          {!isPrivileged && (

            <div className="permission-hint">

              You are a Participant. Playback

              actions are sent as requests to

              the Host/Moderator.

            </div>

          )}



          {/* Room state */}



          <div className="state-card">



            <div>

              <span>Video</span>



              <strong>

                {roomState.videoId ||

                  'None'}

              </strong>

            </div>



            <div>

              <span>Status</span>



              <strong>

                {roomState.isPlaying

                  ? 'Playing'

                  : 'Paused'}

              </strong>

            </div>



            <div>

              <span>Time</span>



              <strong>

                {Math.floor(

                  roomState.currentTime

                )}

                s

              </strong>

            </div>



            <div>

              <span>Version</span>



              <strong>

                {roomState.stateVersion}

              </strong>

            </div>



          </div>



          {/* Pending requests */}



          {isPrivileged &&

            pendingRequests.length > 0 && (

              <div className="requests-card">



                <div className="card-heading">

                  <h2>

                    Action Requests

                  </h2>



                  <span>

                    {

                      pendingRequests.length

                    }

                  </span>

                </div>



                <div className="request-list">



                  {pendingRequests.map(

                    (request) => (

                      <div

                        className="request-item"

                        key={

                          request.requestId

                        }

                      >



                        <div>

                          <strong>

                            {

                              request.username

                            }

                          </strong>



                          <p>

                            requested{' '}

                            <b>

                              {

                                request.action

                              }

                            </b>

                          </p>

                        </div>



                        <div className="request-actions">



                          <button

                            className="approve-button"

                            onClick={() =>

                              handleApproveRequest(

                                request.requestId

                              )

                            }

                          >

                            Approve

                          </button>



                          <button

                            className="reject-button"

                            onClick={() =>

                              handleRejectRequest(

                                request.requestId

                              )

                            }

                          >

                            Reject

                          </button>



                        </div>



                      </div>

                    )

                  )}



                </div>



              </div>

            )}



        </div>



        {/* =========================

            SIDEBAR

           ========================= */}



        <aside className="sidebar">



          {/* Current user */}



          <div className="profile-card">



            <span>

              You are

            </span>



            <strong>

              {username}

            </strong>



            <span

              className={`role-badge ${getRoleClass(

                currentRole

              )}`}

            >

              {currentRole}

            </span>



          </div>



          {/* Participants */}



          <div className="participants-card">



            <div className="card-heading">



              <h2>

                Participants

              </h2>



              <span>

                {participants.length}

              </span>



            </div>



            {participants.length === 0 ? (

              <p className="empty">

                Waiting for other

                participants...

              </p>

            ) : (

              <div className="participant-list">



                {participants.map(

                  (participant) => {



                    const isSelf =

                      participant.userId ===

                      participantId



                    const canManage =

                      isHost &&

                      !isSelf &&

                      participant.role !==

                        'HOST'



                    return (

                      <div

                        className="participant"

                        key={

                          participant.userId

                        }

                      >



                        <div className="avatar">

                          {participant.username

                            ?.charAt(0)

                            .toUpperCase()}

                        </div>



                        <div className="participant-main">



                          <div className="participant-name-row">



                            <strong>

                              {

                                participant.username

                              }

                            </strong>



                            {isSelf && (

                              <small>

                                You

                              </small>

                            )}



                          </div>



                          <div className="participant-meta">



                            <span

                              className={`role-badge ${getRoleClass(

                                participant.role

                              )}`}

                            >

                              {

                                participant.role

                              }

                            </span>



                            <span

                              className={

                                participant.online ===

                                false

                                  ? 'offline'

                                  : 'online'

                              }

                            >

                              ●{' '}

                              {participant.online ===

                              false

                                ? 'Offline'

                                : 'Online'}

                            </span>



                          </div>



                          {canManage && (

                            <div className="participant-actions">



                              {participant.role ===

                                'PARTICIPANT' && (

                                <button

                                  onClick={() =>

                                    handleRoleChange(

                                      participant.userId,

                                      'MODERATOR'

                                    )

                                  }

                                >

                                  Make Moderator

                                </button>

                              )}



                              {participant.role ===

                                'MODERATOR' && (

                                <button

                                  onClick={() =>

                                    handleRoleChange(

                                      participant.userId,

                                      'PARTICIPANT'

                                    )

                                  }

                                >

                                  Remove Moderator

                                </button>

                              )}



                              <button

                                onClick={() =>

                                  handleTransferHost(

                                    participant

                                  )

                                }

                              >

                                Make Host

                              </button>



                              <button

                                className="danger-button"

                                onClick={() =>

                                  handleRemoveParticipant(

                                    participant

                                  )

                                }

                              >

                                Remove

                              </button>



                            </div>

                          )}



                        </div>



                      </div>

                    )

                  }

                )}



              </div>

            )}



          </div>



          {/* Chat */}



          <div className="chat-card">



            <div className="card-heading">



              <h2>

                Chat

              </h2>



              <span>

                {chatMessages.length}

              </span>



            </div>



            <div className="chat-messages">



              {chatMessages.length === 0 ? (

                <p className="empty">

                  No messages yet.

                  Start the conversation.

                </p>

              ) : (

                chatMessages.map(

                  (

                    chatMessage,

                    index

                  ) => (

                    <div

                      className={`chat-message ${

                        chatMessage.isReaction

                          ? 'reaction-message'

                          : ''

                      } ${

                        chatMessage.userId ===

                        participantId

                          ? 'own-message'

                          : ''

                      }`}

                      key={`${chatMessage.userId}-${index}`}

                    >



                      <strong>

                        {

                          chatMessage.username

                        }

                      </strong>



                      <p>

                        {

                          chatMessage.message

                        }

                      </p>



                    </div>

                  )

                )

              )}



            </div>



            {/* Reactions */}



            <div className="reaction-buttons">



              {REACTIONS.map(

                (reaction) => (

                  <button

                    type="button"

                    key={reaction}

                    onClick={() =>

                      handleReaction(

                        reaction

                      )

                    }

                    aria-label={`Send ${reaction} reaction`}

                  >

                    {reaction}

                  </button>

                )

              )}



            </div>



            {/* Chat form */}



            <form

              className="chat-form"

              onSubmit={

                handleSendChat

              }

            >



              <input

                type="text"

                placeholder="Type a message..."

                value={chatInput}

                onChange={(event) =>

                  setChatInput(

                    event.target.value

                  )

                }

                maxLength={500}

              />



              <button type="submit">

                Send

              </button>



            </form>



          </div>



        </aside>



      </section>



    </main>

  )

}



export default Room