import { useEffect, useRef, useState } from 'react'
import ChatWorkspace from './components/ChatWorkspace.jsx'
import SessionExplorer from './components/SessionExplorer.jsx'
import SessionDetail from './components/SessionDetail.jsx'

const WS_BASE_URL = 'ws://localhost:8000/ws/chat'
const API_BASE_URL = 'http://localhost:8000'
const HIDDEN_SESSIONS_KEY = 'cortex-hidden-sessions'

const getHiddenSessions = () => {
  if (typeof window === 'undefined') return []

  try {
    const raw = localStorage.getItem(HIDDEN_SESSIONS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

const formatDate = (value) => {
  if (!value) return '—'

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function App() {
  const [sessions, setSessions] = useState([])
  const [explorerSessions, setExplorerSessions] = useState([])
  const [sessionDetail, setSessionDetail] = useState(null)
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname)
  const [hiddenSessionIds, setHiddenSessionIds] = useState(() => getHiddenSessions())
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [connected, setConnected] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [ingestStatus, setIngestStatus] = useState('')
  const [stage, setStage] = useState(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const wsRef = useRef(null)
  const streamingIndexRef = useRef(null)
  const sessionIdRef = useRef(null)
  const shouldReconnectRef = useRef(true)
  const chatEndRef = useRef(null)

  const visibleSessions = sessions.filter(
    (session) => !hiddenSessionIds.includes(session.session_id)
  )

  const handleOpenSessionExplorer = () => navigateTo('/chat-session')
  const handleBackToChat = () => navigateTo('/')
  const handleOpenSession = (sessionId) => navigateTo(`/chat-session/${sessionId}`)

  const navigateTo = (path) => {
    window.history.pushState({}, '', path)
    setCurrentPath(path)
  }

  const upsertSession = (sessionId, patch = {}) => {
    setSessions((prev) => {
      const existing = prev.find((s) => s.session_id === sessionId)
      const { title: patchTitle, ...restPatch } = patch
      const keepExistingTitle = existing && existing.title && existing.title !== 'New chat'
      const nextTitle = keepExistingTitle
        ? existing.title
        : patchTitle || existing?.title || 'New chat'
      const next = existing
        ? { ...existing, ...restPatch, title: nextTitle }
        : { session_id: sessionId, title: nextTitle, message_count: 0, ...restPatch }
      const rest = prev.filter((s) => s.session_id !== sessionId && (s.message_count ?? 0) > 0)
      return [next, ...rest]
    })
  }

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/sessions`)
      const serverSessions = await response.json()
      const serverIds = new Set(serverSessions.map((s) => s.session_id))

      setSessions((prev) => {
        const pending = prev.filter((s) => !serverIds.has(s.session_id))
        return [...serverSessions, ...pending]
      })
    } catch {
      // Keep the last known sidebar if the session list request fails.
    }
  }

  const fetchExplorerSessions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions`)
      const data = await response.json()
      setExplorerSessions(data)
    } catch {
      setExplorerSessions([])
    }
  }

  const fetchSessionDetail = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}`)
      if (!response.ok) {
        setSessionDetail(null)
        return
      }
      const data = await response.json()
      setSessionDetail(data)
    } catch {
      setSessionDetail(null)
    }
  }

  useEffect(() => {
    localStorage.setItem(HIDDEN_SESSIONS_KEY, JSON.stringify(hiddenSessionIds))
  }, [hiddenSessionIds])

  useEffect(() => {
    const handlePopState = () => setCurrentPath(window.location.pathname)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  useEffect(() => {
    if (currentPath === '/chat-session' || currentPath === '/chat-session/') {
      fetchExplorerSessions()
    }
  }, [currentPath])

  useEffect(() => {
    if (currentPath.startsWith('/chat-session/') && currentPath !== '/chat-session') {
      const sessionId = currentPath.replace('/chat-session/', '')
      fetchSessionDetail(sessionId)
    }
  }, [currentPath])

  const lastAssistantIndexForTurn = (currentMessages) => {
    let lastUser = -1
    for (let i = currentMessages.length - 1; i >= 0; i--) {
      if (currentMessages[i].role === 'user') {
        lastUser = i
        break
      }
    }
    for (let i = currentMessages.length - 1; i > lastUser; i--) {
      if (currentMessages[i].role === 'assistant') return i
    }
    return -1
  }

  const resolveAssistantIndex = (currentMessages) => {
    const idx = streamingIndexRef.current
    if (idx !== null && currentMessages[idx]?.role === 'assistant') return idx
    return lastAssistantIndexForTurn(currentMessages)
  }

  const appendToken = (text) => {
    setMessages((prev) => {
      const idx = resolveAssistantIndex(prev)
      if (idx !== -1) {
        streamingIndexRef.current = idx
        const updated = [...prev]
        updated[idx] = { ...prev[idx], text: prev[idx].text + text }
        return updated
      }
      streamingIndexRef.current = prev.length
      return [...prev, { role: 'assistant', text }]
    })
  }

  const finalizeAssistant = (generation) => {
    setMessages((prev) => {
      const idx = resolveAssistantIndex(prev)
      streamingIndexRef.current = null
      if (idx !== -1) {
        const updated = [...prev]
        updated[idx] = { role: 'assistant', text: generation }
        return updated
      }
      const last = prev[prev.length - 1]
      if (last?.role === 'assistant' && last.text === generation) return prev
      return [...prev, { role: 'assistant', text: generation }]
    })
  }

  const connectWebSocket = (sessionId) => {
    if (wsRef.current) {
      const previous = wsRef.current
      wsRef.current = null
      previous.close()
    }

    streamingIndexRef.current = null
    setStage(null)
    sessionIdRef.current = sessionId
    setActiveSessionId(sessionId)

    const url = sessionId ? `${WS_BASE_URL}?session_id=${sessionId}` : WS_BASE_URL
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (wsRef.current === ws) setConnected(true)
    }

    ws.onclose = () => {
      if (wsRef.current !== ws) return
      setConnected(false)
      if (!shouldReconnectRef.current) return
      window.setTimeout(() => {
        if (wsRef.current === ws && shouldReconnectRef.current) {
          connectWebSocket(sessionIdRef.current)
        }
      }, 600)
    }

    ws.onmessage = (event) => {
      if (wsRef.current !== ws) return
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'session':
          sessionIdRef.current = data.session_id
          setActiveSessionId(data.session_id)
          upsertSession(data.session_id)
          break
        case 'stage':
          setStage(data.stage)
          setIsStreaming(true)
          break
        case 'notice':
          setStage(null)
          setIsStreaming(false)
          setMessages((prev) => [...prev, { role: 'notice', text: data.text }])
          break
        case 'token':
          setStage(null)
          setIsStreaming(true)
          appendToken(data.text)
          break
        case 'error':
          setStage(null)
          setIsStreaming(false)
          setMessages((prev) => [...prev, { role: 'notice', text: data.text }])
          break
        case 'done':
          setStage(null)
          setIsStreaming(false)
          finalizeAssistant(data.generation)
          fetchSessions()
          break
        default:
          break
      }
    }
  }

  useEffect(() => {
    shouldReconnectRef.current = true
    fetchSessions()
    connectWebSocket(null)

    return () => {
      shouldReconnectRef.current = false
      wsRef.current?.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, stage])

  const sendMessage = () => {
    const ws = wsRef.current
    if (!input.trim() || !ws || ws.readyState !== WebSocket.OPEN) return

    const text = input.trim()
    streamingIndexRef.current = null
    setMessages((prev) => [...prev, { role: 'user', text }])
    if (sessionIdRef.current) {
      upsertSession(sessionIdRef.current, { title: text.slice(0, 60) })
    }
    ws.send(JSON.stringify({ query: text }))
    setInput('')
  }

  const handleNewChat = () => {
    setMessages([])
    connectWebSocket(null)
  }

  const handleSelectSession = async (sessionId) => {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`)
    const turns = await response.json()
    const history = turns.flatMap((turn) => [
      { role: 'user', text: turn.query },
      { role: 'assistant', text: turn.generation },
    ])
    setMessages(history)
    connectWebSocket(sessionId)
  }

  const handleHideSession = (sessionId) => {
    setHiddenSessionIds((prev) => (prev.includes(sessionId) ? prev : [...prev, sessionId]))
  }

  const handleDeleteSession = async (sessionId) => {
    const confirmed = window.confirm(
      'Delete this chat session permanently from PostgreSQL? This cannot be undone.'
    )
    if (!confirmed) return

    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        return
      }

      setSessions((prev) => prev.filter((session) => session.session_id !== sessionId))
      setExplorerSessions((prev) => prev.filter((session) => session.session_id !== sessionId))
      setSessionDetail((prev) => (prev?.session_id === sessionId ? null : prev))
      setHiddenSessionIds((prev) => prev.filter((id) => id !== sessionId))
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        connectWebSocket(null)
      }
      await fetchSessions()
      await fetchExplorerSessions()
    } catch {
      // Ignore delete errors here; the UI will continue to show the existing saved session.
    }
  }

  const handleIngest = async (event) => {
    const files = event.target.files
    if (!files.length) return

    const formData = new FormData()
    for (const file of files) formData.append('files', file)

    setIngestStatus('Ingesting...')
    const response = await fetch(`${API_BASE_URL}/ingest`, { method: 'POST', body: formData })
    const data = await response.json()
    setIngestStatus(data.status)
  }

  const renderSessionExplorer = () => (
    <SessionExplorer
      sessions={explorerSessions}
      onOpenSession={handleOpenSession}
      onBackToChat={handleBackToChat}
      onDeleteSession={handleDeleteSession}
    />
  )

  const renderSessionDetail = () => (
    <SessionDetail
      session={sessionDetail}
      onBackToExplorer={handleOpenSessionExplorer}
    />
  )

  if (currentPath === '/chat-session' || currentPath === '/chat-session/') {
    return renderSessionExplorer()
  }

  if (currentPath.startsWith('/chat-session/') && currentPath !== '/chat-session') {
    return renderSessionDetail()
  }

  return (
    <ChatWorkspace
      sessions={visibleSessions}
      activeSessionId={activeSessionId}
      connected={connected}
      messages={messages}
      input={input}
      setInput={setInput}
      stage={stage}
      isStreaming={isStreaming}
      ingestStatus={ingestStatus}
      onSelectSession={handleSelectSession}
      onNewChat={handleNewChat}
      onHideSession={handleHideSession}
      onSendMessage={sendMessage}
      onIngest={handleIngest}
      onOpenSessionExplorer={handleOpenSessionExplorer}
    />
  )
}

export default App
