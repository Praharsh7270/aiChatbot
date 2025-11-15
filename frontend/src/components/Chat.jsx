import React, { useState, useEffect, useRef } from 'react'

function Message({m}){
  return (
    <div className={`message ${m.from}`}>
      <div className="message-body">{m.text}</div>
    </div>
  )
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
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages, loading])

  const apiBase = import.meta.env.VITE_API_URL || 'https://aichatbot-9cn1.onrender.com';


  async function sendMessage(){
    if(!input.trim()) return
    const userText = input.trim()
    setInput('')
    setMessages(prev => [...prev, {from: 'user', text: userText}])
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
      setMessages(prev => [...prev, {from: 'bot', text: botText}])
    }catch(err){
      console.error(err)
      setMessages(prev => [...prev, {from: 'bot', text: 'Error: ' + (err.message || 'unknown error')}])
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
          <div className="empty">Say hi — your messages are sent to the backend at <code>{apiBase}</code></div>
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
