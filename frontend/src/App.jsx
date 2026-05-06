import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { v4 as uuidv4 } from 'uuid'
import './index.css'

const API_BASE = '/api'

const SUGGESTIONS = [
  "Latest AI research papers on transformers",
  "Top papers on reinforcement learning 2024",
  "Research papers on climate change AI",
  "Machine learning papers on drug discovery",
]

export default function App() {
  const [threads, setThreads] = useState(() => {
    const saved = localStorage.getItem('rpa_threads')
    return saved ? JSON.parse(saved) : []
  })
  const [activeThreadId, setActiveThreadId] = useState(() => {
    const saved = localStorage.getItem('rpa_active')
    return saved || null
  })
  const [messages, setMessages] = useState([])
  const [papers, setPapers] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Persist threads to localStorage
  useEffect(() => {
    localStorage.setItem('rpa_threads', JSON.stringify(threads))
  }, [threads])

  useEffect(() => {
    if (activeThreadId) {
      localStorage.setItem('rpa_active', activeThreadId)
    }
  }, [activeThreadId])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // ── Handlers ──────────────────────────────────────
  function handleNewChat() {
    const id = uuidv4()
    setActiveThreadId(id)
    setMessages([])
    setPapers([])
    setInput('')
    // Thread will be added on first message
  }

  function selectThread(threadId) {
    setActiveThreadId(threadId)
    // Load messages from thread data
    const thread = threads.find(t => t.id === threadId)
    if (thread) {
      setMessages(thread.messages || [])
      setPapers(thread.papers || [])
    }
  }

  function deleteThread(e, threadId) {
    e.stopPropagation() // Prevent selecting the thread
    const updated = threads.filter(t => t.id !== threadId)
    setThreads(updated)
    // If we deleted the active thread, reset to empty state
    if (threadId === activeThreadId) {
      setActiveThreadId(null)
      setMessages([])
      setPapers([])
      setInput('')
      localStorage.removeItem('rpa_active')
    }
  }

  async function handleSend(messageText) {
    const text = (messageText || input).trim()
    if (!text || loading) return

    let threadId = activeThreadId
    if (!threadId) {
      threadId = uuidv4()
      setActiveThreadId(threadId)
    }

    // Add user message
    const userMsg = { role: 'user', content: text }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    // Add / update thread in sidebar
    setThreads(prev => {
      const exists = prev.find(t => t.id === threadId)
      if (exists) {
        return prev.map(t =>
          t.id === threadId
            ? { ...t, title: t.title, messages: newMessages }
            : t
        )
      }
      return [{ id: threadId, title: text.slice(0, 40), messages: newMessages, papers: [] }, ...prev]
    })

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, thread_id: threadId }),
      })

      if (!res.ok) throw new Error('Server error')

      const data = await res.json()

      const aiMsg = { role: 'assistant', content: data.answer }
      const updatedMessages = [...newMessages, aiMsg]
      const updatedPapers = data.papers || papers

      setMessages(updatedMessages)
      if (data.papers && data.papers.length > 0) {
        setPapers(data.papers)
      }

      // Update thread
      setThreads(prev =>
        prev.map(t =>
          t.id === threadId
            ? { ...t, messages: updatedMessages, papers: updatedPapers }
            : t
        )
      )
    } catch (err) {
      const errorMsg = { role: 'assistant', content: '⚠️ Something went wrong. Please check that the backend is running and try again.' }
      setMessages([...newMessages, errorMsg])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // ── Render ────────────────────────────────────────
  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">📚</div>
            <h1>Research AI</h1>
          </div>
          <button className="new-chat-btn" id="new-chat-btn" onClick={handleNewChat}>
            ＋ New Research Chat
          </button>
        </div>
        <div className="sidebar-threads">
          {threads.map(thread => (
            <div
              key={thread.id}
              className={`thread-item ${thread.id === activeThreadId ? 'active' : ''}`}
              onClick={() => selectThread(thread.id)}
            >
              <span className="thread-item-title">{thread.title || 'New Chat'}</span>
              <button
                className="thread-delete-btn"
                id={`delete-thread-${thread.id}`}
                onClick={(e) => deleteThread(e, thread.id)}
                title="Delete chat"
              >
                🗑
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main chat area */}
      <main className="main">
        <div className="chat-header">
          <h2>Research Paper Assistant</h2>
          <span className="status-badge">● Online</span>
        </div>

        <div className="messages-area" id="messages-area">
          {messages.length === 0 && !loading ? (
            <div className="welcome-screen">
              <div className="welcome-icon">🔬</div>
              <h2>Research Paper Assistant</h2>
              <p>
                Search, discover, and analyze academic research papers powered by AI.
                Ask me about any research topic and I'll find relevant papers for you.
              </p>
              <div className="welcome-suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} className="suggestion-chip" onClick={() => handleSend(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      msg.content
                    )}

                    {/* Show paper cards after the FIRST assistant message with papers */}
                    {msg.role === 'assistant' && papers.length > 0 && i === messages.findIndex(m => m.role === 'assistant') && (
                      <div className="papers-grid">
                        {papers.map((paper, idx) => (
                          <div key={idx} className="paper-card">
                            <div className="paper-card-number">Paper {idx + 1}</div>
                            <h4>{paper.title}</h4>
                            <p>{paper.snippet}</p>
                            <div className="paper-card-meta">
                              {paper.authors && <span>👤 {paper.authors}</span>}
                              {paper.year && <span>📅 {paper.year}</span>}
                            </div>
                            {paper.link && (
                              <a
                                href={paper.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="paper-card-link"
                              >
                                View Paper →
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message assistant">
                  <div className="message-avatar">🤖</div>
                  <div className="message-content">
                    <div className="typing-indicator">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              ref={inputRef}
              className="input-field"
              id="chat-input"
              placeholder="Ask about research papers..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
            />
            <button
              className="send-btn"
              id="send-btn"
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
            >
              ➤
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
