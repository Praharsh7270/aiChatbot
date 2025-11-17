import React, { useState, useEffect, useRef } from 'react'

function TextGeneration({ text, animate = true }){
  const [visible, setVisible] = useState(animate ? '' : text)
  const mounted = useRef(false)

  useEffect(() => {
    if(!animate){
      setVisible(text)
      return
    }

    let i = 0
    const len = text.length
    // If text is very long, don't animate
    if(len > 1200){ setVisible(text); return }

    let cancelled = false
    function step(){
      if(cancelled) return
      i += 2 // reveal 2 chars per tick for decent speed
      setVisible(text.slice(0, i))
      if(i < len){
        const timeout = Math.max(12, 1200 / Math.max(len, 1))
        setTimeout(step, timeout)
      }
    }

    // small delay before starting to look nicer
    const starter = setTimeout(step, 120)

    return () => { cancelled = true; clearTimeout(starter) }
  }, [text, animate])

  return (
    <span className="gen-text">
      {visible}
      {visible !== text && <span className="cursor">▍</span>}
    </span>
  )
}

function Message({ m }) {
  const match = typeof m.text === 'string' && m.text.match(/^\(tool:\s*([^\)]+)\)\s*(.*)/i);
  const tool = match ? match[1] : null;
  const content = match ? match[2] : m.text;

  const animate = m.from === 'bot';

  return (
    <div className={`message ${m.from}`}>
      <div className="message-body">

        {/* TOOL BADGE */}
        {tool && (
          <div className="tool-badge-animated">
            <span className="tool-name">{tool}</span>
            <span className="tool-loading">running…</span>
          </div>
        )}

        {/* MAIN TEXT */}
        {m.from === "user" ? (
          <div className="plain-text">{content}</div>
        ) : (
          <TextGeneration text={content} animate={animate} />
        )}

      </div>
    </div>
  );
}


export default function Chat(){
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [threadId, setThreadId] = useState(() => localStorage.getItem('chat_thread_id') || null)
  const listRef = useRef(null)

  useEffect(() => {
    localStorage.setItem('chat_thread_id', threadId)
  }, [threadId])

  useEffect(() => {
    // autoscroll when messages change
    if(listRef.current){
      // smooth scroll to bottom
      try{ listRef.current.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' }) }catch(e){ listRef.current.scrollTop = listRef.current.scrollHeight }
    }
  }, [messages, loading])

  const apiBase = import.meta.env.VITE_API_URL || 'https://aichatbot-1-i4j2.onrender.com';


  async function sendMessage(){
    if(!input.trim()) return
    const userText = input.trim()
    setInput('')
    setMessages(prev => [...prev, {from: 'user', text: userText, id: Date.now() + Math.random()}])
    setLoading(true)

    try{
      const payload = { user_message: userText, thread_id: threadId || '' }
      const res = await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if(!res.ok){
        // try to get JSON detail or text
        let errText = ''
        try { errText = (await res.json()).detail || JSON.stringify(await res.json()) } catch(e){
          try { errText = await res.text() } catch(e2){ errText = res.statusText }
        }
        throw new Error(errText || 'Server error')
      }
      const data = await res.json()
      const botText = data.response_content || data.response || 'No response'
      const returnedThreadId = data.thread_id || data.threadId || null
      if(returnedThreadId){
        setThreadId(returnedThreadId)
      }
      setMessages(prev => [...prev, {from: 'bot', text: botText, id: Date.now() + Math.random()}])
    }catch(err){
      console.error(err)
  setMessages(prev => [...prev, {from: 'bot', text: 'Error: ' + (err.message || 'unknown error'), id: Date.now() + Math.random()}])
    }finally{
      setLoading(false)
    }
  }

  function handleKey(e){
    if(e.key === 'Enter' && (e.ctrlKey || !e.shiftKey)){
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-container">
      <div className="chat-window" ref={listRef}>
        {messages.length === 0 && (
          <div className="empty">Say hi </div>
        )}
        {messages.map((m, i) => <Message key={i} m={m} />)}
        {loading && <div className="message bot"><div className="message-body">...</div></div>}
      </div>

      <div className="chat-input">
        <textarea
          placeholder="Type a message and press Enter (Ctrl+Enter for newline)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
        />
        <div className="controls">
          <button onClick={sendMessage} disabled={loading || !input.trim()}>Send</button>
        </div>
      </div>
    </div>
  )
}
